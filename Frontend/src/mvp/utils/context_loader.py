"""
Context Loader for MVP Module

Loads and prepares context data for AI agents from VPM project data.
Integrates with vector storage for RAG-based context enrichment.

Note: Uses VPM adapter for reading VPC/persona/field prep data (read-only).
MVP adapter is used only for writing MVP-specific data.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json
import numpy as np

logger = logging.getLogger(__name__)


class MVPContextLoader:
    """Load context data for MVP generation."""
    
    def __init__(self, vpm_db_adapter, vector_adapter):
        """
        Initialize context loader.
        
        Args:
            vpm_db_adapter: VPM database adapter for reading project context (YubaDatabaseAdapter)q
            vector_adapter: Vector storage adapter instance for RAG
        """
        self.vpm_db_adapter = vpm_db_adapter
        self.vector_adapter = vector_adapter
    
    async def load_vps_context(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Load all context needed for VPS generation.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Dictionary with all context data
            
        Raises:
            ValueError: If project not found or required data missing
        """
        try:
            logger.info(f"Loading VPS context for project {project_id}")
            
            # Get project details from VPM adapter (read-only)
            logger.info(f"🔍 CONTEXT: Fetching project details...")
            project = await self.vpm_db_adapter.get_project_detail(project_id, tenant_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Extract components for normal workflow check
            vpc_data = project.get('vpc_data', {}) or {}
            vpc_v2_data = project.get('vpc_v2_data', {}) or {}
            personas = project.get('personas', []) or []
            field_prep_data = project.get('field_prep_data', {}) or {}
            enhanced_context = project.get('enhanced_context', {}) or {}
            
            # Debug: Log enhanced_context structure
            logger.info(f"🔍 CONTEXT: enhanced_context type: {type(enhanced_context)}")
            logger.info(f"🔍 CONTEXT: enhanced_context keys: {list(enhanced_context.keys()) if isinstance(enhanced_context, dict) else 'not a dict'}")
            if isinstance(enhanced_context, dict):
                logger.info(f"🔍 CONTEXT: enhanced_context.draft exists: {enhanced_context.get('draft') is not None}")
                logger.info(f"🔍 CONTEXT: enhanced_context.confirmed exists: {enhanced_context.get('confirmed') is not None}")
            
            # Determine which context source to use based on actual data presence
            # Priority 1: Normal workflow (VPC data + Personas)
            has_normal_workflow_data = self._has_normal_workflow_data(vpc_data, vpc_v2_data, personas)
            
            # Priority 2: Bootstrap workflow (enhanced_context with draft)
            has_bootstrap_data = self._has_bootstrap_data(enhanced_context)
            
            logger.info(f"🔍 CONTEXT: Normal workflow data present: {has_normal_workflow_data}")
            logger.info(f"🔍 CONTEXT: Bootstrap data present: {has_bootstrap_data}")
            
            # Decision: Use normal workflow if data exists, otherwise try bootstrap
            if has_normal_workflow_data:
                logger.info(f"✅ CONTEXT: Using normal workflow context (VPC + Personas)")
                return await self._load_normal_workflow_context(
                    project, project_id, tenant_id, vpc_data, vpc_v2_data, personas, field_prep_data
                )
            elif has_bootstrap_data:
                logger.info(f"� CONTEXT: Using bootstrap context (enhanced_context)")
                return self._load_bootstrap_context(enhanced_context, project, project_id, tenant_id)
            else:
                # Neither workflow has sufficient data
                raise ValueError(
                    "No valid context found. Please either:\n"
                    "1. Complete VPC 2.0 workflow (personas + customer profile), or\n"
                    "2. Complete bootstrap workflow (enhanced context generation)"
                )
            
        except Exception as e:
            logger.error(f"❌ Error loading VPS context: {e}")
            raise
    
    def _has_normal_workflow_data(
        self,
        vpc_data: Dict[str, Any],
        vpc_v2_data: Dict[str, Any],
        personas: List[Dict[str, Any]]
    ) -> bool:
        """
        Check if project has sufficient normal workflow data for VPS generation.
        
        Normal workflow requires:
        - VPC data (customer_profile or value_map) AND
        - At least one persona
        """
        # Check for VPC data in either location
        has_vpc_data = bool(
            vpc_data.get('customer_profile') or
            vpc_data.get('value_map_selections') or
            vpc_data.get('value_map') or
            vpc_v2_data.get('customer_profile') or
            vpc_v2_data.get('value_map_selections')
        )
        
        has_personas = len(personas) > 0
        
        return has_vpc_data and has_personas
    
    def _has_bootstrap_data(self, enhanced_context: Dict[str, Any]) -> bool:
        """
        Check if project has sufficient bootstrap data for VPS generation.
        
        Bootstrap workflow requires:
        - enhanced_context with draft OR confirmed data
        - Context status should be ready (but we check data presence primarily)
        """
        if not enhanced_context:
            return False
        
        # Check for draft or confirmed context
        draft = enhanced_context.get('draft')
        confirmed = enhanced_context.get('confirmed')
        
        # Either draft or confirmed should have content
        has_context_data = bool(draft or confirmed)
        
        # Check metadata for readiness (optional but good to verify)
        metadata = enhanced_context.get('metadata', {})
        context_mode = metadata.get('context_mode', '')
        
        return has_context_data
    
    async def _load_normal_workflow_context(
        self,
        project: Dict[str, Any],
        project_id: str,
        tenant_id: str,
        vpc_data: Dict[str, Any],
        vpc_v2_data: Dict[str, Any],
        personas: List[Dict[str, Any]],
        field_prep_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Load context from normal VPC workflow data.
        """
        # Merge VPC data (v2 takes precedence)
        effective_vpc_data = vpc_v2_data if vpc_v2_data.get('customer_profile') else vpc_data
        
        # Load PV report content via vector search
        pv_report_context = await self._load_pv_report_context(project_id, tenant_id)
        
        # Load actionable insights
        insights_context = await self._load_insights_context(project_id, tenant_id)
        
        # Load market research analysis data
        analysis_context = await self._load_market_research_analysis(project_id, tenant_id)
        
        # Prepare structured context
        context = {
            "project_id": project_id,
            "project_name": project.get('name'),
            "project_description": project.get('description'),
            "context_mode": "normal",
            
            # VPC 2.0 Data - Handle both formats
            "customer_profile": effective_vpc_data.get('customer_profile', {}),
            "value_map": effective_vpc_data.get('value_map_selections') or effective_vpc_data.get('value_map', {}),
            
            # Personas (all personas for unified VPS)
            "personas": personas,
            "persona_count": len(personas),
            "primary_persona": self._get_primary_persona(personas),
            
            # Field Research
            "hypotheses": field_prep_data.get('hypotheses', []),
            "assumptions": field_prep_data.get('assumptions', []),
            "validation_results": field_prep_data.get('validation_results', {}),
            
            # Market Evidence
            "pv_report_insights": pv_report_context,
            "actionable_insights": insights_context,
            "market_research_analysis": analysis_context,
            
            # Metadata
            "loaded_at": datetime.utcnow().isoformat(),
            "context_completeness": self._calculate_completeness(
                effective_vpc_data, personas, field_prep_data, pv_report_context
            )
        }
        
        logger.info(f"✅ Successfully loaded normal workflow context for project {project_id}")
        logger.info(f"Context completeness: {context['context_completeness']:.2%}")
        
        return context
    
    def _load_bootstrap_context(
        self,
        enhanced_context: Dict[str, Any],
        project: Dict[str, Any],
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Load context from bootstrap enhanced_context using the adapter.
        """
        # Get context status for validation
        context_status = project.get('context_status', 'not_started')
        
        # Validate bootstrap context is ready
        if context_status not in ['context_ready', 'context_confirmed']:
            raise ValueError(
                f"Bootstrap context not ready (status: {context_status}). "
                "Please complete the bootstrap process first."
            )
        
        # Use bootstrap context adapter to transform enhanced_context
        from src.mvp.bootstrap.adapters.context_adapter import get_bootstrap_context_adapter
        adapter = get_bootstrap_context_adapter()
        
        context = adapter.adapt_for_vps(enhanced_context, project_id, tenant_id)
        
        logger.info(f"✅ Successfully loaded bootstrap context for project {project_id}")
        logger.info(f"Context completeness: {context.get('context_completeness', 0):.2%}")
        
        return context
    
    async def load_vps_context_for_persona(
        self,
        project_id: str,
        tenant_id: str,
        persona: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Load context for VPS generation for a specific persona.
        
        This method loads persona-specific context including:
        - The specific persona details
        - VPC data relevant to this persona
        - Persona-specific field research
        - Persona-tagged market research analysis
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            persona: Single persona dictionary with id, name, description, etc.
            
        Returns:
            Dictionary with persona-specific context
            
        Raises:
            ValueError: If project not found or required data missing
        """
        try:
            persona_id = persona.get('id') or persona.get('persona_id')
            persona_name = persona.get('name') or persona.get('persona_name', 'Unknown')
            logger.info(f"Loading VPS context for persona: {persona_name} (ID: {persona_id})")
            
            # Get project details from VPM adapter (read-only)
            project = await self.vpm_db_adapter.get_project_detail(project_id, tenant_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Extract components
            vpc_data = project.get('vpc_data', {})
            field_prep_data = project.get('field_prep_data', {})
            pv_report_id = project.get('pv_report_id')
            
            # Load PV report context (shared across personas)
            pv_report_context = await self._load_pv_report_context(
                project_id,
                tenant_id
            )
            
            # Load actionable insights (shared)
            insights_context = await self._load_insights_context(
                project_id,
                tenant_id
            )
            
            # Load persona-specific market research analysis
            analysis_context = await self._load_analysis_context_for_persona(
                project_id,
                tenant_id,
                persona_id
            )
            
            # Filter field prep for this persona
            persona_field_prep = self._filter_field_prep_for_persona(
                field_prep_data,
                persona_id
            )
            
            # Build context
            context = {
                'project_id': project_id,
                'project_name': project.get('name', ''),
                'project_description': project.get('description', ''),
                'persona': persona,  # Single persona
                'persona_id': persona_id,
                'persona_name': persona_name,
                'vpc_data': vpc_data,
                'field_prep_data': persona_field_prep,
                'pv_report_context': pv_report_context,
                'insights_context': insights_context,
                'analysis_context': analysis_context
            }
            
            # Calculate context completeness for this persona
            context['context_completeness'] = self._calculate_completeness(
                context['vpc_data'],
                [context['persona']],
                context['field_prep_data'],
                context['pv_report_context']
            )
            
            logger.info(f"✅ Loaded persona-specific context for {persona_name}: {context['context_completeness']:.2%} complete")
            
            return context
            
        except Exception as e:
            logger.error(f"❌ Error loading VPS context for persona: {e}")
            raise
    
    async def _load_pv_report_context(
        self,
        project_id: str,
        tenant_id: str,
        max_chunks: int = 10
    ) -> List[Dict[str, Any]]:
        """Load relevant PV report chunks via vector search."""
        try:
            # Use dual_context_search like other VPM services
            query = "value proposition customer needs pain points solutions benefits market opportunity"
            
            context = await self.vector_adapter.dual_context_search(
                project_id=project_id,
                query=query,
                max_results_per_store=max_chunks
            )
            
            # Extract PV report context
            pv_chunks = context.get('pv_report_context', []) if context else []
            logger.info(f"✅ Loaded {len(pv_chunks)} PV report chunks")
            return pv_chunks
            
        except Exception as e:
            logger.warning(f"Error loading PV report context: {e}")
            return []
    
    async def _load_insights_context(
        self,
        project_id: str,
        tenant_id: str,
        max_chunks: int = 5
    ) -> List[Dict[str, Any]]:
        """Load actionable insights via vector search."""
        try:
            # Use dual_context_search like other VPM services
            query = "actionable insights recommendations opportunities market entry strategy"
            
            context = await self.vector_adapter.dual_context_search(
                project_id=project_id,
                query=query,
                max_results_per_store=max_chunks
            )
            
            # Extract actionable insights context
            insights = context.get('actionable_insights_context', []) if context else []
            logger.info(f"✅ Loaded {len(insights)} actionable insight chunks")
            return insights
            
        except Exception as e:
            logger.warning(f"Error loading insights context: {e}")
            return []
    
    async def _load_market_research_analysis(
        self,
        project_id: str,
        tenant_id: str,
        max_chunks: int = 10
    ) -> List[Dict[str, Any]]:
        """
        🎭 MULTI-PERSONA: Load market research analysis report chunks from ALL personas.
        
        This retrieves chunks from the embedded market research analysis reports
        for all personas in the project. Each chunk is tagged with its persona_id.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            max_chunks: Maximum number of chunks to retrieve (per persona)
            
        Returns:
            List of relevant analysis chunks with content and metadata from all personas
        """
        try:
            logger.info(f"📊 Loading market research analysis context for project {project_id}")
            
            # Import chunk storage service
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            
            # 🎭 Get all analysis report chunks for this project (all personas)
            chunk_service = get_chunk_storage_service()
            all_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            # Filter for analysis_report chunks only
            all_chunks = [
                chunk for chunk in all_chunks 
                if chunk.get('metadata', {}).get('source_type') == 'analysis_report'
            ]
            
            if not all_chunks:
                logger.info(f"No market research analysis chunks found for project {project_id}")
                return []
            
            # 🎭 Group chunks by persona_id
            persona_chunks = {}
            for chunk_data in all_chunks:
                persona_id = chunk_data.get('metadata', {}).get('persona_id', 'default')
                if persona_id not in persona_chunks:
                    persona_chunks[persona_id] = []
                persona_chunks[persona_id].append(chunk_data)
            
            logger.info(f"Found {len(all_chunks)} analysis report chunks across {len(persona_chunks)} persona(s)")
            for pid, chunks in persona_chunks.items():
                logger.info(f"  - Persona '{pid}': {len(chunks)} chunks")
            
            # Generate query embedding for value proposition context
            query = "value proposition customer insights pain points gains solutions market analysis competitive advantage"
            
            from src.mint.api.services.ai.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            query_embeddings = await embedding_service.generate_embeddings([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
            
            if not query_embedding:
                logger.warning("Failed to generate query embedding for analysis context")
                return []
            
            # 🎭 Calculate similarity scores for ALL personas' chunks
            all_scored_chunks = []
            for persona_id, chunks in persona_chunks.items():
                for chunk_data in chunks:
                    # Get chunk embedding
                    raw_embedding = chunk_data.get('embedding')
                    if raw_embedding and isinstance(raw_embedding, str):
                        try:
                            chunk_embedding = json.loads(raw_embedding)
                        except:
                            continue
                    elif isinstance(raw_embedding, list):
                        chunk_embedding = raw_embedding
                    else:
                        continue
                    
                    # Calculate cosine similarity
                    try:
                        similarity = np.dot(query_embedding, chunk_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                        )
                        
                        all_scored_chunks.append({
                            'content': chunk_data.get('content', ''),
                            'similarity': float(similarity),
                            'metadata': chunk_data.get('metadata', {}),
                            'section': chunk_data.get('metadata', {}).get('section', 'unknown'),
                            'persona_id': persona_id  # 🎭 Track which persona this chunk belongs to
                        })
                    except Exception as e:
                        logger.warning(f"Failed to calculate similarity: {e}")
                        continue
            
            # Sort by similarity and take top chunks from ALL personas
            all_scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            top_chunks = all_scored_chunks[:max_chunks * len(persona_chunks)]  # Get more chunks when multiple personas
            
            # Filter by relevance threshold and include persona_id
            relevant_chunks = [
                {
                    "content": chunk['content'],
                    "relevance_score": chunk['similarity'],
                    "section": chunk['section'],
                    "persona_id": chunk['persona_id'],  # 🎭 Include persona identifier
                    "source": "market_research_analysis"
                }
                for chunk in top_chunks if chunk['similarity'] > 0.7
            ]
            
            # Log distribution by persona
            persona_distribution = {}
            for chunk in relevant_chunks:
                pid = chunk['persona_id']
                persona_distribution[pid] = persona_distribution.get(pid, 0) + 1
            
            logger.info(f"✅ Retrieved {len(relevant_chunks)} relevant analysis chunks (threshold: 0.7)")
            logger.info(f"🎭 Chunk distribution by persona: {persona_distribution}")
            
            return relevant_chunks
            
        except Exception as e:
            logger.warning(f"Error loading market research analysis context: {e}")
            return []
    
    async def _load_analysis_context_for_persona(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: str,
        max_chunks: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Load persona-specific market research analysis chunks.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            persona_id: Specific persona ID to filter for
            max_chunks: Maximum chunks to return
            
        Returns:
            List of analysis chunks for this persona
        """
        try:
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            
            # Get all chunks for project
            chunk_service = get_chunk_storage_service()
            all_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            # Filter for analysis_report chunks for this persona
            persona_chunks = [
                chunk for chunk in all_chunks
                if (chunk.get('metadata', {}).get('source_type') == 'analysis_report' and
                    chunk.get('metadata', {}).get('persona_id') == persona_id)
            ]
            
            logger.info(f"Found {len(persona_chunks)} analysis chunks for persona {persona_id}")
            
            if not persona_chunks:
                return []
            
            # Generate query embedding
            query = "value proposition customer insights pain points gains solutions market analysis competitive advantage"
            
            from src.mint.api.services.ai.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            query_embeddings = await embedding_service.generate_embeddings([query])
            query_embedding = query_embeddings[0] if query_embeddings else None
            
            if not query_embedding:
                return []
            
            # Calculate similarity scores
            scored_chunks = []
            for chunk_data in persona_chunks:
                raw_embedding = chunk_data.get('embedding')
                if raw_embedding and isinstance(raw_embedding, str):
                    try:
                        chunk_embedding = json.loads(raw_embedding)
                    except:
                        continue
                elif isinstance(raw_embedding, list):
                    chunk_embedding = raw_embedding
                else:
                    continue
                
                try:
                    similarity = np.dot(query_embedding, chunk_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                    )
                    
                    scored_chunks.append({
                        'content': chunk_data.get('content', ''),
                        'similarity': float(similarity),
                        'metadata': chunk_data.get('metadata', {}),
                        'section': chunk_data.get('metadata', {}).get('section', 'unknown')
                    })
                except Exception as e:
                    continue
            
            # Sort and filter
            scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            top_chunks = scored_chunks[:max_chunks]
            
            relevant_chunks = [
                {
                    "content": chunk['content'],
                    "relevance_score": chunk['similarity'],
                    "section": chunk['section'],
                    "source": "market_research_analysis"
                }
                for chunk in top_chunks if chunk['similarity'] > 0.7
            ]
            
            logger.info(f"✅ Retrieved {len(relevant_chunks)} relevant analysis chunks for persona {persona_id}")
            
            return relevant_chunks
            
        except Exception as e:
            logger.warning(f"Error loading persona-specific analysis context: {e}")
            return []
    
    def _filter_field_prep_for_persona(
        self,
        field_prep_data: Dict[str, Any],
        persona_id: str
    ) -> Dict[str, Any]:
        """
        Filter field prep data for specific persona.
        
        Args:
            field_prep_data: Full field prep data
            persona_id: Persona ID to filter for
            
        Returns:
            Filtered field prep data containing only this persona's data
        """
        if not field_prep_data:
            return {}
        
        filtered_data = {}
        
        # Filter hypotheses for this persona
        hypotheses = field_prep_data.get('hypotheses', [])
        persona_hypotheses = [
            h for h in hypotheses
            if h.get('persona_id') == persona_id
        ]
        
        if persona_hypotheses:
            filtered_data['hypotheses'] = persona_hypotheses
            
            # Extract assumptions from persona's hypotheses
            all_assumptions = []
            for hypothesis in persona_hypotheses:
                assumptions = hypothesis.get('assumptions', [])
                all_assumptions.extend(assumptions)
            
            if all_assumptions:
                filtered_data['assumptions'] = all_assumptions
        
        logger.info(f"Filtered field prep for persona {persona_id}: {len(persona_hypotheses)} hypotheses, {len(filtered_data.get('assumptions', []))} assumptions")
        
        return filtered_data
    
    def _get_primary_persona(self, personas: List[Dict]) -> Optional[Dict]:
        """Get the primary persona (first one or marked as primary)."""
        if not personas:
            return None
        
        # Look for persona marked as primary payer
        for persona in personas:
            if persona.get('is_primary_payer', False):
                return persona
        
        # Return first persona if none marked as primary
        return personas[0]
    
    def _calculate_completeness(
        self,
        vpc_data: Dict,
        personas: List,
        field_prep_data: Dict,
        pv_insights: List
    ) -> float:
        """Calculate context completeness score (0.0-1.0)."""
        score = 0.0
        
        # VPC Data (40%) - Handle both old and new VPC 2.0 formats
        customer_profile = vpc_data.get('customer_profile', {})
        # VPC 2.0 stores value map as 'value_map_selections', not 'value_map'
        value_map = vpc_data.get('value_map_selections') or vpc_data.get('value_map') or {}
        
        if customer_profile.get('jobs_to_be_done'):
            score += 0.15
        if customer_profile.get('pains'):
            score += 0.10
        if customer_profile.get('gains'):
            score += 0.15
        
        # Check value_map with safe access
        if value_map and value_map.get('products_services'):
            score += 0.10
        if value_map and value_map.get('pain_relievers'):
            score += 0.10
        if value_map and value_map.get('gain_creators'):
            score += 0.10
        
        # Personas (20%)
        if personas:
            score += 0.20
        
        # Field Research (20%)
        if field_prep_data.get('hypotheses'):
            score += 0.10
        if field_prep_data.get('assumptions'):
            score += 0.10
        
        # Market Evidence (20%)
        if pv_insights:
            score += 0.20
        
        return round(score, 2)
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format context data into a structured prompt string following VPC framework.
        
        Args:
            context: Context dictionary from load_vps_context
            
        Returns:
            Formatted context string for AI prompt with VPC structure
        """
        sections = []
        
        # Project Overview
        sections.append(f"# Project: {context['project_name']}")
        if context.get('project_description'):
            sections.append(f"**Description:** {context['project_description']}\n")
        
        # Target Customers (Personas)
        personas = context.get('personas', [])
        persona_count = context.get('persona_count', len(personas))
        
        if persona_count == 1:
            # Single persona
            primary_persona = context.get('primary_persona') or personas[0]
            sections.append("# Target Customer (Persona)")
            sections.append(f"**Name:** {primary_persona.get('name', 'N/A')}")
            sections.append(f"**Description:** {primary_persona.get('description', 'N/A')}")
            if primary_persona.get('problem_relationship'):
                sections.append(f"**Relationship to Problem:** {primary_persona['problem_relationship']}")
            sections.append("")
        elif persona_count == 2:
            # Multiple personas - show both for unified VPS
            sections.append("# Target Customers (Multiple Personas)")
            sections.append("*Note: The Value Proposition Statement will encompass BOTH personas in a unified statement*")
            sections.append("")
            
            for idx, persona in enumerate(personas, 1):
                sections.append(f"## Persona {idx}: {persona.get('name', 'N/A')}")
                sections.append(f"**Description:** {persona.get('description', 'N/A')}")
                if persona.get('problem_relationship'):
                    sections.append(f"**Relationship to Problem:** {persona['problem_relationship']}")
                if persona.get('is_primary_payer'):
                    sections.append(f"**Role:** Primary Payer (Decision Maker)")
                sections.append("")
        
        sections.append("---")
        sections.append("# VALUE PROPOSITION CANVAS (VPC)")
        sections.append("")
        
        # Customer Profile (Right Side of VPC)
        customer_profile = context.get('customer_profile', {})
        if customer_profile:
            sections.append("## CUSTOMER PROFILE (Right Side)")
            sections.append("")
            
            # Jobs-to-be-Done
            jtbd_list = customer_profile.get('jobs_to_be_done', [])
            if jtbd_list:
                sections.append("### Jobs-to-be-Done")
                sections.append("*Tasks the customer is trying to accomplish (functional, social, emotional)*")
                for idx, jtbd in enumerate(jtbd_list, 1):
                    text = jtbd.get('text') or jtbd.get('description', 'N/A')
                    sections.append(f"{idx}. **{text}**")
                    if jtbd.get('evidence'):
                        sections.append(f"   - Evidence: {jtbd['evidence']}")
                    if jtbd.get('priority'):
                        sections.append(f"   - Priority: {jtbd['priority']}")
                sections.append("")
            
            # Pains
            pains_list = customer_profile.get('pains', [])
            if pains_list:
                sections.append("### Pains")
                sections.append("*Negative outcomes, risks, and obstacles the customer experiences*")
                for idx, pain in enumerate(pains_list, 1):
                    text = pain.get('text') or pain.get('description', 'N/A')
                    sections.append(f"{idx}. **{text}**")
                    if pain.get('evidence'):
                        sections.append(f"   - Evidence: {pain['evidence']}")
                    if pain.get('severity') or pain.get('priority'):
                        severity = pain.get('severity') or pain.get('priority', 'N/A')
                        sections.append(f"   - Severity: {severity}")
                sections.append("")
            
            # Gains
            gains_list = customer_profile.get('gains', [])
            if gains_list:
                sections.append("### Gains (Desired Outcomes)")
                sections.append("*Benefits and outcomes the customer wants to achieve*")
                for idx, gain in enumerate(gains_list, 1):
                    text = gain.get('text') or gain.get('description', 'N/A')
                    sections.append(f"{idx}. **{text}**")
                    if gain.get('evidence'):
                        sections.append(f"   - Evidence: {gain['evidence']}")
                    if gain.get('importance') or gain.get('priority'):
                        importance = gain.get('importance') or gain.get('priority', 'N/A')
                        sections.append(f"   - Importance: {importance}")
                sections.append("")
        
        # Value Map (Left Side of VPC)
        value_map = context.get('value_map', {})
        if value_map:
            sections.append("## VALUE MAP (Left Side)")
            sections.append("")
            
            # Products & Services
            products = value_map.get('products_services', [])
            if products:
                sections.append("### Products & Services")
                sections.append("*What we offer to help customers complete their jobs*")
                for idx, product in enumerate(products, 1):
                    text = product.get('text') or product.get('description', 'N/A')
                    sections.append(f"{idx}. **{text}**")
                    if product.get('addresses_jtbd'):
                        jtbd_refs = product['addresses_jtbd']
                        if isinstance(jtbd_refs, list):
                            sections.append(f"   - Addresses Jobs: {', '.join(jtbd_refs)}")
                    if product.get('evidence'):
                        sections.append(f"   - Evidence: {product['evidence']}")
                    if product.get('priority'):
                        sections.append(f"   - Priority: {product['priority']}")
                sections.append("")
            
            # Pain Relievers
            relievers = value_map.get('pain_relievers', [])
            if relievers:
                sections.append("### Pain Relievers")
                sections.append("*How we alleviate specific customer pains*")
                for idx, reliever in enumerate(relievers, 1):
                    text = reliever.get('text') or reliever.get('description', 'N/A')
                    sections.append(f"{idx}. **{text}**")
                    if reliever.get('addresses_pain'):
                        pain_refs = reliever['addresses_pain']
                        if isinstance(pain_refs, list):
                            sections.append(f"   - Relieves Pains: {', '.join(pain_refs)}")
                    if reliever.get('impact'):
                        sections.append(f"   - Impact: {reliever['impact']}")
                    if reliever.get('evidence'):
                        sections.append(f"   - Evidence: {reliever['evidence']}")
                    if reliever.get('priority'):
                        sections.append(f"   - Priority: {reliever['priority']}")
                sections.append("")
            
            # Gain Creators
            creators = value_map.get('gain_creators', [])
            if creators:
                sections.append("### Gain Creators")
                sections.append("*How we create desired customer gains*")
                for idx, creator in enumerate(creators, 1):
                    text = creator.get('text') or creator.get('description', 'N/A')
                    sections.append(f"{idx}. **{text}**")
                    if creator.get('creates_gain'):
                        gain_refs = creator['creates_gain']
                        if isinstance(gain_refs, list):
                            sections.append(f"   - Creates Gains: {', '.join(gain_refs)}")
                    if creator.get('value'):
                        sections.append(f"   - Value: {creator['value']}")
                    if creator.get('evidence'):
                        sections.append(f"   - Evidence: {creator['evidence']}")
                    if creator.get('priority'):
                        sections.append(f"   - Priority: {creator['priority']}")
                sections.append("")
        
        sections.append("---")
        
        # Validated Assumptions from Field Research
        assumptions = context.get('assumptions', [])
        if assumptions:
            sections.append("# VALIDATED ASSUMPTIONS (Field Research)")
            for idx, assumption in enumerate(assumptions[:5], 1):
                text = assumption.get('assumption_text') or assumption.get('description', 'N/A')
                sections.append(f"{idx}. {text}")
            sections.append("")
        
        # Market Evidence from PV Report
        pv_insights = context.get('pv_report_insights', [])
        if pv_insights:
            sections.append("# MARKET RESEARCH EVIDENCE (PV Report)")
            for idx, insight in enumerate(pv_insights[:5], 1):
                if insight.get('relevance_score', 0) > 0.7:
                    content = insight['content'][:300]
                    sections.append(f"{idx}. {content}")
                    if insight.get('relevance_score'):
                        sections.append(f"   (Relevance: {insight['relevance_score']:.2f})")
            sections.append("")
        
        # Actionable Insights
        actionable = context.get('actionable_insights', [])
        if actionable:
            sections.append("# STRATEGIC OPPORTUNITIES (Actionable Insights)")
            for idx, insight in enumerate(actionable[:3], 1):
                if insight.get('relevance_score', 0) > 0.7:
                    content = insight['content'][:250]
                    sections.append(f"{idx}. {content}")
            sections.append("")
        
        # 🎭 Market Research Analysis (MULTI-PERSONA)
        analysis_chunks = context.get('market_research_analysis', [])
        if analysis_chunks:
            sections.append("# MARKET RESEARCH ANALYSIS INSIGHTS")
            sections.append("*Key findings from comprehensive market research analysis across all personas*")
            sections.append("")
            
            # Group chunks by persona for better organization
            persona_chunks = {}
            for chunk in analysis_chunks:
                persona_id = chunk.get('persona_id', 'default')
                if persona_id not in persona_chunks:
                    persona_chunks[persona_id] = []
                persona_chunks[persona_id].append(chunk)
            
            # Display chunks organized by persona
            chunk_idx = 1
            for persona_id, chunks in persona_chunks.items():
                if len(persona_chunks) > 1:
                    # Multi-persona: show persona header
                    sections.append(f"## Persona: {persona_id}")
                
                for chunk in chunks[:8]:  # Limit per persona
                    if chunk.get('relevance_score', 0) > 0.7:
                        content = chunk['content'][:350]
                        section = chunk.get('section', 'General')
                        sections.append(f"{chunk_idx}. [{section}] {content}")
                        if chunk.get('relevance_score'):
                            sections.append(f"   (Relevance: {chunk['relevance_score']:.2f})")
                        chunk_idx += 1
                
                if len(persona_chunks) > 1:
                    sections.append("")  # Spacing between personas
            
            sections.append("")
        
        return "\n".join(sections)
