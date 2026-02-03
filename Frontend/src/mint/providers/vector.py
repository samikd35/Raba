"""
Vector Provider implementations for MINT.

This module defines the VectorProvider abstract base class and concrete implementations
for pgvector (Supabase) and Qdrant.
"""

import os
from typing import Dict, List, Literal, Optional, Any, Tuple

import numpy as np
from pydantic import BaseModel, Field
from supabase import create_client, Client
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance

from .registry import Provider, ProviderConfig, ProviderError


class VectorConfig(ProviderConfig):
    """Configuration for vector store providers."""
    provider_type: Literal["vector"] = "vector"
    collection_name: str = "mint_embeddings"
    embedding_dimension: int = 1536  # OpenAI default
    distance_metric: str = "cosine"


class VectorSearchResult(BaseModel):
    """Standardized vector search result."""
    id: str
    score: float
    document: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class VectorProvider(Provider[List[VectorSearchResult]]):
    """Abstract base class for vector store providers."""
    
    def __init__(self, config: VectorConfig):
        """Initialize with vector-specific configuration."""
        super().__init__(config)
        self.config = config  # Re-assign for proper type inference
    
    async def create_collection(self, collection_name: Optional[str] = None) -> bool:
        """Create a collection if it doesn't exist."""
        raise NotImplementedError("Subclasses must implement create_collection method")
    
    async def index_documents(
        self, 
        documents: List[Dict[str, Any]], 
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None
    ) -> bool:
        """Index documents with their embeddings."""
        raise NotImplementedError("Subclasses must implement index_documents method")
    
    async def search(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors."""
        raise NotImplementedError("Subclasses must implement search method")


class PgVectorProvider(VectorProvider):
    """pgvector (Supabase) implementation of Vector Provider."""
    
    def __init__(self, config: Optional[VectorConfig] = None):
        """Initialize pgvector provider."""
        config = config or VectorConfig(
            provider_name="pgvector",
            api_key_env_var="SUPABASE_KEY",
        )
        super().__init__(config)
        
        self.client = None
        self.supabase_url = os.environ.get("SUPABASE_URL")
        
        if self.api_key and self.supabase_url:
            self.client = create_client(self.supabase_url, self.api_key)
    
    def health_check(self) -> bool:
        """Check if Supabase is operational."""
        if not self.client:
            return False
        try:
            # Simple API call to check connectivity
            self.client.table("health_check").select("*").limit(1).execute()
            return True
        except Exception:
            return False
    
    def fallback_available(self) -> bool:
        """pgvector doesn't have built-in fallbacks."""
        return False
    
    async def create_collection(self, collection_name: Optional[str] = None) -> bool:
        """Create a collection using pgvector extension."""
        if not self.client:
            raise ProviderError("Supabase client not initialized. Check API keys.")
        
        table_name = collection_name or self.config.collection_name
        
        try:
            # Check if table exists first
            result = self.client.rpc(
                "check_table_exists", 
                {"table_name": table_name}
            ).execute()
            
            if not result.data or not result.data[0].get("exists", False):
                # Create table with vector extension
                dimension = self.config.embedding_dimension
                self.client.rpc(
                    "create_embeddings_table", 
                    {
                        "table_name": table_name,
                        "dimension": dimension
                    }
                ).execute()
            return True
        except Exception as e:
            raise ProviderError(f"Failed to create pgvector collection: {str(e)}")
    
    async def index_documents(
        self, 
        documents: List[Dict[str, Any]], 
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None
    ) -> bool:
        """Index documents with their embeddings in Supabase."""
        if not self.client:
            raise ProviderError("Supabase client not initialized. Check API keys.")
        
        if len(documents) != len(embeddings):
            raise ProviderError("Number of documents must match number of embeddings")
        
        table_name = self.config.collection_name
        
        try:
            # Check if collection exists, create if not
            await self.create_collection()
            
            # Prepare data for insertion
            data_to_insert = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                doc_id = ids[i] if ids and i < len(ids) else f"doc_{i}"
                data_to_insert.append({
                    "id": doc_id,
                    "content": doc.get("content", ""),
                    "metadata": doc.get("metadata", {}),
                    "embedding": embedding
                })
            
            # Insert data in batches of 100
            batch_size = 100
            for i in range(0, len(data_to_insert), batch_size):
                batch = data_to_insert[i:i+batch_size]
                self.client.table(table_name).insert(batch).execute()
            
            return True
        except Exception as e:
            raise ProviderError(f"Failed to index documents in pgvector: {str(e)}")
    
    async def search(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors in Supabase."""
        if not self.client:
            raise ProviderError("Supabase client not initialized. Check API keys.")
        
        table_name = self.config.collection_name
        
        try:
            query = self.client.rpc(
                "match_embeddings",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.7,
                    "match_count": limit,
                    "table_name": table_name
                }
            )
            
            if metadata_filter:
                for key, value in metadata_filter.items():
                    if isinstance(value, list):
                        # Handle array containment
                        query = query.filter(f"metadata->>'{key}'", "in", value)
                    else:
                        # Handle exact match
                        query = query.filter(f"metadata->>'{key}'", "eq", value)
            
            result = query.execute()
            
            vector_results = []
            for item in result.data:
                vector_results.append(VectorSearchResult(
                    id=item.get("id", ""),
                    score=item.get("similarity", 0.0),
                    document={"content": item.get("content", "")},
                    metadata=item.get("metadata", {})
                ))
                
            return vector_results
        except Exception as e:
            raise ProviderError(f"Failed to search vectors in pgvector: {str(e)}")


class QdrantVectorProvider(VectorProvider):
    """Qdrant implementation of Vector Provider."""
    
    def __init__(self, config: Optional[VectorConfig] = None):
        """Initialize Qdrant provider."""
        config = config or VectorConfig(
            provider_name="qdrant",
            api_key_env_var="QDRANT_API_KEY",
        )
        super().__init__(config)
        
        self.client = None
        self.qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        
        if self.api_key:
            self.client = QdrantClient(
                url=self.qdrant_url,
                api_key=self.api_key,
                timeout=self.config.timeout_seconds
            )
        else:
            # Local Qdrant instance without API key
            self.client = QdrantClient(
                url=self.qdrant_url,
                timeout=self.config.timeout_seconds
            )
    
    def health_check(self) -> bool:
        """Check if Qdrant is operational."""
        if not self.client:
            return False
        try:
            # Check if service is alive
            health = self.client.http.health()
            return health
        except Exception:
            return False
    
    def fallback_available(self) -> bool:
        """Qdrant doesn't have built-in fallbacks."""
        return False
    
    async def create_collection(self, collection_name: Optional[str] = None) -> bool:
        """Create a collection in Qdrant if it doesn't exist."""
        if not self.client:
            raise ProviderError("Qdrant client not initialized.")
        
        coll_name = collection_name or self.config.collection_name
        
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(collection.name == coll_name for collection in collections)
            
            if not exists:
                # Create collection
                self.client.create_collection(
                    collection_name=coll_name,
                    vectors_config=VectorParams(
                        size=self.config.embedding_dimension,
                        distance=Distance.COSINE if self.config.distance_metric == "cosine" else Distance.EUCLID,
                    )
                )
            return True
        except Exception as e:
            raise ProviderError(f"Failed to create Qdrant collection: {str(e)}")
    
    async def index_documents(
        self, 
        documents: List[Dict[str, Any]], 
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None
    ) -> bool:
        """Index documents with their embeddings in Qdrant."""
        if not self.client:
            raise ProviderError("Qdrant client not initialized.")
        
        if len(documents) != len(embeddings):
            raise ProviderError("Number of documents must match number of embeddings")
        
        coll_name = self.config.collection_name
        
        try:
            # Ensure collection exists
            await self.create_collection()
            
            # Prepare points for insertion
            points = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                doc_id = ids[i] if ids and i < len(ids) else f"doc_{i}"
                points.append(
                    PointStruct(
                        id=doc_id,
                        vector=embedding,
                        payload={
                            "content": doc.get("content", ""),
                            "metadata": doc.get("metadata", {})
                        }
                    )
                )
            
            # Insert points in batches of 100
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i+batch_size]
                self.client.upsert(
                    collection_name=coll_name,
                    points=batch
                )
            
            return True
        except Exception as e:
            raise ProviderError(f"Failed to index documents in Qdrant: {str(e)}")
    
    async def search(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors in Qdrant."""
        if not self.client:
            raise ProviderError("Qdrant client not initialized.")
        
        coll_name = self.config.collection_name
        
        try:
            # Build filter if metadata_filter is provided
            search_filter = None
            if metadata_filter:
                filter_conditions = []
                for key, value in metadata_filter.items():
                    if isinstance(value, list):
                        # Handle array containment
                        filter_conditions.append({
                            "key": f"metadata.{key}",
                            "match": {"any": value}
                        })
                    else:
                        # Handle exact match
                        filter_conditions.append({
                            "key": f"metadata.{key}",
                            "match": {"value": value}
                        })
                
                if filter_conditions:
                    search_filter = {"must": filter_conditions}
            
            # Perform search
            search_results = self.client.search(
                collection_name=coll_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=search_filter
            )
            
            # Convert to standard format
            vector_results = []
            for result in search_results:
                vector_results.append(VectorSearchResult(
                    id=result.id,
                    score=result.score,
                    document={"content": result.payload.get("content", "")},
                    metadata=result.payload.get("metadata", {})
                ))
                
            return vector_results
        except Exception as e:
            raise ProviderError(f"Failed to search vectors in Qdrant: {str(e)}")
