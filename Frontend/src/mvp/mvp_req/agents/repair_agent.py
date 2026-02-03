"""
Repair Agent for AMRG

Attempts to fix PRD JSON validation errors.
Bounded to N repair attempts before failing.
"""

import logging
import json
from typing import Dict, Any, List, Tuple

from .base_agent import BaseAMRGAgent
from ..models.enums import TemplateCode, ValidationStatus
from ..services.schema_validator import SchemaValidatorService

logger = logging.getLogger(__name__)

# Maximum repair attempts
MAX_REPAIR_ATTEMPTS = 2


class RepairAgent(BaseAMRGAgent):
    """
    Agent for repairing PRD JSON validation errors.
    
    Takes validation errors and attempts to fix the PRD.
    Limited to MAX_REPAIR_ATTEMPTS to prevent infinite loops.
    """
    
    def __init__(self):
        """Initialize repair agent with schema validator."""
        super().__init__()
        self.schema_validator = SchemaValidatorService()
    
    def get_agent_name(self) -> str:
        return "repair_agent"
    
    async def repair_prd(
        self,
        prd_json: Dict[str, Any],
        validation_errors: List[Dict[str, Any]],
        template_code: str,
        tenant_id: str,
        user_id: str,
        project_id: str,
        attempt: int = 1
    ) -> Tuple[Dict[str, Any], ValidationStatus, List[Dict[str, Any]]]:
        """
        Attempt to repair PRD JSON.
        
        Args:
            prd_json: Current PRD JSON with errors
            validation_errors: List of validation errors
            template_code: Template code for re-validation
            tenant_id: Tenant ID
            user_id: User ID
            project_id: Project ID
            attempt: Current attempt number
            
        Returns:
            Tuple of (repaired_prd, status, remaining_errors)
        """
        logger.info(f"🔧 Repair attempt {attempt}/{MAX_REPAIR_ATTEMPTS} for PRD")
        
        if attempt > MAX_REPAIR_ATTEMPTS:
            logger.warning(f"Max repair attempts reached")
            return prd_json, ValidationStatus.REPAIR_FAILED, validation_errors
        
        try:
            # Create monitoring context
            monitoring_context = self.create_monitoring_context(
                tenant_id=tenant_id,
                user_id=user_id,
                project_id=project_id,
                step_name=f"repair_prd_attempt_{attempt}"
            )
            
            # Build repair prompt
            prompt = self._build_repair_prompt(prd_json, validation_errors)
            
            # Call LLM for repair (16000 tokens to avoid truncation)
            repaired_prd = await self.call_llm_with_retry(
                prompt=prompt,
                monitoring_context=monitoring_context,
                temperature=0.1,
                max_tokens=16000,
                json_mode=True
            )
            
            # Re-validate
            tc = TemplateCode(template_code)
            status, new_errors, warnings = self.schema_validator.validate_prd(
                repaired_prd, tc
            )
            
            if status == ValidationStatus.VALID:
                logger.info(f"✅ Repair successful on attempt {attempt}")
                return repaired_prd, ValidationStatus.REPAIRED, []
            
            # Still has errors - try again if attempts remain
            if attempt < MAX_REPAIR_ATTEMPTS:
                logger.warning(f"Repair attempt {attempt} still has {len(new_errors)} errors, retrying")
                return await self.repair_prd(
                    repaired_prd, new_errors, template_code,
                    tenant_id, user_id, project_id, attempt + 1
                )
            
            logger.warning(f"Repair failed after {attempt} attempts")
            return repaired_prd, ValidationStatus.REPAIR_FAILED, new_errors
            
        except Exception as e:
            logger.error(f"❌ Repair failed: {e}")
            return prd_json, ValidationStatus.REPAIR_FAILED, validation_errors
    
    def _build_repair_prompt(
        self,
        prd_json: Dict[str, Any],
        errors: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for PRD repair."""
        
        errors_text = "\n".join([
            f"- Field: {e.get('field')}, Error: {e.get('message')}"
            for e in errors
        ])
        
        suggestions = self.schema_validator.get_repair_suggestions(errors)
        suggestions_text = "\n".join([
            f"- {s.get('field')}: {s.get('suggestion')}"
            for s in suggestions
        ])
        
        return f"""You are a PRD repair specialist. The following PRD JSON has validation errors that need to be fixed.

## Current PRD JSON
```json
{json.dumps(prd_json, indent=2)}
```

## Validation Errors
{errors_text}

## Repair Suggestions
{suggestions_text}

## Your Task

Fix ALL the validation errors while preserving the intent and content of the PRD.

**Rules:**
1. Keep all existing valid content
2. Add missing required fields with appropriate content
3. Fix structural issues (arrays, objects, required properties)
4. Ensure all features have required fields (feature_name, description, job_supported, job_type)
5. Ensure success_signals has at least 2 quantitative and 1 qualitative metric
6. Ensure at least 3 must-have features

Return ONLY the fixed PRD JSON. No explanations.
"""
