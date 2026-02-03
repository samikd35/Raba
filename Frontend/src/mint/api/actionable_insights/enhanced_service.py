#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Actionable Insights Service with Vector Storage.

This module provides enhanced functionality for generating, storing, and retrieving
actionable insights with vector embeddings for semantic search.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from pydantic import BaseModel, Field

from .vector_service import ActionableInsightsVectorService, InsightVectorData, ReportVectorData
from .service import ActionableInsightsService, InsightGenerationContext, ActionableInsight, InsightGenerationResult

logger = logging.getLogger(__name__)


class EnhancedInsightGenerationRequest(BaseModel):
    """Enhanced request for generating actionable insights with vector storage."""
    report_id: str
    user_id: str
    force_regenerate: bool = False
    include_vector_storage: bool = True
    user_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EnhancedInsightResponse(BaseModel):
    """Enhanced response for actionable insights with vector data."""
    id: str
    report_id: str
    title: str
    description: str
    insight_type: str
    priority: str
    confidence_score: float
    impact_level: Optional[str] = None
    implementation_steps: List[Dict[str, Any]] = Field(default_factory=list)
    success_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_effort: Optional[str] = None
    estimated_timeline: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source_sections: Dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    similarity_score: Optional[float] = None  # For search results
    created_at: datetime
    updated_at: datetime


