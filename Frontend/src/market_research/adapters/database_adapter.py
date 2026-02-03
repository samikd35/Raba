"""
Database Adapter for Data Analysis Agent

Provides database operations following VMP service patterns.
Integrates with Yuba's existing database infrastructure.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

try:  # Lazy optional imports for scientific types
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover - numpy optional
    _np = None

try:  # Lazy optional imports for dataframe support
    import pandas as _pd  # type: ignore
except Exception:  # pragma: no cover - pandas optional
    _pd = None


def _truncate_text(value: str, limit: int = 500) -> str:
    """Return a truncated representation of long text blocks."""
    if not isinstance(value, str):
        return value
    if len(value) <= limit:
        return value
    return value[:limit] + "..."


def _ensure_json_serializable(value: Any) -> Any:
    """Convert complex/numpy/pandas values into JSON-safe Python primitives."""

    if isinstance(value, dict):
        return {key: _ensure_json_serializable(val) for key, val in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_ensure_json_serializable(item) for item in value]

    # Handle numpy scalars/arrays lazily
    if _np is not None:
        if isinstance(value, _np.generic):
            return value.item()
        if isinstance(value, _np.ndarray):
            return value.tolist()

    # Handle pandas types lazily
    if _pd is not None:
        if isinstance(value, _pd.Series):
            return [_ensure_json_serializable(item) for item in value.tolist()]
        if isinstance(value, _pd.DataFrame):
            return [_ensure_json_serializable(row) for row in value.to_dict(orient="records")]
        if hasattr(_pd, "isna") and _pd.isna(value):
            return None

    if hasattr(value, "to_dict") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return _ensure_json_serializable(value.to_dict())
        except Exception:
            pass

    if hasattr(value, "tolist") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return _ensure_json_serializable(value.tolist())
        except Exception:
            pass

    if hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return value.item()
        except Exception:
            pass

    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8")
        except Exception:
            return list(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, (int, float, str, bool)) or value is None:
        return value

    return str(value)


def _sanitize_chunk(
    chunk: Dict[str, Any],
    *,
    content_limit: int = 2000,
    preview_limit: int = 500
) -> Dict[str, Any]:
    """Remove large embedding payloads from chunk metadata before storage."""
    sanitized: Dict[str, Any] = {}
    content_preview: Optional[str] = None
    content_truncated = False

    for key, value in chunk.items():
        if key in {"embedding", "embeddings", "embedding_vector", "vector"}:
            # Skip raw embedding payloads – they are stored in the vector DB instead
            continue

        if key in {"content", "text", "raw_text", "chunk_text"} and isinstance(value, str):
            truncated_value = _truncate_text(value, limit=content_limit)
            sanitized[key] = truncated_value

            if len(value) > content_limit:
                content_truncated = True
                content_preview = _truncate_text(value, limit=preview_limit)
        else:
            sanitized[key] = value

    if content_preview and "content_preview" not in sanitized:
        sanitized["content_preview"] = content_preview

    if content_truncated:
        sanitized["content_truncated"] = True

    # Preserve lightweight embedding metadata for observability
    if "has_embedding" not in sanitized:
        sanitized["has_embedding"] = bool(chunk.get("embedding"))
    if "embedding_dimension" not in sanitized and chunk.get("embedding") is not None:
        sanitized["embedding_dimension"] = len(chunk.get("embedding")) if hasattr(chunk.get("embedding"), "__len__") else 0

    if "content" in sanitized and "content_preview" not in sanitized:
        sanitized["content_preview"] = _truncate_text(sanitized["content"], limit=preview_limit)

    if "token_count" in chunk and isinstance(chunk["token_count"], int):
        sanitized["token_count"] = chunk["token_count"]

    return sanitized


def sanitize_chunk_for_storage(
    chunk: Dict[str, Any],
    *,
    content_limit: int = 2000,
    preview_limit: int = 500
) -> Dict[str, Any]:
    """Public helper that wraps ``_sanitize_chunk`` for reuse across services."""
    return _sanitize_chunk(
        chunk,
        content_limit=content_limit,
        preview_limit=preview_limit,
    )


class AnalysisAgentDatabaseAdapter:
    """
    Database adapter for Data Analysis Agent operations.
    
    Follows the same pattern as VMP services while providing
    analysis-specific database operations.
    """
    
    def __init__(self, use_service_role: bool = False):
        """Initialize with Yuba's existing database clients"""
        self.use_service_role = use_service_role
        self.supabase = None
    
    def _get_supabase_client(self):
        """Get supabase client with lazy loading"""
        if self.supabase is None:
            try:
                from src.mint.api.system.core.supabase_client import get_supabase_client, get_service_role_client
                
                if self.use_service_role:
                    self.supabase = get_service_role_client()
                else:
                    self.supabase = get_supabase_client()
                
                if self.supabase is None:
                    raise ValueError("Supabase client returned None")
                
                if not hasattr(self.supabase, 'client'):
                    raise ValueError(f"Supabase client missing 'client' attribute")
                
                if self.supabase.client is None:
                    raise ValueError("Supabase client.client is None")
                
            except Exception as e:
                print(f"❌ DB_ADAPTER ERROR: Failed to initialize supabase client: {e}")
                print(f"❌ DB_ADAPTER ERROR: Exception type: {type(e)}")
                import traceback
                print(f"❌ DB_ADAPTER ERROR: Traceback: {traceback.format_exc()}")
                raise
        
        return self.supabase
    
    async def get_vmp_project_context(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get VMP project context following the same pattern as field_prep_service.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            VMP project context data or None if not found
        """
        try:
            supabase = self._get_supabase_client()
            response = supabase.client.table('vmp_projects').select(
                '*'
            ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                return None
                
            return response.data[0]
            
        except Exception as e:
            print(f"Error fetching VMP project context: {e}")
            return None

    async def get_vmp_project(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Return the complete VMP project row, including research data payloads."""
        try:
            supabase = self._get_supabase_client()
            response = (
                supabase.client
                .table('vmp_projects')
                .select('*')
                .eq('id', project_id)
                .eq('tenant_id', tenant_id)
                .execute()
            )

            if not response.data:
                return None

            project = response.data[0]
            if project.get('research_documents_data'):
                project['research_documents_data'] = self._sanitize_research_documents_data(
                    project['research_documents_data']
                )
            return project

        except Exception as e:
            print(f"Error fetching VMP project: {e}")
            return None
    
    async def update_research_documents_data(
        self,
        project_id: str,
        tenant_id: str,
        research_data: Dict[str, Any]
    ) -> bool:
        """
        Update research documents data in the vmp_projects table.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID  
            research_data: The research documents data to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = self._get_supabase_client()

            # Sanitize large payloads before persisting to Postgres
            sanitized_data = self._sanitize_research_documents_data(research_data)

            response = supabase.client.table('vmp_projects').update({
                'research_documents_data': sanitized_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()

            return len(response.data) > 0
            
        except Exception as e:
            print(f"Error updating research documents data: {e}")
            return False

    def _sanitize_research_documents_data(self, research_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Ensure research document payloads are storage friendly."""
        if not research_data:
            return {}

        sanitized_data: Dict[str, Any] = {}

        for doc_key, doc_payload in research_data.items():
            if not isinstance(doc_payload, dict):
                sanitized_data[doc_key] = _ensure_json_serializable(doc_payload)
                continue

            sanitized_doc: Dict[str, Any] = {}

            for key, value in doc_payload.items():
                if key == "chunks" and isinstance(value, list):
                    sanitized_doc["chunks"] = [
                        _ensure_json_serializable(sanitize_chunk_for_storage(chunk))
                        for chunk in value
                        if isinstance(chunk, dict)
                    ]
                elif key in {"raw_text", "structured_content", "content"} and isinstance(value, str):
                    sanitized_doc[key] = _truncate_text(value, limit=5000)
                else:
                    sanitized_doc[key] = _ensure_json_serializable(value)

            # Derive lightweight metrics if chunks present
            chunks = sanitized_doc.get("chunks", [])
            if isinstance(chunks, list):
                sanitized_doc.setdefault("chunk_count", len(chunks))
                sanitized_doc.setdefault(
                    "chunks_with_embeddings",
                    sum(1 for chunk in chunks if chunk.get("has_embedding"))
                )

            sanitized_data[doc_key] = _ensure_json_serializable(sanitized_doc)

        return _ensure_json_serializable(sanitized_data)
    
    async def update_analysis_data(
        self, 
        project_id: str, 
        tenant_id: str, 
        analysis_data: Dict[str, Any],
        status: str = 'processing',
        persona_id: Optional[str] = None
    ) -> bool:
        """
        🚀 MULTI-PERSONA: Update analysis data with persona-specific storage.
        
        Stores analysis results keyed by persona_id to support multiple personas.
        If persona_id is provided, stores data under that persona key.
        If persona_id is None, stores at root level (backward compatibility).
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            analysis_data: The analysis data to store (includes structured_report)
            status: The analysis status ('processing', 'completed', 'failed')
            persona_id: Optional persona ID for multi-persona projects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Set stage in analysis data first
            if status == 'completed':
                analysis_data["stage"] = "analysis_completed"
            elif status == 'processing':
                analysis_data["stage"] = "analyzing_assumptions"
            elif status == 'not_started':
                analysis_data["stage"] = "not_started"
            elif status == 'failed':
                analysis_data["stage"] = "failed"
            
            # 🎭 MULTI-PERSONA: Optimized approach with retry logic
            if persona_id:
                # Get only the minimal data we need
                supabase = self._get_supabase_client()
                
                # Retry logic for database operations
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        check_response = supabase.client.table('vmp_projects').select('analysis_data').eq('id', project_id).eq('tenant_id', tenant_id).limit(1).execute()
                        
                        if check_response.data and len(check_response.data) > 0:
                            existing_data = check_response.data[0].get('analysis_data') or {}
                        else:
                            existing_data = {}
                        
                        # Initialize personas structure if needed
                        if "personas" not in existing_data:
                            existing_data = {"personas": {}, "stage": "not_started"}
                        
                        # Store this persona's data
                        existing_data["personas"][persona_id] = analysis_data
                        
                        # Simple stage aggregation
                        existing_data["stage"] = analysis_data.get("stage", "not_started")
                        
                        final_data = existing_data
                        print(f"🎭 MULTI-PERSONA STORAGE: Storing analysis for persona '{persona_id}'")
                        print(f"🎭 MULTI-PERSONA STORAGE: Total personas: {len(existing_data['personas'])}")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"❌ MULTI-PERSONA: Failed after {max_retries} retries: {e}")
                            raise
                        print(f"⚠️ MULTI-PERSONA: Retry {retry_count}/{max_retries} after error: {e}")
                        import time
                        time.sleep(0.5 * retry_count)  # Exponential backoff
                
            else:
                # Single persona or legacy mode: store at root level
                final_data = analysis_data
                print(f"📊 SINGLE PERSONA STORAGE: Storing analysis at root level")
            
            # 🚀 JSON STORAGE: Log structured report presence
            if "structured_report" in analysis_data:
                structured_report = analysis_data["structured_report"]
                if isinstance(structured_report, dict):
                    assumptions_count = len(structured_report.get("assumptions", []))
                    persona_tag = f" for persona '{persona_id}'" if persona_id else ""
                    print(f"🚀 JSON STORAGE: Storing structured report with {assumptions_count} assumptions{persona_tag}")
                else:
                    print(f"⚠️ JSON STORAGE: structured_report is not a dict: {type(structured_report)}")
            
            # Log the actual stage that was set
            print(f"🔍 DB_ADAPTER DEBUG: Set stage to '{analysis_data.get('stage', 'unknown')}'")
            print(f"🔍 DB_ADAPTER DEBUG: Root-level stage: '{final_data.get('stage', 'unknown')}'")
            
            # Debug: Log what we're about to save to database
            print(f"🔍 DB_ADAPTER DEBUG: update_analysis_data called with:")
            print(f"🔍 DB_ADAPTER DEBUG: - project_id: {project_id}")
            print(f"🔍 DB_ADAPTER DEBUG: - tenant_id: {tenant_id}")
            print(f"🔍 DB_ADAPTER DEBUG: - status: {status}")
            print(f"🔍 DB_ADAPTER DEBUG: - persona_id: {persona_id}")
            print(f"🔍 DB_ADAPTER DEBUG: - analysis_data keys: {list(analysis_data.keys()) if analysis_data else 'None'}")
            print(f"🔍 DB_ADAPTER DEBUG: - final_data keys: {list(final_data.keys()) if final_data else 'None'}")
            
            if persona_id and "personas" in final_data:
                print(f"🎭 DB_ADAPTER DEBUG: - Personas in storage: {list(final_data['personas'].keys())}")
            
            if analysis_data:
                assumption_analyses = analysis_data.get("assumption_analyses", [])
                final_report = analysis_data.get("final_report", "")
                structured_report = analysis_data.get("structured_report")
                print(f"🔍 DB_ADAPTER DEBUG: - assumption_analyses count: {len(assumption_analyses)}")
                print(f"🔍 DB_ADAPTER DEBUG: - final_report length: {len(final_report)}")
                print(f"🔍 DB_ADAPTER DEBUG: - structured_report present: {structured_report is not None}")
                if structured_report:
                    print(f"🔍 DB_ADAPTER DEBUG: - structured_report type: {type(structured_report)}")
                    if isinstance(structured_report, dict):
                        print(f"🔍 DB_ADAPTER DEBUG: - structured_report assumptions: {len(structured_report.get('assumptions', []))}")
            
            # 🔄 RETRY LOGIC: Apply retry to the actual write operation too
            supabase = self._get_supabase_client()
            max_write_retries = 3
            write_retry_count = 0
            
            while write_retry_count < max_write_retries:
                try:
                    response = supabase.client.table('vmp_projects').update({
                        'analysis_data': final_data,
                        'analysis_status': status,
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
                    
                    success = len(response.data) > 0
                    print(f"🔍 DB_ADAPTER DEBUG: Database update success: {success}")
                    print(f"🔍 DB_ADAPTER DEBUG: Response data count: {len(response.data) if response.data else 0}")
                    
                    return success
                    
                except Exception as write_error:
                    write_retry_count += 1
                    if write_retry_count >= max_write_retries:
                        print(f"❌ DB_ADAPTER: Write failed after {max_write_retries} retries: {write_error}")
                        raise
                    print(f"⚠️ DB_ADAPTER: Write retry {write_retry_count}/{max_write_retries} after error: {write_error}")
                    import time
                    time.sleep(1.0 * write_retry_count)  # 1s, 2s, 3s backoff
            
        except Exception as e:
            print(f"Error updating analysis data: {e}")
            return False
    
    async def update_analysis_status(
        self, 
        project_id: str, 
        tenant_id: str, 
        status: str
    ) -> bool:
        """
        Update analysis status in the vmp_projects table.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            status: The new analysis status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = self._get_supabase_client()
            response = supabase.client.table('vmp_projects').update({
                'analysis_status': status,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            print(f"Error updating analysis status: {e}")
            return False
    
    # Research Document Storage Methods
    
    async def store_research_document(
        self,
        project_id: str,
        tenant_id: str,
        document_type: str,  # 'pdf' or 'csv'
        raw_content: str,
        chunks: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store research document with chunked content and metadata.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            document_type: Type of document ('pdf' or 'csv')
            raw_content: Raw extracted content
            chunks: List of chunked content with embeddings
            metadata: Document metadata (filename, size, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current research documents data
            current_data = await self.get_research_documents_data(project_id, tenant_id)
            if current_data is None:
                current_data = {}
            
            # Add new document data
            document_key = f"{document_type}_content"
            current_data[document_key] = {
                "raw_content": raw_content,
                "chunks": chunks,
                "metadata": {
                    **metadata,
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "chunk_count": len(chunks)
                }
            }
            
            # Update the database
            return await self.update_research_documents_data(project_id, tenant_id, current_data)
            
        except Exception as e:
            print(f"Error storing research document: {e}")
            return False

    async def store_research_documents_data(
        self,
        project_id: str,
        tenant_id: str,
        research_documents: Dict[str, Any]
    ) -> bool:
        """Merge and persist research document metadata in a storage-safe format."""

        try:
            current_data = await self.get_research_documents_data(project_id, tenant_id) or {}

            # Merge document data – new payloads override existing keys
            for key, value in (research_documents or {}).items():
                if isinstance(value, dict) and isinstance(current_data.get(key), dict):
                    merged = {**current_data[key], **value}
                    current_data[key] = merged
                else:
                    current_data[key] = value

            return await self.update_research_documents_data(project_id, tenant_id, current_data)

        except Exception as e:
            print(f"Error storing research documents data: {e}")
            return False
    
    async def get_research_documents_data(
        self,
        project_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve research documents data for a project.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            Research documents data or None if not found
        """
        try:
            supabase = self._get_supabase_client()
            response = supabase.client.table('vmp_projects').select(
                'research_documents_data'
            ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                return None
                
            return response.data[0].get('research_documents_data', {})
            
        except Exception as e:
            print(f"Error retrieving research documents data: {e}")
            return None
    
    async def get_research_chunks_for_analysis(
        self,
        project_id: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all research chunks for analysis processing.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            List of all chunks from all documents
        """
        try:
            research_data = await self.get_research_documents_data(project_id, tenant_id)
            if not research_data:
                return []
            
            all_chunks = []
            
            # AGGRESSIVE FIX: Collect chunks from all document sources
            for doc_key, doc_data in research_data.items():
                if not isinstance(doc_data, dict):
                    continue
                
                # FIXED: Try correct chunk storage locations (chunks is the actual data)
                chunks = []
                if 'chunks' in doc_data:
                    chunks_data = doc_data['chunks']
                    if isinstance(chunks_data, list):
                        chunks = chunks_data
                elif 'chunks_with_embeddings' in doc_data:
                    chunks_data = doc_data['chunks_with_embeddings']
                    if isinstance(chunks_data, list):
                        chunks = chunks_data
                
                if chunks:
                    # Determine source type
                    if 'csv' in doc_key.lower():
                        source_type = 'csv'
                    elif 'pdf' in doc_key.lower():
                        source_type = 'pdf'
                    else:
                        source_type = 'unknown'
                    
                    # Add metadata to chunks
                    for chunk in chunks:
                        chunk['source_type'] = source_type
                        chunk['source_key'] = doc_key
                        chunk['source_metadata'] = doc_data.get('metadata', {})
                    
                    all_chunks.extend(chunks)
            
            return all_chunks
            
        except Exception as e:
            logger.error(f"Error retrieving research chunks: {e}")
            return []
    
    async def get_research_chunks(
        self,
        project_id: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        Enterprise method: Retrieve all research chunks from all sources for comprehensive analysis.
        
        This method provides the complete dataset for enterprise-grade analysis including
        multi-source evidence synthesis and cross-file validation.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            List of all chunks from all documents with enhanced metadata
        """
        try:
            research_data = await self.get_research_documents_data(project_id, tenant_id)
            if not research_data:
                print(f"🔍 ENTERPRISE CHUNKS: No research data found for project {project_id}")
                return []
            
            all_chunks = []
            
            # Process all document types in research_data
            for doc_key, doc_data in research_data.items():
                if not isinstance(doc_data, dict):
                    continue
                    
                # AGGRESSIVE FIX: Check multiple possible chunk locations
                chunks = []
                
                # FIXED: Try correct chunk storage locations (chunks is the actual data)
                if 'chunks' in doc_data:
                    chunks_data = doc_data['chunks']
                    if isinstance(chunks_data, list):
                        chunks = chunks_data
                        print(f"✅ ENTERPRISE CHUNKS: Found {len(chunks)} chunks in chunks for {doc_key}")
                    else:
                        print(f"❌ ENTERPRISE CHUNKS: chunks is not a list for {doc_key}, type: {type(chunks_data)}")
                        continue
                elif 'chunks_with_embeddings' in doc_data:
                    chunks_data = doc_data['chunks_with_embeddings']
                    if isinstance(chunks_data, list):
                        chunks = chunks_data
                        print(f"✅ ENTERPRISE CHUNKS: Found {len(chunks)} chunks in chunks_with_embeddings for {doc_key}")
                    else:
                        print(f"❌ ENTERPRISE CHUNKS: chunks_with_embeddings is count, not chunks for {doc_key}: {chunks_data}")
                        continue
                else:
                    print(f"❌ ENTERPRISE CHUNKS: No chunks found in {doc_key}, keys: {list(doc_data.keys())}")
                    continue
                
                if not chunks:
                    print(f"❌ ENTERPRISE CHUNKS: Empty chunks array in {doc_key}")
                    continue
                
                # Determine source type from document key
                if 'csv' in doc_key.lower():
                    source_type = 'csv'
                elif 'pdf' in doc_key.lower():
                    source_type = 'pdf'
                else:
                    source_type = 'unknown'
                
                # Enhance chunks with enterprise metadata
                for chunk in chunks:
                    enhanced_chunk = {
                        **chunk,
                        'source_type': source_type,
                        'source_key': doc_key,
                        'source_metadata': doc_data.get('metadata', {}),
                        'quantitative_summary': doc_data.get('quantitative_summary', {}),
                        'processing_timestamp': doc_data.get('processing_timestamp'),
                        'enterprise_enhanced': True
                    }
                    all_chunks.append(enhanced_chunk)
            
            print(f"✅ ENTERPRISE CHUNKS: Retrieved {len(all_chunks)} chunks from {len(research_data)} sources")
            return all_chunks
            
        except Exception as e:
            print(f"❌ ENTERPRISE CHUNKS: Error retrieving research chunks: {e}")
            return []
    
    async def store_document_processing_status(
        self,
        project_id: str,
        tenant_id: str,
        document_type: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Store document processing status and error information.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            document_type: Type of document ('pdf' or 'csv')
            status: Processing status ('processing', 'completed', 'failed')
            error_message: Error message if processing failed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current research documents data
            current_data = await self.get_research_documents_data(project_id, tenant_id)
            if current_data is None:
                current_data = {}
            
            # Initialize processing status if not exists
            if 'processing_status' not in current_data:
                current_data['processing_status'] = {}
            
            # Update status for this document type
            current_data['processing_status'][document_type] = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if error_message:
                current_data['processing_status'][document_type]['error_message'] = error_message
            
            # Update the database
            return await self.update_research_documents_data(project_id, tenant_id, current_data)
            
        except Exception as e:
            print(f"Error storing document processing status: {e}")
            return False
    
    async def store_analysis_result(self, analysis_record: Dict[str, Any]) -> bool:
        """
        Store individual analysis result for streaming approach.
        
        Args:
            analysis_record: Complete analysis record with all data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # For now, use the existing store_assumption_analysis method
            # This maintains compatibility with the current database structure
            return await self.store_assumption_analysis(
                analysis_record["project_id"],
                analysis_record["tenant_id"],
                analysis_record
            )
            
        except Exception as e:
            print(f"Error storing analysis result: {e}")
            return False
    
    async def load_analysis_results(self, project_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Load all analysis results for report synthesis.
        
        Handles both single-persona (legacy) and multi-persona storage formats.
        For multi-persona, returns ALL analyses from ALL personas with persona_id tagged.
        
        CRITICAL FIX: Check ROOT level first before looking inside personas.
        Storage sometimes puts assumption_analyses at root even when personas key exists.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            List of all analysis results (with persona_id for multi-persona)
        """
        try:
            # Get current analysis data which contains all assumption analyses
            current_data = await self.get_analysis_data(project_id, tenant_id)
            if not current_data:
                return []
            
            # CRITICAL FIX: Always check ROOT level first
            # Storage may put assumption_analyses at root even when personas key exists
            root_analyses = current_data.get("assumption_analyses", [])
            if root_analyses and len(root_analyses) > 0:
                print(f"📊 LOAD_RESULTS: Loaded {len(root_analyses)} analyses from ROOT level")
                return root_analyses
            
            # MULTI-PERSONA SUPPORT: Check if data is in multi-persona format with actual data
            if "personas" in current_data and isinstance(current_data["personas"], dict):
                # Multi-persona format: aggregate analyses from all personas
                all_analyses = []
                for persona_id, persona_data in current_data["personas"].items():
                    if isinstance(persona_data, dict):
                        persona_analyses = persona_data.get("assumption_analyses", [])
                        # Tag each analysis with its persona_id for filtering
                        for analysis in persona_analyses:
                            if isinstance(analysis, dict):
                                # Ensure persona_id is set on each analysis
                                analysis_copy = analysis.copy()
                                analysis_copy["persona_id"] = persona_id
                                all_analyses.append(analysis_copy)
                
                if all_analyses:
                    print(f"🎭 LOAD_RESULTS: Loaded {len(all_analyses)} analyses from {len(current_data['personas'])} personas")
                    return all_analyses
                else:
                    print(f"🎭 LOAD_RESULTS: Loaded 0 analyses (personas exist but empty)")
                    return []
            
            # No analyses found anywhere
            print(f"📊 LOAD_RESULTS: No analyses found in database")
            return []
            
        except Exception as e:
            print(f"Error loading analysis results: {e}")
            return []
    
    async def cleanup_duplicate_analyses(self, project_id: str, tenant_id: str) -> bool:
        """
        Emergency cleanup of duplicate analysis results.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current analysis data
            current_data = await self.get_analysis_data(project_id, tenant_id)
            if not current_data:
                return True
            
            analyses = current_data.get("assumption_analyses", [])
            if len(analyses) <= 10:
                return True  # No cleanup needed
            
            print(f"🚨 CLEANUP: Found {len(analyses)} analyses. Starting deduplication...")
            
            # Keep only unique analyses (by assumption_id)
            seen_assumptions = set()
            unique_analyses = []
            
            for analysis in analyses:
                assumption_id = analysis.get("assumption_id", "unknown")
                if assumption_id not in seen_assumptions:
                    seen_assumptions.add(assumption_id)
                    unique_analyses.append(analysis)
            
            print(f"🚨 CLEANUP: Reduced from {len(analyses)} to {len(unique_analyses)} unique analyses")
            
            # Update with cleaned data
            current_data["assumption_analyses"] = unique_analyses
            
            success = await self.update_analysis_data(project_id, tenant_id, current_data, 'processing')
            
            if success:
                print(f"✅ CLEANUP: Successfully cleaned database for project {project_id}")
            else:
                print(f"❌ CLEANUP: Failed to update database for project {project_id}")
            
            return success
            
        except Exception as e:
            print(f"Error cleaning duplicate analyses: {e}")
            return False
    
    async def get_document_processing_status(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get document processing status for all documents.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            Dictionary with processing status for each document type
        """
        try:
            research_data = await self.get_research_documents_data(project_id, tenant_id)
            if not research_data:
                return {}
            
            return research_data.get('processing_status', {})
            
        except Exception as e:
            print(f"Error retrieving document processing status: {e}")
            return {}
    
    async def clear_research_documents(
        self,
        project_id: str,
        tenant_id: str
    ) -> bool:
        """
        Clear all research documents data for a project.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.update_research_documents_data(project_id, tenant_id, {})
            
        except Exception as e:
            print(f"Error clearing research documents: {e}")
            return False
    
    async def clear_analysis_data(
        self,
        project_id: str,
        tenant_id: str,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Clear all analysis data to start a fresh analysis.
        
        This method is called when starting a NEW analysis to ensure
        old data doesn't interfere. It resets the analysis state completely.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            session_id: Optional new session ID for the fresh analysis
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import uuid
            
            # Create fresh, empty analysis data structure
            fresh_data = {
                "session_id": session_id or str(uuid.uuid4()),
                "session_metadata": {
                    "stage": "not_started",
                    "started_at": datetime.utcnow().isoformat(),
                    "cleared_at": datetime.utcnow().isoformat()
                },
                "assumption_analyses": [],  # EMPTY - no old data
                "final_report": "",
                "progress": {
                    "total_assumptions": 0,
                    "processed_assumptions": 0,
                    "current_assumption": None
                }
            }
            
            print(f"🔄 CLEAR: Clearing all analysis data for project {project_id}")
            print(f"🔄 CLEAR: New session_id: {fresh_data['session_id']}")
            
            # Update with fresh data and reset status
            success = await self.update_analysis_data(
                project_id, tenant_id, fresh_data, 'not_started'
            )
            
            if success:
                print(f"✅ CLEAR: Successfully cleared analysis data for fresh start")
            else:
                print(f"❌ CLEAR: Failed to clear analysis data")
            
            return success
            
        except Exception as e:
            print(f"Error clearing analysis data: {e}")
            return False
    
    # Analysis Results Storage Methods
    
    async def store_analysis_session(
        self,
        project_id: str,
        tenant_id: str,
        session_id: str,
        session_metadata: Dict[str, Any]
    ) -> bool:
        """
        Initialize a new analysis session with metadata.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            session_id: Unique session identifier
            session_metadata: Session metadata (user_id, started_at, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            analysis_data = {
                "session_id": session_id,
                "session_metadata": {
                    **session_metadata,
                    "started_at": datetime.utcnow().isoformat(),
                    "stage": "initialized"
                },
                "assumption_analyses": [],
                "final_report": "",
                "progress": {
                    "total_assumptions": 0,
                    "processed_assumptions": 0,
                    "current_assumption": None
                }
            }
            
            # Update analysis status to processing
            await self.update_analysis_status(project_id, tenant_id, 'processing')
            
            return await self.update_analysis_data(project_id, tenant_id, analysis_data, 'processing')
            
        except Exception as e:
            print(f"Error storing analysis session: {e}")
            return False
    
    async def update_analysis_progress(
        self,
        project_id: str,
        tenant_id: str,
        total_assumptions: int,
        processed_assumptions: int,
        current_assumption: Optional[str] = None
    ) -> bool:
        """
        Update analysis progress tracking.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            total_assumptions: Total number of assumptions to process
            processed_assumptions: Number of assumptions processed so far
            current_assumption: Currently processing assumption ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current analysis data
            current_data = await self.get_analysis_data(project_id, tenant_id)
            if not current_data:
                return False
            
            # Update progress
            current_data["progress"] = {
                "total_assumptions": total_assumptions,
                "processed_assumptions": processed_assumptions,
                "current_assumption": current_assumption,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            return await self.update_analysis_data(project_id, tenant_id, current_data, 'processing')
            
        except Exception as e:
            print(f"Error updating analysis progress: {e}")
            return False
    
    async def store_assumption_analysis(
        self,
        project_id: str,
        tenant_id: str,
        assumption_analysis: Dict[str, Any]
    ) -> bool:
        """
        Store analysis results for a single assumption.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            assumption_analysis: Complete analysis results for one assumption
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current analysis data
            current_data = await self.get_analysis_data(project_id, tenant_id)
            if not current_data:
                # Initialize analysis data if it doesn't exist
                current_data = {
                    "session_metadata": {
                        "stage": "analyzing_assumptions",
                        "started_at": datetime.utcnow().isoformat()
                    },
                    "assumption_analyses": [],
                    "final_report": "",
                    "progress": {
                        "total_assumptions": 0,
                        "processed_assumptions": 0,
                        "current_assumption": None
                    }
                }
            
            # Ensure session_metadata exists
            if "session_metadata" not in current_data:
                current_data["session_metadata"] = {
                    "stage": "analyzing_assumptions",
                    "started_at": datetime.utcnow().isoformat()
                }
            
            # Ensure assumption_analyses list exists
            if "assumption_analyses" not in current_data:
                current_data["assumption_analyses"] = []
            
            # Add timestamp to assumption analysis
            assumption_analysis["analyzed_at"] = datetime.utcnow().isoformat()
            
            # CRITICAL FIX: Replace existing analyses for the same assumption instead of blindly appending
            assumption_id = assumption_analysis.get("assumption_id", "unknown")

            existing_index = next(
                (
                    index
                    for index, analysis in enumerate(current_data["assumption_analyses"])
                    if analysis.get("assumption_id") == assumption_id
                ),
                None,
            )

            if existing_index is not None:
                print(f"🔁 STORE: Updating existing analysis for assumption '{assumption_id}' at index {existing_index}")
                current_data["assumption_analyses"][existing_index] = assumption_analysis
            else:
                print(f"💾 STORE: Storing analysis for assumption '{assumption_id}'")
                current_data["assumption_analyses"].append(assumption_analysis)

            print(f"💾 STORE: Total analyses in database: {len(current_data['assumption_analyses'])}")
            
            # Update stage
            current_data["session_metadata"]["stage"] = "analyzing_assumptions"
            
            return await self.update_analysis_data(project_id, tenant_id, current_data, 'processing')
            
        except Exception as e:
            print(f"Error storing assumption analysis: {e}")
            return False
    
    async def store_final_report(
        self,
        project_id: str,
        tenant_id: str,
        final_report: str,
        report_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store the final analysis report and mark analysis as completed.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            final_report: The complete markdown report
            report_metadata: Optional metadata about the report
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current analysis data
            current_data = await self.get_analysis_data(project_id, tenant_id)
            if not current_data:
                return False
            
            # Store final report
            current_data["final_report"] = final_report
            current_data["session_metadata"]["stage"] = "analysis_completed"
            current_data["session_metadata"]["completed_at"] = datetime.utcnow().isoformat()
            
            if report_metadata:
                current_data["report_metadata"] = report_metadata
            
            return await self.update_analysis_data(project_id, tenant_id, current_data, 'completed')
            
        except Exception as e:
            print(f"Error storing final report: {e}")
            return False
    
    async def get_analysis_data(
        self,
        project_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis data for a project.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            Analysis data or None if not found
        """
        try:
            supabase = self._get_supabase_client()
            response = supabase.client.table('vmp_projects').select(
                'analysis_data'
            ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                return None
                
            return response.data[0].get('analysis_data', {})
            
        except Exception as e:
            print(f"Error retrieving analysis data: {e}")
            return None
    
    async def get_analysis_status(
        self,
        project_id: str,
        tenant_id: str
    ) -> Optional[str]:
        """
        Get the current analysis status for a project.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            Analysis status or None if not found
        """
        try:
            supabase = self._get_supabase_client()
            response = supabase.client.table('vmp_projects').select(
                'analysis_status'
            ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
            
            if not response.data:
                return None
                
            return response.data[0].get('analysis_status', 'not_started')
            
        except Exception as e:
            print(f"Error retrieving analysis status: {e}")
            return None
    
    async def get_analysis_progress(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get analysis progress information.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            Progress information dictionary
        """
        try:
            analysis_data = await self.get_analysis_data(project_id, tenant_id)
            if not analysis_data:
                return {
                    "total_assumptions": 0,
                    "processed_assumptions": 0,
                    "current_assumption": None,
                    "stage": "not_started"
                }
            
            progress = analysis_data.get("progress", {})
            stage = analysis_data.get("session_metadata", {}).get("stage", "unknown")
            
            return {
                **progress,
                "stage": stage
            }
            
        except Exception as e:
            print(f"Error retrieving analysis progress: {e}")
            return {}
    
    async def store_analysis_error(
        self,
        project_id: str,
        tenant_id: str,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store analysis error information and update status to failed.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            error_message: The error message
            error_context: Optional context about the error
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current analysis data
            current_data = await self.get_analysis_data(project_id, tenant_id)
            if not current_data:
                # Create minimal error data if no existing data
                current_data = {
                    "session_id": f"error-{datetime.utcnow().timestamp()}",
                    "session_metadata": {"stage": "failed"},
                    "assumption_analyses": [],
                    "final_report": ""
                }
            
            # Store error information
            current_data["error"] = {
                "message": error_message,
                "context": error_context or {},
                "occurred_at": datetime.utcnow().isoformat()
            }
            current_data["session_metadata"]["stage"] = "failed"
            
            return await self.update_analysis_data(project_id, tenant_id, current_data, 'failed')
            
        except Exception as e:
            print(f"Error storing analysis error: {e}")
            return False
    
    async def clear_analysis_data(
        self,
        project_id: str,
        tenant_id: str
    ) -> bool:
        """
        Clear analysis data and reset status to not_started.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.update_analysis_data(project_id, tenant_id, {}, 'not_started')
            
        except Exception as e:
            print(f"Error clearing analysis data: {e}")
            return False
    
    # Enhanced methods for statistics registry and two-tier RAG support
    
    async def get_statistics_registry(
        self,
        project_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get statistics registry from research_documents_data.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            Statistics registry or None if not found
        """
        try:
            research_data = await self.get_research_documents_data(project_id, tenant_id)
            if not research_data:
                return None
            
            return research_data.get("statistics_registry", {})
            
        except Exception as e:
            print(f"Error retrieving statistics registry: {e}")
            return None
    
    async def update_statistics_registry(
        self,
        project_id: str,
        tenant_id: str,
        statistics_registry: Dict[str, Any]
    ) -> bool:
        """
        Update statistics registry in research_documents_data.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            statistics_registry: The statistics registry to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current research documents data
            research_data = await self.get_research_documents_data(project_id, tenant_id)
            if research_data is None:
                research_data = {}
            
            # Update statistics registry
            research_data["statistics_registry"] = statistics_registry
            
            # Store back to database
            return await self.update_research_documents_data(project_id, tenant_id, research_data)
            
        except Exception as e:
            print(f"Error updating statistics registry: {e}")
            return False
    
    async def store_fact_validation_results(
        self,
        project_id: str,
        tenant_id: str,
        assumption_id: str,
        validation_results: Dict[str, Any]
    ) -> bool:
        """
        Store fact validation results for an assumption analysis.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            assumption_id: The assumption identifier
            validation_results: Fact validation results
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current analysis data
            analysis_data = await self.get_analysis_data(project_id, tenant_id)
            if not analysis_data:
                return False
            
            # Find the assumption analysis
            assumption_analyses = analysis_data.get("assumption_analyses", [])
            for analysis in assumption_analyses:
                if analysis.get("assumption_id") == assumption_id:
                    # Add fact validation results
                    analysis["fact_validation_results"] = validation_results
                    analysis["validation_updated_at"] = datetime.utcnow().isoformat()
                    break
            
            # Update analysis data
            return await self.update_analysis_data(project_id, tenant_id, analysis_data, "processing")
            
        except Exception as e:
            print(f"Error storing fact validation results: {e}")
            return False
    
    async def store_generated_visualizations(
        self,
        project_id: str,
        tenant_id: str,
        visualizations: Dict[str, Any]
    ) -> bool:
        """
        Store generated visualizations in analysis_data.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            visualizations: Generated visualizations data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current analysis data
            analysis_data = await self.get_analysis_data(project_id, tenant_id)
            if not analysis_data:
                return False
            
            # Store visualizations
            analysis_data["generated_visualizations"] = visualizations
            analysis_data["visualizations_updated_at"] = datetime.utcnow().isoformat()
            
            # Update analysis data
            return await self.update_analysis_data(project_id, tenant_id, analysis_data, "processing")
            
        except Exception as e:
            print(f"Error storing generated visualizations: {e}")
            return False
    
    async def get_persona_data_associations(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get persona data associations from statistics registry.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            persona_id: Optional specific persona ID to filter by
            
        Returns:
            Persona data associations
        """
        try:
            statistics_registry = await self.get_statistics_registry(project_id, tenant_id)
            if not statistics_registry:
                return {}
            
            persona_mappings = statistics_registry.get("persona_mappings", {})
            
            if persona_id:
                return persona_mappings.get(persona_id, {})
            else:
                return persona_mappings
            
        except Exception as e:
            print(f"Error retrieving persona data associations: {e}")
            return {}
    
    async def update_persona_data_associations(
        self,
        project_id: str,
        tenant_id: str,
        persona_id: str,
        associations: Dict[str, Any]
    ) -> bool:
        """
        Update persona data associations in statistics registry.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            persona_id: The persona identifier
            associations: Persona data associations
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current statistics registry
            statistics_registry = await self.get_statistics_registry(project_id, tenant_id)
            if statistics_registry is None:
                statistics_registry = {}
            
            # Ensure persona_mappings exists
            if "persona_mappings" not in statistics_registry:
                statistics_registry["persona_mappings"] = {}
            
            # Update persona associations
            statistics_registry["persona_mappings"][persona_id] = associations
            
            # Store back to database
            return await self.update_statistics_registry(project_id, tenant_id, statistics_registry)
            
        except Exception as e:
            print(f"Error updating persona data associations: {e}")
            return False
    
    async def get_citation_registry(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get citation registry from statistics registry.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            
        Returns:
            Citation registry
        """
        try:
            statistics_registry = await self.get_statistics_registry(project_id, tenant_id)
            if not statistics_registry:
                return {}
            
            return statistics_registry.get("citation_registry", {})
            
        except Exception as e:
            print(f"Error retrieving citation registry: {e}")
            return {}
    
    async def verify_citation(
        self,
        project_id: str,
        tenant_id: str,
        citation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify a citation against the citation registry.
        
        Args:
            project_id: The VMP project ID
            tenant_id: The tenant ID
            citation_id: The citation identifier to verify
            
        Returns:
            Citation data if valid, None if not found
        """
        try:
            citation_registry = await self.get_citation_registry(project_id, tenant_id)
            return citation_registry.get(citation_id)
            
        except Exception as e:
            print(f"Error verifying citation: {e}")
            return None