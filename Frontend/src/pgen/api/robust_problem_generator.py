"""
Robust Problem Generator with Enhanced Error Handling and Timeout Management

This module provides a more stable version of the problem generation system
with comprehensive error handling, timeout management, and fallback mechanisms.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Credit system removed
# from src.mint.api.credit.credit_service import CreditService
# from src.mint.api.credit.credit_database_operations import CreditDatabaseOperations

logger = logging.getLogger(__name__)

@dataclass
class GenerationConfig:
    """Configuration for robust problem generation"""
    max_retries: int = 3
    timeout_per_node: int = 300  # 5 minutes per node
    total_timeout: int = 1800    # 30 minutes total
    batch_size: int = 3
    fallback_enabled: bool = True
    credit_check_enabled: bool = True

class RobustProblemGenerator:
    """
    Enhanced problem generator with comprehensive error handling and stability features
    """
    
    def __init__(self, config: GenerationConfig = None):
        self.config = config or GenerationConfig()
        # Credit system removed
        # self.credit_service = CreditService()
        # self.credit_db = CreditDatabaseOperations()
        
    async def generate_problems_robust(
        self,
        user_id: str,
        parameters: Dict[str, Any],
        job_id: str
    ) -> Dict[str, Any]:
        """
        Generate problems with comprehensive error handling and fallback mechanisms
        """
        start_time = time.time()
        logger.info(f"Starting robust problem generation for job {job_id}")
        
        try:
            # Step 1: Validate user and credits
            await self._validate_user_and_credits(user_id, job_id)
            
            # Step 2: Execute workflow with timeout and retry logic
            result = await self._execute_workflow_with_retry(
                user_id, parameters, job_id, start_time
            )
            
            # Step 3: Process and store results
            await self._process_and_store_results(result, user_id, job_id)
            
            # Step 4: Update credits
            await self._update_credits_after_generation(user_id)
            
            return {
                "status": "completed",
                "job_id": job_id,
                "user_id": user_id,
                "problems_generated": len(result.get("final", [])),
                "processing_time": time.time() - start_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Robust problem generation failed for job {job_id}: {str(e)}")
            
            # Refund credits on failure
            await self._refund_credits_on_failure(user_id)
            
            return {
                "status": "failed",
                "job_id": job_id,
                "user_id": user_id,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _validate_user_and_credits(self, user_id: str, job_id: str):
        """Validate user and check credit availability"""
        # Credit system removed - skip all credit checks
        logger.info(f"Credit validation bypassed for user {user_id} (credit system removed)")
    
    async def _execute_workflow_with_retry(
        self,
        user_id: str,
        parameters: Dict[str, Any],
        job_id: str,
        start_time: float
    ) -> Dict[str, Any]:
        """Execute workflow with retry logic and timeout management"""
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Workflow attempt {attempt + 1}/{self.config.max_retries} for job {job_id}")
                
                # Check total timeout
                if time.time() - start_time > self.config.total_timeout:
                    raise TimeoutError(f"Total timeout exceeded: {self.config.total_timeout}s")
                
                # Execute workflow with timeout
                result = await asyncio.wait_for(
                    self._execute_single_workflow_attempt(parameters, job_id),
                    timeout=self.config.timeout_per_node * 12  # 12 nodes max
                )
                
                if result.get("status") != "failed":
                    logger.info(f"Workflow completed successfully on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"Workflow failed on attempt {attempt + 1}: {result.get('error')}")
                    
            except asyncio.TimeoutError:
                logger.error(f"Workflow timeout on attempt {attempt + 1}")
                if attempt == self.config.max_retries - 1:
                    raise TimeoutError("All workflow attempts timed out")
                    
            except Exception as e:
                logger.error(f"Workflow error on attempt {attempt + 1}: {str(e)}")
                if attempt == self.config.max_retries - 1:
                    raise
                    
            # Wait before retry
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception("All workflow attempts failed")
    
    async def _execute_single_workflow_attempt(
        self,
        parameters: Dict[str, Any],
        job_id: str
    ) -> Dict[str, Any]:
        """Execute a single workflow attempt with enhanced error handling"""
        
        try:
            # Import the workflow graph
            from ..agents.problem_generator_graph import create_problem_generator_graph
            
            # Create graph
            graph = create_problem_generator_graph()
            
            # Prepare parameters
            workflow_params = {
                **parameters,
                "job_id": job_id,
                "user_id": parameters.get("user_id"),
                "timeout_per_node": self.config.timeout_per_node,
                "batch_size": self.config.batch_size
            }
            
            # Execute workflow
            result = await graph.generate_problems(workflow_params)
            
            return result
            
        except Exception as e:
            logger.error(f"Single workflow attempt failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "final": []
            }
    
    async def _process_and_store_results(
        self,
        result: Dict[str, Any],
        user_id: str,
        job_id: str
    ):
        """Process and store the generated problems"""
        
        try:
            problems = result.get("final", [])
            
            if not problems:
                logger.warning(f"No problems generated for job {job_id}")
                return
            
            # Store problems in database
            from ..services.problem_database_service import ProblemDatabaseService
            db_service = ProblemDatabaseService()
            
            for problem in problems:
                await db_service.create_problem_statement(
                    user_id=user_id,
                    problem_data=problem
                )
            
            logger.info(f"Stored {len(problems)} problems for job {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to store results for job {job_id}: {str(e)}")
            # Don't raise - results are still valid even if storage fails
    
    async def _update_credits_after_generation(self, user_id: str):
        """Credit system removed - no credit deduction needed"""
        logger.info(f"Credit deduction bypassed for user {user_id} (credit system removed)")
    
    async def _refund_credits_on_failure(self, user_id: str):
        """Credit system removed - no refund needed"""
        logger.info(f"Credit refund bypassed for user {user_id} (credit system removed)")

# Global instance for use in endpoints
robust_generator = RobustProblemGenerator()

async def generate_problems_with_fallback(
    user_id: str,
    parameters: Dict[str, Any],
    job_id: str
) -> Dict[str, Any]:
    """
    Generate problems using the robust generator with fallback mechanisms
    """
    return await robust_generator.generate_problems_robust(
        user_id=user_id,
        parameters=parameters,
        job_id=job_id
    )
