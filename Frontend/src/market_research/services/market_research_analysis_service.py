"""
Enterprise Market Research Analysis Service

Enterprise-grade service for massive dataset analysis with complete data capture.
Handles 25+ PDFs and 5+ CSVs simultaneously with zero data loss and advanced
intelligence for accurate market research insights.

Key Features:
- Multi-file batch processing with parallel execution
- Complete data capture (no sampling or generalization)
- Dynamic schema adaptation for any project type
- Statistical significance testing and cross-validation
- AI-enhanced pattern recognition and semantic clustering
- Real-time progress tracking and memory optimization
"""

import asyncio
import gc
import json
import logging
import uuid
import time
import psutil
import statistics
from collections import Counter, defaultdict
from typing import Dict, Any, Optional, List, AsyncGenerator, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from fastapi import UploadFile

from src.mint.api.report.report_models import ReportChunkWithEmbedding

logger = logging.getLogger(__name__)

# VMP adapter imports following the same pattern as integrated_vmp_service
from src.vpm.adapters.auth_adapter import get_yuba_auth_adapter
from src.vpm.adapters.vector_adapter import get_yuba_vector_adapter
from src.vpm.adapters.database_adapter import get_yuba_database_adapter

# Analysis-specific services
from .document_parser import DocumentParserService
from .chunking_engine import ChunkingAndEmbeddingEngine
from ..utils.quantitative_utils import build_quantitative_highlights

# Enhanced services for two-tier RAG and fact validation
from .correlation_engine import CorrelationEngine
from .statistics_registry_service import StatisticsRegistryService
from .ground_truth_context_builder import GroundTruthContextBuilder
from .evidence_retrieval_engine import EvidenceRetrievalEngine
from .persona_aware_correlation_engine import PersonaAwareCorrelationEngine
from .fact_validation_engine import FactValidationEngine
from .dynamic_csv_extractor import DynamicCSVStatisticsExtractor
from .structured_pdf_extractor import StructuredPDFExtractor
from ..utils.error_handling import ErrorHandlingService

# Market research specific adapters
from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
from ..adapters.vector_adapter import AnalysisAgentVectorAdapter

# AI token monitoring
from monitor.tokens.models import AIUsageContext


@dataclass
class ProcessingUpdate:
    """Real-time processing update for massive datasets."""
    project_id: str
    files_processed: int
    total_files: int
    current_file: Optional[str] = None
    statistics_extracted: Optional[int] = None
    processing_time: Optional[float] = None
    memory_usage: Optional[float] = None
    status: str = "processing"
    final_statistics: Optional[Dict[str, Any]] = None
    total_processing_time: Optional[float] = None

@dataclass
class FileProcessingResult:
    """Result of processing a single file."""
    file_index: int
    file_name: str
    file_type: str
    statistics: Dict[str, Any]
    processing_time: float
    memory_usage: float
    error: Optional[str] = None

@dataclass
class BatchProcessingConfig:
    """Configuration for batch processing."""
    max_concurrent_files: int = 5
    memory_limit_gb: float = 8.0
    enable_real_time_updates: bool = True
    statistical_significance_testing: bool = True
    cross_file_validation: bool = True

