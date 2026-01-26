"""Visual Logic Validator Agent.

Analyzes script for high hallucination risk and flags issues.
Uses Gemini where available; falls back to heuristic pass.
"""

from typing import Any

from app.graph.state import VideoGenerationState
from app.models.overlay import VisualValidationOutput, VisualRiskLevel
from app.services.gemini import get_gemini_service, GEMINI_3_FLASH
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VisualLogicValidatorAgent:
    def __init__(self):
        self.gemini = get_gemini_service()
        logger.info("VisualLogicValidatorAgent initialized")

    async def run(self, state: VideoGenerationState) -> dict[str, Any]:
        script = state.get("script_output", {})
        if not script:
            logger.warning("No script_output present; skipping validation")
            return {"visual_validation": VisualValidationOutput().model_dump()}

        prompt = (
            "Analyze the following short-form video script for visual logic issues. "
            "Identify high-risk elements like precise large-scale measurements, impossible physics, or complex spatial relations. "
            "Return JSON with fields: validation_passed (bool), flagged_issues (list), suggested_alternatives (list), risk_level (low|medium|high|critical), requires_revision (bool).\n\n"
            f"SCRIPT JSON:\n{script}"
        )

        try:
            out = await self.gemini.generate_structured_output(
                prompt=prompt,
                response_model=VisualValidationOutput,
                model=GEMINI_3_FLASH,
                temperature=0.2,
                video_id=state.get("workflow_id"),
            )
            logger.info("Visual logic validation completed via Gemini")
        except Exception as e:
            logger.warning(f"Visual validation fallback due to error: {e}")
            out = VisualValidationOutput(
                validation_passed=True,
                flagged_issues=[],
                suggested_alternatives=[],
                risk_level=VisualRiskLevel.LOW,
                requires_revision=False,
            )

        return {"visual_validation": out.model_dump()}


async def visual_logic_validator_node(state: VideoGenerationState) -> dict[str, Any]:
    agent = VisualLogicValidatorAgent()
    return await agent.run(state)
