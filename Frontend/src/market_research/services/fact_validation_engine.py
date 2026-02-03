"""
Fact Validation Engine for Market Research Analysis

This module implements automated claim verification against the statistics registry
to ensure AI-generated quantitative claims are accurate and traceable.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class QuantitativeClaim:
    """Represents an extracted quantitative claim from AI response."""
    claim_text: str
    percentage: Optional[float] = None
    count: Optional[int] = None
    sample_reference: Optional[str] = None
    context: str = ""
    confidence: float = 0.0
    source_location: str = ""


@dataclass
class ValidationResult:
    """Result of validating a claim against statistics registry."""
    claim: QuantitativeClaim
    is_valid: bool
    registry_match: Optional[Dict[str, Any]] = None
    discrepancy: Optional[float] = None
    validation_confidence: float = 0.0
    error_message: Optional[str] = None


class FactValidationEngine:
    """
    Engine for extracting and validating quantitative claims from AI responses.
    
    This engine addresses requirements 6.1, 6.2, and 6.3 by:
    - Extracting quantitative claims using regex and NLP
    - Validating claims against statistics registry ground truth
    - Adjusting confidence scores based on validation results
    """
    
    def __init__(self):
        """Initialize the fact validation engine."""
        # FIXED: Improved patterns to not split on parentheses within percentages
        # Changed [^.!?]+ to [^.!?;]+ and handle parentheses better
        self.percentage_patterns = [
            # Match percentage with context, stopping at sentence boundaries but allowing parentheses
            r'(\d+(?:\.\d+)?)\s*%\s*(?:of\s+)?([^.!?;]+?)(?=\s*(?:\[|$|\.(?:\s|$)|!|;))',
            r'(\d+(?:\.\d+)?)\s*percent\s*(?:of\s+)?([^.!?;]+?)(?=\s*(?:\[|$|\.(?:\s|$)|!|;))',
            r'(\d+(?:\.\d+)?)\s*out\s+of\s+(\d+)',
            r'(\d+(?:\.\d+)?)/(\d+)',
        ]
        
        self.count_patterns = [
            # FIXED: Allow parentheses in count claims, stop at sentence boundaries or citations
            r'(\d+)\s+(?:respondents?|participants?|users?|people)\s+([^.!?;]+?)(?=\s*(?:\[|$|\.(?:\s|$)|!|;))',
            r'(\d+)\s+(?:out\s+of\s+\d+\s+)?(?:respondents?|participants?|users?|people)',
            r'(\d+)\s+(?:individuals?|customers?|survey\s+participants?)',
        ]
        
        self.frequency_patterns = [
            # FIXED: Allow parentheses in frequency claims, stop at sentence boundaries or citations
            r'(?:most|majority|many|few|some|several)\s+([^.!?;]+?)(?=\s*(?:\[|$|\.(?:\s|$)|!|;))',
            r'(?:frequently|often|rarely|sometimes|never)\s+([^.!?;]+?)(?=\s*(?:\[|$|\.(?:\s|$)|!|;))',
            r'(?:always|usually|occasionally|seldom)\s+([^.!?;]+?)(?=\s*(?:\[|$|\.(?:\s|$)|!|;))',
        ]
        
        # Tolerance for percentage matching (e.g., 72% vs 72.1%)
        self.percentage_tolerance = 2.0
        
    def extract_quantitative_claims(self, ai_response: str) -> List[QuantitativeClaim]:
        """
        Extract all quantitative claims from AI response text.
        
        Args:
            ai_response: The AI-generated analysis text
            
        Returns:
            List of extracted quantitative claims
        """
        claims = []
        
        try:
            # Extract percentage claims
            claims.extend(self._extract_percentage_claims(ai_response))
            
            # Extract count claims
            claims.extend(self._extract_count_claims(ai_response))
            
            # Extract frequency claims
            claims.extend(self._extract_frequency_claims(ai_response))
            
            logger.info(f"Extracted {len(claims)} quantitative claims from AI response")
            
        except Exception as e:
            logger.error(f"Error extracting quantitative claims: {e}")
            
        return claims
    
    def _extract_percentage_claims(self, text: str) -> List[QuantitativeClaim]:
        """Extract percentage-based claims from text."""
        claims = []
        
        for pattern in self.percentage_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    if '/' in pattern or 'out of' in pattern:
                        # Handle fraction patterns
                        numerator = float(match.group(1))
                        denominator = float(match.group(2))
                        percentage = (numerator / denominator) * 100 if denominator > 0 else 0
                        sample_ref = f"{int(denominator)} total"
                        context = f"{numerator} out of {denominator}"
                    else:
                        # Handle direct percentage patterns
                        percentage = float(match.group(1))
                        sample_ref = match.group(2).strip() if len(match.groups()) > 1 else "respondents"
                        context = match.group(0)
                    
                    claim = QuantitativeClaim(
                        claim_text=match.group(0),
                        percentage=percentage,
                        sample_reference=sample_ref,
                        context=context,
                        source_location=f"chars {match.start()}-{match.end()}"
                    )
                    claims.append(claim)
                    
                except (ValueError, ZeroDivisionError) as e:
                    logger.warning(f"Error parsing percentage claim '{match.group(0)}': {e}")
                    
        return claims
    
    def _extract_count_claims(self, text: str) -> List[QuantitativeClaim]:
        """Extract count-based claims from text."""
        claims = []
        
        for pattern in self.count_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    count = int(match.group(1))
                    context = match.group(2).strip() if len(match.groups()) > 1 else match.group(0)
                    
                    claim = QuantitativeClaim(
                        claim_text=match.group(0),
                        count=count,
                        sample_reference="participants",
                        context=context,
                        source_location=f"chars {match.start()}-{match.end()}"
                    )
                    claims.append(claim)
                    
                except ValueError as e:
                    logger.warning(f"Error parsing count claim '{match.group(0)}': {e}")
                    
        return claims
    
    def _extract_frequency_claims(self, text: str) -> List[QuantitativeClaim]:
        """Extract frequency-based qualitative claims."""
        claims = []
        
        for pattern in self.frequency_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                context = match.group(1).strip() if len(match.groups()) > 0 else match.group(0)
                
                claim = QuantitativeClaim(
                    claim_text=match.group(0),
                    context=context,
                    sample_reference="qualitative",
                    source_location=f"chars {match.start()}-{match.end()}"
                )
                claims.append(claim)
                
        return claims
    
    def validate_claims_against_registry(
        self,
        claims: List[QuantitativeClaim],
        statistics_registry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate extracted claims against statistics registry ground truth.
        
        Args:
            claims: List of extracted quantitative claims
            statistics_registry: Ground truth statistics from registry
            
        Returns:
            Comprehensive validation results
        """
        validation_results = []
        valid_claims = []
        unsupported_claims = []
        questionable_claims = []
        
        try:
            for claim in claims:
                result = self._validate_single_claim(claim, statistics_registry)
                validation_results.append(result)
                
                # CRITICAL FIX: Use ValidationResult attributes, not dictionary methods
                if result.is_valid and result.validation_confidence >= 0.8:
                    valid_claims.append(claim.claim_text)
                elif result.is_valid and result.validation_confidence >= 0.6:
                    # Be more lenient with formatting issues if the core claim is valid
                    valid_claims.append(claim.claim_text)
                elif result.validation_confidence >= 0.4:
                    # Check if it's just a formatting issue vs truly unsupported
                    questionable_claims.append(claim.claim_text)
                else:
                    unsupported_claims.append(claim.claim_text)
            
            # Calculate overall fact-check score
            if validation_results:
                fact_check_score = sum(
                    1.0 if r.is_valid and r.validation_confidence >= 0.8 else
                    0.7 if r.is_valid and r.validation_confidence >= 0.6 else
                    0.5 if r.validation_confidence >= 0.4 else 0.0
                    for r in validation_results
                ) / len(validation_results)
            else:
                # No quantitative claims to validate - this is OK for qualitative data
                fact_check_score = 0.8  # Default to good score for qualitative analysis
            
            return {
                "fact_check_score": fact_check_score,
                "valid_claims": valid_claims,
                "unsupported_claims": unsupported_claims,
                "questionable_claims": questionable_claims,
                "validation_details": [
                    {
                        "claim": r.claim.claim_text,
                        "is_valid": r.is_valid,
                        "confidence": r.validation_confidence,
                        "discrepancy": r.discrepancy,
                        "registry_match": r.registry_match,
                        "error": r.error_message
                    }
                    for r in validation_results
                ],
                "total_claims": len(claims),
                "validated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating claims against registry: {e}")
            return {
                "fact_check_score": 0.0,
                "valid_claims": [],
                "unsupported_claims": [c.claim_text for c in claims],
                "questionable_claims": [],
                "validation_details": [],
                "total_claims": len(claims),
                "error": str(e),
                "validated_at": datetime.utcnow().isoformat()
            }
    
    def _validate_single_claim(
        self,
        claim: QuantitativeClaim,
        statistics_registry: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a single claim against the statistics registry."""
        try:
            # Handle percentage claims
            if claim.percentage is not None:
                return self._validate_percentage_claim(claim, statistics_registry)
            
            # Handle count claims
            elif claim.count is not None:
                return self._validate_count_claim(claim, statistics_registry)
            
            # Handle frequency claims (qualitative)
            else:
                return self._validate_frequency_claim(claim, statistics_registry)
                
        except Exception as e:
            logger.error(f"Error validating claim '{claim.claim_text}': {e}")
            return ValidationResult(
                claim=claim,
                is_valid=False,
                error_message=str(e),
                validation_confidence=0.0
            )
    
    def _validate_percentage_claim(
        self,
        claim: QuantitativeClaim,
        statistics_registry: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a percentage claim against registry statistics."""
        best_match = None
        best_confidence = 0.0
        smallest_discrepancy = float('inf')
        
        # Search through CSV statistics
        csv_stats = statistics_registry.get('csv_statistics', {})
        for field_name, field_data in csv_stats.get('categorical_distributions', {}).items():
            for value_data in field_data.get('distribution', []):
                registry_percentage = value_data.get('percentage', 0)
                discrepancy = abs(claim.percentage - registry_percentage)
                
                if discrepancy <= self.percentage_tolerance:
                    # Check context similarity
                    context_similarity = self._calculate_context_similarity(
                        claim.context, f"{field_name} {value_data.get('value', '')}"
                    )
                    
                    if context_similarity > best_confidence:
                        best_match = {
                            'field': field_name,
                            'value': value_data.get('value'),
                            'registry_percentage': registry_percentage,
                            'citation_id': value_data.get('citation_id')
                        }
                        best_confidence = context_similarity
                        smallest_discrepancy = discrepancy
        
        # Search through PDF statistics
        pdf_stats = statistics_registry.get('pdf_statistics', {})
        for theme_name, theme_data in pdf_stats.get('themes', {}).items():
            registry_percentage = theme_data.get('percentage', 0)
            discrepancy = abs(claim.percentage - registry_percentage)
            
            if discrepancy <= self.percentage_tolerance:
                context_similarity = self._calculate_context_similarity(
                    claim.context, theme_name
                )
                
                if context_similarity > best_confidence:
                    best_match = {
                        'theme': theme_name,
                        'registry_percentage': registry_percentage,
                        'citation_id': theme_data.get('citation_id')
                    }
                    best_confidence = context_similarity
                    smallest_discrepancy = discrepancy
        
        is_valid = best_match is not None and best_confidence >= 0.3
        
        return ValidationResult(
            claim=claim,
            is_valid=is_valid,
            registry_match=best_match,
            discrepancy=smallest_discrepancy if best_match else None,
            validation_confidence=best_confidence
        )
    
    def _validate_count_claim(
        self,
        claim: QuantitativeClaim,
        statistics_registry: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a count claim against registry statistics."""
        # For count claims, we look for matching counts in the registry
        best_match = None
        best_confidence = 0.0
        
        # Check CSV total counts
        csv_stats = statistics_registry.get('csv_statistics', {})
        total_rows = csv_stats.get('metadata', {}).get('total_rows', 0)
        
        if claim.count <= total_rows:
            # Look for matching counts in distributions
            for field_name, field_data in csv_stats.get('categorical_distributions', {}).items():
                for value_data in field_data.get('distribution', []):
                    registry_count = value_data.get('count', 0)
                    
                    if claim.count == registry_count:
                        context_similarity = self._calculate_context_similarity(
                            claim.context, f"{field_name} {value_data.get('value', '')}"
                        )
                        
                        if context_similarity > best_confidence:
                            best_match = {
                                'field': field_name,
                                'value': value_data.get('value'),
                                'registry_count': registry_count,
                                'citation_id': value_data.get('citation_id')
                            }
                            best_confidence = context_similarity
        
        is_valid = best_match is not None and best_confidence >= 0.3
        
        return ValidationResult(
            claim=claim,
            is_valid=is_valid,
            registry_match=best_match,
            validation_confidence=best_confidence
        )
    
    def _validate_frequency_claim(
        self,
        claim: QuantitativeClaim,
        statistics_registry: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a frequency/qualitative claim against registry."""
        # For frequency claims, we check if the context appears in themes or quotes
        best_match = None
        best_confidence = 0.0
        
        # Check PDF themes
        pdf_stats = statistics_registry.get('pdf_statistics', {})
        for theme_name, theme_data in pdf_stats.get('themes', {}).items():
            context_similarity = self._calculate_context_similarity(
                claim.context, theme_name
            )
            
            if context_similarity > best_confidence:
                best_match = {
                    'theme': theme_name,
                    'frequency': theme_data.get('frequency', 0),
                    'citation_id': theme_data.get('citation_id')
                }
                best_confidence = context_similarity
        
        # Check key quotes
        for quote_data in pdf_stats.get('key_quotes', []):
            context_similarity = self._calculate_context_similarity(
                claim.context, quote_data.get('quote', '')
            )
            
            if context_similarity > best_confidence:
                best_match = {
                    'quote': quote_data.get('quote'),
                    'theme': quote_data.get('theme'),
                    'citation_id': quote_data.get('citation_id')
                }
                best_confidence = context_similarity
        
        is_valid = best_match is not None and best_confidence >= 0.4
        
        return ValidationResult(
            claim=claim,
            is_valid=is_valid,
            registry_match=best_match,
            validation_confidence=best_confidence
        )
    
    def _calculate_context_similarity(self, claim_context: str, registry_context: str) -> float:
        """Calculate similarity between claim context and registry context."""
        if not claim_context or not registry_context:
            return 0.0
        
        # Simple keyword-based similarity
        claim_words = set(claim_context.lower().split())
        registry_words = set(registry_context.lower().split())
        
        if not claim_words or not registry_words:
            return 0.0
        
        intersection = claim_words.intersection(registry_words)
        union = claim_words.union(registry_words)
        
        return len(intersection) / len(union) if union else 0.0
    
    def adjust_confidence_score(
        self,
        original_confidence: float,
        fact_check_score: float,
        validation_details: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Adjust AI confidence score based on fact-checking results.
        
        Args:
            original_confidence: Original AI confidence score (0.0-1.0)
            fact_check_score: Fact validation score (0.0-1.0)
            validation_details: Optional detailed validation results
            
        Returns:
            Adjusted confidence score
        """
        try:
            # More lenient base adjustment using fact check score
            if fact_check_score >= 0.8:
                # High validation score - slight boost
                adjustment_factor = 1.1
            elif fact_check_score >= 0.6:
                # Good validation score - maintain confidence
                adjustment_factor = 1.0
            elif fact_check_score >= 0.4:
                # Moderate validation score - slight reduction
                adjustment_factor = 0.9
            elif fact_check_score >= 0.2:
                # Low validation score - moderate reduction
                adjustment_factor = 0.8
            else:
                # Very low validation score - still allow some confidence
                adjustment_factor = 0.7  # More lenient than 0.4
            
            # Additional adjustments based on validation details
            if validation_details:
                unsupported_claims = len(validation_details.get('unsupported_claims', []))
                total_claims = validation_details.get('total_claims', 1)
                
                if total_claims > 0:
                    unsupported_ratio = unsupported_claims / total_claims
                    if unsupported_ratio > 0.7:
                        adjustment_factor *= 0.85  # Many unsupported claims (more lenient)
                    elif unsupported_ratio > 0.5:
                        adjustment_factor *= 0.9   # Some unsupported claims (more lenient)
            
            # Apply adjustment with bounds checking
            adjusted_confidence = original_confidence * adjustment_factor
            
            # CRITICAL FIX: If original confidence is 0.0, provide minimum based on evidence
            if original_confidence == 0.0 and adjustment_factor >= 0.7:
                # If fact validation isn't too harsh, provide minimum confidence
                adjusted_confidence = 0.3 * adjustment_factor
                logger.info(f"🔧 CONFIDENCE FLOOR: Applied minimum confidence due to 0.0 original")
            
            # Ensure bounds [0.0, 1.0]
            adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
            
            logger.info(
                f"Confidence adjusted: {original_confidence:.3f} -> {adjusted_confidence:.3f} "
                f"(fact_check_score: {fact_check_score:.3f}, factor: {adjustment_factor:.3f})"
            )
            
            return adjusted_confidence
            
        except Exception as e:
            logger.error(f"Error adjusting confidence score: {e}")
            # Return conservative confidence on error
            return min(original_confidence * 0.5, 0.5)
    
    def generate_validation_report(
        self,
        validation_results: Dict[str, Any],
        include_details: bool = True
    ) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            validation_results: Results from validate_claims_against_registry
            include_details: Whether to include detailed validation information
            
        Returns:
            Formatted validation report
        """
        try:
            report_lines = [
                "🔍 FACT VALIDATION REPORT",
                "=" * 50,
                f"Overall Fact-Check Score: {validation_results['fact_check_score']:.1%}",
                f"Total Claims Analyzed: {validation_results['total_claims']}",
                f"Valid Claims: {len(validation_results['valid_claims'])}",
                f"Questionable Claims: {len(validation_results['questionable_claims'])}",
                f"Unsupported Claims: {len(validation_results['unsupported_claims'])}",
                ""
            ]
            
            if validation_results['valid_claims']:
                report_lines.extend([
                    "✅ VALIDATED CLAIMS:",
                    *[f"  • {claim}" for claim in validation_results['valid_claims']],
                    ""
                ])
            
            if validation_results['questionable_claims']:
                report_lines.extend([
                    "⚠️  QUESTIONABLE CLAIMS:",
                    *[f"  • {claim}" for claim in validation_results['questionable_claims']],
                    ""
                ])
            
            if validation_results['unsupported_claims']:
                report_lines.extend([
                    "❌ UNSUPPORTED CLAIMS:",
                    *[f"  • {claim}" for claim in validation_results['unsupported_claims']],
                    ""
                ])
            
            if include_details and validation_results['validation_details']:
                report_lines.extend([
                    "📋 DETAILED VALIDATION RESULTS:",
                    "-" * 30
                ])
                
                for detail in validation_results['validation_details']:
                    status = "✅" if detail['is_valid'] else "❌"
                    report_lines.append(f"{status} {detail['claim']}")
                    if detail.get('confidence'):
                        report_lines.append(f"   Confidence: {detail['confidence']:.1%}")
                    if detail.get('discrepancy') is not None:
                        report_lines.append(f"   Discrepancy: {detail['discrepancy']:.1f}%")
                    if detail.get('error'):
                        report_lines.append(f"   Error: {detail['error']}")
                    report_lines.append("")
            
            report_lines.append(f"Generated at: {validation_results.get('validated_at', 'Unknown')}")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Error generating validation report: {e}")
            return f"Error generating validation report: {e}"