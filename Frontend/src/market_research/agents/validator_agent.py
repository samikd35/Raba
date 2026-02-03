"""
Validator Agent for assumption validation status assessment.

Provides logic for determining overall validation status based on individual
analysis results and confidence scoring.
"""

import logging
from typing import Dict, Any, List, Literal, Set
from ..models.analysis_models import AnalysisOutput

logger = logging.getLogger(__name__)


class ValidatorAgent:
    """Agent responsible for validating assumptions based on analysis results."""
    
    def __init__(self):
        """Initialize the validator agent."""
        self.validation_thresholds = {
            # Confidence-based thresholds for validation status
            "validated_min_confidence": 0.5,      # VALIDATED: 0.5 - 1.0
            "partial_validated_min_confidence": 0.3,  # PARTIALLY VALIDATED: 0.3 - 0.5
            # INVALIDATED: < 0.3
            
            # Legacy thresholds for support score calculations
            "high_confidence_threshold": 0.6,
            "medium_confidence_threshold": 0.3,
            "validation_ratio_threshold": 0.4,
            "partial_validation_ratio_threshold": 0.2
        }
    
    async def validate_assumption(
        self,
        assumption: Dict[str, Any],
        analyses: Dict[str, AnalysisOutput],
        persona: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate an assumption based on all analysis results.
        
        Args:
            assumption: The assumption being validated
            analyses: Dictionary of analysis results by type
            persona: Target persona for the assumption
            
        Returns:
            Validation result with status, confidence, and findings
        """
        try:
            # Calculate overall confidence first
            overall_confidence = self._calculate_overall_confidence(analyses)
            
            # Determine validation status based on confidence (NEW LOGIC)
            validation_status = self._determine_validation_status(analyses, overall_confidence)
            
            # Extract additional metrics
            key_findings = self._extract_key_findings(analyses)
            evidence_strength = self._assess_evidence_strength(analyses)
            
            # Generate validation summary
            validation_summary = self._generate_validation_summary(
                assumption, analyses, validation_status, overall_confidence
            )
            
            result = {
                "assumption_id": assumption.get("id", assumption.get("assumption_id")),
                "assumption_text": assumption.get("text", assumption.get("assumption_text", "")),
                "persona_name": persona.get("name", ""),
                "validation_status": validation_status,
                "overall_confidence": overall_confidence,
                "key_findings": key_findings,
                "evidence_strength": evidence_strength,
                "validation_summary": validation_summary,
                "analysis_breakdown": self._create_analysis_breakdown(analyses)
            }
            
            logger.info(
                f"Validated assumption {result['assumption_id']}: "
                f"{validation_status} (confidence: {overall_confidence:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating assumption: {str(e)}")
            return {
                "assumption_id": assumption.get("id", "unknown"),
                "validation_status": "error",
                "overall_confidence": 0.0,
                "error": str(e)
            }
    
    def _determine_validation_status(
        self,
        analyses: Dict[str, AnalysisOutput],
        overall_confidence: float = None
    ) -> Literal["validated", "partially_validated", "invalidated"]:
        """
        Determine overall validation status based on overall confidence score.
        
        NEW LOGIC (confidence-based):
        - VALIDATED: overall_confidence >= 0.5
        - PARTIALLY VALIDATED: 0.3 <= overall_confidence < 0.5
        - INVALIDATED: overall_confidence < 0.3
        """
        if not analyses:
            return "invalidated"
        
        # If overall_confidence is provided, use confidence-based thresholds
        if overall_confidence is not None:
            if overall_confidence >= self.validation_thresholds["validated_min_confidence"]:
                return "validated"
            elif overall_confidence >= self.validation_thresholds["partial_validated_min_confidence"]:
                return "partially_validated"
            else:
                return "invalidated"
        
        # Fallback to legacy support score logic if confidence not provided
        support_scores = []
        for analysis in analyses.values():
            metrics = self._collect_support_metrics(analysis)
            support_scores.append(metrics)

        if not support_scores:
            return "invalidated"

        total_count = len(support_scores)
        strong_contributors = sum(1 for m in support_scores if m["support_score"] >= 0.65)
        moderate_contributors = sum(1 for m in support_scores if m["support_score"] >= 0.4)

        if strong_contributors / total_count >= self.validation_thresholds["validation_ratio_threshold"]:
            return "validated"

        combined = (strong_contributors + moderate_contributors) / total_count
        if combined >= self.validation_thresholds["partial_validation_ratio_threshold"]:
            return "partially_validated"

        return "invalidated"
    
    def _calculate_overall_confidence(self, analyses: Dict[str, AnalysisOutput]) -> float:
        """Calculate overall confidence score across all analyses."""
        if not analyses:
            return 0.0
        
        # CRITICAL DEBUG: Log individual confidence scores
        logger.info(f"🔍 VALIDATOR DEBUG: Calculating overall confidence from {len(analyses)} analyses")
        for analysis_type, analysis in analyses.items():
            logger.info(f"🔍 VALIDATOR DEBUG: {analysis_type} - confidence: {analysis.confidence_score}, accuracy: {analysis.accuracy_level}")
        
        weighted_scores = []
        weights = []

        for analysis in analyses.values():
            metrics = self._collect_support_metrics(analysis)
            weight = max(metrics["support_score"], 0.1)
            weighted_scores.append(analysis.confidence_score * weight)
            weights.append(weight)

        if sum(weights) > 0:
            overall_confidence = sum(weighted_scores) / sum(weights)
            logger.info(
                f"🔍 VALIDATOR DEBUG: Overall confidence calculated: {overall_confidence:.3f} (from weighted scores: {weighted_scores})"
            )
            return overall_confidence

        logger.warning("⚠️ VALIDATOR DEBUG: No weights available, returning 0.0")
        return 0.0
    
    def _extract_key_findings(self, analyses: Dict[str, AnalysisOutput]) -> List[str]:
        """Extract key findings from all analyses - actual insights, not assumption restatements."""
        findings: List[str] = []
        seen_normalised: Set[str] = set()

        # Sort analyses by confidence score (highest first)
        sorted_analyses = sorted(
            analyses.items(),
            key=lambda x: x[1].confidence_score,
            reverse=True
        )

        for analysis_type, analysis in sorted_analyses:
            if analysis.accuracy_level in ["high", "medium"]:
                # Extract actual insights from supporting evidence, not the claim (which is just the assumption)
                evidence_list = analysis.supporting_evidence or []

                # Get the most specific, data-driven evidence
                for evidence in evidence_list[:2]:  # Top 2 pieces of evidence per analysis type
                    # Skip generic statements - look for specific data points
                    if evidence and len(evidence) > 20:  # Meaningful evidence
                        # Clean up the evidence text
                        clean_evidence = evidence.strip()
                        if self._is_generic_statement(clean_evidence):
                            continue

                        finding = f"{analysis_type.replace('_', ' ').title()}: {clean_evidence}"
                        normalised = finding.lower()
                        if normalised not in seen_normalised:
                            seen_normalised.add(normalised)
                            findings.append(finding)
                            if len(findings) >= 5:  # Stop once we have 5 findings
                                break

                if len(findings) >= 5:
                    break

        # If we didn't get enough specific findings, fall back to statistical data
        if len(findings) < 3:
            for analysis_type, analysis in sorted_analyses:
                if analysis.statistical_data and isinstance(analysis.statistical_data, dict):
                    # Extract quantitative insights from statistical_data
                    for key, value in analysis.statistical_data.items():
                        if key not in ["fact_validation", "original_data"] and value:
                            finding = f"{analysis_type.replace('_', ' ').title()}: {key.replace('_', ' ').title()} - {value}"
                            normalised = finding.lower()
                            if normalised not in seen_normalised:
                                seen_normalised.add(normalised)
                                findings.append(finding)
                            if len(findings) >= 5:
                                break
                if len(findings) >= 5:
                    break

        return findings[:5]  # Limit to top 5 findings

    def _is_generic_statement(self, text: str) -> bool:
        """Identify boilerplate statements that restate assumptions without evidence."""

        lowered = text.lower()
        if not lowered:
            return True

        generic_prefixes = [
            "the assumption",
            "smallholder farmers currently",
            "this analysis",
            "overall",
            "in summary",
        ]

        if any(lowered.startswith(prefix) for prefix in generic_prefixes):
            return True

        # Discard statements that contain no numerals, counts, or quote markers
        has_numbers = any(char.isdigit() for char in lowered)
        has_quote = '"' in text or "'" in text

        return not (has_numbers or has_quote)
    
    def _assess_evidence_strength(self, analyses: Dict[str, AnalysisOutput]) -> Dict[str, Any]:
        """Assess the strength of evidence across all analyses."""
        total_supporting = 0
        total_debunking = 0
        has_statistical_data = False
        support_scores: List[float] = []

        for analysis in analyses.values():
            total_supporting += len(analysis.supporting_evidence)
            total_debunking += len(analysis.debunking_evidence or [])

            if analysis.statistical_data:
                has_statistical_data = True
            support_scores.append(self._collect_support_metrics(analysis)["support_score"])

        # Calculate evidence ratios
        total_evidence = total_supporting + total_debunking
        support_ratio = total_supporting / total_evidence if total_evidence > 0 else 0
        average_support = sum(support_scores) / len(support_scores) if support_scores else 0.0

        # Determine evidence strength
        if support_ratio >= 0.8 and total_supporting >= 3:
            strength = "strong"
        elif support_ratio >= 0.6 and total_supporting >= 2:
            strength = "moderate"
        elif support_ratio >= 0.4:
            strength = "weak"
        else:
            strength = "insufficient"
        
        return {
            "strength": strength,
            "supporting_evidence_count": total_supporting,
            "debunking_evidence_count": total_debunking,
            "support_ratio": support_ratio,
            "has_statistical_data": has_statistical_data,
            "average_support_score": average_support
        }

    def _collect_support_metrics(self, analysis: AnalysisOutput) -> Dict[str, Any]:
        """Derive support metrics from fact validation metadata and evidence balance."""

        metadata = analysis.validation_metadata or {}
        valid_claims = metadata.get("valid_claims", [])
        questionable = metadata.get("questionable_claims", [])
        unsupported = metadata.get("unsupported_claims", [])
        total_claims = metadata.get("total_claims") or len(valid_claims) + len(questionable) + len(unsupported)

        if total_claims:
            support_ratio = (len(valid_claims) + 0.5 * len(questionable)) / total_claims
        else:
            support_ratio = None

        supporting = len(analysis.supporting_evidence or [])
        debunking = len(analysis.debunking_evidence or [])
        evidence_total = supporting + debunking
        evidence_balance = supporting / evidence_total if evidence_total else 0.0

        if support_ratio is None:
            base_score = {"high": 0.65, "medium": 0.5, "low": 0.3}.get(analysis.accuracy_level, 0.3)
        else:
            base_score = support_ratio
            if analysis.accuracy_level == "high":
                base_score += 0.15
            elif analysis.accuracy_level == "medium":
                base_score += 0.05

        base_score += min(0.2, evidence_balance * 0.2)
        base_score = max(0.0, min(1.0, base_score))

        metrics = {
            "support_score": base_score,
            "support_ratio": support_ratio,
            "evidence_balance": evidence_balance,
            "total_claims": total_claims,
            "valid_claims": len(valid_claims),
            "questionable_claims": len(questionable),
            "unsupported_claims": len(unsupported),
        }

        if isinstance(metadata, dict):
            metadata.setdefault("support_metrics", metrics)
            analysis.validation_metadata = metadata

        return metrics
    
    def _generate_validation_summary(
        self,
        assumption: Dict[str, Any],
        analyses: Dict[str, AnalysisOutput],
        validation_status: str,
        overall_confidence: float
    ) -> str:
        """Generate a human-readable validation summary."""
        assumption_text = assumption.get("text", assumption.get("assumption_text", ""))
        
        # Status description
        status_descriptions = {
            "validated": "is strongly supported by the research data",
            "partially_validated": "has mixed support from the research data",
            "invalidated": "is not supported by the research data"
        }
        
        status_desc = status_descriptions.get(validation_status, "has unclear validation")
        
        # Confidence description (aligned with validation thresholds)
        if overall_confidence >= 0.7:
            confidence_desc = "very high confidence"
        elif overall_confidence >= 0.5:
            confidence_desc = "high confidence (validated)"
        elif overall_confidence >= 0.3:
            confidence_desc = "moderate confidence (partially validated)"
        else:
            confidence_desc = "low confidence (invalidated)"
        
        # Analysis breakdown
        analysis_summary = []
        for analysis_type, analysis in analyses.items():
            type_name = analysis_type.replace('_', ' ')
            accuracy = analysis.accuracy_level
            analysis_summary.append(f"{type_name} analysis shows {accuracy} accuracy")
        
        summary = (
            f"The assumption '{assumption_text}' {status_desc} "
            f"with {confidence_desc} (score: {overall_confidence:.2f}). "
        )
        
        if analysis_summary:
            summary += "Analysis breakdown: " + "; ".join(analysis_summary) + "."
        
        return summary
    
    def _create_analysis_breakdown(self, analyses: Dict[str, AnalysisOutput]) -> Dict[str, Any]:
        """Create detailed breakdown of analysis results."""
        breakdown = {}
        
        for analysis_type, analysis in analyses.items():
            breakdown[analysis_type] = {
                "accuracy_level": analysis.accuracy_level,
                "confidence_score": analysis.confidence_score,
                "claim": analysis.claim,
                "supporting_evidence_count": len(analysis.supporting_evidence),
                "debunking_evidence_count": len(analysis.debunking_evidence or []),
                "has_statistical_data": bool(analysis.statistical_data)
            }
        
        return breakdown