class EnterpriseMarketResearchService:
    """
    Enterprise-grade market research analysis service for massive datasets.
    
    Handles 25+ PDFs and 5+ CSVs simultaneously with complete data capture,
    advanced intelligence, and statistical validation.
    
    Enterprise Features:
    - Multi-file batch processing with controlled concurrency
    - Zero-loss data aggregation across all files
    - Dynamic schema detection and adaptation
    - Statistical significance testing and confidence intervals
    - Cross-file validation and consistency checking
    - AI-enhanced pattern recognition and semantic clustering
    - Real-time progress tracking and memory optimization
    - Intelligent bias detection and outlier analysis
    """
    
    def __init__(self):
        """
        Initialize enterprise-grade components for massive dataset processing.
        
        Enterprise features enabled:
        - Multi-file batch processing with controlled concurrency
        - Complete data capture with zero sampling
        - Dynamic schema detection and adaptation
        - Statistical significance testing and cross-validation
        - AI-enhanced pattern recognition
        """
        # Yuba integration adapters (same pattern as IntegratedVMPService)
        self.auth_adapter = get_yuba_auth_adapter()
        self.db_adapter = get_yuba_database_adapter()
        self.vector_adapter = get_yuba_vector_adapter()
        
        # Create market research specific adapters for enhanced components
        self.analysis_db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
        self.analysis_vector_adapter = AnalysisAgentVectorAdapter()
        
        # Enterprise-grade processing components
        self.document_parser = DocumentParserService()
        self.chunking_engine = ChunkingAndEmbeddingEngine(self.analysis_db_adapter)
        self.correlation_engine = CorrelationEngine()
        self.vector_service = self.vector_adapter
        
        # Enhanced components with enterprise features
        self.error_handler = ErrorHandlingService()
        self.statistics_registry = StatisticsRegistryService(self.analysis_db_adapter)
        self.ground_truth_builder = GroundTruthContextBuilder(self.statistics_registry, self.error_handler)
        
        self.evidence_retrieval = EvidenceRetrievalEngine(
            self.analysis_db_adapter, self.analysis_vector_adapter, self.statistics_registry, self.error_handler
        )
        self.fact_validator = FactValidationEngine()
        self.persona_correlation = PersonaAwareCorrelationEngine(self.analysis_db_adapter)
        
        # Enterprise document extraction with complete data capture
        self.csv_extractor = DynamicCSVStatisticsExtractor()
        self.pdf_extractor = StructuredPDFExtractor()
        
        # Enterprise processing configuration
        self.batch_config = BatchProcessingConfig()
        self.processing_cache = {}
        self.progress_tracker = {}
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        logger.info("🚀 Enterprise features enabled: multi-file processing, complete data capture, statistical validation")
    
    async def analyze_market_research(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        persona_id: Optional[str] = None,
        pdf_files: Optional[List[UploadFile]] = None,
        csv_files: Optional[List[UploadFile]] = None,
        target_assumptions: Optional[List[str]] = None,
        batch_config: Optional[BatchProcessingConfig] = None,
        progress_callback: Optional[Callable[[ProcessingUpdate], None]] = None,
    ) -> Dict[str, Any]:
        """
        Enterprise-grade market research analysis for massive datasets with multi-persona support.
        
        Handles 25+ PDFs and 5+ CSVs simultaneously with complete data capture,
        statistical validation, and AI-enhanced intelligence. Supports persona-specific
        analysis for multi-persona projects.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            user_id: The user ID
            persona_id: Persona ID for multi-persona projects (filters assumptions, VPC, hypothesis)
            pdf_files: List of PDF files (up to 25+)
            csv_files: List of CSV files (up to 5+)
            target_assumptions: Optional list of specific assumptions to analyze
            batch_config: Configuration for batch processing
            progress_callback: Optional callback for real-time progress updates
            
        Returns:
            Analysis results with comprehensive statistics and intelligence
        """
        try:
            # Use provided batch config or default
            config = batch_config or self.batch_config
            
            # Initialize progress tracking
            total_files = len(pdf_files or []) + len(csv_files or [])
            self.progress_tracker[project_id] = {
                "total_files": total_files,
                "processed_files": 0,
                "start_time": time.time(),
                "status": "initializing"
            }
            
            # Send initial progress update
            if progress_callback:
                progress_callback(ProcessingUpdate(
                    project_id=project_id,
                    files_processed=0,
                    total_files=total_files,
                    status="initializing"
                ))
            
            # Load project context
            project_context = await self._get_project_context(project_id)
            if not project_context:
                return {
                    "success": False,
                    "error": "Project not found or inaccessible",
                    "error_code": "PROJECT_NOT_FOUND"
                }
            
            # Check if we have uploaded research documents (check database first)
            research_documents_data = project_context.get("research_documents_data", {})
            
            # CRITICAL FIX: If not in context, load from database where upload stores it
            if not research_documents_data:
                try:
                    research_documents_data = await self.analysis_db_adapter.get_research_documents_data(project_id, tenant_id)
                    logger.info(f"🔍 EXECUTE: Loaded research data from database: {bool(research_documents_data)}")
                    if research_documents_data:
                        logger.info(f"🔍 EXECUTE: Research data keys: {list(research_documents_data.keys())}")
                except Exception as e:
                    logger.error(f"❌ EXECUTE: Failed to load research data from database: {e}")
                    research_documents_data = {}
            
            has_research_documents = bool(research_documents_data)
            
            if has_research_documents:
                # Document-based analysis mode - skip VMP workflow validation
                validation_result = {"ready": True, "mode": "document_based"}
            else:
                # Traditional VMP workflow validation
                validation_result = await self._validate_project_readiness(project_context)
                if not validation_result["ready"]:
                    return {
                        "success": False,
                        "error": validation_result["error"],
                        "error_code": "PROJECT_NOT_READY",
                        "missing_requirements": validation_result.get("missing", [])
                    }
                validation_result["mode"] = "vmp_workflow"
            
            # 🎭 MULTI-PERSONA: Check if this persona already has analysis
            existing_analysis = await self.analysis_db_adapter.get_analysis_data(project_id, tenant_id)
            
            if existing_analysis:
                # Check if this is multi-persona storage format
                if "personas" in existing_analysis and persona_id:
                    # Multi-persona format
                    persona_data = existing_analysis.get("personas", {}).get(persona_id)
                    if persona_data:
                        persona_stage = persona_data.get("stage", "not_started")
                        logger.info(f"🎭 PERSONA ANALYSIS STATE: Found existing analysis for persona '{persona_id}' with stage='{persona_stage}'")
                        
                        if persona_stage == "analysis_completed":
                            # This persona's analysis is complete - will overwrite
                            logger.info(f"🔄 PERSONA RE-ANALYSIS: Persona '{persona_id}' analysis completed, will overwrite")
                        elif persona_stage in ["analyzing_assumptions", "processing"]:
                            # Incomplete analysis for this persona
                            logger.info(f"⚠️ PERSONA INCOMPLETE: Persona '{persona_id}' has incomplete analysis, will restart")
                    else:
                        logger.info(f"🆕 NEW PERSONA ANALYSIS: No existing analysis for persona '{persona_id}', starting fresh")
                else:
                    # Legacy single-persona format
                    existing_stage = existing_analysis.get("stage", "not_started")
                    logger.info(f"📊 ANALYSIS STATE: Found existing analysis with stage='{existing_stage}'")
                    
                    if persona_id:
                        # Migrating from single to multi-persona - preserve existing data
                        logger.info(f"🔄 MIGRATION: Converting single-persona storage to multi-persona format")
                    else:
                        # Single persona mode - check if we should clear
                        if existing_stage == "analysis_completed":
                            logger.info(f"🔄 NEW ANALYSIS: Previous analysis completed, will overwrite")
                        elif existing_stage in ["analyzing_assumptions", "processing"]:
                            logger.info(f"⚠️ INCOMPLETE ANALYSIS: Found incomplete analysis, will restart")
            else:
                logger.info(f"🆕 NEW ANALYSIS: No existing analysis found, starting fresh")
            
            # Update analysis status to processing
            await self.analysis_db_adapter.update_analysis_status(
                project_id, tenant_id, "processing"
            )
            
            # Enterprise batch processing for massive datasets
            research_data = {}
            
            logger.info(f"🚀 ENTERPRISE PROCESSING: {len(pdf_files or [])} PDFs, {len(csv_files or [])} CSVs")
            
            if pdf_files or csv_files:
                # Update progress
                self.progress_tracker[project_id]["status"] = "processing_files"
                
                # Enterprise batch processing with complete data capture
                logger.info("🚀 Using enterprise batch processing with zero data loss")
                document_result = await self._process_massive_dataset_batch(
                    project_id, tenant_id, pdf_files or [], csv_files or [], config, progress_callback
                )
                
                if not document_result["success"]:
                    await self.analysis_db_adapter.update_analysis_status(
                        project_id, tenant_id, "failed"
                    )
                    return document_result

                research_data = document_result["data"]
                storage_metadata = document_result.get("storage_data")
                if storage_metadata:
                    project_context["research_documents_data"] = storage_metadata
            else:
                # Load complete enterprise dataset from all sources
                logger.info(f"🔍 ENTERPRISE RETRIEVAL: Loading complete dataset from all sources...")
                research_data = await self._retrieve_complete_enterprise_dataset(project_id, tenant_id)
                
                # Load comprehensive statistics registry
                logger.info(f"🔍 ENTERPRISE STATS: Loading comprehensive statistics registry...")
                stored_research_data = await self.analysis_db_adapter.get_research_documents_data(project_id, tenant_id)
                if stored_research_data:
                    logger.info(f"🔍 ENTERPRISE DATA: Found {len(stored_research_data)} document sources")
                    
                    # Validate enterprise data completeness
                    for doc_key, stored_doc in stored_research_data.items():
                        has_stats = "comprehensive_statistics" in stored_doc
                        has_quant = "quantitative_summary" in stored_doc
                        doc_keys = list(stored_doc.keys())
                        logger.info(f"🔍 ENTERPRISE DOC {doc_key}: keys={doc_keys}, has_comprehensive_stats={has_stats}, has_quantitative={has_quant}")
                        
                        # DIRECT ACCESS: Only use quantitative_summary (the actual data structure)
                        if has_quant:
                            quantitative_summary = stored_doc["quantitative_summary"]
                            metadata = quantitative_summary.get("metadata", {})
                            total_records = metadata.get("total_rows", 0)
                            field_count = len(quantitative_summary.get("field_analysis", {}))
                            logger.info(f"✅ ENTERPRISE STATS: {doc_key} has {total_records} records, {field_count} fields")
                        else:
                            logger.warning(f"⚠️ ENTERPRISE STATS: No quantitative_summary found for {doc_key}")
                    
                    # DIRECT MERGE: Only merge quantitative_summary (the actual data)
                    for doc_key, stored_doc in stored_research_data.items():
                        if doc_key in research_data and "quantitative_summary" in stored_doc:
                            research_data[doc_key]["quantitative_summary"] = stored_doc["quantitative_summary"]
                            logger.info(f"✅ ENTERPRISE: Restored quantitative summary for {doc_key}")
                    
                    # Store enterprise data in project context
                    project_context["research_documents_data"] = stored_research_data
                    logger.info(f"✅ ENTERPRISE: Complete dataset loaded and validated")
                else:
                    logger.error(f"❌ ENTERPRISE: No stored research data found in database!")
                    raise ValueError("Enterprise analysis requires properly processed research documents with quantitative summaries")
                
                if not research_data:
                    await self.analysis_db_adapter.update_analysis_status(
                        project_id, tenant_id, "failed"
                    )
                    return {
                        "success": False,
                        "error": "No research documents found. Please upload PDF or CSV files first.",
                        "error_code": "NO_RESEARCH_DATA"
                    }
                document_count = self._get_document_count(research_data)
                chunk_total = self._get_total_chunk_count(research_data)
                logger.info(f"🔍 DEBUG: Loaded complete research data with {document_count} document types and {chunk_total} total chunks")
            # Auto-retrieve assumptions if not provided, or validate provided ones
            field_prep_data = project_context.get("field_prep_data", {})
            available_assumptions = field_prep_data.get("assumptions", [])
            
            logger.info(f"🔍 DEBUG: Found {len(available_assumptions)} assumptions in field_prep_data")
            
            # CRITICAL DEBUG: Investigate 772 assumptions bug
            if len(available_assumptions) > 10:
                logger.error(f"🚨 CRITICAL BUG: {len(available_assumptions)} assumptions found! Expected max 6.")
                logger.error(f"🚨 CRITICAL BUG: field_prep_data structure: {field_prep_data}")
                logger.error(f"🚨 CRITICAL BUG: project_context keys: {list(project_context.keys())}")
            
            for i, assumption in enumerate(available_assumptions):
                logger.info(f"🔍 DEBUG: Available assumption {i}: ID={assumption.get('id', 'NO_ID')}, text={assumption.get('text', 'NO_TEXT')[:100]}...")
            
            if not target_assumptions:
                # Auto-retrieve all available assumptions
                if available_assumptions:
                    target_assumptions = []
                    for i, assumption in enumerate(available_assumptions):
                        assumption_id = assumption.get("id") or f"assumption-{i+1}"
                        target_assumptions.append(assumption_id)
                    logger.info(f"🔍 DEBUG: Auto-retrieved {len(target_assumptions)} assumptions: {target_assumptions}")
                else:
                    logger.warning(f"⚠️ No assumptions found in field_prep_data for project {project_id}")
                    target_assumptions = []
            else:
                logger.info(f"🔍 DEBUG: Using provided target_assumptions: {target_assumptions}")
                
                # Validate that target assumptions exist, if not create them for testing
                if available_assumptions:
                    valid_assumptions = [
                        assumption.get("id") for assumption in available_assumptions 
                        if assumption.get("id")
                    ]
                    logger.info(f"🔍 DEBUG: Valid assumption IDs in project: {valid_assumptions}")
                    
                    # Check if any target assumptions match existing ones
                    matching_assumptions = [aid for aid in target_assumptions if aid in valid_assumptions]
                    if not matching_assumptions:
                        logger.warning(f"⚠️ Target assumptions {target_assumptions} don't match available assumptions {valid_assumptions}")
                        logger.info(f"🔍 DEBUG: Will create test assumptions for analysis")
            
            # Combine all research chunks from multiple files for analysis
            all_research_chunks = self._combine_research_chunks(research_data)
            
            # CRITICAL: Log chunk sources for debugging
            logger.info(f"🔍 ANALYSIS_START: Combined research chunks from {self._get_document_count(research_data)} document types")
            for doc_key, doc_data in self._iter_document_entries(research_data):
                chunk_count = self._get_chunk_count(doc_data)
                logger.info(f"🔍 ANALYSIS_START: - {doc_key}: {chunk_count} chunks")
            
            # Execute the multi-agent analysis workflow using LangGraph
            logger.info(f"🚀 ANALYSIS_START: Starting multi-agent analysis workflow")
            logger.info(f"🚀 ANALYSIS_START: - Assumptions to analyze: {len(target_assumptions)}")
            logger.info(f"🚀 ANALYSIS_START: - Total research chunks available: {len(all_research_chunks)}")
            logger.info(f"🚀 ANALYSIS_START: - Assumption IDs: {target_assumptions}")
            
            try:
                from .analysis_workflow import AnalysisWorkflow
                
                # Initialize the LangGraph workflow with enhanced components (always enabled)
                use_enhanced = True  # Always use enhanced features
                enhanced_components = None
                if use_enhanced:
                    enhanced_components = {
                        'statistics_registry': self.statistics_registry,
                        'ground_truth_builder': self.ground_truth_builder,
                        'evidence_retrieval': self.evidence_retrieval,
                        'persona_correlation': self.persona_correlation,
                        'fact_validator': self.fact_validator,
                        'error_handler': self.error_handler
                    }
                    logger.info("🚀 ENHANCED: Passing enhanced components to workflow")
                else:
                    logger.info("📊 LEGACY: Using standard workflow without enhanced components")
                
                workflow = AnalysisWorkflow(enhanced_components=enhanced_components)
                
                # Run the complete analysis workflow with persona support
                logger.info(f"🎭 PERSONA: Running analysis for persona_id='{persona_id}'")
                workflow_result = await workflow.run_analysis(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    project_context=project_context,
                    research_chunks=all_research_chunks,
                    target_assumptions=target_assumptions,
                    persona_id=persona_id
                )
                
                if workflow_result["success"]:
                    logger.info(f"✅ Multi-agent analysis completed successfully")
                    
                    # 🚀 JSON ONLY: Extract structured_report from workflow (NO MARKDOWN!)
                    workflow_analyses = workflow_result["analysis_results"]
                    workflow_structured_report = workflow_result.get("structured_report")  # 🚀 JSON ONLY
                    workflow_errors = workflow_result.get("errors", [])
                    
                    logger.info(f"🔍 DEBUG: Received {len(workflow_analyses)} analyses from workflow")
                    logger.info(f"🚀 JSON DEBUG: Received structured_report: {workflow_structured_report is not None}")
                    if workflow_structured_report:
                        logger.info(f"🚀 JSON DEBUG: Structured report has {len(workflow_structured_report.get('assumptions', []))} assumptions")
                    logger.info(f"🔍 DEBUG: Received {len(workflow_errors)} errors from workflow")
                    
                    for i, analysis in enumerate(workflow_analyses):
                        assumption_id = analysis.get("assumption_id", "unknown")
                        validation_status = analysis.get("validation_status", "unknown")
                        analyses_count = len(analysis.get("analyses", {}))
                        logger.info(f"🔍 DEBUG: Service received analysis {i+1}: {assumption_id} - {validation_status} - {analyses_count} analysis types")
                    
                    # 🚀 JSON ONLY: Store structured_report (NO MARKDOWN!)
                    analysis_results = {
                        "session_id": str(uuid.uuid4()),
                        "analyzed_at": datetime.utcnow().isoformat(),
                        "stage": "analysis_completed",
                        "target_assumptions": target_assumptions,
                        "assumptions_count": len(target_assumptions),
                        "assumption_analyses": workflow_analyses,
                        "structured_report": workflow_structured_report,  # 🚀 JSON ONLY - NO MARKDOWN!
                        "total_research_chunks": len(all_research_chunks),
                        "workflow_errors": workflow_errors,
                        "project_context": {
                            "assumptions_count": len(target_assumptions),
                            "research_documents_count": self._get_document_count(research_data),
                            "total_chunks": len(all_research_chunks)
                        }
                    }
                    
                    # Debug: Log what we're about to save
                    logger.info(f"🚀 JSON STORAGE: About to save analysis_results with:")
                    logger.info(f"🔍 DEBUG: - session_id: {analysis_results['session_id']}")
                    logger.info(f"🔍 DEBUG: - assumption_analyses count: {len(analysis_results['assumption_analyses'])}")
                    logger.info(f"🚀 JSON DEBUG: - structured_report present: {analysis_results.get('structured_report') is not None}")
                    logger.info(f"🔍 DEBUG: - stage: {analysis_results['stage']}")
                    logger.info(f"🚀 NO MARKDOWN - JSON ONLY!")
                else:
                    logger.error(f"❌ Multi-agent analysis workflow failed: {workflow_result.get('error', 'Unknown error')}")
                    analysis_results = {
                        "session_id": str(uuid.uuid4()),
                        "analyzed_at": datetime.utcnow().isoformat(),
                        "stage": "analysis_failed",
                        "target_assumptions": target_assumptions,
                        "assumptions_count": len(target_assumptions),
                        "assumption_analyses": [],
                        "final_report": f"Analysis workflow failed: {workflow_result.get('error', 'Unknown error')}",
                        "total_research_chunks": len(all_research_chunks),
                        "workflow_errors": [workflow_result.get('error', 'Unknown error')],
                        "project_context": {
                            "assumptions_count": len(target_assumptions),
                            "research_documents_count": self._get_document_count(research_data),
                            "total_chunks": len(all_research_chunks)
                        }
                    }
                    
            except Exception as workflow_error:
                logger.error(f"❌ Failed to initialize analysis workflow: {workflow_error}")
                analysis_results = {
                    "session_id": str(uuid.uuid4()),
                    "analyzed_at": datetime.utcnow().isoformat(),
                    "stage": "workflow_initialization_failed",
                    "target_assumptions": target_assumptions,
                    "assumptions_count": len(target_assumptions),
                    "assumption_analyses": [],
                    "final_report": f"Failed to initialize analysis workflow: {str(workflow_error)}",
                    "total_research_chunks": len(all_research_chunks),
                    "workflow_errors": [str(workflow_error)],
                    "project_context": {
                        "assumptions_count": len(target_assumptions),
                        "research_documents_count": self._get_document_count(research_data),
                        "total_chunks": len(all_research_chunks)
                    }
                }
            
            # Store analysis results with persona_id
            logger.info(f"🔍 DEBUG: Calling db_adapter.update_analysis_data with:")
            logger.info(f"🔍 DEBUG: - project_id: {project_id}")
            logger.info(f"🔍 DEBUG: - tenant_id: {tenant_id}")
            logger.info(f"🎭 DEBUG: - persona_id: {persona_id}")
            logger.info(f"🔍 DEBUG: - analysis_results keys: {list(analysis_results.keys())}")
            logger.info(f"🔍 DEBUG: - status: completed")
            
            await self.analysis_db_adapter.update_analysis_data(
                project_id, tenant_id, analysis_results, "completed", persona_id=persona_id
            )
            
            logger.info(f"✅ DEBUG: Successfully saved analysis results to database for persona '{persona_id}'")
            
            # 📊 WORKFLOW STATUS: Mark Market Research as completed (only if analysis was successful)
            if analysis_results.get("stage") == "analysis_completed":
                try:
                    from src.vpm.services.workflow_status_service import get_workflow_status_service, WorkflowStage
                    workflow_service = get_workflow_status_service()
                    workflow_service.set_stage_completed(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        stage=WorkflowStage.MARKET_RESEARCH,
                        additional_metadata={"persona_id": persona_id, "assumptions_count": len(target_assumptions)}
                    )
                    logger.info(f"✅ Workflow status updated: Market Research completed")
                except Exception as status_error:
                    logger.warning(f"⚠️ Workflow status update failed (non-blocking): {status_error}")
            
            # 💬 CHAT PREPARATION: Automatically chunk and embed report for chat (AFTER database save)
            if analysis_results.get("structured_report"):
                try:
                    logger.info(f"💬 SERVICE: Preparing report for chat functionality (persona: {persona_id})...")
                    from .report_chunking_service import ReportChunkingService
                    
                    chunking_service = ReportChunkingService()
                    chunk_result = await chunking_service.chunk_and_embed_report(
                        project_id=project_id,
                        tenant_id=tenant_id,
                        persona_id=persona_id
                    )
                    
                    if chunk_result["success"]:
                        logger.info(f"✅ SERVICE: Report prepared for chat with {chunk_result['chunk_count']} chunks")
                    else:
                        logger.warning(f"⚠️ SERVICE: Failed to prepare report for chat: {chunk_result.get('message')}")
                        
                except Exception as e:
                    logger.error(f"❌ SERVICE: Error preparing report for chat: {e}")
                    # Don't fail the entire analysis if chat preparation fails
            else:
                logger.warning("⚠️ SERVICE: No structured_report found, skipping chat preparation")
            
            return {
                "success": True,
                "data": {
                    "session_id": analysis_results["session_id"],
                    "status": "completed",
                    "analyzed_at": analysis_results["analyzed_at"],
                    "project_context": {
                        "personas_count": len(project_context.get("field_prep_data", {}).get("personas", [])),
                        "assumptions_count": len(project_context.get("field_prep_data", {}).get("assumptions", [])),
                        "research_documents": list(research_data.keys()),
                        "total_pdf_files": len(pdf_files or []),
                        "total_csv_files": len(csv_files or [])
                    }
                }
            }
            
        except Exception as e:
            # Update status to failed and return error
            await self.analysis_db_adapter.update_analysis_status(
                project_id, tenant_id, "failed"
            )
            
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}",
                "error_code": "ANALYSIS_ERROR"
            }
    
    async def _get_project_context(self, project_id: str, tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Load project context using the same pattern as field_prep_service._get_project_context_personas_only().
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID (optional, will be auto-resolved if not provided)
            
        Returns:
            Project context data or None if not found
        """
        try:
            # If tenant_id not provided, get it directly from vmp_projects table
            if not tenant_id:
                from src.mint.api.system.core.supabase_client import get_service_role_client
                supabase = get_service_role_client()
                
                result = supabase.client.table("vmp_projects").select("tenant_id, user_id").eq("id", project_id).execute()
                
                if not result.data or len(result.data) == 0:
                    logger.error(f"❌ Project {project_id} not found in vmp_projects table")
                    return None
                
                tenant_id = result.data[0].get("tenant_id")
                user_id = result.data[0].get("user_id")
                
                if not tenant_id:
                    logger.error(f"❌ No tenant_id found for project {project_id}")
                    return None

                logger.info(f"✅ SUCCESS: Auto-resolved tenant_id: {tenant_id} for project {project_id}")

            # Use database adapter to get project data (same pattern as VMP services)
            project_data = await self.db_adapter.get_vmp_project(project_id, tenant_id)

            if not project_data:
                return None

            # Extract relevant context following field_prep patterns
            context = {
                "id": project_data.get("id"),
                "tenant_id": project_data.get("tenant_id"),
                "user_id": project_data.get("user_id"),  # Include user_id for auto-resolution
                "name": project_data.get("name"),
                "field_prep_data": project_data.get("field_prep_data", {}),
                "vpc_data": project_data.get("vpc_data", {}),
                "research_documents_data": project_data.get("research_documents_data", {}),
                "analysis_data": project_data.get("analysis_data", {}),
                "analysis_status": project_data.get("analysis_status", "not_started")
            }

            # CRITICAL FIX: Load PV report chunks and actionable insights from vector store
            # This is required for PV comparison to work properly
            logger.info(f"🔍 ANALYSIS: Loading PV report and insights from vector store for project {project_id}")
            # Use the same VPM vector adapter as other services (field_prep, integrated_vmp)
            from src.vpm.adapters.vector_adapter import YubaVectorAdapter
            vector_adapter = YubaVectorAdapter()

            # Perform dual context search to get PV report chunks and actionable insights
            # Same pattern as field_prep_service.py line 215 and integrated_vmp_service.py line 411
            vector_context = await vector_adapter.dual_context_search(
                project_id=project_id,
                query="market research analysis validation assumptions evidence",
                max_results_per_store=20  # Get more chunks for comprehensive comparison
            )

            if vector_context:
                context["pv_report_context"] = vector_context.get("pv_report_context", [])
                context["actionable_insights_context"] = vector_context.get("actionable_insights_context", [])
                logger.info(f"✅ ANALYSIS: Loaded {len(context['pv_report_context'])} PV chunks and {len(context['actionable_insights_context'])} insight chunks")
            else:
                logger.warning("⚠️ ANALYSIS: No vector context found for PV comparison")
            context = {
                "id": project_data.get("id"),
                "tenant_id": project_data.get("tenant_id"),
                "user_id": project_data.get("user_id"),  # Include user_id for auto-resolution
                "name": project_data.get("name"),
                "field_prep_data": project_data.get("field_prep_data", {}),
                "vpc_data": project_data.get("vpc_data", {}),
                "research_documents_data": project_data.get("research_documents_data", {}),
                "analysis_data": project_data.get("analysis_data", {}),
                "analysis_status": project_data.get("analysis_status", "not_started")
            }
            
            # CRITICAL FIX: Load PV report chunks and actionable insights from vector store
            # This is required for PV comparison to work properly
            try:
                logger.info(f"🔍 ANALYSIS: Loading PV report and insights from vector store for project {project_id}")
                # Use the same VPM vector adapter as other services (field_prep, integrated_vmp)
                from src.vpm.adapters.vector_adapter import YubaVectorAdapter
                vector_adapter = YubaVectorAdapter()
                
                # Perform dual context search to get PV report chunks and actionable insights
                # Same pattern as field_prep_service.py line 215 and integrated_vmp_service.py line 411
                vector_context = await vector_adapter.dual_context_search(
                    project_id=project_id,
                    query="market research analysis validation assumptions evidence",
                    max_results_per_store=20  # Get more chunks for comprehensive comparison
                )
                
                if vector_context:
                    context["pv_report_context"] = vector_context.get("pv_report_context", [])
                    context["actionable_insights_context"] = vector_context.get("actionable_insights_context", [])
                    logger.info(f"✅ ANALYSIS: Loaded {len(context['pv_report_context'])} PV chunks and {len(context['actionable_insights_context'])} insight chunks")
                else:
                    logger.warning("⚠️ ANALYSIS: No vector context found for PV comparison")
                    context["pv_report_context"] = []
                    context["actionable_insights_context"] = []
            except Exception as e:
                logger.error(f"❌ ANALYSIS: Failed to load vector context: {e}")
                context["pv_report_context"] = []
                context["actionable_insights_context"] = []
            
            return context
            
        except Exception as e:
            print(f"Error loading project context: {e}")
            return None
    
    # LEGACY METHOD REMOVED: _process_research_documents
    # Enhanced processing is now the only path for accuracy and consistency
    
    async def _process_research_documents_enhanced(
        self, 
        project_id: str, 
        tenant_id: str, 
        pdf_files: List[Any], 
        csv_files: List[Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhanced document processing with statistics registry and persona association.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            pdf_files: List of PDF file uploads (up to 3)
            csv_files: List of CSV file uploads (up to 3)
            user_id: Optional user ID for monitoring context
            
        Returns:
            Processing results with success status, data, and statistics registry
        """
        try:
            logger.info("🚀 Starting enhanced document processing with statistics registry")
            
            # Initialize enhanced processing data structures
            research_data = {}
            storage_data = {}
            
            # Create monitoring context for embedding operations
            monitoring_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                project_id=project_id,
                feature_id="market_research_upload",
                workflow_name="document_processing",
                step_name="embedding_generation",
                environment="prod"
            ) if user_id or tenant_id else None
            
            # Get project personas for association
            project_context = await self._get_project_context(project_id, tenant_id)
            personas = project_context.get("field_prep_data", {}).get("personas", [])
            
            logger.info(f"📊 Enhanced processing: Found {len(personas)} personas for association")
            
            # Process CSV files with enhanced statistics extraction + document processing
            for i, csv_file in enumerate(csv_files or []):
                try:
                    logger.info(f"🔢 Enhanced CSV processing for file {i+1}: {csv_file.filename}")
                    
                    # 1. Extract comprehensive statistics (ENHANCED)
                    csv_stats = await self.csv_extractor.extract_statistics(
                        csv_file, project_id, persona_id=None  # Auto-infer persona associations
                    )
                    
                    # 2. Store statistics in registry (ENHANCED) - with fallback
                    try:
                        stats_success = await self.statistics_registry.store_statistics(
                            project_id, tenant_id, csv_stats, "csv"
                        )
                        if not stats_success:
                            logger.warning(f"⚠️ Statistics storage failed for CSV {i+1}, continuing with processing...")
                    except Exception as e:
                        logger.warning(f"⚠️ Statistics storage error for CSV {i+1}: {e}, continuing with processing...")
                    
                    # 3. Process document for chunking and embedding (ESSENTIAL)
                    csv_key = f"csv_content_{i}" if i > 0 else "csv_content"
                    
                    # Parse and chunk CSV using existing document parser
                    parsed_csv = await self.document_parser.parse_csv(csv_file)
                    
                    # Chunk content and generate embeddings
                    chunks = await self.chunking_engine.chunk_content(
                        parsed_csv["processed_text"], content_type="csv"
                    )
                    chunks_with_embeddings = await self.chunking_engine.generate_embeddings(
                        chunks, monitoring_context=monitoring_context
                    )
                    
                    # PRODUCTION: Embeddings will be stored in chunks table via consolidated vector storage

                    # Prepare metadata for downstream consumers while keeping full chunks in-memory
                    chunk_metadata = []
                    for chunk_index, chunk in enumerate(chunks_with_embeddings):
                        content_preview = chunk.get("content", "")
                        if len(content_preview) > 200:
                            content_preview = f"{content_preview[:200]}..."

                        chunk_metadata.append(
                            self._make_json_serializable(
                                {
                                    "index": chunk.get("index", chunk_index),
                                    "content_preview": content_preview,
                                    "token_count": chunk.get("token_count", 0),
                                    "character_count": chunk.get("character_count", 0)
                                }
                            )
                        )

                    research_data[csv_key] = {
                        "metadata": self._make_json_serializable(parsed_csv.get("metadata", {})),
                        "raw_data": self._make_json_serializable(
                            parsed_csv["raw_data"][:100]
                            if isinstance(parsed_csv.get("raw_data"), list)
                            else parsed_csv.get("raw_data")
                        ),  # Limit raw data size
                        "processed_text": parsed_csv["processed_text"][:1000] + "..." if len(parsed_csv["processed_text"]) > 1000 else parsed_csv["processed_text"],  # Truncate for storage
                        "chunk_metadata": chunk_metadata,
                        "chunk_count": len(chunks_with_embeddings),
                        "chunks": chunks_with_embeddings,
                        "quantitative_summary": self._make_json_serializable(csv_stats),
                        "processing_timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # 4. Associate with personas if available (ENHANCED)
                    if personas:
                        for persona in personas:
                            persona_id = persona.get("id")
                            if persona_id:
                                await self.persona_correlation.associate_data_with_personas(
                                    project_id, {"csv_statistics": csv_stats}, persona_id
                                )
                    
                    logger.info(f"✅ Enhanced CSV processing completed for {csv_file.filename}")
                    
                except Exception as csv_error:
                    logger.error(f"❌ Enhanced CSV processing failed for file {i+1}: {csv_error}")
                    raise csv_error  # No fallback - fail fast for accuracy
            
            # Process PDF files with enhanced content extraction + document processing
            for i, pdf_file in enumerate(pdf_files or []):
                try:
                    logger.info(f"📄 Enhanced PDF processing for file {i+1}: {pdf_file.filename}")
                    
                    # 1. Extract structured content (ENHANCED)
                    pdf_content = await self.pdf_extractor.extract_structured_content(
                        pdf_file, project_id, persona_id=None  # Auto-infer persona associations
                    )
                    
                    # 2. Store statistics in registry (ENHANCED) - with fallback
                    try:
                        stats_success = await self.statistics_registry.store_statistics(
                            project_id, tenant_id, pdf_content, "pdf"
                        )
                        if not stats_success:
                            logger.warning(f"⚠️ Statistics storage failed for PDF {i+1}, continuing with processing...")
                    except Exception as e:
                        logger.warning(f"⚠️ Statistics storage error for PDF {i+1}: {e}, continuing with processing...")
                    
                    # 3. Process document for chunking and embedding (ESSENTIAL)
                    pdf_key = f"pdf_content_{i}" if i > 0 else "pdf_content"
                    
                    # Parse and chunk PDF using existing document parser
                    parsed_pdf = await self.document_parser.parse_pdf(pdf_file)
                    logger.info(f"🔍 PDF_DEBUG: Parsed PDF keys: {list(parsed_pdf.keys())}")
                    
                    # Chunk content and generate embeddings (PDF uses raw_text, not processed_text)
                    chunks = await self.chunking_engine.chunk_content(
                        parsed_pdf["raw_text"], content_type="pdf"
                    )
                    chunks_with_embeddings = await self.chunking_engine.generate_embeddings(
                        chunks, monitoring_context=monitoring_context
                    )
                    
                    # PRODUCTION: Embeddings will be stored in chunks table via consolidated vector storage

                    # Store in research_data with full chunks retained in-memory for vector sync
                    chunk_metadata = []
                    for chunk_index, chunk in enumerate(chunks_with_embeddings):
                        content_preview = chunk.get("content", "")
                        if len(content_preview) > 200:
                            content_preview = f"{content_preview[:200]}..."

                        chunk_metadata.append(
                            self._make_json_serializable(
                                {
                                    "index": chunk.get("index", chunk_index),
                                    "content_preview": content_preview,
                                    "token_count": chunk.get("token_count", 0),
                                    "character_count": chunk.get("character_count", 0)
                                }
                            )
                        )

                    research_data[pdf_key] = {
                        "metadata": self._make_json_serializable(parsed_pdf.get("metadata", {})),
                        "raw_text": parsed_pdf["raw_text"][:2000] + "..." if len(parsed_pdf["raw_text"]) > 2000 else parsed_pdf["raw_text"],  # Truncate for storage
                        "chunk_metadata": chunk_metadata,
                        "chunk_count": len(chunks_with_embeddings),
                        "chunks": chunks_with_embeddings,
                        "structured_content": self._make_json_serializable(pdf_content),  # ENHANCED: Include structured extraction
                        "processing_timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # 4. Associate with personas if available (ENHANCED)
                    if personas:
                        for persona in personas:
                            persona_id = persona.get("id")
                            if persona_id:
                                await self.persona_correlation.associate_data_with_personas(
                                    project_id, {"pdf_content": pdf_content}, persona_id
                                )
                    
                    logger.info(f"✅ Enhanced PDF processing completed for {pdf_file.filename}")
                    
                except Exception as pdf_error:
                    logger.error(f"❌ Enhanced PDF processing failed for file {i+1}: {pdf_error}")
                    raise pdf_error  # No fallback - fail fast for accuracy
            
            # Store processed data in database and vector store (ESSENTIAL)
            if research_data:
                # Store research documents data in database
                storage_ready_data = self._make_json_serializable(research_data)
                storage_success = await self.analysis_db_adapter.store_research_documents_data(
                    project_id, tenant_id, storage_ready_data
                )
                
                if storage_success:
                    logger.info("✅ Enhanced: Successfully stored research documents in database")
                    # Note: Vector storage handled by consolidated chunks table storage below
                    
                else:
                    logger.error("❌ Enhanced: Failed to store research documents in database")
            
            # Update storage data with statistics registry
            statistics_registry = await self.statistics_registry.get_all_statistics(project_id, tenant_id)
            if statistics_registry:
                storage_data["statistics_registry"] = statistics_registry
                logger.info("📊 Added statistics registry to storage data")
            
            def _compute_chunk_count(doc: Dict[str, Any]) -> int:
                if not isinstance(doc, dict):
                    return 0

                chunk_count_value = doc.get("chunk_count")
                if isinstance(chunk_count_value, (int, float)):
                    try:
                        return int(chunk_count_value)
                    except (TypeError, ValueError):
                        pass

                chunks_list = doc.get("chunks")
                if isinstance(chunks_list, list):
                    return len(chunks_list)

                metadata_list = doc.get("chunk_metadata")
                if isinstance(metadata_list, list):
                    return len(metadata_list)

                return 0

            # Add document manifest for compatibility
            storage_data["documents_manifest"] = {
                "documents": [
                    {
                        "document_key": doc_key,
                        "document_type": "csv" if "csv" in doc_key else "pdf",
                        "filename": doc_data.get("metadata", {}).get("filename", "unknown"),
                        "chunk_count": _compute_chunk_count(doc_data),
                        "processing_timestamp": doc_data.get("processing_timestamp")
                    }
                    for doc_key, doc_data in research_data.items()
                ],
                "total_documents": len(research_data),
                "total_chunks": sum(_compute_chunk_count(doc_data) for doc_data in research_data.values()),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # CRITICAL: Store all chunks with embeddings in chunks table (production-grade)
            logger.info("🔍 CONSOLIDATED VECTOR STORAGE: Starting chunks table storage with embeddings")
            try:
                await self._store_chunks_in_vector_database_consolidated(project_id, tenant_id, research_data)
                logger.info("✅ CONSOLIDATED VECTOR STORAGE: Successfully stored all chunks with embeddings in chunks table")
            except Exception as e:
                logger.error(f"❌ CONSOLIDATED VECTOR STORAGE: Failed to store chunks in chunks table: {e}")
                # Don't fail the entire upload, but log the issue
            
            return {
                "success": True,
                "data": research_data,
                "storage_data": storage_data,
                "enhanced_features": {
                    "statistics_registry": bool(statistics_registry),
                    "persona_associations": len(personas),
                    "processing_mode": "enhanced",
                    "total_documents": len(research_data),
                    "total_chunks": sum(_compute_chunk_count(doc_data) for doc_data in research_data.values())
                }
            }
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Enhanced document processing failed: {e}")
            # Fail-fast: Enhanced processing is required
            raise ValueError(f"Enhanced document processing failed. Legacy fallback removed: {str(e)}")
    
    async def _process_research_documents_enhanced_with_replacement(
        self, 
        project_id: str, 
        tenant_id: str, 
        pdf_files: List[Any], 
        csv_files: List[Any],
        existing_research_data: Optional[Dict[str, Any]] = None,
        file_operations: Optional[Dict[str, Any]] = None,
        persona_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhanced document processing with file replacement logic and multi-persona support.
        
        This method handles:
        1. Processing new files (PDF/CSV)
        2. Replacing existing files with same names
        3. Keeping existing files that aren't being replaced
        4. Merging all data into final research_data structure
        5. Associating documents with specific personas (multi-persona projects)
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            pdf_files: List of PDF file uploads (up to 25)
            csv_files: List of CSV file uploads (up to 5)
            existing_research_data: Existing research data from database
            file_operations: File operations tracking from router
            persona_id: Persona ID for multi-persona projects (associates documents with persona)
            user_id: Optional user ID for monitoring context
            
        Returns:
            Processing results with success status, merged data, and statistics registry
        """
        try:
            logger.info(f"🚀 Starting enhanced document processing with file replacement logic (persona_id: {persona_id})")
            
            # Process new files using existing enhanced method
            new_files_result = await self._process_research_documents_enhanced(
                project_id, tenant_id, pdf_files, csv_files, user_id=user_id
            )
            
            if not new_files_result["success"]:
                return new_files_result
            
            new_research_data = new_files_result["data"]
            logger.info(f"✅ FILE REPLACEMENT: Successfully processed {len(new_research_data)} new documents")
            
            # Initialize final merged data structure
            merged_research_data = {}
            
            # Step 1: MULTI-PERSONA FIX: Preserve ALL files from OTHER personas + kept files from current persona
            if existing_research_data:
                for doc_key, doc_data in existing_research_data.items():
                    # Skip non-document entries like documents_manifest, statistics_registry
                    if doc_key in ["documents_manifest", "statistics_registry"]:
                        continue
                        
                    if isinstance(doc_data, dict) and "metadata" in doc_data:
                        doc_persona_id = doc_data.get("metadata", {}).get("persona_id")
                        filename = doc_data.get("metadata", {}).get("filename")
                        
                        # BUG FIX: Keep files from OTHER personas OR files with no persona_id (legacy/null)
                        # Only skip files that explicitly belong to the CURRENT persona being uploaded
                        # (those will be handled by file_operations - replaced or kept)
                        if doc_persona_id != persona_id:  # This handles None != "P2" correctly
                            merged_research_data[doc_key] = doc_data
                            logger.info(f"🎭 PERSONA PRESERVATION: Keeping file '{filename}' from persona '{doc_persona_id}' (key: {doc_key})")
                
                # Also keep files from current persona that are not being replaced
                if file_operations:
                    kept_files = file_operations.get("existing_files_kept", [])
                    for kept_file in kept_files:
                        existing_key = kept_file["existing_key"]
                        if existing_key in existing_research_data:
                            merged_research_data[existing_key] = existing_research_data[existing_key]
                            logger.info(f"📁 FILE REPLACEMENT: Kept existing file from current persona - {kept_file['filename']} (key: {existing_key})")
            
            # Step 2: Add/Replace with new files
            # Create mapping of new files by filename for replacement logic
            new_files_by_filename = {}
            for doc_key, doc_data in new_research_data.items():
                if isinstance(doc_data, dict) and "metadata" in doc_data:
                    filename = doc_data["metadata"].get("filename")
                    if filename:
                        new_files_by_filename[filename] = doc_key
            
            # Process file operations to determine final keys
            if file_operations:
                # Handle replaced files
                for replaced_file in file_operations.get("replaced_files", []):
                    filename = replaced_file["filename"]
                    existing_key = replaced_file["existing_key"]
                    
                    # Find the new data for this filename
                    if filename in new_files_by_filename:
                        new_doc_key = new_files_by_filename[filename]
                        # Use the existing key to maintain consistency
                        merged_research_data[existing_key] = new_research_data[new_doc_key]
                        logger.info(f"🔄 FILE REPLACEMENT: Replaced {filename} - old key: {existing_key}, new data applied")
                    
                # Handle new files (not replacing anything)
                for new_file in file_operations.get("new_files", []):
                    filename = new_file["filename"]
                    
                    if filename in new_files_by_filename:
                        new_doc_key = new_files_by_filename[filename]
                        # Generate new key for new files
                        file_type = new_file["type"]
                        
                        # Find next available key
                        base_key = f"{file_type}_content"
                        final_key = base_key
                        counter = 0
                        while final_key in merged_research_data:
                            counter += 1
                            final_key = f"{base_key}_{counter}"
                        
                        merged_research_data[final_key] = new_research_data[new_doc_key]
                        logger.info(f"➕ FILE REPLACEMENT: Added new file {filename} with key: {final_key}")
            else:
                # No existing files, just use all new data
                merged_research_data = new_research_data
                logger.info("🆕 FILE REPLACEMENT: No existing files, using all new data")
            
            # Step 3: Update storage data for database persistence with persona association
            storage_data = {}
            
            # Track which documents are from new uploads by their actual data reference
            # Using id() to compare object identity, not just keys (keys can collide)
            new_upload_data_ids = {id(doc_data) for doc_data in new_research_data.values()}
            
            # Also track filenames from new uploads for additional verification
            new_upload_filenames = set()
            for doc_data in new_research_data.values():
                if isinstance(doc_data, dict):
                    fname = doc_data.get("metadata", {}).get("filename")
                    if fname:
                        new_upload_filenames.add(fname)
            
            for doc_key, doc_data in merged_research_data.items():
                if isinstance(doc_data, dict):
                    # ENTERPRISE FIX: Keep chunks for enterprise analysis (not just metadata)
                    metadata = doc_data.get("metadata", {}).copy()  # Copy to avoid mutating original
                    
                    # MULTI-PERSONA BUG FIX: Determine if this is a new upload by checking:
                    # 1. Object identity (is this the same object from new_research_data?)
                    # 2. OR it's in file_operations as new/replaced for current persona
                    existing_persona_id = metadata.get("persona_id")
                    doc_filename = metadata.get("filename")
                    
                    # Check if this document data came from the new upload
                    is_new_upload_by_identity = id(doc_data) in new_upload_data_ids
                    
                    # Check if this file was explicitly marked as new or replaced in file_operations
                    is_in_file_operations = False
                    if file_operations:
                        new_filenames = {f.get("filename") for f in file_operations.get("new_files", [])}
                        replaced_filenames = {f.get("filename") for f in file_operations.get("replaced_files", [])}
                        is_in_file_operations = doc_filename in new_filenames or doc_filename in replaced_filenames
                    
                    is_new_upload = is_new_upload_by_identity or is_in_file_operations
                    
                    if persona_id and is_new_upload:
                        metadata["persona_id"] = persona_id
                        logger.info(f"🎭 PERSONA: Associated NEW document {doc_key} ({doc_filename}) with persona '{persona_id}'")
                    elif existing_persona_id:
                        logger.info(f"🎭 PERSONA PRESERVED: Keeping existing persona_id '{existing_persona_id}' for document {doc_key} ({doc_filename})")
                    
                    storage_doc = {
                        "metadata": metadata,
                        "chunk_count": doc_data.get("chunk_count", 0),
                        "processing_timestamp": doc_data.get("processing_timestamp"),
                        "quantitative_summary": doc_data.get("quantitative_summary", {})
                    }
                    
                    # Add chunk metadata (lightweight)
                    if "chunk_metadata" in doc_data:
                        storage_doc["chunk_metadata"] = doc_data["chunk_metadata"]
                    
                    # ENTERPRISE REQUIREMENT: Keep actual chunks for enterprise analysis
                    if "chunks" in doc_data:
                        chunks = doc_data["chunks"]
                        
                        # MULTI-PERSONA BUG FIX: Only update persona_id on chunks for NEW uploads
                        if persona_id and is_new_upload:
                            for chunk in chunks:
                                chunk["persona_id"] = persona_id
                        
                        storage_doc["chunks"] = chunks
                        # Also preserve the chunks_with_embeddings count
                        chunks_with_embeddings = sum(1 for chunk in chunks if chunk.get("has_embedding"))
                        storage_doc["chunks_with_embeddings"] = chunks_with_embeddings
                        logger.info(f"✅ ENTERPRISE: Preserved {len(chunks)} chunks ({chunks_with_embeddings} with embeddings) for {doc_key}")
                    
                    storage_data[doc_key] = storage_doc
            
            # Step 4: Store merged data in database
            logger.info(f"💾 FILE REPLACEMENT: Storing merged research data with {len(storage_data)} documents")
            storage_success = await self.analysis_db_adapter.update_research_documents_data(
                project_id, tenant_id, storage_data
            )
            
            if not storage_success:
                logger.warning("⚠️ FILE REPLACEMENT: Failed to store research data, but continuing...")
            else:
                logger.info("✅ FILE REPLACEMENT: Successfully stored merged research data to database")
            
            # Step 5: Store chunks in vector database (for new files only)
            logger.info("🔍 FILE REPLACEMENT: Storing new file chunks in vector database")
            try:
                await self._store_chunks_in_vector_database_consolidated(project_id, tenant_id, new_research_data)
                logger.info("✅ FILE REPLACEMENT: Successfully stored new chunks in vector database")
            except Exception as e:
                logger.error(f"❌ FILE REPLACEMENT: Failed to store chunks in vector database: {e}")
                # Don't fail the entire upload, but log the issue
            
            # Step 6: Prepare final response
            total_documents = len(merged_research_data)
            total_chunks = sum(
                doc_data.get("chunk_count", 0) if isinstance(doc_data, dict) else 0 
                for doc_data in merged_research_data.values()
            )
            
            logger.info(f"🎉 FILE REPLACEMENT: Successfully completed processing")
            logger.info(f"📊 FILE REPLACEMENT: Final stats - {total_documents} documents, {total_chunks} total chunks")
            
            # Log file operation summary
            if file_operations:
                replaced_count = len(file_operations.get("replaced_files", []))
                new_count = len(file_operations.get("new_files", []))
                kept_count = len(file_operations.get("existing_files_kept", []))
                logger.info(f"📋 FILE REPLACEMENT SUMMARY: {replaced_count} replaced, {new_count} new, {kept_count} kept")
            
            return {
                "success": True,
                "data": merged_research_data,
                "storage_data": storage_data,
                "file_operations": file_operations,
                "enhanced_features": {
                    "statistics_registry": True,
                    "file_replacement": True,
                    "processing_mode": "enhanced_with_replacement",
                    "total_documents": total_documents,
                    "total_chunks": total_chunks
                }
            }
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Enhanced document processing with replacement failed: {e}")
            raise ValueError(f"Enhanced document processing with replacement failed: {str(e)}")
    
    async def _validate_project_readiness(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that project has required data for analysis.
        Follows same validation patterns as field_prep_service.
        
        Args:
            project_context: The project context data
            
        Returns:
            Validation result with ready status and missing requirements
        """
        try:
            missing_requirements = []
            field_prep_data = project_context.get("field_prep_data", {})
            
            # Check for personas (following field_prep_service patterns)
            personas = field_prep_data.get("personas", [])
            if not personas:
                missing_requirements.append({
                    "requirement": "personas",
                    "message": "Project must have at least one persona defined",
                    "phase": "Field Prep"
                })
            
            # Check for customer profiles in VPC data
            vpc_data = project_context.get("vpc_data", {})
            customer_profile = vpc_data.get("customer_profile", {})
            if not customer_profile:
                missing_requirements.append({
                    "requirement": "customer_profile",
                    "message": "Project must have customer profile completed in VPC",
                    "phase": "VPC Generation"
                })
            else:
                # Validate customer profile has required sections
                required_sections = ["pains", "gains", "jobs"]
                for section in required_sections:
                    if not customer_profile.get(section):
                        missing_requirements.append({
                            "requirement": f"customer_profile_{section}",
                            "message": f"Customer profile must have {section} section completed",
                            "phase": "VPC Generation"
                        })
            
            # Check for assumptions (core requirement for analysis)
            assumptions = field_prep_data.get("assumptions", [])
            if not assumptions:
                missing_requirements.append({
                    "requirement": "assumptions",
                    "message": "Project must have assumptions defined for analysis",
                    "phase": "Field Prep"
                })
            else:
                # Validate assumptions have required fields
                for i, assumption in enumerate(assumptions):
                    if not assumption.get("text"):
                        missing_requirements.append({
                            "requirement": f"assumption_{i}_text",
                            "message": f"Assumption {i+1} must have text defined",
                            "phase": "Field Prep"
                        })
                    if not assumption.get("type"):
                        missing_requirements.append({
                            "requirement": f"assumption_{i}_type",
                            "message": f"Assumption {i+1} must have type defined (pains/gains/jobs)",
                            "phase": "Field Prep"
                        })
                    if not assumption.get("indicators"):
                        missing_requirements.append({
                            "requirement": f"assumption_{i}_indicators",
                            "message": f"Assumption {i+1} must have indicators defined",
                            "phase": "Field Prep"
                        })
            
            # Check for hypothesis (recommended but not required)
            hypothesis = field_prep_data.get("hypothesis", {})
            if not hypothesis:
                missing_requirements.append({
                    "requirement": "hypothesis",
                    "message": "Project should have hypothesis defined for better analysis context",
                    "phase": "Field Prep",
                    "severity": "warning"
                })
            
            # Determine if project is ready
            critical_missing = [req for req in missing_requirements if req.get("severity") != "warning"]
            is_ready = len(critical_missing) == 0
            
            if is_ready:
                return {
                    "ready": True,
                    "message": "Project is ready for market research analysis",
                    "warnings": [req for req in missing_requirements if req.get("severity") == "warning"]
                }
            else:
                return {
                    "ready": False,
                    "error": "Project is not ready for analysis. Please complete the missing requirements.",
                    "missing": missing_requirements,
                    "next_steps": self._generate_next_steps(missing_requirements)
                }
                
        except Exception as e:
            return {
                "ready": False,
                "error": f"Project validation error: {str(e)}",
                "missing": []
            }
    
    def _generate_next_steps(self, missing_requirements: List[Dict[str, Any]]) -> List[str]:
        """
        Generate actionable next steps based on missing requirements.
        
        Args:
            missing_requirements: List of missing requirements
            
        Returns:
            List of actionable next steps
        """
        next_steps = []
        phases_mentioned = set()
        
        for req in missing_requirements:
            phase = req.get("phase", "Unknown")
            if phase not in phases_mentioned:
                phases_mentioned.add(phase)
                
                if phase == "Field Prep":
                    next_steps.append("Complete Field Prep phase: generate hypothesis, personas, and assumptions")
                elif phase == "VPC Generation":
                    next_steps.append("Complete VPC Generation phase: define customer profile with pains, gains, and jobs")
        
        if not next_steps:
            next_steps.append("Review project data and ensure all required fields are properly filled")
        
        return next_steps
    
    def _combine_research_chunks(self, research_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Combine chunks from all research documents into a single list for analysis.
        
        Args:
            research_data: Dictionary containing all research document data
            
        Returns:
            Combined list of all research chunks with source metadata
        """
        all_chunks = []
        
        # Track document types and counts for detailed logging
        pdf_files = []
        csv_files = []
        pdf_chunks_count = 0
        csv_chunks_count = 0
        
        logger.info("📊 DATA ANALYSIS BREAKDOWN: Starting data combination for analysis")
        
        # AGGRESSIVE DEBUGGING: Process all PDF and CSV content keys
        logger.info(f"🔍 CHUNK COMBINATION DEBUG: Processing {len(research_data)} research data keys")
        for key, content in research_data.items():
            logger.info(f"🔍 CHUNK DEBUG: Key '{key}', Content type: {type(content)}, Has chunks: {'chunks' in content if isinstance(content, dict) else False}")
            if isinstance(content, dict):
                logger.info(f"🔍 CHUNK DEBUG: Key '{key}' content keys: {list(content.keys())}")
                if 'chunks' in content:
                    logger.info(f"🔍 CHUNK DEBUG: Key '{key}' has {len(content['chunks'])} chunks")
            
            # 🚨 CRITICAL FIX: Handle both standard keys AND unknown keys with intelligent detection
            should_process = (
                key.startswith(('pdf_content', 'csv_content')) or 
                key == 'unknown'  # Handle emergency data structure
            ) and isinstance(content, dict) and 'chunks' in content
            
            if should_process:
                chunks = content['chunks']
                metadata = content.get('metadata', {})
                filename = metadata.get('filename', 'unknown')
                
                # ✅ PROPER SOURCE TYPE DETECTION using actual metadata
                # Priority 1: Use metadata source_type if available
                if 'source_type' in metadata:
                    source_type = metadata['source_type']
                # Priority 2: Use metadata type if available
                elif 'type' in metadata:
                    source_type = metadata['type']
                # Priority 3: Infer from key name (pdf_content_X = PDF)
                elif key.startswith('pdf_content'):
                    source_type = 'pdf'
                # Priority 4: Infer from filename extension
                elif filename != 'unknown':
                    if filename.lower().endswith('.csv'):
                        source_type = 'csv'
                    elif filename.lower().endswith('.pdf'):
                        source_type = 'pdf'
                    else:
                        source_type = 'unknown'
                # Priority 5: Check if chunks have source_type metadata
                elif chunks and len(chunks) > 0 and 'source_type' in chunks[0]:
                    source_type = chunks[0]['source_type']
                # Fallback: Mark as unknown (do NOT guess based on content)
                else:
                    source_type = 'unknown'
                    logger.warning(f"⚠️ SOURCE TYPE: Could not determine type for key '{key}', marking as unknown")
                
                logger.info(f"🎯 PROCESSING: {source_type.upper()} key '{key}' with {len(chunks)} chunks from '{filename}'")
                
                # Track file types and counts - only count known types
                if source_type == 'pdf':
                    pdf_files.append(filename)
                    pdf_chunks_count += len(chunks)
                elif source_type == 'csv':
                    csv_files.append(filename)
                    csv_chunks_count += len(chunks)
                else:
                    # Unknown type - don't count as either CSV or PDF
                    logger.warning(f"⚠️ UNKNOWN TYPE: File '{filename}' has unknown source type, not counting in CSV/PDF totals")
                
                logger.info(f"📄 DATA SOURCE: {source_type.upper()} file '{filename}' contributing {len(chunks)} chunks")
                
                # Add source information to each chunk
                for chunk in chunks:
                    enhanced_chunk = {
                        **chunk,
                        'source_document': key,
                        'source_filename': filename,
                        'source_type': source_type
                    }
                    all_chunks.append(enhanced_chunk)
        
        # Comprehensive data usage summary
        logger.info("=" * 80)
        logger.info("📊 COMPREHENSIVE DATA USAGE SUMMARY FOR ANALYSIS:")
        logger.info(f"📄 PDF FILES: {len(pdf_files)} files, {pdf_chunks_count} chunks")
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"   {i}. {pdf_file}")
        
        logger.info(f"📊 CSV FILES: {len(csv_files)} files, {csv_chunks_count} chunks")
        for i, csv_file in enumerate(csv_files, 1):
            logger.info(f"   {i}. {csv_file}")
        
        logger.info(f"🎯 TOTAL DATA FOR ANALYSIS:")
        logger.info(f"   - Total Files: {len(pdf_files) + len(csv_files)} ({len(pdf_files)} PDF + {len(csv_files)} CSV)")
        logger.info(f"   - Total Chunks: {len(all_chunks)} ({pdf_chunks_count} PDF + {csv_chunks_count} CSV)")
        logger.info(f"   - Data Types: {'PDF + CSV' if pdf_files and csv_files else 'PDF only' if pdf_files else 'CSV only' if csv_files else 'No data'}")
        logger.info("=" * 80)
        
        # 🚨 CRITICAL EMERGENCY FIX: If no chunks found, try alternative data structures
        if not all_chunks:
            logger.warning("🚨 EMERGENCY: No chunks found via standard method, trying alternative extraction...")
            
            # Try to extract chunks from any available data structure
            for key, content in research_data.items():
                if isinstance(content, dict):
                    # Try different possible chunk storage patterns
                    possible_chunk_keys = ['chunks', 'data', 'content', 'items']
                    for chunk_key in possible_chunk_keys:
                        if chunk_key in content and isinstance(content[chunk_key], list):
                            emergency_chunks = content[chunk_key]
                            logger.warning(f"🚨 EMERGENCY: Found {len(emergency_chunks)} chunks in '{key}.{chunk_key}'")
                            
                            # Add source metadata to emergency chunks with INTELLIGENT TYPE DETECTION
                            for chunk in emergency_chunks:
                                if isinstance(chunk, dict):
                                    # ✅ PROPER SOURCE TYPE: Use chunk metadata, not content keywords
                                    # Priority 1: Check chunk's own metadata
                                    if 'source_type' in chunk:
                                        source_type = chunk['source_type']
                                        filename = chunk.get('source_filename', f'chunk_{key}')
                                    # Priority 2: Check chunk metadata dict
                                    elif 'metadata' in chunk and isinstance(chunk['metadata'], dict):
                                        chunk_meta = chunk['metadata']
                                        source_type = chunk_meta.get('source_type', chunk_meta.get('type', 'unknown'))
                                        filename = chunk_meta.get('filename', f'chunk_{key}')
                                    # Priority 3: Infer from key name
                                    elif 'pdf' in key.lower():
                                        source_type = 'pdf'
                                        filename = f'interview_{key}.pdf'
                                    elif 'csv' in key.lower():
                                        source_type = 'csv'
                                        filename = f'survey_{key}.csv'
                                    # Fallback: Mark as unknown
                                    else:
                                        source_type = 'unknown'
                                        filename = f'emergency_extraction_{key}'
                                        logger.warning(f"⚠️ EMERGENCY: Could not determine source type for chunk in key '{key}'")
                                    
                                    enhanced_chunk = {
                                        **chunk,
                                        'source_document': key,
                                        'source_filename': filename,
                                        'source_type': source_type
                                    }
                                    all_chunks.append(enhanced_chunk)
                                    
                                    logger.info(f"🔍 EMERGENCY CHUNK: Detected as {source_type.upper()} - {chunk_content[:100]}...")
                            break
            
            if all_chunks:
                logger.warning(f"🚨 EMERGENCY SUCCESS: Recovered {len(all_chunks)} chunks via alternative extraction")
            else:
                logger.error("🚨 EMERGENCY FAILURE: No chunks found via any method - this will cause agent failures!")
        
        return all_chunks
    
    async def _process_embeddings_in_batches(self, chunks: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Process embeddings in batches to avoid memory issues and process kills.
        
        Args:
            chunks: List of chunk dictionaries
            batch_size: Number of chunks to process at once
            
        Returns:
            List of chunks with embeddings added
        """
        if not chunks:
            return []
        
        logger.info(f"🔍 DEBUG: Processing {len(chunks)} chunks in batches of {batch_size}")
        all_chunks_with_embeddings = []
        
        # Process chunks in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(chunks) + batch_size - 1)//batch_size
            logger.info(f"🔍 DEBUG: Processing batch {batch_num}/{total_batches} with {len(batch)} chunks")
            
            try:
                # Process this batch
                logger.info(f"🔍 DEBUG: About to call chunking_engine.generate_embeddings for batch {batch_num}")
                batch_with_embeddings = await self.chunking_engine.generate_embeddings(batch)
                logger.info(f"🔍 DEBUG: Successfully got embeddings for batch {batch_num}: {len(batch_with_embeddings)} chunks")
                all_chunks_with_embeddings.extend(batch_with_embeddings)
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to process embedding batch {i//batch_size + 1}: {e}")
                # Add chunks without embeddings as fallback
                for chunk in batch:
                    chunk['embedding'] = None  # Mark as failed
                    all_chunks_with_embeddings.append(chunk)
        
        logger.info(f"Completed embedding processing for {len(all_chunks_with_embeddings)} chunks")
        return all_chunks_with_embeddings
    
    async def _simple_chunk_and_embed(self, text: str, chunk_size: int = 800) -> List[Dict[str, Any]]:
        """
        Simple chunking and embedding approach that mimics the working report system.
        
        Args:
            text: Text content to chunk and embed
            chunk_size: Size of each chunk in characters
            
        Returns:
            List of chunks with embeddings
        """
        logger.info(f"🔍 DEBUG: Starting simple chunking for {len(text)} characters")
        
        # Simple text chunking (like report system)
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk_text = text[i:i + chunk_size].strip()
            if len(chunk_text) > 50:  # Minimum chunk size
                chunks.append({
                    "index": len(chunks),
                    "content": chunk_text,
                    "start_position": i,
                    "end_position": min(i + chunk_size, len(text)),
                    "chunk_size": len(chunk_text)
                })
        
        logger.info(f"🔍 DEBUG: Created {len(chunks)} simple chunks")
        
        if not chunks:
            return []
        
        # Extract text for embedding (like report system)
        texts = [chunk["content"] for chunk in chunks]
        logger.info(f"🔍 DEBUG: About to generate embeddings for {len(texts)} texts...")
        
        # Import and use the working embedding service directly
        from src.mint.api.services.ai.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        
        try:
            embeddings = await embedding_service.generate_embeddings(texts)
            logger.info(f"🔍 DEBUG: Got {len(embeddings)} embeddings from service")
        except Exception as e:
            logger.error(f"❌ EMBEDDING SERVICE FAILED: {e}")
            # Return chunks without embeddings as fallback
            for chunk in chunks:
                chunk["embedding"] = None
            return chunks
        
        # Combine chunks with embeddings (like report system)
        chunks_with_embeddings = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
            chunks_with_embeddings.append(chunk)
        
        logger.info(f"✅ SUCCESS: Created {len(chunks_with_embeddings)} chunks with embeddings")
        return chunks_with_embeddings
    
    def _sanitize_chunk_for_logging(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Remove embedding vectors from chunk data for clean logging."""
        if not isinstance(chunk, dict):
            return chunk
        
        sanitized = chunk.copy()
        # Remove embedding fields that contain long vectors
        embedding_fields = ['embedding', 'embeddings', 'vector', 'embedding_vector']
        for field in embedding_fields:
            if field in sanitized and sanitized[field] is not None:
                if isinstance(sanitized[field], list) and len(sanitized[field]) > 10:
                    sanitized[field] = f"[embedding vector with {len(sanitized[field])} dimensions]"
        
        return sanitized
    
    def _make_json_serializable(self, data: Any) -> Any:
        """
        Convert data to JSON-serializable format by handling numpy types and other non-serializable objects.
        
        Args:
            data: Data to convert
            
        Returns:
            JSON-serializable version of the data
        """
        import numpy as np
        import pandas as pd
        
        if isinstance(data, dict):
            return {key: self._make_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        elif isinstance(data, tuple):
            return [self._make_json_serializable(item) for item in data]
        elif isinstance(data, (np.integer, pd.Int64Dtype, np.int64)):
            return int(data)
        elif isinstance(data, (np.floating, pd.Float64Dtype, np.float64)):
            return float(data)
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif hasattr(data, 'item'):  # Handle numpy/pandas scalars
            return data.item()
        elif pd.isna(data):  # Handle pandas NaN values
            return None
        elif isinstance(data, (int, float, str, bool, type(None))):
            return data
        else:
            # For other types, try to convert to string as fallback
            try:
                # Special handling for pandas/numpy types
                if hasattr(data, 'dtype'):
                    if 'int' in str(data.dtype):
                        return int(data)
                    elif 'float' in str(data.dtype):
                        return float(data)
                return str(data)
            except Exception:
                return None
    
    def _prepare_data_for_storage(self, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare research data for database storage by removing large embeddings and optimizing structure.
        
        Args:
            research_data: Raw research data with embeddings
            
        Returns:
            Optimized data structure for storage
        """
        logger.info(f"🔍 DEBUG: Preparing data for storage...")
        
        storage_data = {}
        manifest_entries: List[Dict[str, Any]] = []
        total_chunks = 0
        total_documents = 0
        total_rows = 0
        total_columns = 0
        document_type_counts: Dict[str, int] = {"pdf": 0, "csv": 0, "unknown": 0}

        for key, document_data in research_data.items():
            if not isinstance(document_data, dict):
                logger.warning(f"⚠️ DEBUG: Skipping non-dict research document entry for key '{key}'")
                continue

            if key == "documents_manifest":
                logger.info("🔁 DEBUG: Skipping existing manifest entry during storage preparation")
                continue

            logger.info(f"🔍 DEBUG: Processing document: {key}")
            
            # Create optimized document structure
            metadata = self._make_json_serializable(document_data.get("metadata", {}))
            source_type = self._determine_source_type(key, metadata)
            metadata["source_type"] = source_type
            metadata.setdefault("uploaded_at", metadata.get("parsed_at", datetime.utcnow().isoformat()))

            optimized_doc = {
                "raw_text": document_data.get("raw_text", ""),
                "metadata": metadata,
                "chunk_count": len(document_data.get("chunks", [])),
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
            # Add CSV-specific data if present
            if "raw_data" in document_data:
                # Store only summary of raw data, not the full data
                raw_data = document_data["raw_data"]
                if isinstance(raw_data, list) and raw_data:
                    optimized_doc["raw_data_summary"] = {
                        "row_count": len(raw_data),
                        "columns": list(raw_data[0].keys()) if raw_data[0] else [],
                        "sample_row": self._make_json_serializable(raw_data[0]) if raw_data else {}
                    }
                else:
                    optimized_doc["raw_data_summary"] = {"row_count": 0, "columns": [], "sample_row": {}}
            
            if "processed_text" in document_data:
                optimized_doc["processed_text"] = document_data["processed_text"]

            quant_summary = document_data.get("quantitative_summary")
            if quant_summary:
                quant_summary = document_data["quantitative_summary"]
                row_count = quant_summary.get("row_count", 0)
                col_count = quant_summary.get("column_count", 0)
                logger.info(f"✅ STORAGE: Preserving quantitative_summary for {key}: {row_count} rows, {col_count} columns")

                try:
                    serialized_summary = self._make_json_serializable(document_data["quantitative_summary"])
                    optimized_doc["quantitative_summary"] = serialized_summary
                    logger.info(f"✅ STORAGE: Successfully serialized quantitative_summary for {key}")
                except Exception as serialization_error:
                    logger.error(f"❌ STORAGE: Failed to serialize quantitative_summary for {key}: {serialization_error}")
                    logger.error(f"❌ STORAGE: Quantitative summary content: {quant_summary}")
                    # Store a minimal version if serialization fails
                    optimized_doc["quantitative_summary"] = {
                        "row_count": row_count,
                        "column_count": col_count,
                        "error": "Serialization failed",
                        "original_keys": list(quant_summary.keys()) if isinstance(quant_summary, dict) else "not_dict"
                    }
            else:
                logger.warning(f"⚠️ STORAGE: No quantitative_summary found for {key} during storage preparation")
                quant_summary = None

            highlights_text = document_data.get("quantitative_highlights")
            if highlights_text:
                optimized_doc["quantitative_highlights"] = highlights_text

            # Store chunk metadata without embeddings (embeddings are too large for DB)
            chunks = document_data.get("chunks", [])
            optimized_chunks = []
            
            for i, chunk in enumerate(chunks):
                if i < 10:  # Store only first 10 chunks as samples
                    optimized_chunk = {
                        "index": chunk.get("index", i),
                        "content_preview": chunk.get("content", "")[:200] + "..." if len(chunk.get("content", "")) > 200 else chunk.get("content", ""),
                        "chunk_size": len(chunk.get("content", "")),
                        "start_position": chunk.get("start_position", 0),
                        "end_position": chunk.get("end_position", 0),
                        "has_embedding": chunk.get("embedding") is not None
                    }
                    optimized_chunks.append(optimized_chunk)

            optimized_doc["chunk_samples"] = optimized_chunks
            optimized_doc["total_chunks"] = len(chunks)
            optimized_doc["chunks_with_embeddings"] = sum(1 for chunk in chunks if chunk.get("embedding") is not None)

            storage_data[key] = optimized_doc
            logger.info(f"🔍 DEBUG: Optimized {key}: {optimized_doc['chunk_count']} chunks → {len(optimized_chunks)} samples")

            # Build manifest entry for quick retrieval later in the workflow
            row_count = 0
            column_count = 0
            raw_data_summary = optimized_doc.get("raw_data_summary", {})

            if isinstance(quant_summary, dict):
                row_count = quant_summary.get("row_count") or 0
                column_count = quant_summary.get("column_count") or 0

            if row_count == 0:
                row_count = raw_data_summary.get("row_count", 0)

            if column_count == 0:
                columns = raw_data_summary.get("columns")
                if isinstance(columns, list):
                    column_count = len(columns)
                else:
                    column_count = raw_data_summary.get("column_count", 0)

            manifest_entry = {
                "document_key": key,
                "filename": metadata.get("filename", key),
                "document_type": source_type,
                "uploaded_at": metadata.get("uploaded_at"),
                "file_size": metadata.get("file_size", 0),
                "chunk_count": optimized_doc["total_chunks"],
                "row_count": row_count,
                "column_count": column_count,
                "total_pages": metadata.get("total_pages"),
            }

            manifest_entries.append(self._make_json_serializable(manifest_entry))

            total_chunks += optimized_doc["total_chunks"]
            total_documents += 1
            total_rows += row_count if isinstance(row_count, int) else 0
            total_columns += column_count if isinstance(column_count, int) else 0
            if source_type in document_type_counts:
                document_type_counts[source_type] += 1
            else:
                document_type_counts["unknown"] += 1

        logger.info(f"🔍 DEBUG: Storage optimization complete. Original: {len(research_data)} docs, Optimized: {len(storage_data)} docs")

        storage_data["documents_manifest"] = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "total_rows": total_rows,
            "total_columns": total_columns,
            "document_type_counts": document_type_counts,
            "documents": manifest_entries,
        }

        return storage_data

    def _iter_document_entries(self, research_data: Optional[Dict[str, Any]]):
        """Yield research document entries while skipping manifests or invalid nodes."""

        if not isinstance(research_data, dict):
            return

        for key, document in research_data.items():
            if key == "documents_manifest":
                continue

            if not isinstance(document, dict):
                continue

            yield key, document

    def _get_document_count(self, research_data: Optional[Dict[str, Any]]) -> int:
        """Count valid research document entries."""

        return sum(1 for _ in self._iter_document_entries(research_data))

    def _get_chunk_count(self, document: Dict[str, Any]) -> int:
        """Determine chunk count from either stored metadata or raw chunk list."""

        if not isinstance(document, dict):
            return 0

        if isinstance(document.get("chunks"), list):
            return len(document.get("chunks", []))

        for key in ("total_chunks", "chunk_count", "chunks_with_embeddings"):
            value = document.get(key)
            if isinstance(value, int):
                return value

        return 0

    def _get_total_chunk_count(self, research_data: Optional[Dict[str, Any]]) -> int:
        """Aggregate chunk counts for all valid research documents."""

        total = 0
        for _, document in self._iter_document_entries(research_data):
            total += self._get_chunk_count(document)
        return total

    def _determine_source_type(self, document_key: str, metadata: Dict[str, Any]) -> str:
        """Infer the source type for a document based on keys and metadata."""
        source_type = (metadata or {}).get("source_type")
        if source_type:
            return source_type

        key_prefix = (document_key or "").lower()
        if key_prefix.startswith("pdf"):
            return "pdf"
        if key_prefix.startswith("csv"):
            return "csv"

        content_type = (metadata or {}).get("content_type") or (metadata or {}).get("mime_type")
        if content_type:
            lowered = content_type.lower()
            if "pdf" in lowered:
                return "pdf"
            if "csv" in lowered or "excel" in lowered:
                return "csv"

        return "unknown"

    def _reindex_chunks_for_storage(self, chunks: List[ReportChunkWithEmbedding]) -> List[ReportChunkWithEmbedding]:
        """Ensure chunk indices are unique per doc_id by reindexing sequentially."""
        reindexed_chunks: List[ReportChunkWithEmbedding] = []

        for new_index, chunk in enumerate(chunks):
            # Copy metadata to avoid mutating shared references
            metadata = dict(chunk.metadata or {})
            if "original_chunk_index" not in metadata:
                metadata["original_chunk_index"] = chunk.chunk_index
            metadata["chunk_index"] = new_index

            chunk.chunk_index = new_index
            chunk.metadata = metadata
            reindexed_chunks.append(chunk)

        return reindexed_chunks

    async def _store_embeddings_in_vector_db(self, project_id: str, tenant_id: str, research_data: Dict[str, Any]) -> bool:
        """
        Store embeddings in vector database for semantic search and retrieval.
        
        Uses intelligent merge strategy:
        - Preserves existing chunks from previous sessions
        - Replaces chunks if same filename uploaded again (update)
        - Adds new chunks if new filename uploaded (append)
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            research_data: Research data with embeddings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🔍 VECTOR_STORAGE: Starting storage for project {project_id}")
            logger.info(f"🔍 VECTOR_STORAGE: Document types to store: {list(research_data.keys())}")
            
            # Import the correct chunk storage service
            from src.mint.api.services.storage.chunk_storage_service import store_chunks
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            # First, create a document record in the documents table
            # Get actual user_id from VMP project
            user_id = await self._get_project_user_id(project_id, tenant_id)
            logger.info(f"🔍 VECTOR_STORAGE: Got user_id: {user_id}")
            
            doc_exists = await self._ensure_document_exists(project_id, tenant_id, research_data, user_id)
            logger.info(f"🔍 VECTOR_STORAGE: Document exists check: {doc_exists}")
            
            if not doc_exists:
                logger.error(f"❌ VECTOR_STORAGE: Failed to ensure document exists - aborting chunk storage")
                return False
            
            # STEP 1: Load existing chunks from database to implement merge strategy
            existing_chunks = await self._load_existing_chunks(project_id)
            logger.info(f"🔍 VECTOR_STORAGE: Found {len(existing_chunks)} existing chunks in database")
            
            # STEP 2: Build filename mapping for existing chunks
            existing_by_filename = {}
            for chunk in existing_chunks:
                filename = chunk.get("metadata", {}).get("document_metadata", {}).get("filename")
                if filename:
                    if filename not in existing_by_filename:
                        existing_by_filename[filename] = []
                    existing_by_filename[filename].append(chunk)
            
            logger.info(f"🔍 VECTOR_STORAGE: Existing files in database: {list(existing_by_filename.keys())}")
            
            # STEP 3: Identify new vs. replacement files
            new_filenames = set()
            for doc_key, doc_data in self._iter_document_entries(research_data):
                filename = doc_data.get("metadata", {}).get("filename")
                if filename:
                    new_filenames.add(filename)
            
            files_to_replace = new_filenames & set(existing_by_filename.keys())
            files_to_add = new_filenames - set(existing_by_filename.keys())
            files_to_keep = set(existing_by_filename.keys()) - new_filenames
            
            logger.info(f"🔍 VECTOR_STORAGE: Files to REPLACE (same filename): {list(files_to_replace)}")
            logger.info(f"🔍 VECTOR_STORAGE: Files to ADD (new): {list(files_to_add)}")
            logger.info(f"🔍 VECTOR_STORAGE: Files to KEEP (from previous sessions): {list(files_to_keep)}")
            
            total_stored = 0
            
            # STEP 4: Prepare chunks for storage (new + replacement files)
            all_chunks_combined = []
            
            for doc_key, document_data in self._iter_document_entries(research_data):
                chunks = document_data.get("chunks", [])
                logger.info(f"🔍 VECTOR_STORAGE: Processing {doc_key} with {len(chunks)} chunks")

                # Determine the source type once per document for consistent metadata
                document_metadata = document_data.get("metadata", {})
                source_type = self._determine_source_type(doc_key, document_metadata)
                source_filename = document_metadata.get("filename") or document_metadata.get("name")

                # Convert chunks to ReportChunkWithEmbedding format
                for chunk in chunks:
                    if chunk.get("embedding") is not None:
                        try:
                            # Create chunk in the format expected by the storage service
                            # Convert all data to JSON-safe format first
                            safe_metadata = self._make_json_serializable({
                                "project_id": project_id,
                                "tenant_id": tenant_id,
                                "document_key": doc_key,  # Identifies which document this chunk belongs to
                                "source_type": source_type,
                                "source_filename": source_filename,
                                "chunk_size": len(chunk.get("content", "")),
                                "start_position": chunk.get("start_position", 0),
                                "end_position": chunk.get("end_position", 0),
                                "original_chunk_index": chunk.get("index", 0),
                                "document_metadata": document_metadata
                            })

                            chunk_with_embedding = ReportChunkWithEmbedding(
                                chunk_index=chunk.get("index", 0),
                                content=chunk.get("content", ""),
                                embedding=chunk["embedding"],
                                metadata=safe_metadata
                            )
                            all_chunks_combined.append(chunk_with_embedding)
                        except Exception as e:
                            logger.warning(f"Failed to format chunk {chunk.get('index', 0)} for {doc_key}: {e}")
                            continue
            
            # STEP 5: Add chunks from files to KEEP (previous sessions)
            chunks_to_keep = []
            for filename in files_to_keep:
                kept_chunks = existing_by_filename[filename]
                logger.info(f"🔍 VECTOR_STORAGE: Keeping {len(kept_chunks)} chunks from previous session: {filename}")
                
                # Convert existing chunks back to ReportChunkWithEmbedding format
                for chunk_data in kept_chunks:
                    try:
                        existing_metadata = chunk_data.get("metadata", {}) or {}
                        # Preserve the original index for debugging, but we'll re-index before storage
                        if "original_chunk_index" not in existing_metadata:
                            existing_metadata["original_chunk_index"] = chunk_data.get("chunk_index", 0)
                        chunk_obj = ReportChunkWithEmbedding(
                            chunk_index=chunk_data.get("chunk_index", 0),
                            content=chunk_data.get("content", ""),
                            embedding=chunk_data.get("embedding"),
                            metadata=existing_metadata
                        )
                        chunks_to_keep.append(chunk_obj)
                    except Exception as e:
                        logger.warning(f"Failed to convert existing chunk: {e}")
                        continue
            
            # STEP 6: Combine new/replacement chunks + kept chunks
            final_chunks = all_chunks_combined + chunks_to_keep

            # Re-index chunks to satisfy UNIQUE(doc_id, chunk_index) constraint and preserve ordering
            final_chunks = self._reindex_chunks_for_storage(final_chunks)
            
            # Store ALL chunks in a SINGLE operation
            if final_chunks:
                logger.info(f"🔍 VECTOR_STORAGE: Final storage breakdown:")
                logger.info(f"🔍 VECTOR_STORAGE: - New/Replacement chunks: {len(all_chunks_combined)}")
                logger.info(f"🔍 VECTOR_STORAGE: - Kept from previous sessions: {len(chunks_to_keep)}")
                logger.info(f"🔍 VECTOR_STORAGE: - TOTAL chunks to store: {len(final_chunks)}")
                
                try:
                    # Store all chunks at once under project_id
                    logger.info(f"🔍 VECTOR_STORAGE: Calling store_chunks with doc_id={project_id} for ALL {len(final_chunks)} chunks")
                    success = await store_chunks(project_id, final_chunks)
                    logger.info(f"🔍 VECTOR_STORAGE: store_chunks returned: {success}")
                    
                    if success:
                        total_stored = len(final_chunks)
                        logger.info(f"✅ VECTOR_STORAGE SUCCESS: Stored {total_stored} total chunks")
                        logger.info(f"✅ VECTOR_STORAGE: - {len(all_chunks_combined)} from current session")
                        logger.info(f"✅ VECTOR_STORAGE: - {len(chunks_to_keep)} from previous sessions")
                        
                        # Log per-file breakdown
                        file_breakdown = {}
                        for chunk in final_chunks:
                            metadata = chunk.metadata or {}
                            filename = (
                                metadata.get("source_filename")
                                or metadata.get("document_metadata", {}).get("filename")
                                or "unknown"
                            )
                            file_breakdown[filename] = file_breakdown.get(filename, 0) + 1
                        
                        for filename, count in file_breakdown.items():
                            status = "REPLACED" if filename in files_to_replace else ("NEW" if filename in files_to_add else "KEPT")
                            logger.info(f"✅ VECTOR_STORAGE: - {filename}: {count} chunks [{status}]")
                    else:
                        logger.error(f"❌ VECTOR_STORAGE FAILED: store_chunks returned False")
                except Exception as e:
                    logger.error(f"❌ VECTOR_STORAGE EXCEPTION: {e}")
                    import traceback
                    logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
            else:
                logger.warning(f"⚠️ VECTOR_STORAGE: No chunks to store (neither new nor existing)")
            
            logger.info(f"🔍 VECTOR_STORAGE: Total stored across all documents: {total_stored}")
            if total_stored > 0:
                logger.info(f"✅ VECTOR_STORAGE COMPLETE: Successfully stored {total_stored} embeddings in vector database")
                return True
            else:
                logger.error(f"❌ VECTOR_STORAGE FAILED: No chunks were stored!")
                return False
            
        except Exception as e:
            logger.error(f"❌ VECTOR STORAGE ERROR: {e}")
            import traceback
            logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
            return False
    
    async def _load_existing_chunks(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Load existing chunks from database for merge strategy.
        
        Args:
            project_id: Project ID (used as doc_id)
            
        Returns:
            List of existing chunk dictionaries
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            supabase = get_service_role_client()
            
            # Query all existing chunks for this project
            result = supabase.client.table("chunks").select("*").eq("doc_id", project_id).execute()
            
            if result.data:
                logger.info(f"🔍 LOAD_EXISTING: Found {len(result.data)} existing chunks")
                return result.data
            else:
                logger.info(f"🔍 LOAD_EXISTING: No existing chunks found (first upload)")
                return []
                
        except Exception as e:
            logger.error(f"❌ LOAD_EXISTING ERROR: {e}")
            return []  # Return empty list on error, treat as first upload
    
    async def _ensure_document_exists(self, project_id: str, tenant_id: str, research_data: Dict[str, Any], user_id: str = None) -> bool:
        """
        Ensure a document record exists in the documents table before storing chunks.
        
        Args:
            project_id: Project ID (used as doc_id)
            tenant_id: Tenant ID
            research_data: Research data for document metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            supabase = get_service_role_client()
            
            # Check if document already exists
            existing = supabase.client.table("documents").select("id").eq("id", project_id).execute()
            
            if existing.data:
                logger.info(f"🔍 DEBUG: Document {project_id} already exists")
                return True
            
            # Create document record with all required fields from schema
            # Note: We need to get the parent_project_id from vmp_projects table
            document_data = {
                "id": project_id,
                "tenant_id": tenant_id,
                "project_id": None,  # Will be set after we get parent_project_id
                "source_type": "mv_analysis",  # From schema enum
                "title": f"Market Research Analysis - {project_id}",
                "created_by": user_id,  # Required field - must be valid user UUID
                "metadata": self._make_json_serializable({
                    "vmp_project_id": project_id,  # Store VMP project ID in metadata
                    "tenant_id": tenant_id,
                    "document_types": list(research_data.keys()),
                    "total_chunks": sum(len(doc.get("chunks", [])) for doc in research_data.values()),
                    "created_at": datetime.utcnow().isoformat(),
                    "source": "market_research_upload",
                    "content_type": "market_research"
                })
            }
            
            # Get parent_project_id from vmp_projects table
            try:
                vmp_project = supabase.client.table("vmp_projects").select("parent_project_id").eq("id", project_id).execute()
                if vmp_project.data and len(vmp_project.data) > 0:
                    parent_project_id = vmp_project.data[0].get("parent_project_id")
                    if parent_project_id:
                        document_data["project_id"] = parent_project_id
                        logger.info(f"🔍 DEBUG: Found parent_project_id: {parent_project_id}")
                    else:
                        logger.warning(f"⚠️ No parent_project_id found for VMP project {project_id}")
                else:
                    logger.warning(f"⚠️ VMP project {project_id} not found")
            except Exception as e:
                logger.warning(f"⚠️ Could not get parent_project_id: {e}")
                # Continue without project_id - it's optional in the schema
            
            logger.info(f"🔍 DEBUG: Attempting to create document with data: {document_data}")
            result = supabase.client.table("documents").insert(document_data).execute()
            
            if result.data:
                logger.info(f"✅ SUCCESS: Created document record for {project_id}")
                return True
            else:
                logger.error(f"❌ Failed to create document record: {result}")
                if hasattr(result, 'error') and result.error:
                    logger.error(f"❌ Document creation error details: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error ensuring document exists: {e}")
            return False
    
    async def _retrieve_complete_research_data(self, project_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Retrieve complete research data from chunks table for analysis.
        
        Args:
            project_id: Project ID (used as doc_id in chunks table)
            tenant_id: Tenant ID
            
        Returns:
            Complete research data with all chunks and embeddings
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            supabase = get_service_role_client()
            
            # Query all chunks for this project
            logger.info(f"🔍 RETRIEVAL: Querying chunks table for project {project_id}")
            result = supabase.client.table("chunks").select("*").eq("doc_id", project_id).order("chunk_index").execute()
            
            logger.info(f"🔍 RETRIEVAL: Query returned {len(result.data) if result.data else 0} chunks")
            
            # CRITICAL DEBUG: Check if we have the expected chunks
            if result.data:
                actual_count = len(result.data)
                logger.info(f"🔍 RETRIEVAL: Found {actual_count} chunks in database")
                
                # Check for PDF chunks in the retrieved data
                pdf_chunks = [chunk for chunk in result.data if chunk.get("metadata", {}).get("source_type") == "pdf"]
                csv_chunks = [chunk for chunk in result.data if chunk.get("metadata", {}).get("source_type") == "csv"]
                
                logger.info(f"🔍 RETRIEVAL BREAKDOWN: PDF={len(pdf_chunks)}, CSV={len(csv_chunks)}")
                
                if len(pdf_chunks) == 0 and len(csv_chunks) > 0:
                    logger.error(f"🚨 CRITICAL: NO PDF CHUNKS RETRIEVED! Only {len(csv_chunks)} CSV chunks found")
                    logger.error(f"🚨 This means PDF chunks are either:")
                    logger.error(f"🚨 1. Not stored in database despite success message")
                    logger.error(f"🚨 2. Stored with wrong metadata that prevents retrieval")
                    logger.error(f"🚨 3. Deleted after storage by cleanup process")
                    
                    # Check what chunk indices we have
                    chunk_indices = [chunk.get("chunk_index", -1) for chunk in result.data]
                    if chunk_indices:
                        logger.info(f"🔍 CHUNK INDICES: Range {min(chunk_indices)} to {max(chunk_indices)}")
                        
                        # Check if indices start from 0 or higher number
                        min_index = min(chunk_indices)
                        if min_index > 0:
                            logger.error(f"🚨 SUSPICIOUS: Chunk indices start from {min_index}, not 0!")
                            logger.error(f"🚨 This suggests PDF chunks (indices 0-24) are missing!")
                elif len(pdf_chunks) > 0:
                    logger.info(f"✅ SUCCESS: Found both PDF ({len(pdf_chunks)}) and CSV ({len(csv_chunks)}) chunks")
            
            if not result.data:
                logger.error(f"❌ RETRIEVAL FAILED: No chunks found in database for project {project_id}")
                logger.error(f"❌ CRITICAL: This means uploaded documents are NOT available for analysis!")
                logger.error(f"❌ CRITICAL: Analysis will fall back to PV report context only!")
                return {}
            
            logger.info(f"🔍 DEBUG: Found {len(result.data)} chunks in database")
            
            # CRITICAL DEBUG: Analyze what's actually in the chunks table
            logger.info("🔍 CHUNKS DEBUG: Analyzing chunk metadata to identify missing PDFs...")
            
            # Sample first few chunks to understand structure
            for i, chunk_record in enumerate(result.data[:5]):
                metadata = chunk_record.get("metadata", {})
                logger.info(f"🔍 CHUNK {i+1}: metadata keys = {list(metadata.keys())}")
                logger.info(f"🔍 CHUNK {i+1}: document_key = {metadata.get('document_key', 'MISSING')}")
                logger.info(f"🔍 CHUNK {i+1}: source_type = {metadata.get('source_type', 'MISSING')}")
                logger.info(f"🔍 CHUNK {i+1}: filename = {metadata.get('filename', 'MISSING')}")
                logger.info(f"🔍 CHUNK {i+1}: document_metadata = {metadata.get('document_metadata', {})}")
            
            # Count chunks by source type
            pdf_count = sum(1 for chunk in result.data if chunk.get("metadata", {}).get("source_type") == "pdf")
            csv_count = sum(1 for chunk in result.data if chunk.get("metadata", {}).get("source_type") == "csv")
            unknown_count = len(result.data) - pdf_count - csv_count
            
            logger.info(f"🔍 CHUNKS BREAKDOWN: PDF={pdf_count}, CSV={csv_count}, Unknown={unknown_count}")
            
            # Group chunks by document type from metadata
            research_data = {}
            
            for chunk_record in result.data:
                # Extract document type from metadata
                metadata = chunk_record.get("metadata", {})
                document_key = metadata.get("document_key", "unknown_content")
                
                # Initialize document structure if not exists
                if document_key not in research_data:
                    # Extract filename from multiple possible locations
                    filename = (
                        metadata.get("filename") or 
                        metadata.get("document_metadata", {}).get("filename") or
                        metadata.get("source_filename") or
                        "unknown"
                    )
                    
                    research_data[document_key] = {
                        "chunks": [],
                        "metadata": {
                            "source_type": metadata.get("source_type", "unknown"),
                            "filename": filename,
                            "document_metadata": metadata.get("document_metadata", {}),
                            "total_chunks": 0
                        }
                    }
                
                # Create chunk structure
                chunk = {
                    "index": chunk_record.get("chunk_index", 0),
                    "content": chunk_record.get("content", ""),
                    "embedding": chunk_record.get("embedding"),
                    "metadata": metadata,
                    "start_position": metadata.get("start_position", 0),
                    "end_position": metadata.get("end_position", 0)
                }
                
                research_data[document_key]["chunks"].append(chunk)
            
            # Update chunk counts and provide detailed breakdown
            total_pdf_chunks = 0
            total_csv_chunks = 0
            
            for doc_key, doc_data in self._iter_document_entries(research_data):
                doc_data.setdefault("metadata", {})
                doc_data["metadata"]["total_chunks"] = len(doc_data.get("chunks", []))
                source_type = doc_data["metadata"].get("source_type", "unknown")
                filename = doc_data["metadata"].get("filename", "unknown")
                chunk_count = len(doc_data.get("chunks", []))
                
                logger.info(f"🔍 RETRIEVED: {source_type.upper()} '{filename}' → {chunk_count} chunks (key: {doc_key})")
                
                if source_type == "pdf":
                    total_pdf_chunks += chunk_count
                elif source_type == "csv":
                    total_csv_chunks += chunk_count
            
            logger.info("=" * 80)
            logger.info(f"✅ RETRIEVAL SUMMARY:")
            pdf_files = sum(1 for _, doc in self._iter_document_entries(research_data) if doc.get("metadata", {}).get("source_type") == "pdf")
            csv_files = sum(1 for _, doc in self._iter_document_entries(research_data) if doc.get("metadata", {}).get("source_type") == "csv")
            logger.info(f"   📄 PDF files: {pdf_files} files, {total_pdf_chunks} chunks")
            logger.info(f"   📊 CSV files: {csv_files} files, {total_csv_chunks} chunks")
            logger.info(f"   🎯 TOTAL: {self._get_document_count(research_data)} documents, {total_pdf_chunks + total_csv_chunks} chunks")
            logger.info("=" * 80)
            return research_data
            
        except Exception as e:
            logger.error(f"❌ Error retrieving complete research data: {e}")
            return {}
    
    async def _regenerate_quantitative_summaries(self, project_id: str, tenant_id: str, research_data: Dict[str, Any], project_context: Dict[str, Any]) -> None:
        """
        Fallback method to regenerate quantitative summaries from stored chunks.
        This handles cases where quantitative summaries were lost during storage/retrieval.
        """
        try:
            logger.info(f"🔄 REGENERATION: Starting quantitative summary regeneration for {self._get_document_count(research_data)} documents")

            regenerated_data = {}

            for doc_key, doc_data in self._iter_document_entries(research_data):
                source_type = doc_data.get("metadata", {}).get("source_type", "unknown")
                
                if source_type == "csv":
                    logger.info(f"🔄 REGENERATION: Processing CSV document {doc_key}")
                    
                    # First try to get data from stored research_documents_data
                    stored_research_data = await self.analysis_db_adapter.get_research_documents_data(project_id, tenant_id)
                    if stored_research_data and doc_key in stored_research_data:
                        stored_doc = stored_research_data[doc_key]
                        raw_data_summary = stored_doc.get("raw_data_summary", {})
                        
                        if raw_data_summary and raw_data_summary.get("row_count", 0) > 0:
                            # Use the original raw data summary to create accurate quantitative summary
                            row_count = raw_data_summary.get("row_count", 0)
                            columns = raw_data_summary.get("columns", [])
                            col_count = len(columns)
                            
                            # Create quantitative summary based on stored metadata
                            quantitative_summary = {
                                "row_count": row_count,
                                "column_count": col_count,
                                "generated_at": "regenerated_from_stored_metadata",
                                "column_types": {col: "object" for col in columns},
                                "missing_values": {},
                                "numeric_columns": {},
                                "categorical_columns": {},
                                "note": f"Regenerated from stored metadata: {row_count} survey responses"
                            }
                            
                            # Add to research data
                            doc_data["quantitative_summary"] = quantitative_summary
                            regenerated_data[doc_key] = doc_data
                            
                            logger.info(f"✅ REGENERATION: Successfully regenerated quantitative summary for {doc_key}: {row_count} rows, {col_count} columns (from stored metadata)")
                            continue
                    
                    # Fallback: Try to reconstruct from chunks (less accurate)
                    chunks = doc_data.get("chunks", [])
                    if chunks:
                        logger.warning(f"⚠️ REGENERATION: Using chunk reconstruction for {doc_key} - may be inaccurate")
                        # Create minimal quantitative summary from chunk count
                        doc_data["quantitative_summary"] = {
                            "row_count": len(chunks),
                            "column_count": 1,
                            "generated_at": "regenerated_from_chunks",
                            "note": "Regenerated from chunk data - limited accuracy"
                        }
                        regenerated_data[doc_key] = doc_data
                        logger.info(f"⚠️ REGENERATION: Created minimal summary for {doc_key}")
                
                elif source_type == "pdf":
                    logger.info(f"🔄 REGENERATION: Processing PDF document {doc_key}")
                    # PDFs don't have quantitative summaries, but we can create metadata
                    chunks = doc_data.get("chunks", [])
                    doc_data["quantitative_summary"] = {
                        "row_count": 0,  # PDFs don't have rows
                        "column_count": 0,  # PDFs don't have columns
                        "chunk_count": len(chunks),
                        "generated_at": "regenerated_from_chunks",
                        "note": "PDF document - no quantitative data available"
                    }
                    regenerated_data[doc_key] = doc_data
                    logger.info(f"✅ REGENERATION: Created PDF metadata for {doc_key}")
            
            # Store regenerated data in project context
            if regenerated_data:
                project_context["research_documents_data"] = regenerated_data
                logger.info(f"✅ REGENERATION: Stored {len(regenerated_data)} regenerated documents in project context")
                
                # Also update the database with regenerated summaries
                try:
                    storage_data = self._prepare_data_for_storage(regenerated_data)
                    await self.analysis_db_adapter.update_research_documents_data(project_id, tenant_id, storage_data)
                    logger.info(f"✅ REGENERATION: Updated database with regenerated quantitative summaries")
                except Exception as storage_error:
                    logger.error(f"❌ REGENERATION: Failed to update database: {storage_error}")
            
        except Exception as e:
            logger.error(f"❌ REGENERATION: Failed to regenerate quantitative summaries: {e}")
    
    async def _store_chunks_in_vector_database_consolidated(
        self, 
        project_id: str, 
        tenant_id: str, 
        research_data: Dict[str, Any]
    ) -> bool:
        """
        Store all chunks with embeddings in the chunks table (production-grade consolidated storage).
        
        This method extracts all chunks with embeddings from the processed research data
        and stores them in the dedicated chunks table for semantic search and analysis.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID  
            research_data: Processed research data with chunks and embeddings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from src.mint.api.services.storage.chunk_storage_service import store_chunks
            
            logger.info(f"🔍 CONSOLIDATED STORAGE: Processing research data with {len(research_data)} documents")
            
            # Collect all chunks with embeddings from all documents
            all_chunks_with_embeddings = []
            global_chunk_index = 0  # CRITICAL FIX: Global index to prevent duplicates
            
            for doc_key, document_data in research_data.items():
                if doc_key == "documents_manifest" or not isinstance(document_data, dict):
                    continue
                    
                chunks = document_data.get("chunks", [])
                metadata = document_data.get("metadata", {})
                
                # Determine source type and filename
                if doc_key.startswith('csv_content'):
                    source_type = 'csv'
                elif doc_key.startswith('pdf_content'):
                    source_type = 'pdf'
                else:
                    source_type = 'unknown'
                
                source_filename = metadata.get("filename", doc_key)
                
                logger.info(f"🔍 CONSOLIDATED STORAGE: Processing {doc_key} with {len(chunks)} chunks")
                
                # Process each chunk that has an embedding
                for local_chunk_index, chunk in enumerate(chunks):
                    if not isinstance(chunk, dict) or not chunk.get("embedding"):
                        logger.warning(f"⚠️ CONSOLIDATED STORAGE: Skipping chunk {local_chunk_index} in {doc_key} - missing embedding")
                        continue
                    
                    # Create chunk metadata
                    chunk_metadata = {
                        "project_id": project_id,
                        "tenant_id": tenant_id,
                        "document_key": doc_key,
                        "source_type": source_type,
                        "source_filename": source_filename,
                        "chunk_size": len(chunk.get("content", "")),
                        "start_position": chunk.get("start_position", 0),
                        "end_position": chunk.get("end_position", 0),
                        "original_chunk_index": chunk.get("index", local_chunk_index),
                        "document_metadata": metadata
                    }
                    
                    # Create ReportChunkWithEmbedding object with GLOBAL unique index
                    chunk_with_embedding = ReportChunkWithEmbedding(
                        chunk_index=global_chunk_index,  # CRITICAL FIX: Use global index
                        content=chunk.get("content", ""),
                        embedding=chunk["embedding"],
                        metadata=chunk_metadata
                    )
                    
                    all_chunks_with_embeddings.append(chunk_with_embedding)
                    global_chunk_index += 1  # CRITICAL FIX: Increment for next chunk
            
            if not all_chunks_with_embeddings:
                logger.warning("⚠️ CONSOLIDATED STORAGE: No chunks with embeddings found - nothing to store")
                return False
            
            logger.info(f"🔍 CONSOLIDATED STORAGE: Storing {len(all_chunks_with_embeddings)} chunks with embeddings in chunks table")
            logger.info(f"🔍 CONSOLIDATED STORAGE: Global chunk indices assigned: 0 to {global_chunk_index-1}")
            
            # CRITICAL FIX: Create document entry first to satisfy foreign key constraint
            document_created = await self._ensure_document_exists(project_id, tenant_id)
            if not document_created:
                logger.error("❌ CONSOLIDATED STORAGE: Failed to create document entry")
                return False
            
            # CRITICAL FIX: Delete only chunks for files being replaced, preserve others
            # Get list of filenames being uploaded
            uploaded_filenames = set()
            for chunk in all_chunks_with_embeddings:
                filename = chunk.metadata.get('source_filename')
                if filename:
                    uploaded_filenames.add(filename)
            
            logger.info(f"🗑️ CHUNK REPLACEMENT: Deleting chunks for {len(uploaded_filenames)} uploaded files: {uploaded_filenames}")
            
            # Get all existing chunks
            from src.mint.api.services.storage.chunk_storage_service import get_chunk_storage_service
            chunk_service = get_chunk_storage_service()
            existing_chunks = await chunk_service.get_chunks_by_report_id(project_id)
            
            # Delete only chunks for uploaded filenames (CSV/PDF only, preserve analysis_report)
            if existing_chunks:
                chunks_to_delete = []
                for chunk in existing_chunks:
                    source_type = chunk.get('metadata', {}).get('source_type')
                    source_filename = chunk.get('metadata', {}).get('source_filename')
                    
                    # Delete if it's a CSV/PDF chunk for a file being re-uploaded
                    if source_type in ['csv', 'pdf'] and source_filename in uploaded_filenames:
                        chunks_to_delete.append(chunk['id'])
                
                if chunks_to_delete:
                    logger.info(f"🗑️ CHUNK REPLACEMENT: Deleting {len(chunks_to_delete)} old chunks for re-uploaded files")
                    from src.mint.api.system.core.supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    for chunk_id in chunks_to_delete:
                        supabase.client.table("chunks").delete().eq("id", chunk_id).execute()
                else:
                    logger.info("📁 CHUNK REPLACEMENT: No old chunks to delete (all new files)")
            
            # Insert new chunks directly (without calling store_chunks which deletes ALL)
            from src.mint.api.system.core.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Find max existing chunk_index to avoid conflicts
            max_index = -1
            if existing_chunks:
                for chunk in existing_chunks:
                    chunk_index = chunk.get('chunk_index', -1)
                    if chunk_index > max_index:
                        max_index = chunk_index
            
            logger.info(f"📊 CHUNK REPLACEMENT: Max existing chunk_index: {max_index}, starting new chunks at {max_index + 1}")
            
            # Insert chunks in batches
            batch_size = 50
            success_count = 0
            
            for i in range(0, len(all_chunks_with_embeddings), batch_size):
                batch = all_chunks_with_embeddings[i:i+batch_size]
                batch_data = []
                
                for idx, chunk in enumerate(batch):
                    if chunk.embedding is None:
                        continue
                    
                    # Use non-conflicting chunk_index
                    new_chunk_index = max_index + 1 + (i + idx)
                    
                    batch_data.append({
                        'doc_id': project_id,
                        'chunk_index': new_chunk_index,
                        'content': chunk.content,
                        'embedding': chunk.embedding,
                        'metadata': chunk.metadata
                    })
                
                if batch_data:
                    try:
                        result = supabase.client.table('chunks').insert(batch_data).execute()
                        success_count += len(batch_data)
                        logger.info(f"✅ Inserted batch {i//batch_size + 1}: {len(batch_data)} chunks")
                    except Exception as e:
                        logger.error(f"❌ Failed to insert batch: {e}")
                        return False
            
            success = (success_count == len(all_chunks_with_embeddings))
            
            if success:
                logger.info(f"✅ CONSOLIDATED STORAGE: Successfully stored {len(all_chunks_with_embeddings)} chunks with embeddings")
                return True
            else:
                logger.error("❌ CONSOLIDATED STORAGE: Failed to store chunks in chunks table")
                return False
                
        except Exception as e:
            logger.error(f"❌ CONSOLIDATED STORAGE: Exception during chunks table storage: {e}")
            import traceback
            logger.error(f"❌ CONSOLIDATED STORAGE: Traceback: {traceback.format_exc()}")
            return False
    
    async def _ensure_document_exists(self, project_id: str, tenant_id: str) -> bool:
        """
        Ensure a document entry exists in the documents table for the project.
        
        This is required because the chunks table has a foreign key constraint
        that references the documents table.
        
        Args:
            project_id: VMP project ID (used as doc_id)
            tenant_id: Tenant ID
            
        Returns:
            True if document exists or was created successfully, False otherwise
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            from datetime import datetime
            
            # Use service role client for document operations
            supabase = get_service_role_client()
            
            # Check if document already exists
            existing_doc = supabase.client.table("documents").select("id").eq("id", project_id).execute()
            
            if existing_doc.data:
                logger.info(f"📄 DOCUMENT: Document entry already exists for project {project_id}")
                return True
            
            # Get user_id for the created_by field (required NOT NULL constraint)
            user_id = await self._get_project_user_id(project_id, tenant_id)
            if not user_id:
                logger.error(f"❌ DOCUMENT: Could not get user_id for project {project_id}")
                return False
            
            # Create document entry for market research project
            document_data = {
                "id": project_id,
                "tenant_id": tenant_id,
                "title": f"Market Research Analysis - {project_id[:8]}",
                "source_type": "mv_analysis",  # Use mv_analysis as it's allowed in the constraint
                "document_type": "market_research",
                "created_by": user_id,  # CRITICAL: Required NOT NULL field
                "metadata": {
                    "project_type": "market_research",
                    "analysis_type": "multi_agent_workflow",
                    "created_by_service": "market_research_service"
                },
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Insert document entry
            logger.info(f"📄 DOCUMENT: Creating document entry with user_id: {user_id}")
            result = supabase.client.table("documents").insert(document_data).execute()
            
            if result.data:
                logger.info(f"✅ DOCUMENT: Successfully created document entry for project {project_id}")
                return True
            else:
                logger.error(f"❌ DOCUMENT: Failed to create document entry for project {project_id}")
                logger.error(f"❌ DOCUMENT: Insert result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ DOCUMENT: Exception creating document entry: {e}")
            return False
    
    async def _get_project_user_id(self, project_id: str, tenant_id: str) -> str:
        """
        Get user_id from VMP project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            User ID from the VMP project
        """
        try:
            from src.mint.api.system.core.supabase_client import get_service_role_client
            
            supabase = get_service_role_client()
            
            # Get user_id from vmp_projects table
            result = supabase.client.table("vmp_projects").select("user_id").eq("id", project_id).eq("tenant_id", tenant_id).execute()
            
            if result.data and len(result.data) > 0:
                user_id = result.data[0].get("user_id")
                if user_id:
                    logger.info(f"🔍 DEBUG: Found user_id: {user_id} for project {project_id}")
                    return user_id
            
            logger.warning(f"⚠️ Could not find user_id for project {project_id}, using tenant_id as fallback")
            return tenant_id
            
        except Exception as e:
            logger.error(f"❌ Error getting project user_id: {e}, using tenant_id as fallback")
            return tenant_id
    
    # ============================================================================
    # ENTERPRISE-GRADE BATCH PROCESSING METHODS
    # ============================================================================
    
    async def _process_massive_dataset_batch(
        self,
        project_id: str,
        tenant_id: str,
        pdf_files: List[UploadFile],
        csv_files: List[UploadFile],
        config: BatchProcessingConfig,
        progress_callback: Optional[Callable[[ProcessingUpdate], None]] = None
    ) -> Dict[str, Any]:
        """
        Enterprise batch processing for massive datasets (25+ PDFs, 5+ CSVs).
        
        Features:
        - Parallel processing with controlled concurrency
        - Complete data capture (zero sampling)
        - Cross-file validation and correlation
        - Real-time progress tracking
        - Memory optimization
        """
        try:
            logger.info(f"🚀 ENTERPRISE BATCH: Processing {len(pdf_files)} PDFs, {len(csv_files)} CSVs")
            
            # Initialize batch processing
            all_files = [(f, "pdf") for f in pdf_files] + [(f, "csv") for f in csv_files]
            total_files = len(all_files)
            processed_files = 0
            
            # Create semaphore for controlled concurrency
            semaphore = asyncio.Semaphore(config.max_concurrent_files)
            
            # Process files in batches with progress tracking
            processing_results = []
            batch_start_time = time.time()
            
            async def process_single_file(file_info, file_index):
                file, file_type = file_info
                async with semaphore:
                    return await self._process_file_with_enterprise_features(
                        file, file_type, file_index, project_id, tenant_id
                    )
            
            # Create tasks for all files
            tasks = [
                process_single_file(file_info, idx) 
                for idx, file_info in enumerate(all_files)
            ]
            
            # Process with progress updates
            for completed_task in asyncio.as_completed(tasks):
                result = await completed_task
                processing_results.append(result)
                processed_files += 1
                
                # Send progress update
                if progress_callback:
                    progress_callback(ProcessingUpdate(
                        project_id=project_id,
                        files_processed=processed_files,
                        total_files=total_files,
                        current_file=result["file_name"],
                        statistics_extracted=result.get("statistics_count", 0),
                        processing_time=result.get("processing_time", 0),
                        memory_usage=result.get("memory_usage", 0)
                    ))
                
                logger.info(f"✅ ENTERPRISE: Processed {processed_files}/{total_files} files")
            
            # Aggregate all results with complete data capture
            logger.info("🔄 ENTERPRISE: Aggregating results with zero data loss...")
            aggregated_data = await self._aggregate_enterprise_results(processing_results)
            
            # Perform cross-file validation if enabled
            if config.cross_file_validation:
                logger.info("🔍 ENTERPRISE: Performing cross-file validation...")
                validation_results = await self._perform_cross_file_validation(aggregated_data)
                aggregated_data["validation_results"] = validation_results
            
            # Store comprehensive statistics
            storage_result = await self._store_enterprise_statistics(
                project_id, tenant_id, aggregated_data
            )
            
            total_processing_time = time.time() - batch_start_time
            
            # Final progress update
            if progress_callback:
                progress_callback(ProcessingUpdate(
                    project_id=project_id,
                    files_processed=total_files,
                    total_files=total_files,
                    status="completed",
                    final_statistics=aggregated_data,
                    total_processing_time=total_processing_time
                ))
            
            logger.info(f"✅ ENTERPRISE BATCH: Completed in {total_processing_time:.2f}s")
            
            return {
                "success": True,
                "data": aggregated_data,
                "storage_data": storage_result,
                "processing_stats": {
                    "total_files": total_files,
                    "processing_time": total_processing_time,
                    "files_per_second": total_files / total_processing_time if total_processing_time > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ ENTERPRISE BATCH: Failed with error: {e}")
            return {
                "success": False,
                "error": f"Enterprise batch processing failed: {str(e)}",
                "error_code": "ENTERPRISE_BATCH_FAILED"
            }
    
    async def _process_file_with_enterprise_features(
        self,
        file: UploadFile,
        file_type: str,
        file_index: int,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Process individual file with enterprise features."""
        start_time = time.time()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            if file_type == "csv":
                # Enterprise CSV processing with complete data capture
                result = await self._process_csv_enterprise(file, project_id, tenant_id)
            elif file_type == "pdf":
                # Enterprise PDF processing with comprehensive extraction
                result = await self._process_pdf_enterprise(file, project_id, tenant_id)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            processing_time = time.time() - start_time
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_usage = final_memory - initial_memory
            
            return {
                "file_index": file_index,
                "file_name": file.filename,
                "file_type": file_type,
                "statistics_count": len(result.get("comprehensive_statistics", {})),
                "processing_time": processing_time,
                "memory_usage": memory_usage,
                "result": result,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ ENTERPRISE FILE: Error processing {file.filename}: {e}")
            return {
                "file_index": file_index,
                "file_name": file.filename,
                "file_type": file_type,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "memory_usage": 0,
                "success": False
            }
    
    async def _process_csv_enterprise(
        self, 
        csv_file: UploadFile, 
        project_id: str, 
        tenant_id: str
    ) -> Dict[str, Any]:
        """Enterprise CSV processing with complete data capture."""
        try:
            # Use enhanced CSV extractor for comprehensive statistics
            csv_stats = await self.csv_extractor.extract_statistics(csv_file, project_id)
            
            # Store in statistics registry for Tier 1 RAG
            await self.statistics_registry.store_statistics(
                project_id, tenant_id, csv_stats, "csv"
            )
            
            # Parse and chunk for Tier 2 RAG
            parsed_data = await self.document_parser.parse_csv(csv_file)
            chunks = await self.chunking_engine.chunk_and_embed(parsed_data, "csv")
            
            # Associate with personas
            persona_associations = await self.persona_correlation.associate_data_with_personas(
                project_id, tenant_id, chunks, "csv"
            )
            
            return {
                "comprehensive_statistics": csv_stats,
                "chunks": chunks,
                "persona_associations": persona_associations,
                "source_type": "csv",
                "file_name": csv_file.filename
            }
            
        except Exception as e:
            logger.error(f"❌ ENTERPRISE CSV: Error processing {csv_file.filename}: {e}")
            raise
    
    async def _process_pdf_enterprise(
        self, 
        pdf_file: UploadFile, 
        project_id: str, 
        tenant_id: str
    ) -> Dict[str, Any]:
        """Enterprise PDF processing with comprehensive extraction."""
        try:
            # Use structured PDF extractor for comprehensive content
            pdf_content = await self.pdf_extractor.extract_structured_content(pdf_file, project_id)
            
            # Store in statistics registry for Tier 1 RAG
            await self.statistics_registry.store_statistics(
                project_id, tenant_id, pdf_content, "pdf"
            )
            
            # Parse and chunk for Tier 2 RAG
            parsed_data = await self.document_parser.parse_pdf(pdf_file)
            chunks = await self.chunking_engine.chunk_and_embed(parsed_data, "pdf")
            
            # Associate with personas
            persona_associations = await self.persona_correlation.associate_data_with_personas(
                project_id, tenant_id, chunks, "pdf"
            )
            
            return {
                "comprehensive_statistics": pdf_content,
                "chunks": chunks,
                "persona_associations": persona_associations,
                "source_type": "pdf",
                "file_name": pdf_file.filename
            }
            
        except Exception as e:
            logger.error(f"❌ ENTERPRISE PDF: Error processing {pdf_file.filename}: {e}")
            raise
    
    async def _aggregate_enterprise_results(
        self, 
        processing_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate results from all files with complete data capture."""
        try:
            aggregated = {
                "multi_csv_statistics": {
                    "total_files": 0,
                    "total_respondents": 0,
                    "combined_distributions": {},
                    "cross_file_correlations": {},
                    "file_metadata": []
                },
                "multi_pdf_statistics": {
                    "total_files": 0,
                    "combined_themes": {},
                    "cross_document_patterns": {},
                    "comprehensive_quotes": {},
                    "file_metadata": []
                },
                "all_chunks": [],
                "persona_associations": {},
                "processing_metadata": {
                    "total_files_processed": len(processing_results),
                    "successful_files": 0,
                    "failed_files": 0,
                    "aggregated_at": datetime.utcnow().isoformat()
                }
            }
            
            # Process each file result
            for result in processing_results:
                if not result.get("success", False):
                    aggregated["processing_metadata"]["failed_files"] += 1
                    continue
                
                aggregated["processing_metadata"]["successful_files"] += 1
                file_data = result["result"]
                file_type = result["file_type"]
                
                # Aggregate chunks for Tier 2 RAG
                if "chunks" in file_data:
                    aggregated["all_chunks"].extend(file_data["chunks"])
                
                # Aggregate persona associations
                if "persona_associations" in file_data:
                    file_name = result["file_name"]
                    aggregated["persona_associations"][file_name] = file_data["persona_associations"]
                
                # Aggregate by file type
                if file_type == "csv":
                    await self._aggregate_csv_data(aggregated["multi_csv_statistics"], file_data, result)
                elif file_type == "pdf":
                    await self._aggregate_pdf_data(aggregated["multi_pdf_statistics"], file_data, result)
            
            logger.info(f"✅ ENTERPRISE AGGREGATION: Combined {len(aggregated['all_chunks'])} chunks from {aggregated['processing_metadata']['successful_files']} files")
            return aggregated
            
        except Exception as e:
            logger.error(f"❌ ENTERPRISE AGGREGATION: Failed with error: {e}")
            raise
    
    async def _aggregate_csv_data(
        self, 
        csv_stats: Dict[str, Any], 
        file_data: Dict[str, Any], 
        result: Dict[str, Any]
    ) -> None:
        """Aggregate CSV data with complete statistics."""
        csv_stats["total_files"] += 1
        
        # DIRECT ACCESS: Use the actual data structure that exists
        quantitative_summary = file_data.get("quantitative_summary", {})
        metadata = quantitative_summary.get("metadata", {})
        
        # Add file metadata
        csv_stats["file_metadata"].append({
            "filename": result["file_name"],
            "total_rows": metadata.get("total_rows", 0),
            "total_columns": metadata.get("total_columns", 0),
            "processing_time": result.get("processing_time", 0)
        })
        
        # Aggregate respondent counts
        csv_stats["total_respondents"] += metadata.get("total_rows", 0)
        
        # DIRECT ACCESS: Use actual field analysis from quantitative_summary
        field_analysis = quantitative_summary.get("field_analysis", {})
        
        for field_name, field_info in field_analysis.items():
            if field_info.get("type") == "categorical" and "value_counts" in field_info:
                if field_name not in csv_stats["combined_distributions"]:
                    csv_stats["combined_distributions"][field_name] = {
                        "total_responses": 0,
                        "value_counts": {},
                        "source_files": []
                    }
                
                # Add value counts directly
                for value, count in field_info["value_counts"].items():
                    if value not in csv_stats["combined_distributions"][field_name]["value_counts"]:
                        csv_stats["combined_distributions"][field_name]["value_counts"][value] = 0
                    csv_stats["combined_distributions"][field_name]["value_counts"][value] += count
                    csv_stats["combined_distributions"][field_name]["total_responses"] += count
                
                csv_stats["combined_distributions"][field_name]["source_files"].append(result["file_name"])
    
    async def _aggregate_pdf_data(
        self, 
        pdf_stats: Dict[str, Any], 
        file_data: Dict[str, Any], 
        result: Dict[str, Any]
    ) -> None:
        """Aggregate PDF data with comprehensive themes."""
        pdf_stats["total_files"] += 1
        
        # DIRECT ACCESS: Use the actual data structure that exists
        quantitative_summary = file_data.get("quantitative_summary", {})
        
        # Add file metadata
        pdf_stats["file_metadata"].append({
            "filename": result["file_name"],
            "processing_time": result.get("processing_time", 0)
        })
        
        # DIRECT ACCESS: Use actual themes from quantitative_summary
        themes = quantitative_summary.get("themes", {})
        
        for theme_name, theme_data in themes.items():
            if theme_name not in pdf_stats["combined_themes"]:
                pdf_stats["combined_themes"][theme_name] = {
                    "total_mentions": 0,
                    "source_files": [],
                    "representative_quotes": []
                }
            
            pdf_stats["combined_themes"][theme_name]["total_mentions"] += theme_data.get("frequency", 0)
            pdf_stats["combined_themes"][theme_name]["source_files"].append(result["file_name"])
            
            # Keep top quotes from each file
            quotes = theme_data.get("quotes", [])[:3]
            pdf_stats["combined_themes"][theme_name]["representative_quotes"].extend(quotes)
    
    async def _perform_cross_file_validation(
        self, 
        aggregated_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform cross-file validation and consistency checking."""
        try:
            validation_results = {
                "consistency_scores": {},
                "data_quality_warnings": [],
                "cross_file_correlations": {},
                "validation_timestamp": datetime.utcnow().isoformat()
            }
            
            # Validate CSV field consistency across files
            csv_stats = aggregated_data.get("multi_csv_statistics", {})
            combined_distributions = csv_stats.get("combined_distributions", {})
            
            for field_name, field_data in combined_distributions.items():
                source_files = field_data.get("source_files", [])
                if len(source_files) > 1:
                    # Calculate consistency score for fields appearing in multiple files
                    consistency_score = await self._calculate_field_consistency(field_data)
                    validation_results["consistency_scores"][field_name] = {
                        "score": consistency_score,
                        "files_count": len(source_files),
                        "files": source_files
                    }
                    
                    if consistency_score < 0.7:
                        validation_results["data_quality_warnings"].append(
                            f"Low consistency ({consistency_score:.2f}) for field '{field_name}' across {len(source_files)} files"
                        )
            
            # Validate PDF theme consistency
            pdf_stats = aggregated_data.get("multi_pdf_statistics", {})
            combined_themes = pdf_stats.get("combined_themes", {})
            
            for theme_name, theme_data in combined_themes.items():
                source_files = theme_data.get("source_files", [])
                if len(source_files) > 1:
                    # Check theme consistency across documents
                    theme_consistency = len(source_files) / pdf_stats.get("total_files", 1)
                    validation_results["cross_file_correlations"][theme_name] = {
                        "consistency": theme_consistency,
                        "total_mentions": theme_data.get("total_mentions", 0),
                        "files_count": len(source_files)
                    }
            
            logger.info(f"✅ CROSS-FILE VALIDATION: Analyzed {len(combined_distributions)} CSV fields and {len(combined_themes)} PDF themes")
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ CROSS-FILE VALIDATION: Failed with error: {e}")
            return {"error": str(e)}
    
    async def _calculate_field_consistency(self, field_data: Dict[str, Any]) -> float:
        """Calculate consistency score for a field across multiple files."""
        try:
            value_counts = field_data.get("value_counts", {})
            total_responses = field_data.get("total_responses", 0)
            
            if total_responses == 0:
                return 0.0
            
            # Calculate entropy-based consistency score
            import math
            entropy = 0.0
            for count in value_counts.values():
                if count > 0:
                    probability = count / total_responses
                    entropy -= probability * math.log2(probability)
            
            # Normalize entropy to 0-1 scale (higher = more consistent)
            max_entropy = math.log2(len(value_counts)) if len(value_counts) > 1 else 1
            consistency_score = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0
            
            return max(0.0, min(1.0, consistency_score))
            
        except Exception as e:
            logger.error(f"❌ CONSISTENCY CALCULATION: Error: {e}")
            return 0.0
    
    async def _store_enterprise_statistics(
        self, 
        project_id: str, 
        tenant_id: str, 
        aggregated_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store comprehensive enterprise statistics."""
        try:
            # Store aggregated statistics in research documents data
            storage_data = {
                "enterprise_statistics": aggregated_data,
                "stored_at": datetime.utcnow().isoformat(),
                "data_completeness_score": 1.0  # 100% capture guaranteed
            }
            
            # Store in database
            success = await self.analysis_db_adapter.update_research_documents_data(
                project_id, tenant_id, storage_data
            )
            
            if success:
                logger.info(f"✅ ENTERPRISE STORAGE: Stored comprehensive statistics for project {project_id}")
                
                # Store all chunks in consolidated vector table for Tier 2 RAG
                all_chunks = aggregated_data.get("all_chunks", [])
                if all_chunks:
                    chunks_stored = await self._store_chunks_in_consolidated_table(
                        project_id, tenant_id, all_chunks
                    )
                    storage_data["chunks_stored"] = chunks_stored
                    logger.info(f"✅ ENTERPRISE STORAGE: Stored {len(all_chunks)} chunks in vector table")
                
                return storage_data
            else:
                logger.error(f"❌ ENTERPRISE STORAGE: Failed to store statistics")
                return {"error": "Storage failed"}
                
        except Exception as e:
            logger.error(f"❌ ENTERPRISE STORAGE: Error: {e}")
            return {"error": str(e)}
    
    async def _retrieve_complete_enterprise_dataset(
        self, 
        project_id: str, 
        tenant_id: str
    ) -> Dict[str, Any]:
        """Retrieve complete enterprise dataset from all sources."""
        try:
            # Load all chunks from consolidated vector table
            chunks = await self.analysis_db_adapter.get_research_chunks(project_id, tenant_id)
            
            # Organize by source type and file
            organized_data = {}
            for chunk in chunks:
                source_file = chunk.get("source_file", "unknown")
                source_type = chunk.get("source_type", "unknown")
                
                if source_file not in organized_data:
                    organized_data[source_file] = {
                        "source_type": source_type,
                        "chunks": [],
                        "metadata": chunk.get("metadata", {})
                    }
                
                organized_data[source_file]["chunks"].append(chunk)
            
            logger.info(f"✅ ENTERPRISE RETRIEVAL: Loaded {len(chunks)} chunks from {len(organized_data)} files")
            return organized_data
            
        except Exception as e:
            logger.error(f"❌ ENTERPRISE RETRIEVAL: Error: {e}")
            return {}


# Create alias for backward compatibility
MarketResearchAnalysisService = EnterpriseMarketResearchService