class EnhancedInsightsListResponse(BaseModel):
    """Enhanced response for lists of actionable insights."""
    insights: List[EnhancedInsightResponse]
    total_count: int
    report_id: str
    generation_time: Optional[float] = None
    vector_search_enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EnhancedActionableInsightsService:
    """Enhanced service for managing actionable insights with vector storage."""
    
    def __init__(self):
        self.base_service = ActionableInsightsService()
        self.vector_service = ActionableInsightsVectorService()
        self.embedding_dimension = 1536
    
    async def generate_insights_with_vectors(
        self, 
        request: EnhancedInsightGenerationRequest
    ) -> EnhancedInsightsListResponse:
        """Generate actionable insights and store them with vector embeddings."""
        try:
            logger.info(f"Generating enhanced insights for report {request.report_id}")
            
            # Generate insights using the base service
            context = InsightGenerationContext(
                user_id=request.user_id,
                report_id=request.report_id,
                tenant_id=getattr(request, 'tenant_id', None),  # For AI usage monitoring
                project_id=getattr(request, 'project_id', None)  # For AI usage monitoring
            )
            
            result = await self.base_service.generate_insights(context)
            
            if not result.success:
                logger.error(f"Failed to generate insights: {result.error_message}")
                return EnhancedInsightsListResponse(
                    insights=[],
                    total_count=0,
                    report_id=request.report_id,
                    vector_search_enabled=request.include_vector_storage,
                    metadata={"error": result.error_message}
                )
            
            enhanced_insights = []
            
            for insight in result.insights:
                # Create enhanced insight response
                enhanced_insight = EnhancedInsightResponse(
                    id=str(insight.id),
                    report_id=request.report_id,
                    title=insight.title,
                    description=insight.description,
                    insight_type=insight.insight_type,
                    priority=insight.priority,
                    confidence_score=insight.confidence_score,
                    impact_level=insight.impact_level,
                    implementation_steps=insight.implementation_steps,
                    success_metrics=insight.success_metrics,
                    estimated_effort=insight.estimated_effort,
                    estimated_timeline=insight.estimated_timeline,
                    tags=insight.tags,
                    source_sections=insight.source_sections,
                    status=insight.status,
                    created_at=insight.generated_at,
                    updated_at=insight.generated_at
                )
                
                # Store with vector embedding if requested
                if request.include_vector_storage:
                    try:
                        # Generate embedding for the insight content
                        embedding = await self._generate_embedding(
                            f"{insight.title}: {insight.description}"
                        )
                        
                        if embedding:
                            # Create vector data
                            vector_data = InsightVectorData(
                                id=str(insight.id),
                                report_id=request.report_id,
                                user_id=request.user_id,
                                title=insight.title,
                                description=insight.description,
                                category=insight.insight_type,
                                priority=insight.priority,
                                impact_level=insight.impact_level or "medium",
                                content_vector=embedding,
                                confidence_score=insight.confidence_score,
                                tags=insight.tags,
                                metadata=insight.source_sections
                            )
                            
                            # Store in vector database
                            success = await self.vector_service.store_insight_vector(vector_data)
                            if success:
                                logger.info(f"Stored vector for insight {insight.id}")
                            else:
                                logger.warning(f"Failed to store vector for insight {insight.id}")
                        
                    except Exception as e:
                        logger.error(f"Error storing vector for insight {insight.id}: {str(e)}")
                
                enhanced_insights.append(enhanced_insight)
            
            return EnhancedInsightsListResponse(
                insights=enhanced_insights,
                total_count=len(enhanced_insights),
                report_id=request.report_id,
                generation_time=result.generation_time,
                vector_search_enabled=request.include_vector_storage,
                metadata={
                    "generated_at": datetime.utcnow().isoformat(),
                    "vector_storage_success": request.include_vector_storage
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating enhanced insights: {str(e)}")
            return EnhancedInsightsListResponse(
                insights=[],
                total_count=0,
                report_id=request.report_id,
                vector_search_enabled=request.include_vector_storage,
                metadata={"error": str(e)}
            )
    
    async def search_insights_by_similarity(
        self,
        query: str,
        user_id: str,
        report_id: Optional[str] = None,
        match_threshold: float = 0.7,
        match_count: int = 10,
        category_filter: Optional[str] = None,
        priority_filter: Optional[str] = None
    ) -> EnhancedInsightsListResponse:
        """Search actionable insights by semantic similarity."""
        try:
            logger.info(f"Searching insights by similarity for user {user_id}")
            
            # Generate embedding for the query
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return EnhancedInsightsListResponse(
                    insights=[],
                    total_count=0,
                    report_id=report_id or "search",
                    vector_search_enabled=True,
                    metadata={"error": "Failed to generate query embedding"}
                )
            
            # Search using vector service
            search_results = await self.vector_service.search_insights_by_similarity(
                query_vector=query_embedding,
                user_id=user_id,
                match_threshold=match_threshold,
                match_count=match_count,
                category_filter=category_filter,
                priority_filter=priority_filter
            )
            
            # Convert search results to enhanced insights
            enhanced_insights = []
            for result in search_results:
                # Get full insight data
                insight_data = await self.vector_service.get_insight_by_id(result.id, user_id)
                if insight_data:
                    enhanced_insight = EnhancedInsightResponse(
                        id=result.id,
                        report_id=insight_data.get("report_id", ""),
                        title=insight_data.get("title", ""),
                        description=insight_data.get("description", ""),
                        insight_type=insight_data.get("insight_type", ""),
                        priority=insight_data.get("priority", ""),
                        confidence_score=insight_data.get("confidence_score", 0.0),
                        impact_level=insight_data.get("impact_level"),
                        implementation_steps=insight_data.get("implementation_steps", []),
                        success_metrics=insight_data.get("success_metrics", []),
                        estimated_effort=insight_data.get("estimated_effort"),
                        estimated_timeline=insight_data.get("estimated_timeline"),
                        tags=insight_data.get("tags", []),
                        source_sections=insight_data.get("source_sections", {}),
                        status=insight_data.get("status", "draft"),
                        similarity_score=result.similarity,
                        created_at=datetime.fromisoformat(insight_data.get("created_at", datetime.utcnow().isoformat())),
                        updated_at=datetime.fromisoformat(insight_data.get("updated_at", datetime.utcnow().isoformat()))
                    )
                    enhanced_insights.append(enhanced_insight)
            
            return EnhancedInsightsListResponse(
                insights=enhanced_insights,
                total_count=len(enhanced_insights),
                report_id=report_id or "search",
                vector_search_enabled=True,
                metadata={
                    "search_query": query,
                    "match_threshold": match_threshold,
                    "search_timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error searching insights by similarity: {str(e)}")
            return EnhancedInsightsListResponse(
                insights=[],
                total_count=0,
                report_id=report_id or "search",
                vector_search_enabled=True,
                metadata={"error": str(e)}
            )
    
    async def get_insights_for_report(
        self, 
        report_id: str, 
        user_id: str,
        include_vectors: bool = False
    ) -> EnhancedInsightsListResponse:
        """Get all insights for a specific report."""
        try:
            logger.info(f"Getting insights for report {report_id}")
            
            # Get insights from base service
            result = await self.base_service.get_insights_for_report(report_id, user_id)
            
            if not result.success:
                logger.error(f"Failed to get insights: {result.error_message}")
                return EnhancedInsightsListResponse(
                    insights=[],
                    total_count=0,
                    report_id=report_id,
                    vector_search_enabled=include_vectors,
                    metadata={"error": result.error_message}
                )
            
            enhanced_insights = []
            
            for insight in result.insights:
                enhanced_insight = EnhancedInsightResponse(
                    id=str(insight.id),
                    report_id=report_id,
                    title=insight.title,
                    description=insight.description,
                    insight_type=insight.insight_type,
                    priority=insight.priority,
                    confidence_score=insight.confidence_score,
                    impact_level=insight.impact_level,
                    implementation_steps=insight.implementation_steps,
                    success_metrics=insight.success_metrics,
                    estimated_effort=insight.estimated_effort,
                    estimated_timeline=insight.estimated_timeline,
                    tags=insight.tags,
                    source_sections=insight.source_sections,
                    status=insight.status,
                    created_at=insight.generated_at,
                    updated_at=insight.generated_at
                )
                enhanced_insights.append(enhanced_insight)
            
            return EnhancedInsightsListResponse(
                insights=enhanced_insights,
                total_count=len(enhanced_insights),
                report_id=report_id,
                vector_search_enabled=include_vectors,
                metadata={
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "total_found": len(enhanced_insights)
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting insights for report: {str(e)}")
            return EnhancedInsightsListResponse(
                insights=[],
                total_count=0,
                report_id=report_id,
                vector_search_enabled=include_vectors,
                metadata={"error": str(e)}
            )
    
    async def update_insight_status(
        self, 
        insight_id: str, 
        user_id: str, 
        status: str,
        reviewed_by: Optional[str] = None
    ) -> bool:
        """Update the status of an actionable insight."""
        try:
            # Update in vector service
            success = await self.vector_service.update_insight_status(
                insight_id, user_id, status, reviewed_by
            )
            
            if success:
                logger.info(f"Updated insight {insight_id} status to {status}")
            else:
                logger.error(f"Failed to update insight {insight_id} status")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating insight status: {str(e)}")
            return False
    
    async def get_user_insights_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of all insights for a user."""
        try:
            return await self.vector_service.get_user_insights_summary(user_id)
        except Exception as e:
            logger.error(f"Error getting user insights summary: {str(e)}")
            return {
                "total_insights": 0,
                "by_category": {},
                "by_priority": {},
                "by_status": {}
            }
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI API."""
        try:
            # This is a placeholder - in production, you would call OpenAI's embedding API
            # For now, return a mock embedding
            import random
            return [random.uniform(-1, 1) for _ in range(self.embedding_dimension)]
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None


# Global instance
_enhanced_service = None

def get_enhanced_actionable_insights_service() -> EnhancedActionableInsightsService:
    """Get the global enhanced actionable insights service instance."""
    global _enhanced_service
    if _enhanced_service is None:
        _enhanced_service = EnhancedActionableInsightsService()
    return _enhanced_service
