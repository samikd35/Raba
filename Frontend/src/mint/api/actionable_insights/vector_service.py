#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vector Storage Service for Actionable Insights.

This module provides vector storage and semantic search capabilities
for actionable insights and problem validation reports.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import numpy as np
from pydantic import BaseModel, Field

from ...api.system.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class VectorSearchResult(BaseModel):
    """Result from vector similarity search."""
    id: str
    similarity: float
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InsightVectorData(BaseModel):
    """Data structure for storing actionable insight vectors."""
    id: str
    report_id: str
    user_id: str
    title: str
    description: str
    category: str
    priority: str
    impact_level: str
    content_vector: List[float]
    confidence_score: float = 0.0
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReportVectorData(BaseModel):
    """Data structure for storing problem validation report vectors."""
    id: str
    session_id: str
    user_id: str
    title: str
    problem_statement: str
    report_type: str = "market_validation"
    industry: Optional[str] = None
    geography: Optional[str] = None
    full_content_vector: List[float]
    problem_statement_vector: List[float]
    market_analysis_vector: Optional[List[float]] = None
    recommendations_vector: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionableInsightsVectorService:
    """Service for managing vector storage of actionable insights and reports."""
    
    def __init__(self, use_service_role: bool = True):
        self.client = get_supabase_client(use_service_role=use_service_role)
        self.embedding_dimension = 1536  # OpenAI text-embedding-3-small
    
    async def store_insight_vector(
        self, 
        insight_data: InsightVectorData
    ) -> bool:
        """Store an actionable insight with its vector embedding."""
        try:
            # Validate embedding dimension
            if len(insight_data.content_vector) != self.embedding_dimension:
                logger.error(f"Invalid embedding dimension: {len(insight_data.content_vector)}, expected {self.embedding_dimension}")
                return False
            
            # Prepare data for insertion
            data = {
                "id": insight_data.id,
                "report_id": insight_data.report_id,
                "user_id": insight_data.user_id,
                "insight_type": insight_data.category,  # Map category to insight_type
                "title": insight_data.title,
                "description": insight_data.description,
                "priority": insight_data.priority,
                "impact_level": insight_data.impact_level,
                "content_vector": insight_data.content_vector,
                "confidence_score": insight_data.confidence_score,
                "tags": insight_data.tags,
                "source_sections": insight_data.metadata,
                "status": "active",  # Use 'active' instead of 'draft'
                "generated_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Insert into database
            result = self.client.client.table("actionable_insights").insert(data).execute()
            
            if result.data:
                logger.info(f"Successfully stored insight vector for {insight_data.id}")
                return True
            else:
                logger.error(f"Failed to store insight vector for {insight_data.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing insight vector: {str(e)}")
            return False
    
    async def store_report_vector(
        self, 
        report_data: ReportVectorData
    ) -> bool:
        """Store a problem validation report with its vector embeddings."""
        try:
            # Validate embedding dimensions
            if len(report_data.full_content_vector) != self.embedding_dimension:
                logger.error(f"Invalid full_content_vector dimension: {len(report_data.full_content_vector)}")
                return False
            
            if len(report_data.problem_statement_vector) != self.embedding_dimension:
                logger.error(f"Invalid problem_statement_vector dimension: {len(report_data.problem_statement_vector)}")
                return False
            
            # Prepare data for insertion
            data = {
                "id": report_data.id,
                "session_id": report_data.session_id,
                "user_id": report_data.user_id,
                "title": report_data.title,
                "problem_statement": report_data.problem_statement,
                "report_type": report_data.report_type,
                "industry": report_data.industry,
                "geography": report_data.geography,
                "full_content_vector": report_data.full_content_vector,
                "problem_statement_vector": report_data.problem_statement_vector,
                "market_analysis_vector": report_data.market_analysis_vector,
                "recommendations_vector": report_data.recommendations_vector,
                "status": "completed",
                "completion_percentage": 100,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Insert into database
            result = self.client.client.table("problem_validation_reports").insert(data).execute()
            
            if result.data:
                logger.info(f"Successfully stored report vector for {report_data.id}")
                return True
            else:
                logger.error(f"Failed to store report vector for {report_data.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing report vector: {str(e)}")
            return False
    
    async def search_insights_by_similarity(
        self,
        query_vector: List[float],
        user_id: str,
        match_threshold: float = 0.7,
        match_count: int = 10,
        category_filter: Optional[str] = None,
        priority_filter: Optional[str] = None
    ) -> List[VectorSearchResult]:
        """Search actionable insights by semantic similarity."""
        try:
            # Validate query vector
            if len(query_vector) != self.embedding_dimension:
                logger.error(f"Invalid query vector dimension: {len(query_vector)}")
                return []
            
            # Call the database function for vector search
            result = self.client.client.rpc(
                "search_actionable_insights",
                {
                    "query_embedding": query_vector,
                    "user_id_param": user_id,
                    "match_threshold": match_threshold,
                    "match_count": match_count,
                    "category_filter": category_filter,
                    "priority_filter": priority_filter
                }
            ).execute()
            
            if result.data:
                search_results = []
                for row in result.data:
                    search_results.append(VectorSearchResult(
                        id=row["id"],
                        similarity=row["similarity"],
                        content=f"{row['title']}: {row['description']}",
                        metadata={
                            "report_id": row["report_id"],
                            "insight_type": row["insight_type"],
                            "priority": row["priority"],
                            "impact_level": row["impact_level"],
                            "confidence_score": row["confidence_score"]
                        }
                    ))
                
                logger.info(f"Found {len(search_results)} similar insights for user {user_id}")
                return search_results
            else:
                logger.info(f"No similar insights found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching insights by similarity: {str(e)}")
            return []
    
    async def search_reports_by_similarity(
        self,
        query_vector: List[float],
        user_id: str,
        match_threshold: float = 0.7,
        match_count: int = 10,
        report_type_filter: Optional[str] = None
    ) -> List[VectorSearchResult]:
        """Search problem validation reports by semantic similarity."""
        try:
            # Validate query vector
            if len(query_vector) != self.embedding_dimension:
                logger.error(f"Invalid query vector dimension: {len(query_vector)}")
                return []
            
            # Call the database function for vector search
            result = self.client.client.rpc(
                "search_problem_validation_reports",
                {
                    "query_embedding": query_vector,
                    "user_id_param": user_id,
                    "match_threshold": match_threshold,
                    "match_count": match_count,
                    "report_type_filter": report_type_filter
                }
            ).execute()
            
            if result.data:
                search_results = []
                for row in result.data:
                    search_results.append(VectorSearchResult(
                        id=row["id"],
                        similarity=row["similarity"],
                        content=f"{row['title']}: {row['problem_statement']}",
                        metadata={
                            "session_id": row["session_id"],
                            "report_type": row["report_type"],
                            "industry": row["industry"]
                        }
                    ))
                
                logger.info(f"Found {len(search_results)} similar reports for user {user_id}")
                return search_results
            else:
                logger.info(f"No similar reports found for user {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching reports by similarity: {str(e)}")
            return []
    
    async def get_insight_by_id(self, insight_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific actionable insight by ID."""
        try:
            result = self.client.client.table("actionable_insights").select("*").eq("id", insight_id).eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                logger.warning(f"Insight {insight_id} not found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting insight by ID: {str(e)}")
            return None
    
    async def get_report_by_id(self, report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific problem validation report by ID."""
        try:
            result = self.client.client.table("problem_validation_reports").select("*").eq("id", report_id).eq("user_id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                logger.warning(f"Report {report_id} not found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting report by ID: {str(e)}")
            return None
    
    async def update_insight_status(
        self, 
        insight_id: str, 
        user_id: str, 
        status: str,
        reviewed_by: Optional[str] = None
    ) -> bool:
        """Update the status of an actionable insight."""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if reviewed_by:
                update_data["reviewed_by"] = reviewed_by
                update_data["reviewed_at"] = datetime.utcnow().isoformat()
            
            result = self.client.client.table("actionable_insights").update(update_data).eq("id", insight_id).eq("user_id", user_id).execute()
            
            if result.data:
                logger.info(f"Successfully updated insight {insight_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to update insight {insight_id} status")
                return False
                
        except Exception as e:
            logger.error(f"Error updating insight status: {str(e)}")
            return False
    
    async def get_user_insights_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of all insights for a user."""
        try:
            # Get insights count by category
            category_result = self.client.client.table("actionable_insights").select("category").eq("user_id", user_id).execute()
            
            # Get insights count by priority
            priority_result = self.client.client.table("actionable_insights").select("priority").eq("user_id", user_id).execute()
            
            # Get insights count by status
            status_result = self.client.client.table("actionable_insights").select("status").eq("user_id", user_id).execute()
            
            # Count by category
            category_counts = {}
            for row in category_result.data:
                category = row["category"]
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Count by priority
            priority_counts = {}
            for row in priority_result.data:
                priority = row["priority"]
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Count by status
            status_counts = {}
            for row in status_result.data:
                status = row["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_insights": len(category_result.data),
                "by_category": category_counts,
                "by_priority": priority_counts,
                "by_status": status_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting user insights summary: {str(e)}")
            return {
                "total_insights": 0,
                "by_category": {},
                "by_priority": {},
                "by_status": {}
            }


# Global instance
_vector_service = None

def get_vector_service() -> ActionableInsightsVectorService:
    """Get the global vector service instance."""
    global _vector_service
    if _vector_service is None:
        _vector_service = ActionableInsightsVectorService()
    return _vector_service
