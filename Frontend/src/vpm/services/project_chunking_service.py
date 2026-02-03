"""
VMP Project Chunking Service

Unified chunking and embedding service for all VMP project features.
Enables "Chat with Project" functionality by creating searchable vector embeddings
for all project artifacts from Persona to MVP Requirements.

Features supported:
- Persona Identification
- Customer Profile (v1 and v2)
- Hypothesis
- Assumptions
- Questionnaires
- Value Map
- VPS (v1 and v2)
- BMC (v1 and v2)
- MVP Requirements

Each feature uses a unique source_type tag for proper chunk management during regeneration.
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from src.mint.api.system.core.supabase_client import get_service_role_client
from src.mint.api.services.ai.embedding_service import get_embedding_service
from src.mint.api.report.report_models import ReportChunkWithEmbedding

# Import AI usage monitoring
try:
    from monitor.tokens.service import get_monitoring_service
    from monitor.tokens.models import AIUsageContext
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    get_monitoring_service = None
    AIUsageContext = None

logger = logging.getLogger(__name__)


class VMPFeatureType(str, Enum):
    """Feature types for VMP project chunking with unique source_type tags."""
    PERSONA = "vmp_persona"
    CUSTOMER_PROFILE = "vmp_customer_profile"
    CUSTOMER_PROFILE_V2 = "vmp_customer_profile_v2"
    HYPOTHESIS = "vmp_hypothesis"
    ASSUMPTIONS = "vmp_assumptions"
    QUESTIONNAIRE = "vmp_questionnaire"
    VALUE_MAP = "vmp_value_map"
    VPS_V1 = "vmp_vps_v1"
    VPS_V2 = "vmp_vps_v2"
    BMC_V1 = "vmp_bmc_v1"
    BMC_V2 = "vmp_bmc_v2"
    MVP_REQUIREMENTS = "vmp_mvp_requirements"
    MARKET_RESEARCH = "vmp_market_research"
    PITCH_DECK = "vmp_pitch_deck"
    GTM = "vmp_gtm"


class VMPProjectChunkingService:
    """
    Service for chunking and embedding all VMP project features.
    
    Processes project data and creates searchable chunks that can be
    retrieved during chat interactions for the "Chat with Project" feature.
    """
    
    def __init__(self):
        """Initialize VMP project chunking service."""
        self.supabase = get_service_role_client()
        self.embedding_service = get_embedding_service()
        
        # Chunking configuration
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 150  # Overlap between chunks (15%)
        
        # Monitoring service
        self.monitoring_service = None
        if MONITORING_AVAILABLE:
            try:
                self.monitoring_service = get_monitoring_service()
                logger.info("✅ VMPProjectChunkingService: AI monitoring enabled")
            except Exception as e:
                logger.warning(f"⚠️ VMPProjectChunkingService: AI monitoring unavailable: {e}")
        
        logger.info("✅ VMPProjectChunkingService initialized")
    
    def _create_monitoring_context(
        self,
        project_id: str,
        tenant_id: str,
        feature_type: VMPFeatureType,
        persona_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        Create AI usage monitoring context for tracking embedding operations.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            feature_type: Feature being chunked
            persona_id: Optional persona ID
            
        Returns:
            AIUsageContext or None if monitoring unavailable
        """
        if not MONITORING_AVAILABLE or AIUsageContext is None:
            return None
        
        try:
            return AIUsageContext(
                user_id=None,
                tenant_id=tenant_id,
                team_id=None,
                project_id=project_id,
                feature_id=f"vmp_chunking_{feature_type.value}",
                workflow_name="vmp_project_chunking",
                step_name=feature_type.value,
                environment="prod",
                request_id=None
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to create monitoring context: {e}")
            return None
    
    # ==================== PUBLIC API ====================
    
    async def chunk_feature_background(
        self,
        project_id: str,
        tenant_id: str,
        feature_type: VMPFeatureType,
        feature_data: Dict[str, Any],
        persona_id: Optional[str] = None
    ) -> None:
        """
        Background task to chunk and embed a feature without blocking.
        
        This is the main entry point - it spawns a fire-and-forget task
        so the calling code can return immediately.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            feature_type: Type of feature being chunked
            feature_data: The feature data to chunk
            persona_id: Optional persona ID for multi-persona projects
        """
        # Create background task
        asyncio.create_task(
            self._chunk_feature_safe(
                project_id=project_id,
                tenant_id=tenant_id,
                feature_type=feature_type,
                feature_data=feature_data,
                persona_id=persona_id
            )
        )
        logger.info(f"🚀 BACKGROUND CHUNKING: Spawned task for {feature_type.value} on project {project_id}")
    
    async def _chunk_feature_safe(
        self,
        project_id: str,
        tenant_id: str,
        feature_type: VMPFeatureType,
        feature_data: Dict[str, Any],
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Safe wrapper for chunking that catches all errors.
        Never raises - logs errors instead.
        """
        try:
            return await self.chunk_feature(
                project_id=project_id,
                tenant_id=tenant_id,
                feature_type=feature_type,
                feature_data=feature_data,
                persona_id=persona_id
            )
        except Exception as e:
            logger.error(f"❌ BACKGROUND CHUNKING ERROR [{feature_type.value}]: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "feature_type": feature_type.value
            }
    
    async def chunk_feature(
        self,
        project_id: str,
        tenant_id: str,
        feature_type: VMPFeatureType,
        feature_data: Dict[str, Any],
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chunk and embed a specific feature.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            feature_type: Type of feature being chunked
            feature_data: The feature data to chunk
            persona_id: Optional persona ID for multi-persona projects
            
        Returns:
            Result dict with success status and chunk count
        """
        # Track timing for monitoring
        start_time = time.time()
        started_at = datetime.utcnow()
        
        # Create monitoring context
        monitoring_context = self._create_monitoring_context(
            project_id=project_id,
            tenant_id=tenant_id,
            feature_type=feature_type,
            persona_id=persona_id
        )
        
        try:
            persona_tag = f" [persona={persona_id}]" if persona_id else ""
            logger.info(f"📊 VMP CHUNKING: Starting {feature_type.value} for project {project_id}{persona_tag}")
            logger.info(f"📊 VMP CHUNKING [{feature_type.value}]: Input data keys: {list(feature_data.keys()) if feature_data else 'None'}")
            
            if not feature_data:
                logger.warning(f"⚠️ VMP CHUNKING [{feature_type.value}]: No data provided")
                self._log_chunking_result(feature_type, project_id, False, 0, time.time() - start_time, "no_data")
                return {
                    "success": False,
                    "error": "no_data",
                    "message": f"No data provided for {feature_type.value}"
                }
            
            # Format feature data into text chunks based on type
            chunk_start = time.time()
            chunks = await self._create_feature_chunks(
                feature_type=feature_type,
                feature_data=feature_data,
                persona_id=persona_id
            )
            chunk_duration = time.time() - chunk_start
            
            if not chunks:
                logger.warning(f"⚠️ VMP CHUNKING [{feature_type.value}]: No chunks created (duration: {chunk_duration:.2f}s)")
                self._log_chunking_result(feature_type, project_id, False, 0, time.time() - start_time, "no_chunks")
                return {
                    "success": False,
                    "error": "no_chunks",
                    "message": f"No chunks created for {feature_type.value}"
                }
            
            total_chars = sum(len(c.get("content", "")) for c in chunks)
            logger.info(f"✅ VMP CHUNKING [{feature_type.value}]: Created {len(chunks)} chunks ({total_chars} chars) in {chunk_duration:.2f}s")
            
            # Generate embeddings with monitoring
            embed_start = time.time()
            chunks_with_embeddings = await self._generate_embeddings(
                chunks=chunks,
                monitoring_context=monitoring_context,
                feature_type=feature_type,
                project_id=project_id
            )
            embed_duration = time.time() - embed_start
            
            if not chunks_with_embeddings:
                logger.error(f"❌ VMP CHUNKING [{feature_type.value}]: Failed to generate embeddings (duration: {embed_duration:.2f}s)")
                self._log_chunking_result(feature_type, project_id, False, len(chunks), time.time() - start_time, "embedding_error")
                return {
                    "success": False,
                    "error": "embedding_error",
                    "message": f"Failed to generate embeddings for {feature_type.value}"
                }
            
            valid_embeddings = sum(1 for c in chunks_with_embeddings if c.get("embedding"))
            logger.info(f"✅ VMP CHUNKING [{feature_type.value}]: Generated {valid_embeddings}/{len(chunks_with_embeddings)} embeddings in {embed_duration:.2f}s")
            
            # Store chunks (handles deletion of old chunks with same source_type)
            store_start = time.time()
            success = await self._store_feature_chunks(
                project_id=project_id,
                tenant_id=tenant_id,
                feature_type=feature_type,
                chunks=chunks_with_embeddings,
                persona_id=persona_id
            )
            store_duration = time.time() - store_start
            
            total_duration = time.time() - start_time
            
            if success:
                logger.info(f"✅ VMP CHUNKING [{feature_type.value}]: SUCCESS - Stored {len(chunks_with_embeddings)} chunks in {store_duration:.2f}s")
                logger.info(f"📊 VMP CHUNKING [{feature_type.value}]: Total duration: {total_duration:.2f}s (chunk: {chunk_duration:.2f}s, embed: {embed_duration:.2f}s, store: {store_duration:.2f}s)")
                self._log_chunking_result(feature_type, project_id, True, len(chunks_with_embeddings), total_duration)
                
                # Record successful monitoring
                await self._record_monitoring_success(
                    monitoring_context=monitoring_context,
                    started_at=started_at,
                    chunk_count=len(chunks_with_embeddings),
                    total_chars=total_chars,
                    feature_type=feature_type
                )
                
                return {
                    "success": True,
                    "message": f"Successfully chunked {feature_type.value}",
                    "chunk_count": len(chunks_with_embeddings),
                    "feature_type": feature_type.value,
                    "project_id": project_id,
                    "persona_id": persona_id,
                    "duration_seconds": round(total_duration, 2),
                    "total_characters": total_chars
                }
            else:
                logger.error(f"❌ VMP CHUNKING [{feature_type.value}]: FAILED - Storage error after {store_duration:.2f}s")
                self._log_chunking_result(feature_type, project_id, False, len(chunks_with_embeddings), total_duration, "storage_error")
                return {
                    "success": False,
                    "error": "storage_error",
                    "message": f"Failed to store chunks for {feature_type.value}"
                }
                
        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"❌ VMP CHUNKING [{feature_type.value}]: EXCEPTION after {total_duration:.2f}s: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._log_chunking_result(feature_type, project_id, False, 0, total_duration, f"exception: {str(e)[:100]}")
            
            # Record error in monitoring
            await self._record_monitoring_error(
                monitoring_context=monitoring_context,
                started_at=started_at,
                error=str(e),
                feature_type=feature_type
            )
            
            return {
                "success": False,
                "error": "chunking_error",
                "message": f"Failed to chunk {feature_type.value}: {str(e)}"
            }
    
    def _log_chunking_result(
        self,
        feature_type: VMPFeatureType,
        project_id: str,
        success: bool,
        chunk_count: int,
        duration: float,
        error: Optional[str] = None
    ) -> None:
        """Log chunking result for analytics and debugging."""
        status = "SUCCESS" if success else "FAILED"
        error_info = f" error={error}" if error else ""
        logger.info(
            f"📈 VMP CHUNKING RESULT: feature={feature_type.value} project={project_id} "
            f"status={status} chunks={chunk_count} duration={duration:.2f}s{error_info}"
        )
    
    async def _record_monitoring_success(
        self,
        monitoring_context: Optional[Any],
        started_at: datetime,
        chunk_count: int,
        total_chars: int,
        feature_type: VMPFeatureType
    ) -> None:
        """Record successful chunking operation in monitoring system."""
        if not self.monitoring_service or not monitoring_context:
            return
        
        try:
            finished_at = datetime.utcnow()
            asyncio.create_task(
                self.monitoring_service.record_ai_usage(
                    context=monitoring_context,
                    provider="azure_openai",
                    model_name="text-embedding-3-small",
                    operation_type="embedding",
                    started_at=started_at,
                    finished_at=finished_at,
                    status="success",
                    embedding_tokens=total_chars // 4,  # Approximate 1 token per 4 chars
                    input_chars=total_chars,
                    extra_metadata={
                        "feature_type": feature_type.value,
                        "chunk_count": chunk_count
                    }
                )
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to record monitoring success: {e}")
    
    async def _record_monitoring_error(
        self,
        monitoring_context: Optional[Any],
        started_at: datetime,
        error: str,
        feature_type: VMPFeatureType
    ) -> None:
        """Record failed chunking operation in monitoring system."""
        if not self.monitoring_service or not monitoring_context:
            return
        
        try:
            finished_at = datetime.utcnow()
            asyncio.create_task(
                self.monitoring_service.record_ai_usage(
                    context=monitoring_context,
                    provider="azure_openai",
                    model_name="text-embedding-3-small",
                    operation_type="embedding",
                    started_at=started_at,
                    finished_at=finished_at,
                    status="error",
                    error_type="chunking_error",
                    extra_metadata={
                        "feature_type": feature_type.value,
                        "error": error[:200]
                    }
                )
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to record monitoring error: {e}")
    
    async def chunk_all_features(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Chunk all features for a project (useful for initial setup or full refresh).
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Summary of chunking results for all features
        """
        try:
            logger.info(f"📊 VMP CHUNKING: Starting full project chunking for {project_id}")
            
            # Load project data
            project = await self._load_project_data(project_id, tenant_id)
            if not project:
                return {
                    "success": False,
                    "error": "project_not_found",
                    "message": f"Project {project_id} not found"
                }
            
            results = {}
            
            # 1. Personas
            personas = project.get("personas", [])
            if personas:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.PERSONA,
                    feature_data={"personas": personas}
                )
                results["persona"] = result
            
            # 2. Customer Profile (from vpc_data)
            vpc_data = project.get("vpc_data", {})
            customer_profile = vpc_data.get("customer_profile")
            if customer_profile:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.CUSTOMER_PROFILE,
                    feature_data={"customer_profile": customer_profile}
                )
                results["customer_profile"] = result
            
            # 3. Value Map (from vpc_data)
            value_map = vpc_data.get("value_map")
            if value_map:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.VALUE_MAP,
                    feature_data={"value_map": value_map}
                )
                results["value_map"] = result
            
            # 4. Field Prep (Hypothesis, Assumptions, Questionnaires)
            field_prep = project.get("field_prep_data", {})
            
            hypotheses = field_prep.get("hypotheses", [])
            if hypotheses:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.HYPOTHESIS,
                    feature_data={"hypotheses": hypotheses}
                )
                results["hypothesis"] = result
            
            assumptions = field_prep.get("assumptions", [])
            if assumptions:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.ASSUMPTIONS,
                    feature_data={"assumptions": assumptions}
                )
                results["assumptions"] = result
            
            questionnaires = field_prep.get("questionnaires", [])
            if questionnaires:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.QUESTIONNAIRE,
                    feature_data={"questionnaires": questionnaires}
                )
                results["questionnaire"] = result
            
            # 5. MVP Data (VPS, BMC)
            mvp_data = project.get("mvp_data", {})
            
            vps_v1 = mvp_data.get("vps_v1")
            if vps_v1:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.VPS_V1,
                    feature_data={"vps": vps_v1}
                )
                results["vps_v1"] = result
            
            vps_v2 = mvp_data.get("vps_v2")
            if vps_v2:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.VPS_V2,
                    feature_data={"vps": vps_v2}
                )
                results["vps_v2"] = result
            
            bmc_v1 = mvp_data.get("bmc_v1")
            if bmc_v1:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.BMC_V1,
                    feature_data={"bmc": bmc_v1}
                )
                results["bmc_v1"] = result
            
            bmc_v2 = mvp_data.get("bmc_v2")
            if bmc_v2:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.BMC_V2,
                    feature_data={"bmc": bmc_v2}
                )
                results["bmc_v2"] = result
            
            # AMRG data can be stored under 'amrg' or 'mvp_requirements' key
            mvp_requirements = mvp_data.get("amrg") or mvp_data.get("mvp_requirements")
            if mvp_requirements:
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.MVP_REQUIREMENTS,
                    feature_data={"mvp_requirements": mvp_requirements}
                )
                results["mvp_requirements"] = result
            
            # 6. VPC v2 Data (Customer Profile v2)
            vpc_v2_data = project.get("vpc_v2_data", {})
            if vpc_v2_data:
                # Handle both single and multi-persona formats
                for persona_key, persona_data in vpc_v2_data.items():
                    if persona_key.startswith("P") and isinstance(persona_data, dict):
                        cp_v2 = persona_data.get("customer_profile")
                        if cp_v2:
                            result = await self.chunk_feature(
                                project_id=project_id,
                                tenant_id=tenant_id,
                                feature_type=VMPFeatureType.CUSTOMER_PROFILE_V2,
                                feature_data={"customer_profile": cp_v2},
                                persona_id=persona_key
                            )
                            results[f"customer_profile_v2_{persona_key}"] = result
            
            # 7. Market Research Analysis
            analysis_data = project.get("analysis_data", {})
            if analysis_data and analysis_data.get("stage") == "analysis_completed":
                result = await self.chunk_feature(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    feature_type=VMPFeatureType.MARKET_RESEARCH,
                    feature_data={"analysis_data": analysis_data}
                )
                results["market_research"] = result
            
            # Summary
            successful = sum(1 for r in results.values() if r.get("success"))
            total = len(results)
            
            logger.info(f"✅ VMP CHUNKING: Completed full project chunking - {successful}/{total} features successful")
            
            return {
                "success": successful > 0,
                "message": f"Chunked {successful}/{total} features",
                "results": results,
                "project_id": project_id
            }
            
        except Exception as e:
            logger.error(f"❌ VMP CHUNKING: Error in full project chunking: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": "full_chunking_error",
                "message": str(e)
            }
    
    # ==================== CHUNK CREATION BY FEATURE TYPE ====================
    
    async def _create_feature_chunks(
        self,
        feature_type: VMPFeatureType,
        feature_data: Dict[str, Any],
        persona_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Route to appropriate chunk creation method based on feature type."""
        
        formatters = {
            VMPFeatureType.PERSONA: self._format_personas,
            VMPFeatureType.CUSTOMER_PROFILE: self._format_customer_profile,
            VMPFeatureType.CUSTOMER_PROFILE_V2: self._format_customer_profile_v2,
            VMPFeatureType.HYPOTHESIS: self._format_hypotheses,
            VMPFeatureType.ASSUMPTIONS: self._format_assumptions,
            VMPFeatureType.QUESTIONNAIRE: self._format_questionnaires,
            VMPFeatureType.VALUE_MAP: self._format_value_map,
            VMPFeatureType.VPS_V1: self._format_vps,
            VMPFeatureType.VPS_V2: self._format_vps,
            VMPFeatureType.BMC_V1: self._format_bmc,
            VMPFeatureType.BMC_V2: self._format_bmc,
            VMPFeatureType.MVP_REQUIREMENTS: self._format_mvp_requirements,
            VMPFeatureType.MARKET_RESEARCH: self._format_market_research,
            VMPFeatureType.PITCH_DECK: self._format_pitch_deck,
            VMPFeatureType.GTM: self._format_gtm,
        }
        
        formatter = formatters.get(feature_type)
        if not formatter:
            logger.error(f"❌ No formatter for feature type: {feature_type}")
            return []
        
        # Format the feature data into text
        text = formatter(feature_data, persona_id)
        
        if not text or len(text.strip()) < 50:
            logger.warning(f"⚠️ Insufficient text content for {feature_type.value}: {len(text) if text else 0} chars")
            return []
        
        # Split into chunks
        chunk_texts = self._split_text_into_chunks(text)
        
        # Create chunk objects
        chunks = []
        for i, chunk_text in enumerate(chunk_texts):
            chunks.append({
                "content": chunk_text,
                "chunk_index": i,
                "section": feature_type.value,
                "metadata": {
                    "source_type": feature_type.value,
                    "chunk_position": i,
                    "total_chunks": len(chunk_texts),
                    "persona_id": persona_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            })
        
        return chunks
    
    # ==================== FEATURE FORMATTERS ====================
    
    def _format_personas(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format personas data as text."""
        personas = data.get("personas", [])
        if not personas:
            return ""
        
        lines = [
            "=== IDENTIFIED PERSONAS ===",
            "",
            f"Total Personas: {len(personas)}",
            ""
        ]
        
        for i, persona in enumerate(personas, 1):
            lines.append(f"--- PERSONA {i}: {persona.get('name', 'Unnamed')} ---")
            lines.append(f"ID: {persona.get('id', f'P{i}')}")
            
            if persona.get("description"):
                lines.append(f"Description: {persona.get('description')}")
            
            if persona.get("characteristics"):
                lines.append("Characteristics:")
                chars = persona.get("characteristics", [])
                if isinstance(chars, list):
                    for char in chars:
                        lines.append(f"  - {char}")
                elif isinstance(chars, str):
                    lines.append(f"  {chars}")
            
            if persona.get("demographics"):
                lines.append(f"Demographics: {persona.get('demographics')}")
            
            if persona.get("pain_points"):
                lines.append("Key Pain Points:")
                for pain in persona.get("pain_points", []):
                    lines.append(f"  - {pain}")
            
            if persona.get("goals"):
                lines.append("Goals:")
                for goal in persona.get("goals", []):
                    lines.append(f"  - {goal}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_customer_profile(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format customer profile (JTBD, Pains, Gains) as text."""
        cp = data.get("customer_profile", {})
        if not cp:
            return ""
        
        persona_tag = f" (Persona: {persona_id})" if persona_id else ""
        lines = [
            f"=== CUSTOMER PROFILE{persona_tag} ===",
            ""
        ]
        
        # Jobs to be Done
        jtbd = cp.get("jobs_to_be_done", [])
        if jtbd:
            lines.append("JOBS TO BE DONE:")
            for job in jtbd:
                if isinstance(job, dict):
                    lines.append(f"- {job.get('title', job.get('description', 'Unknown'))}")
                    if job.get("importance"):
                        lines.append(f"  Importance: {job.get('importance')}")
                    if job.get("description") and job.get("title"):
                        lines.append(f"  {job.get('description')}")
                else:
                    lines.append(f"- {job}")
            lines.append("")
        
        # Pains
        pains = cp.get("pains", [])
        if pains:
            lines.append("PAINS:")
            for pain in pains:
                if isinstance(pain, dict):
                    lines.append(f"- {pain.get('title', pain.get('description', 'Unknown'))}")
                    if pain.get("severity"):
                        lines.append(f"  Severity: {pain.get('severity')}")
                    if pain.get("description") and pain.get("title"):
                        lines.append(f"  {pain.get('description')}")
                else:
                    lines.append(f"- {pain}")
            lines.append("")
        
        # Gains
        gains = cp.get("gains", [])
        if gains:
            lines.append("GAINS:")
            for gain in gains:
                if isinstance(gain, dict):
                    lines.append(f"- {gain.get('title', gain.get('description', 'Unknown'))}")
                    if gain.get("relevance"):
                        lines.append(f"  Relevance: {gain.get('relevance')}")
                    if gain.get("description") and gain.get("title"):
                        lines.append(f"  {gain.get('description')}")
                else:
                    lines.append(f"- {gain}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_customer_profile_v2(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format Customer Profile v2 (VPC v2) with customer profile AND value map selections."""
        # Handle both formats: wrapped in customer_profiles_v2 or direct customer_profile
        customer_profiles_v2 = data.get("customer_profiles_v2", {})
        
        # If not found, check if it's a direct customer_profile (from per-persona chunking)
        if not customer_profiles_v2:
            direct_cp = data.get("customer_profile", {})
            if direct_cp:
                # Wrap it with persona_id as key
                customer_profiles_v2 = {persona_id or "P1": {"customer_profile": direct_cp, "persona_name": persona_id}}
        
        if not customer_profiles_v2:
            logger.warning("⚠️ No customer_profiles_v2 or customer_profile data found in input")
            return ""
        
        all_lines = []
        
        for persona_key, persona_data in customer_profiles_v2.items():
            if not isinstance(persona_data, dict):
                continue
            
            persona_name = persona_data.get("persona_name", persona_key)
            lines = [
                f"=== CUSTOMER PROFILE V2: {persona_name} ===",
                "",
                f"Persona ID: {persona_key}",
                ""
            ]
            
            # Customer Profile (JTBD, Pains, Gains)
            cp = persona_data.get("customer_profile", {})
            if cp:
                lines.append("--- CUSTOMER PROFILE ---")
                lines.append("")
                
                # Jobs to be Done
                jtbd = cp.get("jobs_to_be_done", [])
                if jtbd:
                    lines.append("JOBS TO BE DONE:")
                    for job in jtbd:
                        if isinstance(job, dict):
                            lines.append(f"- {job.get('title', job.get('description', 'Unknown'))}")
                            if job.get("importance"):
                                lines.append(f"  Importance: {job.get('importance')}")
                            if job.get("description") and job.get("title"):
                                lines.append(f"  {job.get('description')}")
                        else:
                            lines.append(f"- {job}")
                    lines.append("")
                
                # Pains
                pains = cp.get("pains", [])
                if pains:
                    lines.append("PAINS:")
                    for pain in pains:
                        if isinstance(pain, dict):
                            lines.append(f"- {pain.get('title', pain.get('description', 'Unknown'))}")
                            if pain.get("severity"):
                                lines.append(f"  Severity: {pain.get('severity')}")
                            if pain.get("description") and pain.get("title"):
                                lines.append(f"  {pain.get('description')}")
                        else:
                            lines.append(f"- {pain}")
                    lines.append("")
                
                # Gains
                gains = cp.get("gains", [])
                if gains:
                    lines.append("GAINS:")
                    for gain in gains:
                        if isinstance(gain, dict):
                            lines.append(f"- {gain.get('title', gain.get('description', 'Unknown'))}")
                            if gain.get("relevance"):
                                lines.append(f"  Relevance: {gain.get('relevance')}")
                            if gain.get("description") and gain.get("title"):
                                lines.append(f"  {gain.get('description')}")
                        else:
                            lines.append(f"- {gain}")
                    lines.append("")
            
            # Value Map Selections (Products, Pain Relievers, Gain Creators)
            vm_selections = persona_data.get("value_map_selections", {})
            if vm_selections:
                lines.append("--- VALUE MAP SELECTIONS ---")
                lines.append("")
                
                # Products/Services
                products = vm_selections.get("products_services", [])
                if products:
                    lines.append("PRODUCTS/SERVICES:")
                    for product in products:
                        if isinstance(product, dict):
                            lines.append(f"- {product.get('title', product.get('description', 'Unknown'))}")
                            if product.get("description") and product.get("title"):
                                lines.append(f"  {product.get('description')}")
                        else:
                            lines.append(f"- {product}")
                    lines.append("")
                
                # Pain Relievers
                relievers = vm_selections.get("pain_relievers", [])
                if relievers:
                    lines.append("PAIN RELIEVERS:")
                    for reliever in relievers:
                        if isinstance(reliever, dict):
                            lines.append(f"- {reliever.get('title', reliever.get('description', 'Unknown'))}")
                            if reliever.get("description") and reliever.get("title"):
                                lines.append(f"  {reliever.get('description')}")
                        else:
                            lines.append(f"- {reliever}")
                    lines.append("")
                
                # Gain Creators
                creators = vm_selections.get("gain_creators", [])
                if creators:
                    lines.append("GAIN CREATORS:")
                    for creator in creators:
                        if isinstance(creator, dict):
                            lines.append(f"- {creator.get('title', creator.get('description', 'Unknown'))}")
                            if creator.get("description") and creator.get("title"):
                                lines.append(f"  {creator.get('description')}")
                        else:
                            lines.append(f"- {creator}")
                    lines.append("")
            
            all_lines.extend(lines)
            all_lines.append("="*80)
            all_lines.append("")
        
        result = "\n".join(all_lines)
        logger.info(f"📝 VMP CHUNKING [customer_profile_v2]: Formatted {len(customer_profiles_v2)} persona(s), {len(result)} chars")
        return result
    
    def _format_hypotheses(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format hypotheses as text."""
        hypotheses = data.get("hypotheses", [])
        if not hypotheses:
            return ""
        
        lines = [
            "=== MARKET HYPOTHESES ===",
            "",
            f"Total Hypotheses: {len(hypotheses)}",
            ""
        ]
        
        for i, hyp in enumerate(hypotheses, 1):
            lines.append(f"--- HYPOTHESIS {i} ---")
            lines.append(f"ID: {hyp.get('id', f'H{i}')}")
            
            if hyp.get("persona_name"):
                lines.append(f"Persona: {hyp.get('persona_name')}")
            
            if hyp.get("hypothesis_statement"):
                lines.append(f"Statement: {hyp.get('hypothesis_statement')}")
            elif hyp.get("statement"):
                lines.append(f"Statement: {hyp.get('statement')}")
            
            if hyp.get("rationale"):
                lines.append(f"Rationale: {hyp.get('rationale')}")
            
            if hyp.get("key_metrics"):
                lines.append("Key Metrics:")
                for metric in hyp.get("key_metrics", []):
                    lines.append(f"  - {metric}")
            
            if hyp.get("validation_criteria"):
                lines.append("Validation Criteria:")
                for criteria in hyp.get("validation_criteria", []):
                    lines.append(f"  - {criteria}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_assumptions(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format assumptions as text."""
        assumptions = data.get("assumptions", [])
        if not assumptions:
            return ""
        
        lines = [
            "=== TESTABLE ASSUMPTIONS ===",
            "",
            f"Total Assumptions: {len(assumptions)}",
            ""
        ]
        
        for i, assumption in enumerate(assumptions, 1):
            lines.append(f"--- ASSUMPTION {assumption.get('id', f'A{i}')} ---")
            
            if assumption.get("persona_name"):
                lines.append(f"Persona: {assumption.get('persona_name')}")
            
            if assumption.get("hypothesis_id"):
                lines.append(f"Related Hypothesis: {assumption.get('hypothesis_id')}")
            
            if assumption.get("assumption_text"):
                lines.append(f"Assumption: {assumption.get('assumption_text')}")
            elif assumption.get("text"):
                lines.append(f"Assumption: {assumption.get('text')}")
            
            if assumption.get("risk_level"):
                lines.append(f"Risk Level: {assumption.get('risk_level')}")
            
            if assumption.get("test_method"):
                lines.append(f"Test Method: {assumption.get('test_method')}")
            
            if assumption.get("success_criteria"):
                lines.append(f"Success Criteria: {assumption.get('success_criteria')}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_questionnaires(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format questionnaires as text."""
        questionnaires = data.get("questionnaires", [])
        if not questionnaires:
            return ""
        
        lines = [
            "=== RESEARCH QUESTIONNAIRES ===",
            "",
            f"Total Questionnaires: {len(questionnaires)}",
            ""
        ]
        
        for i, q in enumerate(questionnaires, 1):
            lines.append(f"--- QUESTIONNAIRE {i} ---")
            
            if q.get("persona_name"):
                lines.append(f"Persona: {q.get('persona_name')}")
            
            if q.get("title"):
                lines.append(f"Title: {q.get('title')}")
            
            if q.get("objective"):
                lines.append(f"Objective: {q.get('objective')}")
            
            questions = q.get("questions", [])
            if questions:
                lines.append(f"Questions ({len(questions)}):")
                for j, question in enumerate(questions, 1):
                    if isinstance(question, dict):
                        lines.append(f"  Q{j}: {question.get('text', question.get('question', 'Unknown'))}")
                        if question.get("type"):
                            lines.append(f"      Type: {question.get('type')}")
                        if question.get("rationale"):
                            lines.append(f"      Rationale: {question.get('rationale')}")
                    else:
                        lines.append(f"  Q{j}: {question}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_value_map(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format value map as text."""
        vm = data.get("value_map", {})
        if not vm:
            return ""
        
        persona_tag = f" (Persona: {persona_id})" if persona_id else ""
        lines = [
            f"=== VALUE MAP{persona_tag} ===",
            ""
        ]
        
        # Products & Services
        products = vm.get("products_services", [])
        if products:
            lines.append("PRODUCTS & SERVICES:")
            for item in products:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('title', item.get('name', 'Unknown'))}")
                    if item.get("description"):
                        lines.append(f"  {item.get('description')}")
                else:
                    lines.append(f"- {item}")
            lines.append("")
        
        # Pain Relievers
        relievers = vm.get("pain_relievers", [])
        if relievers:
            lines.append("PAIN RELIEVERS:")
            for item in relievers:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('title', item.get('name', 'Unknown'))}")
                    if item.get("description"):
                        lines.append(f"  {item.get('description')}")
                    if item.get("addressed_pain"):
                        lines.append(f"  Addresses: {item.get('addressed_pain')}")
                else:
                    lines.append(f"- {item}")
            lines.append("")
        
        # Gain Creators
        creators = vm.get("gain_creators", [])
        if creators:
            lines.append("GAIN CREATORS:")
            for item in creators:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('title', item.get('name', 'Unknown'))}")
                    if item.get("description"):
                        lines.append(f"  {item.get('description')}")
                    if item.get("addressed_gain"):
                        lines.append(f"  Creates: {item.get('addressed_gain')}")
                else:
                    lines.append(f"- {item}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_vps(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format Value Proposition Statement as text. Handles both VPS v1 and v2 structures."""
        vps_list = data.get("vps", [])
        
        # Handle both list and single VPS
        if isinstance(vps_list, dict):
            vps_list = [vps_list]
        
        if not vps_list:
            return ""
        
        lines = [
            "=== VALUE PROPOSITION STATEMENTS ===",
            "",
            f"Total VPS: {len(vps_list)}",
            ""
        ]
        
        for i, vps in enumerate(vps_list, 1):
            lines.append(f"--- VPS {i} ---")
            
            if vps.get("persona_id") or vps.get("persona_name"):
                lines.append(f"Persona: {vps.get('persona_name', vps.get('persona_id'))}")
            
            # Check for VPS v2 structure (has primary_statement)
            primary = vps.get("primary_statement", {})
            if primary:
                # VPS v2 format
                if primary.get("our"):
                    lines.append(f"Our (Product/Service): {primary.get('our')}")
                if primary.get("help"):
                    lines.append(f"Help: {primary.get('help')}")
                if primary.get("who_want_to"):
                    lines.append(f"Who Want To: {primary.get('who_want_to')}")
                if primary.get("by"):
                    lines.append(f"By: {primary.get('by')}")
                if primary.get("and"):
                    lines.append(f"And: {primary.get('and')}")
                if primary.get("unlike"):
                    lines.append(f"Unlike (Competition): {primary.get('unlike')}")
                
                # Extended statement
                if vps.get("extended_statement"):
                    lines.append(f"Extended Statement: {vps.get('extended_statement')}")
                
                # Refinement info
                if vps.get("refinement_decision"):
                    lines.append(f"Refinement: {vps.get('refinement_decision')}")
                if vps.get("refinement_rationale"):
                    lines.append(f"Rationale: {vps.get('refinement_rationale')}")
            else:
                # VPS v1 format
                if vps.get("statement"):
                    lines.append(f"Statement: {vps.get('statement')}")
                elif vps.get("value_proposition"):
                    lines.append(f"Value Proposition: {vps.get('value_proposition')}")
                
                if vps.get("for_target"):
                    lines.append(f"For (Target Customer): {vps.get('for_target')}")
                if vps.get("who_need"):
                    lines.append(f"Who Need: {vps.get('who_need')}")
                if vps.get("our_product"):
                    lines.append(f"Our Product: {vps.get('our_product')}")
                if vps.get("that_provides"):
                    lines.append(f"That Provides: {vps.get('that_provides')}")
                if vps.get("unlike"):
                    lines.append(f"Unlike (Competition): {vps.get('unlike')}")
                if vps.get("our_solution"):
                    lines.append(f"Our Solution: {vps.get('our_solution')}")
            
            # Key benefits (both formats)
            benefits = vps.get("key_benefits", [])
            if benefits:
                lines.append("Key Benefits:")
                for benefit in benefits:
                    lines.append(f"  - {benefit}")
            
            # Confidence score
            gen_meta = vps.get("generation_metadata", {})
            if gen_meta.get("confidence_score"):
                lines.append(f"Confidence: {gen_meta.get('confidence_score')}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_bmc(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format Business Model Canvas as text. Handles both BMC v1 and v2 structures."""
        bmc_list = data.get("bmc", [])
        
        # Handle both list and single BMC
        if isinstance(bmc_list, dict):
            bmc_list = [bmc_list]
        
        if not bmc_list:
            return ""
        
        lines = [
            "=== BUSINESS MODEL CANVAS ===",
            "",
            f"Total BMC: {len(bmc_list)}",
            ""
        ]
        
        # BMC fields mapping
        bmc_fields = [
            ("customer_segments", "Customer Segments"),
            ("value_propositions", "Value Propositions"),
            ("channels", "Channels"),
            ("customer_relationships", "Customer Relationships"),
            ("revenue_streams", "Revenue Streams"),
            ("key_resources", "Key Resources"),
            ("key_activities", "Key Activities"),
            ("key_partnerships", "Key Partnerships"),
            ("cost_structure", "Cost Structure"),
        ]
        
        for i, bmc in enumerate(bmc_list, 1):
            if len(bmc_list) > 1:
                lines.append(f"--- BMC {i} ---")
                if bmc.get("persona_id") or bmc.get("persona_name"):
                    lines.append(f"Persona: {bmc.get('persona_name', bmc.get('persona_id'))}")
                lines.append("")
            
            # Refinement metadata (BMC v2)
            if bmc.get("refinement_decision"):
                lines.append(f"Refinement: {bmc.get('refinement_decision')}")
            if bmc.get("refinement_rationale"):
                lines.append(f"Rationale: {bmc.get('refinement_rationale')}")
            if bmc.get("overall_improvement_summary"):
                lines.append(f"Summary: {bmc.get('overall_improvement_summary')}")
            if bmc.get("vps_v2_alignment_notes"):
                lines.append(f"VPS v2 Alignment: {bmc.get('vps_v2_alignment_notes')}")
            
            for field_key, field_name in bmc_fields:
                field_value = bmc.get(field_key)
                if field_value:
                    lines.append(f"{field_name.upper()}:")
                    if isinstance(field_value, list):
                        # BMC v1 format: list of items
                        for item in field_value:
                            if isinstance(item, dict):
                                lines.append(f"  - {item.get('title', item.get('name', item.get('description', str(item))))}")
                            else:
                                lines.append(f"  - {item}")
                    elif isinstance(field_value, dict):
                        # BMC v2 format: object with items/entries
                        items = field_value.get("items", field_value.get("entries", []))
                        if items and isinstance(items, list):
                            for item in items:
                                if isinstance(item, dict):
                                    # Extract title/name/description
                                    title = item.get('title', item.get('name', item.get('description', '')))
                                    if title:
                                        lines.append(f"  - {title}")
                                    # Also include any details
                                    if item.get('details'):
                                        lines.append(f"    {item.get('details')}")
                                else:
                                    lines.append(f"  - {item}")
                        else:
                            # Fallback: dump the dict content
                            for k, v in field_value.items():
                                if k not in ['items', 'entries'] and v:
                                    lines.append(f"  {k}: {v}")
                    elif isinstance(field_value, str):
                        lines.append(f"  {field_value}")
                    lines.append("")
        
        return "\n".join(lines)
    
    def _format_mvp_requirements(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format MVP requirements (AMRG PRD JSON) as text."""
        mvp = data.get("mvp_requirements", {})
        if not mvp:
            return ""
        
        lines = [
            "=== MVP REQUIREMENTS (PRD) ===",
            ""
        ]
        
        # Template info
        if mvp.get("template_code"):
            lines.append(f"Template: {mvp.get('template_code')} v{mvp.get('template_version', '1.0.0')}")
            lines.append("")
        
        # Purpose section
        purpose = mvp.get("purpose", {})
        if purpose:
            lines.append("PURPOSE:")
            if purpose.get("statement"):
                lines.append(f"  {purpose.get('statement')}")
            if purpose.get("validated_problem"):
                lines.append(f"  Validated Problem: {purpose.get('validated_problem')}")
            if purpose.get("target_persona"):
                lines.append(f"  Target Persona: {purpose.get('target_persona')}")
            lines.append("")
        
        # Objective section
        objective = mvp.get("objective", {})
        if objective:
            lines.append("OBJECTIVE:")
            learning_goals = objective.get("learning_goals", [])
            if learning_goals:
                lines.append("  Learning Goals:")
                for goal in learning_goals:
                    lines.append(f"    - {goal}")
            success_criteria = objective.get("success_criteria", [])
            if success_criteria:
                lines.append("  Success Criteria:")
                for criteria in success_criteria:
                    lines.append(f"    - {criteria}")
            lines.append("")
        
        # Scope section
        scope = mvp.get("scope", {})
        if scope:
            lines.append("SCOPE:")
            in_scope = scope.get("in_scope", {})
            if in_scope:
                lines.append("  In Scope:")
                if in_scope.get("user_segments"):
                    lines.append(f"    User Segments: {', '.join(in_scope.get('user_segments', []))}")
                if in_scope.get("core_flows"):
                    lines.append(f"    Core Flows: {', '.join(in_scope.get('core_flows', []))}")
                if in_scope.get("geography"):
                    lines.append(f"    Geography: {in_scope.get('geography')}")
            out_of_scope = scope.get("out_of_scope", [])
            if out_of_scope:
                lines.append("  Out of Scope:")
                for item in out_of_scope:
                    lines.append(f"    - {item}")
            lines.append("")
        
        # Primary Persona
        primary_persona = mvp.get("primary_persona", {})
        if primary_persona:
            lines.append("PRIMARY PERSONA:")
            if primary_persona.get("name"):
                lines.append(f"  Name: {primary_persona.get('name')}")
            if primary_persona.get("description"):
                lines.append(f"  Description: {primary_persona.get('description')}")
            primary_job = primary_persona.get("primary_job", {})
            if primary_job:
                lines.append(f"  Primary Job: {primary_job.get('job_statement', '')} ({primary_job.get('job_type', '')})")
            lines.append("")
        
        # MVP Features - Must Haves (support both old and new structure)
        # New structure: must_have_features.features
        # Old structure: mvp_features.must_haves
        must_have_features = mvp.get("must_have_features", {})
        must_haves = must_have_features.get("features", []) if must_have_features else []
        if not must_haves:
            # Fallback to old structure
            mvp_features = mvp.get("mvp_features", {})
            must_haves = mvp_features.get("must_haves", []) if mvp_features else []
        
        if must_haves:
            lines.append("MUST-HAVE FEATURES:")
            for feature in must_haves:
                lines.append(f"  - {feature.get('feature_name', 'Unknown Feature')}")
                if feature.get("description"):
                    lines.append(f"    Description: {feature.get('description')}")
                if feature.get("job_supported"):
                    lines.append(f"    Job Supported: {feature.get('job_supported')} ({feature.get('job_type', '')})")
                if feature.get("vpc_reference"):
                    lines.append(f"    VPC Reference: {feature.get('vpc_reference')}")
                # New FAB fields merged into feature
                if feature.get("advantage"):
                    lines.append(f"    Advantage: {feature.get('advantage')}")
                if feature.get("benefit"):
                    lines.append(f"    Benefit: {feature.get('benefit')}")
            lines.append("")
        
        # Nice to Haves (support both old and new structure)
        nice_to_have_features = mvp.get("nice_to_have_features", {})
        nice_to_haves = nice_to_have_features.get("features", []) if nice_to_have_features else []
        if not nice_to_haves:
            # Fallback to old structure
            mvp_features = mvp.get("mvp_features", {})
            nice_to_haves = mvp_features.get("nice_to_haves", []) if mvp_features else []
        
        if nice_to_haves:
            lines.append("NICE-TO-HAVE FEATURES:")
            for feature in nice_to_haves:
                lines.append(f"  - {feature.get('feature_name', 'Unknown Feature')}")
                if feature.get("description"):
                    lines.append(f"    Description: {feature.get('description')}")
                if feature.get("rationale_for_deferral"):
                    lines.append(f"    Deferral Rationale: {feature.get('rationale_for_deferral')}")
                # New FAB fields merged into feature
                if feature.get("advantage"):
                    lines.append(f"    Advantage: {feature.get('advantage')}")
                if feature.get("benefit"):
                    lines.append(f"    Benefit: {feature.get('benefit')}")
            lines.append("")
        
        # Critical Workflows (support both old array and new object structure)
        critical_workflows_data = mvp.get("critical_workflows", [])
        # New structure: critical_workflows.workflows (object with workflows array)
        # Old structure: critical_workflows (direct array)
        if isinstance(critical_workflows_data, dict):
            workflows = critical_workflows_data.get("workflows", [])
        else:
            workflows = critical_workflows_data if isinstance(critical_workflows_data, list) else []
        
        if workflows:
            lines.append("CRITICAL WORKFLOWS:")
            for workflow in workflows:
                if isinstance(workflow, dict):
                    lines.append(f"  {workflow.get('workflow_name', 'Unknown Workflow')} {'(MUST-HAVE)' if workflow.get('is_must_have') else '(NICE-TO-HAVE)'}")
                    if workflow.get("description"):
                        lines.append(f"    Description: {workflow.get('description')}")
                    steps = workflow.get("steps", [])
                    if steps:
                        lines.append("    Steps:")
                        for i, step in enumerate(steps, 1):
                            lines.append(f"      {i}. {step}")
                    if workflow.get("value_delivered"):
                        lines.append(f"    Value Delivered: {workflow.get('value_delivered')}")
            lines.append("")
        
        # Constraints (support both old and new structure)
        # New structure: constraints.items
        # Old structure: constraints_and_nongoals (array)
        constraints_data = mvp.get("constraints", {})
        if isinstance(constraints_data, dict):
            constraints = constraints_data.get("items", [])
        else:
            constraints = []
        if not constraints:
            constraints = mvp.get("constraints_and_nongoals", [])
        
        if constraints:
            lines.append("CONSTRAINTS:")
            for constraint in constraints:
                if isinstance(constraint, dict):
                    lines.append(f"  - {constraint.get('constraint', '')}")
                    if constraint.get("rationale"):
                        lines.append(f"    Rationale: {constraint.get('rationale')}")
                    if constraint.get("impact"):
                        lines.append(f"    Impact: {constraint.get('impact')}")
                    if constraint.get("category"):
                        lines.append(f"    Category: {constraint.get('category')}")
                elif isinstance(constraint, str):
                    lines.append(f"  - {constraint}")
            lines.append("")
        
        # Success Signals
        success_signals = mvp.get("success_signals", {})
        if success_signals:
            lines.append("SUCCESS SIGNALS:")
            quantitative = success_signals.get("quantitative", [])
            if quantitative:
                lines.append("  Quantitative Metrics:")
                for metric in quantitative:
                    lines.append(f"    - {metric.get('metric_name', 'Unknown')}: Target {metric.get('target', 'N/A')}")
                    if metric.get("description"):
                        lines.append(f"      Description: {metric.get('description')}")
                    if metric.get("measurement_method"):
                        lines.append(f"      Measurement: {metric.get('measurement_method')}")
            qualitative = success_signals.get("qualitative", [])
            if qualitative:
                lines.append("  Qualitative Signals:")
                for signal in qualitative:
                    lines.append(f"    - {signal.get('signal_name', 'Unknown')}: {signal.get('description', '')}")
                    if signal.get("collection_method"):
                        lines.append(f"      Collection: {signal.get('collection_method')}")
            lines.append("")
        
        # Assumptions and Risks (support both old and new structure)
        # New structure: assumptions_and_risks.items
        # Old structure: assumptions_and_risks (array)
        assumptions_data = mvp.get("assumptions_and_risks", [])
        if isinstance(assumptions_data, dict):
            assumptions_risks = assumptions_data.get("items", [])
        else:
            assumptions_risks = assumptions_data if isinstance(assumptions_data, list) else []
        
        if assumptions_risks:
            lines.append("ASSUMPTIONS AND RISKS:")
            for item in assumptions_risks:
                if isinstance(item, dict):
                    lines.append(f"  Assumption: {item.get('assumption', '')}")
                    if item.get("why_it_matters"):
                        lines.append(f"    Why It Matters: {item.get('why_it_matters')}")
                    if item.get("confidence"):
                        lines.append(f"    Confidence: {item.get('confidence')}")
                    if item.get("risk_if_wrong"):
                        lines.append(f"    Risk if Wrong: {item.get('risk_if_wrong')}")
                    if item.get("mitigation"):
                        lines.append(f"    Mitigation: {item.get('mitigation')}")
            lines.append("")
        
        # Research (if available)
        research = mvp.get("research", {})
        if research:
            key_findings = research.get("key_findings", [])
            if key_findings:
                lines.append("KEY RESEARCH FINDINGS:")
                for finding in key_findings:
                    lines.append(f"  - {finding}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_market_research(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format Market Research Analysis as text."""
        analysis = data.get("analysis_data", {})
        if not analysis:
            return ""
        
        lines = [
            "=== MARKET RESEARCH ANALYSIS ===",
            ""
        ]
        
        # Stage/Status
        if analysis.get("stage"):
            lines.append(f"Stage: {analysis.get('stage')}")
            lines.append("")
        
        # Final Report (if available)
        final_report = analysis.get("final_report", "")
        if final_report:
            lines.append("ANALYSIS REPORT:")
            lines.append(final_report)
            lines.append("")
        
        # Assumption Analyses
        assumption_analyses = analysis.get("assumption_analyses", [])
        if assumption_analyses:
            lines.append(f"ASSUMPTION ANALYSES ({len(assumption_analyses)} assumptions):")
            lines.append("")
            for i, aa in enumerate(assumption_analyses, 1):
                lines.append(f"--- Assumption {i}: {aa.get('assumption_id', f'A{i}')} ---")
                
                if aa.get("assumption_text"):
                    lines.append(f"Text: {aa.get('assumption_text')}")
                
                if aa.get("validation_status"):
                    lines.append(f"Status: {aa.get('validation_status')}")
                
                if aa.get("confidence_score"):
                    lines.append(f"Confidence: {aa.get('confidence_score')}")
                
                if aa.get("summary"):
                    lines.append(f"Summary: {aa.get('summary')}")
                
                if aa.get("key_findings"):
                    lines.append("Key Findings:")
                    for finding in aa.get("key_findings", []):
                        if isinstance(finding, dict):
                            lines.append(f"  - {finding.get('finding', finding.get('text', str(finding)))}")
                        else:
                            lines.append(f"  - {finding}")
                
                if aa.get("evidence"):
                    lines.append("Evidence:")
                    for evidence in aa.get("evidence", [])[:3]:  # Limit to 3 evidence items
                        if isinstance(evidence, dict):
                            lines.append(f"  - {evidence.get('source', evidence.get('title', ''))}: {evidence.get('snippet', '')[:200]}")
                        else:
                            lines.append(f"  - {str(evidence)[:200]}")
                
                if aa.get("recommendations"):
                    lines.append("Recommendations:")
                    for rec in aa.get("recommendations", []):
                        lines.append(f"  - {rec}")
                
                lines.append("")
        
        # Session metadata
        session = analysis.get("session_metadata", {})
        if session:
            if session.get("started_at"):
                lines.append(f"Analysis Started: {session.get('started_at')}")
            if session.get("completed_at"):
                lines.append(f"Analysis Completed: {session.get('completed_at')}")
        
        return "\n".join(lines)
    
    def _format_pitch_deck(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format Pitch Deck as text for chunking and embedding."""
        pitch_deck = data.get("pitch_deck", {})
        if not pitch_deck:
            return ""
        
        lines = [
            "=== PITCH DECK ===",
            ""
        ]
        
        # Deck metadata
        if pitch_deck.get("deck_purpose"):
            lines.append(f"Purpose: {pitch_deck.get('deck_purpose')}")
        if pitch_deck.get("stage"):
            lines.append(f"Stage: {pitch_deck.get('stage')}")
        if pitch_deck.get("category"):
            lines.append(f"Category: {pitch_deck.get('category')}")
        if pitch_deck.get("version"):
            lines.append(f"Version: {pitch_deck.get('version')}")
        lines.append("")
        
        # Slides
        slides = pitch_deck.get("slides", [])
        if slides:
            lines.append(f"SLIDES ({len(slides)} total):")
            lines.append("")
            
            for i, slide in enumerate(slides, 1):
                slide_type = slide.get("slide_type", "Unknown")
                slide_title = slide.get("slide_title", "Untitled")
                
                lines.append(f"--- SLIDE {i}: {slide_type} ---")
                lines.append(f"Title: {slide_title}")
                
                # Bullets
                bullets = slide.get("slide_bullets", [])
                if bullets:
                    lines.append("Key Points:")
                    for bullet in bullets:
                        lines.append(f"  • {bullet}")
                
                # Description
                description = slide.get("description", "")
                if description:
                    lines.append(f"Description: {description}")
                
                # Citations
                citations = slide.get("citations_used", [])
                if citations:
                    lines.append(f"Citations: {', '.join(citations)}")
                
                # Placeholders
                placeholders = slide.get("placeholders", [])
                if placeholders:
                    lines.append("Placeholders to fill:")
                    for ph in placeholders:
                        lines.append(f"  - {ph.get('field', 'Unknown')}: {ph.get('prompt', '')}")
                
                # Warnings
                warnings = slide.get("warnings", [])
                if warnings:
                    lines.append("Warnings:")
                    for warning in warnings:
                        lines.append(f"  ⚠️ {warning}")
                
                lines.append("")
        
        # Global citations
        citations = pitch_deck.get("citations", [])
        if citations:
            lines.append(f"CITATIONS ({len(citations)} sources):")
            for cite in citations:
                cite_id = cite.get("id", "?")
                cite_type = cite.get("type", "unknown")
                artifact = cite.get("artifact_ref", "")
                snippet = cite.get("snippet", "")[:200] if cite.get("snippet") else ""
                lines.append(f"  [{cite_id}] ({cite_type}) {artifact}: {snippet}...")
            lines.append("")
        
        # Warnings
        warnings = pitch_deck.get("warnings", [])
        if warnings:
            lines.append("DECK WARNINGS:")
            for warning in warnings:
                lines.append(f"  ⚠️ {warning}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_gtm(self, data: Dict[str, Any], persona_id: Optional[str] = None) -> str:
        """Format GTM Strategy Pack as text for chunking and embedding."""
        gtm_pack = data.get("gtm_pack", {})
        if not gtm_pack:
            return ""
        
        lines = [
            "=== GO-TO-MARKET STRATEGY ===",
            ""
        ]
        
        # GTM metadata
        if gtm_pack.get("version"):
            lines.append(f"Version: {gtm_pack.get('version')}")
        if gtm_pack.get("summary"):
            lines.append(f"Summary: {gtm_pack.get('summary')}")
        lines.append("")
        
        # Steps
        steps = gtm_pack.get("steps", [])
        if steps:
            lines.append(f"GTM STEPS ({len(steps)} total):")
            lines.append("")
            
            for step in steps:
                step_num = step.get("step", 0)
                step_name = step.get("name", "Unknown")
                
                lines.append(f"--- STEP {step_num}: {step_name} ---")
                
                # Content
                content = step.get("content", {})
                if content.get("decisions"):
                    lines.append("Strategic Decisions:")
                    for decision in content.get("decisions", []):
                        lines.append(f"  • {decision}")
                
                if content.get("plan"):
                    lines.append("Action Plan:")
                    for action in content.get("plan", []):
                        lines.append(f"  • {action}")
                
                if content.get("experiments"):
                    lines.append("Experiments:")
                    for exp in content.get("experiments", []):
                        exp_name = exp.get("name", "Unnamed")
                        exp_hypothesis = exp.get("hypothesis", "")
                        lines.append(f"  • {exp_name}: {exp_hypothesis}")
                
                # Description with citations
                description = step.get("description", "")
                if description:
                    lines.append(f"Rationale: {description}")
                
                # Assumptions
                assumptions = step.get("assumptions_applied", [])
                if assumptions:
                    lines.append("Assumptions Applied:")
                    for assumption in assumptions:
                        lines.append(f"  ⚠️ {assumption}")
                
                lines.append("")
        
        # Channel Plan
        channel_plan = gtm_pack.get("channel_plan", {})
        if channel_plan:
            lines.append("CHANNEL PLAN:")
            prioritized = channel_plan.get("prioritized_channels", [])
            for ch in prioritized:
                ch_name = ch.get("channel", "Unknown")
                ch_rationale = ch.get("rationale", "")
                lines.append(f"  • {ch_name}: {ch_rationale}")
            lines.append("")
        
        # Customer Success Motion
        cs_motion = gtm_pack.get("customer_success_motion", {})
        if cs_motion:
            lines.append("CUSTOMER SUCCESS MOTION:")
            lines.append(f"  Type: {cs_motion.get('motion_type', 'Unknown')}")
            lines.append(f"  Rationale: {cs_motion.get('motion_rationale', '')}")
            onboarding = cs_motion.get("onboarding_milestones", [])
            if onboarding:
                lines.append("  Onboarding Milestones:")
                for milestone in onboarding:
                    lines.append(f"    • {milestone}")
            lines.append("")
        
        # Metrics Plan
        metrics = gtm_pack.get("metrics_plan", {})
        if metrics:
            lines.append("METRICS DASHBOARD:")
            lines.append(f"  North Star: {metrics.get('north_star', 'TBD')}")
            lines.append(f"  Rationale: {metrics.get('north_star_rationale', '')}")
            funnel_kpis = metrics.get("funnel_kpis", [])
            if funnel_kpis:
                lines.append("  Funnel KPIs:")
                for kpi in funnel_kpis:
                    stage = kpi.get("stage", "")
                    metric = kpi.get("metric_name", "")
                    lines.append(f"    • {stage}: {metric}")
            lines.append("")
        
        # Execution Plan
        exec_plan = gtm_pack.get("execution_plan_30_60_90", {})
        if exec_plan:
            lines.append("30/60/90-DAY EXECUTION PLAN:")
            for period in ["days_0_30", "days_31_60", "days_61_90"]:
                milestones = exec_plan.get(period, [])
                if milestones:
                    period_label = period.replace("_", " ").replace("days ", "Days ").title()
                    lines.append(f"  {period_label}:")
                    for m in milestones:
                        milestone = m.get("milestone", "")
                        lines.append(f"    • {milestone}")
            lines.append("")
        
        # Experiment Backlog
        experiments = gtm_pack.get("experiment_backlog", {})
        if experiments:
            lines.append("EXPERIMENT BACKLOG:")
            channel_exps = experiments.get("channel_experiments", [])
            if channel_exps:
                lines.append("  Channel Experiments:")
                for exp in channel_exps:
                    lines.append(f"    • {exp.get('channel', 'Unknown')}: {exp.get('hypothesis', '')}")
            messaging_exps = experiments.get("messaging_experiments", [])
            if messaging_exps:
                lines.append("  Messaging Experiments:")
                for exp in messaging_exps:
                    lines.append(f"    • {exp.get('message_variant', 'Unknown')}: {exp.get('hypothesis', '')}")
            lines.append("")
        
        # Sources
        sources = gtm_pack.get("sources", [])
        if sources:
            lines.append(f"SOURCES ({len(sources)} citations):")
            for src in sources:
                src_id = src.get("id", "?")
                src_type = src.get("type", "unknown")
                if src_type == "project":
                    artifact = src.get("artifact_ref", "")
                    lines.append(f"  [{src_id}] (project) {artifact}")
                elif src_type == "web":
                    domain = src.get("domain", "")
                    lines.append(f"  [{src_id}] (web) {domain}")
            lines.append("")
        
        return "\n".join(lines)
    
    # ==================== TEXT SPLITTING ====================
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If not the last chunk, try to break at a sentence boundary
            if end < len(text):
                search_start = max(start, end - self.chunk_overlap)
                sentence_end = text.rfind(". ", search_start, end)
                
                if sentence_end != -1 and sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start with overlap
            start = end - self.chunk_overlap if end < len(text) else end
        
        return chunks
    
    # ==================== EMBEDDINGS ====================
    
    async def _generate_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        monitoring_context: Optional[Any] = None,
        feature_type: Optional[VMPFeatureType] = None,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for chunks with logging and monitoring."""
        feature_tag = f"[{feature_type.value}]" if feature_type else ""
        
        try:
            total_chars = sum(len(c.get("content", "")) for c in chunks)
            logger.info(f"🔄 VMP EMBEDDING {feature_tag}: Starting for {len(chunks)} chunks ({total_chars} chars)")
            
            texts = [chunk["content"] for chunk in chunks]
            
            # Generate embeddings with timeout
            embed_start = time.time()
            try:
                embeddings = await asyncio.wait_for(
                    self.embedding_service.generate_embeddings(texts),
                    timeout=120.0
                )
                embed_duration = time.time() - embed_start
                logger.info(f"✅ VMP EMBEDDING {feature_tag}: API call completed in {embed_duration:.2f}s")
            except asyncio.TimeoutError:
                embed_duration = time.time() - embed_start
                logger.error(f"❌ VMP EMBEDDING {feature_tag}: TIMEOUT after {embed_duration:.2f}s")
                return []
            
            if not embeddings:
                logger.error(f"❌ VMP EMBEDDING {feature_tag}: Empty result from embedding service")
                return []
            
            # Add embeddings to chunks
            valid_count = 0
            null_count = 0
            for i, chunk in enumerate(chunks):
                if i < len(embeddings) and embeddings[i] is not None:
                    chunk["embedding"] = embeddings[i]
                    valid_count += 1
                else:
                    chunk["embedding"] = []
                    null_count += 1
            
            if null_count > 0:
                logger.warning(f"⚠️ VMP EMBEDDING {feature_tag}: {null_count} chunks received null embeddings")
            
            logger.info(f"✅ VMP EMBEDDING {feature_tag}: SUCCESS - {valid_count}/{len(chunks)} valid embeddings in {embed_duration:.2f}s")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ VMP EMBEDDING {feature_tag}: EXCEPTION - {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    # ==================== STORAGE ====================
    
    async def _store_feature_chunks(
        self,
        project_id: str,
        tenant_id: str,
        feature_type: VMPFeatureType,
        chunks: List[Dict[str, Any]],
        persona_id: Optional[str] = None
    ) -> bool:
        """
        Store feature chunks in vector database.
        
        Handles regeneration by deleting old chunks with matching source_type
        before inserting new ones.
        """
        feature_tag = f"[{feature_type.value}]"
        store_start = time.time()
        
        try:
            logger.info(f"💾 VMP STORAGE {feature_tag}: Starting storage for project {project_id}")
            
            # Ensure document entry exists for FK constraint
            await self._ensure_document_exists(project_id, tenant_id)
            
            # Get existing chunks for this project
            existing_result = self.supabase.client.table("chunks").select(
                "id, chunk_index, metadata"
            ).eq("doc_id", project_id).execute()
            
            existing_chunks = existing_result.data or []
            logger.info(f"💾 VMP STORAGE {feature_tag}: Found {len(existing_chunks)} existing chunks for project")
            
            # Delete ONLY chunks with matching source_type (and persona_id if provided)
            chunks_to_delete = []
            for chunk in existing_chunks:
                metadata = chunk.get("metadata", {})
                if metadata.get("source_type") == feature_type.value:
                    # If persona_id specified, only delete chunks for that persona
                    if persona_id:
                        if metadata.get("persona_id") == persona_id:
                            chunks_to_delete.append(chunk["id"])
                    else:
                        chunks_to_delete.append(chunk["id"])
            
            if chunks_to_delete:
                delete_start = time.time()
                logger.info(f"🗑️ VMP STORAGE {feature_tag}: Deleting {len(chunks_to_delete)} old chunks (regeneration)")
                for chunk_id in chunks_to_delete:
                    self.supabase.client.table("chunks").delete().eq("id", chunk_id).execute()
                delete_duration = time.time() - delete_start
                logger.info(f"🗑️ VMP STORAGE {feature_tag}: Deleted {len(chunks_to_delete)} chunks in {delete_duration:.2f}s")
            else:
                logger.info(f"💾 VMP STORAGE {feature_tag}: No existing chunks to delete (first time chunking)")
            
            # Filter chunks with valid embeddings
            valid_chunks = [c for c in chunks if c.get("embedding")]
            invalid_count = len(chunks) - len(valid_chunks)
            
            if invalid_count > 0:
                logger.warning(f"⚠️ VMP STORAGE {feature_tag}: {invalid_count} chunks skipped (no embedding)")
            
            if not valid_chunks:
                logger.error(f"❌ VMP STORAGE {feature_tag}: No chunks with valid embeddings to store")
                return False
            
            # Find max chunk_index from remaining chunks
            remaining_chunks = [c for c in existing_chunks if c["id"] not in chunks_to_delete]
            max_index = max((c.get("chunk_index", -1) for c in remaining_chunks), default=-1)
            
            logger.info(f"📊 VMP STORAGE {feature_tag}: Max existing index={max_index}, inserting {len(valid_chunks)} new chunks")
            
            # Store chunks in batches
            batch_size = 50
            success_count = 0
            failed_batches = 0
            
            insert_start = time.time()
            for batch_num, i in enumerate(range(0, len(valid_chunks), batch_size)):
                batch = valid_chunks[i:i + batch_size]
                batch_data = []
                
                for idx, chunk in enumerate(batch):
                    new_index = max_index + 1 + i + idx
                    
                    # Ensure metadata has source_type and persona_id
                    metadata = chunk.get("metadata", {})
                    metadata["source_type"] = feature_type.value
                    if persona_id:
                        metadata["persona_id"] = persona_id
                    
                    batch_data.append({
                        "doc_id": project_id,
                        "chunk_index": new_index,
                        "content": chunk["content"],
                        "embedding": chunk["embedding"],
                        "metadata": metadata,
                        "created_at": datetime.utcnow().isoformat()
                    })
                
                try:
                    result = self.supabase.client.table("chunks").insert(batch_data).execute()
                    if result.data:
                        success_count += len(result.data)
                        logger.debug(f"💾 VMP STORAGE {feature_tag}: Batch {batch_num + 1} inserted {len(result.data)} chunks")
                except Exception as batch_error:
                    failed_batches += 1
                    logger.error(f"❌ VMP STORAGE {feature_tag}: Batch {batch_num + 1} failed: {batch_error}")
            
            insert_duration = time.time() - insert_start
            total_duration = time.time() - store_start
            
            success = success_count >= len(valid_chunks) * 0.8  # 80% success threshold
            success_rate = (success_count / len(valid_chunks) * 100) if valid_chunks else 0
            
            if success:
                logger.info(
                    f"✅ VMP STORAGE {feature_tag}: SUCCESS - Stored {success_count}/{len(valid_chunks)} chunks "
                    f"({success_rate:.1f}%) in {insert_duration:.2f}s (total: {total_duration:.2f}s)"
                )
            else:
                logger.error(
                    f"❌ VMP STORAGE {feature_tag}: FAILED - Only {success_count}/{len(valid_chunks)} chunks stored "
                    f"({success_rate:.1f}%), {failed_batches} batches failed"
                )
            
            return success
            
        except Exception as e:
            total_duration = time.time() - store_start
            logger.error(f"❌ VMP STORAGE {feature_tag}: EXCEPTION after {total_duration:.2f}s: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def _ensure_document_exists(self, project_id: str, tenant_id: str) -> None:
        """Ensure a document entry exists for the project (required for FK constraint)."""
        try:
            # Check if document exists
            result = self.supabase.client.table("documents").select("id").eq(
                "id", project_id
            ).execute()
            
            if not result.data:
                # Get VMP project info
                vmp_result = self.supabase.client.table("vmp_projects").select(
                    "name, user_id, parent_project_id, pv_report_id"
                ).eq("id", project_id).execute()
                
                if not vmp_result.data:
                    logger.error(f"❌ VMP STORAGE: VMP project {project_id} not found")
                    return
                
                vmp_project = vmp_result.data[0]
                parent_project_id = vmp_project.get("parent_project_id")
                
                # CRITICAL FIX: Ensure parent project exists in projects table
                if not parent_project_id:
                    logger.warning(f"⚠️ VMP STORAGE: No parent_project_id for VMP project {project_id}, creating parent project...")
                    parent_project_id = await self._create_parent_project(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        vmp_project=vmp_project
                    )
                    
                    if not parent_project_id:
                        logger.error(f"❌ VMP STORAGE: Failed to create parent project for {project_id}")
                        return
                else:
                    # Verify parent project exists
                    parent_check = self.supabase.client.table("projects").select("id").eq(
                        "id", parent_project_id
                    ).execute()
                    
                    if not parent_check.data:
                        logger.warning(f"⚠️ VMP STORAGE: Parent project {parent_project_id} doesn't exist, recreating...")
                        parent_project_id = await self._create_parent_project(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            vmp_project=vmp_project
                        )
                        
                        if not parent_project_id:
                            logger.error(f"❌ VMP STORAGE: Failed to recreate parent project for {project_id}")
                            return
                
                # Now create document entry with valid project_id FK
                self.supabase.client.table("documents").insert({
                    "id": project_id,
                    "tenant_id": tenant_id,
                    "project_id": parent_project_id,  # Use parent_project_id for FK
                    "source_type": "vp_map",
                    "title": f"VMP Project: {vmp_project.get('name', 'Unnamed')}",
                    "content": None,
                    "created_by": vmp_project.get("user_id"),
                    "metadata": {
                        "type": "vmp_project_chunks",
                        "created_for_chunking": True,
                        "vmp_project_id": project_id,
                        "parent_project_id": parent_project_id
                    }
                }).execute()
                
                logger.info(f"✅ VMP STORAGE: Created document entry for project {project_id} with parent {parent_project_id}")
                    
        except Exception as e:
            logger.error(f"❌ VMP STORAGE: Could not ensure document exists: {e}")
            import traceback
            logger.error(f"❌ VMP STORAGE: Traceback: {traceback.format_exc()}")
    
    async def _create_parent_project(
        self,
        project_id: str,
        tenant_id: str,
        vmp_project: Dict[str, Any]
    ) -> Optional[str]:
        """Create parent project in projects table for VMP project."""
        try:
            parent_data = {
                "tenant_id": tenant_id,
                "user_id": vmp_project.get("user_id"),
                "name": vmp_project.get("name", "VMP Project"),
                "description": f"Value proposition development project",
                "current_module": "value_proposition",
                "problem_statement": f"Value proposition development for {vmp_project.get('name', 'project')}",
                "pv_report_id": vmp_project.get("pv_report_id"),
                "status": "active",
                "settings": {
                    "vmp_enabled": True,
                    "created_by_chunking_service": True,
                    "vmp_project_id": project_id
                }
            }
            
            result = self.supabase.client.table("projects").insert(parent_data).execute()
            
            if result.data:
                parent_id = result.data[0]["id"]
                
                # Update VMP project with parent_project_id
                self.supabase.client.table("vmp_projects").update({
                    "parent_project_id": parent_id
                }).eq("id", project_id).execute()
                
                logger.info(f"✅ VMP STORAGE: Created parent project {parent_id} for VMP project {project_id}")
                return parent_id
            
            return None
            
        except Exception as e:
            logger.error(f"❌ VMP STORAGE: Error creating parent project: {e}")
            import traceback
            logger.error(f"❌ VMP STORAGE: Traceback: {traceback.format_exc()}")
            return None
    
    async def _load_project_data(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Load complete project data."""
        try:
            result = self.supabase.client.table("vmp_projects").select(
                "id, tenant_id, name, personas, vpc_data, vpc_v2_data, "
                "field_prep_data, mvp_data, analysis_data, soln_critique_data"
            ).eq("id", project_id).eq("tenant_id", tenant_id).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"❌ VMP CHUNKING: Error loading project: {e}")
            return None


# ==================== SINGLETON & CONVENIENCE FUNCTIONS ====================

_vmp_chunking_service: Optional[VMPProjectChunkingService] = None


def get_vmp_chunking_service() -> VMPProjectChunkingService:
    """Get singleton instance of VMP chunking service."""
    global _vmp_chunking_service
    if _vmp_chunking_service is None:
        _vmp_chunking_service = VMPProjectChunkingService()
    return _vmp_chunking_service


async def chunk_vmp_feature_background(
    project_id: str,
    tenant_id: str,
    feature_type: VMPFeatureType,
    feature_data: Dict[str, Any],
    persona_id: Optional[str] = None
) -> None:
    """
    Convenience function to chunk a feature in background.
    
    Usage:
        await chunk_vmp_feature_background(
            project_id="...",
            tenant_id="...",
            feature_type=VMPFeatureType.PERSONA,
            feature_data={"personas": [...]}
        )
    """
    service = get_vmp_chunking_service()
    await service.chunk_feature_background(
        project_id=project_id,
        tenant_id=tenant_id,
        feature_type=feature_type,
        feature_data=feature_data,
        persona_id=persona_id
    )
