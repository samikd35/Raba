"""
Problem Generator LangGraph Implementation

Main graph implementation for the Problem Generator agent workflow.
Implements the 12-node "Cause → Effect + Context" workflow using LangGraph.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langsmith.run_helpers import traceable

from .graph_state import ProblemGraphState
from .nodes import (
    parameter_validator_node,
    query_expander_node,
    search_fanout_node,
    scraper_pool_node,
    passage_extractor_node,
    passage_embedder_node,
    cluster_merge_node,
    micro_story_generator_node,
    statement_refiner_node,
    quality_filter_node,
    relevance_ranker_node,
    curator_selector_node
)

logger = logging.getLogger(__name__)


class ProblemGeneratorGraph:
    """
    Problem Generator LangGraph Implementation
    
    Implements the 12-node workflow for generating tailored problem statements
    for African market contexts using the "Cause → Effect + Context" approach.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the Problem Generator graph.
        
        Args:
            config: Configuration dictionary for the graph
        """
        self.config = config or {}
        self.graph = None
        self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow."""
        logger.info("Building Problem Generator LangGraph workflow")
        
        # Initialize the state graph
        workflow = StateGraph(dict)  # Using dict as state type for flexibility
        
        # =============================================
        # ADD NODES TO GRAPH
        # =============================================
        
        # Node 0: Parameter Validator
        workflow.add_node("parameter_validator", parameter_validator_node)
        
        # Node 1: Query Expander
        workflow.add_node("query_expander", query_expander_node)
        
        # Node 2: Search Fan-out (Parallel searches)
        workflow.add_node("search_fanout", search_fanout_node)
        
        # Node 3: Scraper Pool
        workflow.add_node("scraper_pool", scraper_pool_node)
        
        # Node 4: Passage Extractor
        workflow.add_node("passage_extractor", passage_extractor_node)
        
        # Node 5: Passage Embedder
        workflow.add_node("passage_embedder", passage_embedder_node)
        
        # Node 6: Cluster Merge
        workflow.add_node("cluster_merge", cluster_merge_node)
        
        # Node 7: Micro Story Generator
        workflow.add_node("micro_story_generator", micro_story_generator_node)
        
        # Node 8: Statement Refiner
        workflow.add_node("statement_refiner", statement_refiner_node)
        
        # Node 9: Quality Filter
        workflow.add_node("quality_filter", quality_filter_node)
        
        # Node 10: Relevance Ranker
        workflow.add_node("relevance_ranker", relevance_ranker_node)
        
        # Node 11: Curator Selector (Final)
        workflow.add_node("curator_selector", curator_selector_node)
        
        # =============================================
        # DEFINE GRAPH EDGES (WORKFLOW FLOW)
        # =============================================
        
        # Set entry point
        workflow.set_entry_point("parameter_validator")
        
        # Linear workflow with conditional routing
        workflow.add_edge("parameter_validator", "query_expander")
        workflow.add_edge("query_expander", "search_fanout")
        workflow.add_edge("search_fanout", "scraper_pool")
        workflow.add_edge("scraper_pool", "passage_extractor")
        workflow.add_edge("passage_extractor", "passage_embedder")
        workflow.add_edge("passage_embedder", "cluster_merge")
        workflow.add_edge("cluster_merge", "micro_story_generator")
        workflow.add_edge("micro_story_generator", "statement_refiner")
        workflow.add_edge("statement_refiner", "quality_filter")
        workflow.add_edge("quality_filter", "relevance_ranker")
        workflow.add_edge("relevance_ranker", "curator_selector")
        
        # End workflow
        workflow.add_edge("curator_selector", END)
        
        # Add conditional routing for error handling
        workflow.add_conditional_edges(
            "parameter_validator",
            self._should_continue,
            {
                "continue": "query_expander",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "query_expander",
            self._should_continue,
            {
                "continue": "search_fanout",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "search_fanout",
            self._should_continue,
            {
                "continue": "scraper_pool",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "scraper_pool",
            self._should_continue,
            {
                "continue": "passage_extractor",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "passage_extractor",
            self._should_continue,
            {
                "continue": "passage_embedder",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "passage_embedder",
            self._should_continue,
            {
                "continue": "cluster_merge",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "cluster_merge",
            self._should_continue,
            {
                "continue": "micro_story_generator",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "micro_story_generator",
            self._should_continue,
            {
                "continue": "statement_refiner",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "statement_refiner",
            self._should_continue,
            {
                "continue": "quality_filter",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "quality_filter",
            self._should_continue,
            {
                "continue": "relevance_ranker",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "relevance_ranker",
            self._should_continue,
            {
                "continue": "curator_selector",
                "end": END
            }
        )
        
        # Compile the graph
        self.graph = workflow.compile()
        
        logger.info("Problem Generator LangGraph workflow built successfully")
    
    def _should_continue(self, state: Dict[str, Any]) -> str:
        """
        Determine if the workflow should continue or end due to error.
        
        Args:
            state: Current workflow state
            
        Returns:
            "continue" or "end"
        """
        # Check for errors
        if state.get("error") or state.get("status") == "failed":
            logger.error(f"Workflow stopping due to error: {state.get('error', 'Unknown error')}")
            return "end"
        
        return "continue"
    
    @traceable(name="problem_generator_workflow")
    async def generate_problems(
        self, 
        user_params: Dict[str, Any], 
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete problem generation workflow.
        
        Args:
            user_params: User input parameters
            config: Optional configuration override
            
        Returns:
            Final workflow state with generated problems
        """
        logger.info("Starting Problem Generator workflow execution")
        start_time = datetime.now()
        
        try:
            # Initialize workflow state
            initial_state = {
                "params": user_params,
                "config": config or self.config,
                "status": "pending",
                "current_node": None,
                "workflow_start_time": start_time.isoformat(),
                "processing_metrics": {},
                
                # Context for logging and AI monitoring - extract from user_params
                "job_id": user_params.get("job_id") or (config.get("job_id") if config else None),
                "user_id": user_params.get("user_id") or (config.get("user_id") if config else None),
                "tenant_id": user_params.get("tenant_id"),  # For AI usage monitoring
                "project_id": user_params.get("project_id"),  # For AI usage monitoring
                
                # Initialize all state fields
                "queries": [],
                "db_hits": [],
                "web_hits": [],
                "scraped_content": [],
                "extracted_passages": [],
                "embedded_passages": [],
                "clusters": [],
                "micro_stories": [],
                "refined_statements": [],
                "filtered_statements": [],
                "ranked_statements": [],
                "final": [],
                
                # Metadata fields
                "search_metadata": {},
                "scraping_stats": {},
                "extraction_stats": {},
                "embedding_stats": {},
                "clustering_stats": {},
                "story_generation_stats": {},
                "refinement_stats": {},
                "filter_stats": {},
                "ranking_stats": {},
                "curation_metadata": {}
            }
            
            logger.info(f"Executing workflow with parameters: {list(user_params.keys())}")
            
            # Execute the workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            # Add final timing
            end_time = datetime.now()
            total_time = int((end_time - start_time).total_seconds() * 1000)
            
            final_state["workflow_end_time"] = end_time.isoformat()
            final_state["total_processing_time_ms"] = total_time
            
            # Log completion
            final_problems = final_state.get("final", [])
            logger.info(f"Problem Generator workflow completed successfully")
            logger.info(f"Generated {len(final_problems)} final problem statements")
            logger.info(f"Total processing time: {total_time}ms")
            
            return final_state
            
        except Exception as e:
            error_msg = f"Problem Generator workflow failed: {str(e)}"
            logger.error(error_msg)
            
            # Return error state
            return {
                "status": "failed",
                "error": error_msg,
                "workflow_start_time": start_time.isoformat(),
                "workflow_end_time": datetime.now().isoformat(),
                "final": []
            }
    
    async def generate_problems_stream(
        self, 
        user_params: Dict[str, Any], 
        config: Dict[str, Any] = None
    ):
        """
        Execute the workflow with streaming updates.
        
        Args:
            user_params: User input parameters
            config: Optional configuration override
            
        Yields:
            State updates as the workflow progresses
        """
        logger.info("Starting Problem Generator workflow with streaming")
        
        try:
            # Initialize state
            initial_state = {
                "params": user_params,
                "config": config or self.config,
                "status": "pending",
                "current_node": None,
                "workflow_start_time": datetime.now().isoformat(),
                "processing_metrics": {},
                
                # Initialize all state fields
                "queries": [],
                "db_hits": [],
                "web_hits": [],
                "scraped_content": [],
                "extracted_passages": [],
                "embedded_passages": [],
                "clusters": [],
                "micro_stories": [],
                "refined_statements": [],
                "filtered_statements": [],
                "ranked_statements": [],
                "final": []
            }
            
            # Stream workflow execution
            async for state_update in self.graph.astream(initial_state):
                yield state_update
                
        except Exception as e:
            logger.error(f"Streaming workflow failed: {str(e)}")
            yield {
                "status": "failed",
                "error": str(e),
                "final": []
            }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """
        Get information about the workflow structure.
        
        Returns:
            Workflow metadata
        """
        return {
            "name": "Problem Generator",
            "version": "2.1",
            "approach": "Cause → Effect + Context",
            "total_nodes": 12,
            "nodes": [
                {"id": 0, "name": "parameter_validator", "description": "Validates and normalizes user parameters"},
                {"id": 1, "name": "query_expander", "description": "Generates search queries from parameters"},
                {"id": 2, "name": "search_fanout", "description": "Executes parallel searches (DB, news, deep)"},
                {"id": 3, "name": "scraper_pool", "description": "Scrapes content from web results"},
                {"id": 4, "name": "passage_extractor", "description": "Extracts relevant problem passages"},
                {"id": 5, "name": "passage_embedder", "description": "Generates embeddings for passages"},
                {"id": 6, "name": "cluster_merge", "description": "Clusters passages by theme"},
                {"id": 7, "name": "micro_story_generator", "description": "Creates micro-stories from clusters"},
                {"id": 8, "name": "statement_refiner", "description": "Refines stories into formal statements"},
                {"id": 9, "name": "quality_filter", "description": "Filters statements by quality criteria"},
                {"id": 10, "name": "relevance_ranker", "description": "Ranks by relevance to user parameters"},
                {"id": 11, "name": "curator_selector", "description": "Selects final 3-5 problem statements"}
            ],
            "parallel_execution": ["search_fanout"],
            "llm_nodes": ["query_expander", "passage_extractor", "micro_story_generator", "statement_refiner", "curator_selector"],
            "embedding_nodes": ["passage_embedder"],
            "clustering_nodes": ["cluster_merge"],
            "expected_output": "3-5 tailored problem statements following Cause → Effect + Context format"
        }


# Factory function for creating the graph
def create_problem_generator_graph(config: Dict[str, Any] = None) -> ProblemGeneratorGraph:
    """
    Factory function to create a Problem Generator graph instance.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured ProblemGeneratorGraph instance
    """
    return ProblemGeneratorGraph(config)
