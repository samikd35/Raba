"""
BMC Context Loader

Loads and prepares context data for BMC generation.
Extends MVPContextLoader to include VPS v1 and format context for each BMC block.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from src.mvp.utils.context_loader import MVPContextLoader

logger = logging.getLogger(__name__)


class BMCContextLoader:
    """Load context data for BMC generation."""
    
    def __init__(self, vpm_db_adapter, vector_adapter, mvp_db_adapter):
        """
        Initialize BMC context loader.
        
        Args:
            vpm_db_adapter: VPM database adapter for reading project context
            vector_adapter: Vector storage adapter for RAG
            mvp_db_adapter: MVP database adapter for reading VPS v1
        """
        self.mvp_context_loader = MVPContextLoader(vpm_db_adapter, vector_adapter)
        self.mvp_db_adapter = mvp_db_adapter
        self.vpm_db_adapter = vpm_db_adapter
        self.vector_adapter = vector_adapter
        
        logger.info("BMC Context Loader initialized")
    
    async def load_bmc_context(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Load all context needed for BMC generation.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Dictionary with all context data including VPS v1
            
        Raises:
            ValueError: If VPS v1 not found or required data missing
        """
        try:
            logger.info(f"🔍 Loading BMC context for project {project_id}")
            
            # Step 1: Load VPS v1 (REQUIRED for BMC)
            logger.info(f"Step 1: Loading VPS v1...")
            vps_v1 = self.mvp_db_adapter.get_vps_v1(project_id, tenant_id)
            if not vps_v1:
                raise ValueError(
                    f"VPS v1 not found for project {project_id}. "
                    "Please generate VPS v1 before creating BMC."
                )
            logger.info(f"✅ VPS v1 loaded successfully")
            
            # Check for bootstrap mode - use bootstrap context adapter if applicable
            project = self.mvp_db_adapter.get_project(project_id, tenant_id)
            context_mode = project.get('context_mode', 'normal') if project else 'normal'
            
            if context_mode == 'bootstrap':
                logger.info(f"🚀 CONTEXT: Bootstrap mode detected - using bootstrap context adapter for BMC")
                enhanced_context = project.get('enhanced_context', {})
                context_status = project.get('context_status', 'not_started')
                
                # Validate bootstrap context is ready
                if context_status not in ['context_ready', 'context_confirmed']:
                    raise ValueError(
                        f"Bootstrap context not ready (status: {context_status}). "
                        "Please complete the bootstrap process first."
                    )
                
                # Use bootstrap context adapter for BMC
                from src.mvp.bootstrap.adapters.context_adapter import get_bootstrap_context_adapter
                adapter = get_bootstrap_context_adapter()
                bmc_context = adapter.adapt_for_bmc(enhanced_context, vps_v1, project_id, tenant_id)
                
                logger.info(f"✅ Successfully loaded BMC context (bootstrap mode) for project {project_id}")
                return bmc_context
            
            # Step 2: Load base context from VPS context loader (normal mode)
            logger.info(f"Step 2: Loading base context (VPC, personas, research)...")
            base_context = await self.mvp_context_loader.load_vps_context(
                project_id,
                tenant_id
            )
            logger.info(f"✅ Base context loaded with {base_context.get('context_completeness', 0):.2%} completeness")
            
            # Step 3: Combine VPS v1 with base context
            logger.info(f"Step 3: Combining VPS v1 with base context...")
            bmc_context = {
                **base_context,
                "vps_v1": vps_v1,
                "loaded_for": "bmc_generation",
                "loaded_at": datetime.utcnow().isoformat()
            }
            
            # Validate context completeness
            completeness = bmc_context.get('context_completeness', 0.0)
            if completeness < 0.5:
                logger.warning(f"Low context completeness: {completeness:.2%}")
                raise ValueError(
                    f"Insufficient context for BMC generation (completeness: {completeness:.2%}). "
                    "Please ensure VPC 2.0, personas, and field research are completed."
                )
            
            logger.info(f"✅ Successfully loaded BMC context for project {project_id}")
            logger.info(f"Context includes:")
            logger.info(f"  - VPS v1: {bool(vps_v1)}")
            logger.info(f"  - Customer Profile: {bool(bmc_context.get('customer_profile'))}")
            logger.info(f"  - Value Map: {bool(bmc_context.get('value_map'))}")
            logger.info(f"  - Personas: {len(bmc_context.get('personas', []))}")
            logger.info(f"  - Hypotheses: {len(bmc_context.get('hypotheses', []))}")
            logger.info(f"  - Assumptions: {len(bmc_context.get('assumptions', []))}")
            logger.info(f"  - PV Report Insights: {len(bmc_context.get('pv_report_insights', []))}")
            logger.info(f"  - Market Research Analysis: {len(bmc_context.get('market_research_analysis', []))}")
            
            return bmc_context
            
        except Exception as e:
            logger.error(f"❌ Error loading BMC context: {e}")
            raise
    
    def format_context_for_block(
        self,
        context: Dict[str, Any],
        block_name: str,
        previous_blocks: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format context for specific BMC block generation.
        
        Args:
            context: Base context from load_bmc_context
            block_name: Name of block being generated
            previous_blocks: Previously generated blocks (for sequential context)
            
        Returns:
            Formatted context string for AI prompt
        """
        sections = []
        
        # Project Overview
        sections.append(f"# PROJECT: {context.get('project_name', 'N/A')}")
        if context.get('project_description'):
            sections.append(f"**Description:** {context['project_description']}\n")
        
        sections.append("---")
        sections.append("# VALUE PROPOSITION STATEMENT (VPS v1) - PRIMARY INPUT\n")
        
        # VPS v1 (Primary Input)
        vps_v1 = context.get('vps_v1', {})
        if vps_v1:
            sections.append("## Primary Statement")
            # Handle both structured (dict) and legacy (string) primary_statement formats
            primary_stmt = vps_v1.get('primary_statement', 'N/A')
            if isinstance(primary_stmt, dict):
                primary_text = " ".join([
                    primary_stmt.get('our', ''),
                    primary_stmt.get('help', ''),
                    primary_stmt.get('who_want_to', ''),
                    primary_stmt.get('by', ''),
                    primary_stmt.get('and', ''),
                    primary_stmt.get('unlike', '')
                ]).strip() or 'N/A'
            else:
                primary_text = primary_stmt
            sections.append(primary_text)
            sections.append("")
            
            sections.append("## Extended Statement")
            sections.append(vps_v1.get('extended_statement', 'N/A'))
            sections.append("")
            
            sections.append("## Key Differentiators")
            differentiators = vps_v1.get('key_differentiators', [])
            for idx, diff in enumerate(differentiators, 1):
                sections.append(f"{idx}. **{diff.get('title', 'N/A')}**: {diff.get('description', 'N/A')}")
            sections.append("")
        
        sections.append("---")
        sections.append("# VALUE PROPOSITION CANVAS (VPC 2.0)\n")
        
        # Use the existing MVPContextLoader's format_context_for_prompt method
        # to get VPC, personas, and research formatted
        formatted_base = self.mvp_context_loader.format_context_for_prompt(context)
        
        # Extract VPC and research sections from formatted base
        # (Skip project header since we already added it)
        base_lines = formatted_base.split('\n')
        vpc_start = False
        for line in base_lines:
            if 'VALUE PROPOSITION CANVAS' in line or vpc_start:
                vpc_start = True
                sections.append(line)
        
        # Add previously generated BMC blocks
        if previous_blocks:
            sections.append("\n---")
            sections.append("# PREVIOUSLY GENERATED BMC BLOCKS\n")
            sections.append(f"**Current Block Being Generated:** {block_name}")
            sections.append("**Use these blocks as context for consistency and cross-referencing**\n")
            
            # Format each previous block
            block_order = [
                'customer_segments',
                'value_propositions',
                'channels',
                'customer_relationships',
                'revenue_streams',
                'key_resources',
                'key_activities',
                'key_partnerships',
                'cost_structure'
            ]
            
            for block_key in block_order:
                if block_key in previous_blocks and previous_blocks[block_key]:
                    block_data = previous_blocks[block_key]
                    block_title = block_key.replace('_', ' ').title()
                    sections.append(f"## {block_title}")
                    sections.append(f"```json")
                    import json
                    sections.append(json.dumps(block_data, indent=2))
                    sections.append(f"```")
                    sections.append("")
        
        sections.append("\n---")
        sections.append(f"\n**GENERATE {block_name.upper().replace('_', ' ')} NOW** based on this context.\n")
        
        return "\n".join(sections)
