"""
Comparison Agent for PV report consistency checking.

Compares market research analysis results with existing PV (Problem Validation)
report findings to identify consistencies and discrepancies.
"""

import logging
from typing import Dict, Any, List, Optional
from ..models.analysis_models import AnalysisOutput

logger = logging.getLogger(__name__)


class ComparisonAgent:
    """Agent responsible for comparing analysis results with PV report data."""
    
    def __init__(self):
        """Initialize the comparison agent."""
        self.comparison_thresholds = {
            "high_consistency_threshold": 0.8,
            "medium_consistency_threshold": 0.6,
            "similarity_threshold": 0.5  # Lowered from 0.7 to 0.5 for more lenient matching
        }
    
    async def compare_with_pv_report(
        self,
        assumption_analysis: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare assumption analysis results with PV report findings.
        
        Args:
            assumption_analysis: Complete analysis results for an assumption
            project_context: Full project context including PV report data
            
        Returns:
            Comparison results with consistency analysis
        """
        try:
            # Extract PV report data
            pv_data = self._extract_pv_data(project_context)
            
            if not pv_data:
                return {
                    "comparison_status": "no_pv_data",
                    "message": "No PV report data available for comparison",
                    "consistencies": [],
                    "discrepancies": [],
                    "overall_consistency_score": 0.0
                }
            
            # Perform detailed comparison
            comparison_results = self._perform_detailed_comparison(
                assumption_analysis, pv_data
            )
            
            # Calculate overall consistency
            overall_consistency = self._calculate_overall_consistency(comparison_results)
            
            # Generate comparison summary
            comparison_summary = self._generate_comparison_summary(
                comparison_results, overall_consistency
            )
            
            result = {
                "comparison_status": "completed",
                "overall_consistency_score": overall_consistency,
                "comparison_summary": comparison_summary,
                "detailed_comparisons": comparison_results,
                "consistencies": self._extract_consistencies(comparison_results),
                "discrepancies": self._extract_discrepancies(comparison_results),
                "recommendations": self._generate_recommendations(comparison_results)
            }
            
            logger.info(
                f"PV comparison completed for assumption {assumption_analysis.get('assumption_id')}: "
                f"consistency score {overall_consistency:.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error comparing with PV report: {str(e)}")
            return {
                "comparison_status": "error",
                "error": str(e),
                "overall_consistency_score": 0.0
            }
    
    def _extract_pv_data(self, project_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract PV report data from project context."""
        # CRITICAL FIX: Extract actual PV report content from RAG contexts
        pv_data = {}
        
        # DEBUG: Log what's in project_context
        logger.info(f"🔍 PV_COMPARISON: project_context keys: {list(project_context.keys())}")
        
        # Extract PV report chunks (actual report content)
        pv_report_context = project_context.get("pv_report_context", [])
        if pv_report_context:
            logger.info(f"🔍 PV_COMPARISON: Found {len(pv_report_context)} PV report chunks")
            pv_data["pv_report_chunks"] = pv_report_context
        
        # Extract actionable insights (key findings from PV report)
        actionable_insights = project_context.get("actionable_insights_context", [])
        if actionable_insights:
            logger.info(f"🔍 PV_COMPARISON: Found {len(actionable_insights)} actionable insights")
            pv_data["actionable_insights"] = actionable_insights
        
        # Extract VPC data if available (customer profile, value map)
        vpc_data = project_context.get("vpc_data", {})
        if vpc_data:
            logger.info(f"🔍 PV_COMPARISON: Found VPC data with keys: {list(vpc_data.keys())}")
            # Extract customer profile for comparison
            if "vpcs" in vpc_data:
                for persona_id, vpc_info in vpc_data.get("vpcs", {}).items():
                    customer_profile = vpc_info.get("customer_profile", {})
                    if customer_profile:
                        pv_data.setdefault("customer_profiles", []).append(customer_profile)
        
        if not pv_data:
            logger.warning("⚠️ PV_COMPARISON: No PV data found in project_context!")
            logger.warning(f"⚠️ PV_COMPARISON: Available keys: {list(project_context.keys())}")
        else:
            logger.info(f"✅ PV_COMPARISON: Extracted PV data with keys: {list(pv_data.keys())}")
        
        return pv_data if pv_data else None
    
    def _perform_detailed_comparison(
        self,
        assumption_analysis: Dict[str, Any],
        pv_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform detailed comparison between analysis and PV data."""
        comparisons = {}
        
        analyses = assumption_analysis.get("analyses", {})
        
        # Compare each analysis type with relevant PV data
        for analysis_type, analysis in analyses.items():
            comparison = self._compare_analysis_with_pv(
                analysis_type, analysis, pv_data
            )
            comparisons[analysis_type] = comparison
        
        return comparisons
    
    def _compare_analysis_with_pv(
        self,
        analysis_type: str,
        analysis: AnalysisOutput,
        pv_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare a specific analysis with relevant PV data."""
        comparison = {
            "analysis_type": analysis_type,
            "consistency_score": 0.0,
            "status": "no_comparison_data",
            "matching_elements": [],
            "conflicting_elements": [],
            "additional_insights": []
        }
        
        # Map analysis types to PV data fields
        pv_field_mapping = {
            "pain": ["pains", "pain_points", "customer_pains"],
            "size": ["problem_size", "market_size", "frequency"],
            "solution": ["existing_solutions", "alternatives", "current_solutions"],
            "gains": ["gains", "benefits", "value_propositions"],
            "jtbd": ["jobs", "jobs_to_be_done", "customer_jobs"]
        }
        
        # Get relevant PV fields for this analysis type
        relevant_fields = pv_field_mapping.get(analysis_type, [])
        pv_content = self._extract_pv_content(pv_data, relevant_fields)
        
        if not pv_content:
            return comparison
        
        # Perform comparison
        comparison["status"] = "compared"
        
        # Check for matching elements
        # Handle both AnalysisOutput objects and dictionaries
        if hasattr(analysis, 'claim'):
            analysis_claim = analysis.claim.lower()
            analysis_evidence = [ev.lower() for ev in analysis.supporting_evidence]
        else:
            analysis_claim = analysis.get('claim', '').lower()
            analysis_evidence = [ev.lower() for ev in analysis.get('supporting_evidence', [])]
        
        for pv_item in pv_content:
            pv_text = str(pv_item).lower()
            
            # Check for semantic similarity (simplified)
            if self._check_semantic_similarity(analysis_claim, pv_text):
                comparison["matching_elements"].append({
                    "analysis_claim": analysis.claim,
                    "pv_item": str(pv_item),
                    "similarity_type": "claim_match"
                })
            
            # Check evidence matches
            for evidence in analysis_evidence:
                if self._check_semantic_similarity(evidence, pv_text):
                    comparison["matching_elements"].append({
                        "analysis_evidence": evidence,
                        "pv_item": str(pv_item),
                        "similarity_type": "evidence_match"
                    })
        
        # Check for conflicts (simplified logic)
        accuracy_level = analysis.accuracy_level if hasattr(analysis, 'accuracy_level') else analysis.get('accuracy_level', 'low')
        claim = analysis.claim if hasattr(analysis, 'claim') else analysis.get('claim', '')
        confidence = analysis.confidence_score if hasattr(analysis, 'confidence_score') else analysis.get('confidence_score', 0.0)
        
        if accuracy_level == "high" and not comparison["matching_elements"]:
            comparison["conflicting_elements"].append({
                "issue": "High confidence analysis finding not reflected in PV report",
                "analysis_claim": claim,
                "analysis_confidence": confidence
            })
        
        # Calculate consistency score
        total_elements = len(comparison["matching_elements"]) + len(comparison["conflicting_elements"])
        if total_elements > 0:
            consistency_score = len(comparison["matching_elements"]) / total_elements
        else:
            consistency_score = 0.5  # Neutral when no comparison data
        
        comparison["consistency_score"] = consistency_score
        
        return comparison
    
    def _extract_pv_content(self, pv_data: Dict[str, Any], field_names: List[str]) -> List[Any]:
        """Extract content from PV data for specific fields."""
        content = []
        
        # CRITICAL FIX: Extract from actual PV report chunks and insights
        
        # Extract from PV report chunks (text content)
        pv_chunks = pv_data.get("pv_report_chunks", [])
        logger.info(f"🔍 PV_EXTRACTION: Processing {len(pv_chunks)} PV report chunks")
        for i, chunk in enumerate(pv_chunks):
            if isinstance(chunk, dict):
                chunk_content = chunk.get("content", "")
                if chunk_content:
                    # CRITICAL FIX: Strip HTML tags from PV report chunks
                    import re
                    clean_content = re.sub(r'<[^>]+>', '', chunk_content)  # Remove HTML tags
                    clean_content = clean_content.strip()
                    if clean_content:
                        content.append(clean_content)
                        if i < 2:  # Log first 2 chunks for debugging
                            logger.info(f"🔍 PV_EXTRACTION: Chunk {i+1} preview (cleaned): {clean_content[:100]}...")
            elif isinstance(chunk, str):
                # Strip HTML from string chunks too
                import re
                clean_chunk = re.sub(r'<[^>]+>', '', chunk).strip()
                if clean_chunk:
                    content.append(clean_chunk)
                    if i < 2:
                        logger.info(f"🔍 PV_EXTRACTION: Chunk {i+1} (string, cleaned) preview: {clean_chunk[:100]}...")
        
        # Extract from actionable insights
        insights = pv_data.get("actionable_insights", [])
        logger.info(f"🔍 PV_EXTRACTION: Processing {len(insights)} actionable insights")
        for i, insight in enumerate(insights):
            if isinstance(insight, dict):
                insight_content = insight.get("content", "")
                if insight_content:
                    content.append(insight_content)
                    if i < 2:  # Log first 2 insights for debugging
                        logger.info(f"🔍 PV_EXTRACTION: Insight {i+1} preview: {insight_content[:100]}...")
            elif isinstance(insight, str):
                content.append(insight)
                if i < 2:
                    logger.info(f"🔍 PV_EXTRACTION: Insight {i+1} (string) preview: {insight[:100]}...")
        
        # Extract from customer profiles (VPC data)
        customer_profiles = pv_data.get("customer_profiles", [])
        logger.info(f"🔍 PV_EXTRACTION: Processing {len(customer_profiles)} customer profiles")
        for profile in customer_profiles:
            # Map field names to customer profile fields
            for field_name in field_names:
                if "pain" in field_name:
                    pains = profile.get("pains", [])
                    content.extend([p.get("label", "") for p in pains if isinstance(p, dict)])
                elif "gain" in field_name:
                    gains = profile.get("gains", [])
                    content.extend([g.get("label", "") for g in gains if isinstance(g, dict)])
                elif "job" in field_name or "jtbd" in field_name:
                    jobs = profile.get("jobs_to_be_done", [])
                    content.extend([j.get("label", "") for j in jobs if isinstance(j, dict)])
        
        logger.info(f"🔍 PV_COMPARISON: Extracted {len(content)} content items for fields: {field_names}")
        if len(content) == 0:
            logger.error(f"❌ PV_COMPARISON: NO CONTENT EXTRACTED! pv_data keys: {list(pv_data.keys())}")
        
        return content
    
    def _check_semantic_similarity(self, text1: str, text2: str) -> bool:
        """Check semantic similarity between two texts (simplified implementation)."""
        # Simple keyword-based similarity check
        # In a production system, this would use embeddings or NLP similarity
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1 or not words2:
            return False
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= self.comparison_thresholds.get("similarity_threshold", 0.3)
    
    def _calculate_overall_consistency(self, comparison_results: Dict[str, Any]) -> float:
        """Calculate overall consistency score across all comparisons."""
        if not comparison_results:
            return 0.0
        
        scores = []
        for comparison in comparison_results.values():
            if comparison.get("status") == "compared":
                scores.append(comparison.get("consistency_score", 0.0))
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _generate_comparison_summary(
        self,
        comparison_results: Dict[str, Any],
        overall_consistency: float
    ) -> str:
        """Generate human-readable comparison summary."""
        if overall_consistency >= self.comparison_thresholds["high_consistency_threshold"]:
            consistency_level = "high consistency"
        elif overall_consistency >= self.comparison_thresholds["medium_consistency_threshold"]:
            consistency_level = "moderate consistency"
        else:
            consistency_level = "low consistency"
        
        total_matches = sum(
            len(comp.get("matching_elements", []))
            for comp in comparison_results.values()
        )
        
        total_conflicts = sum(
            len(comp.get("conflicting_elements", []))
            for comp in comparison_results.values()
        )
        
        summary = (
            f"Market research analysis shows {consistency_level} "
            f"with existing PV report findings (score: {overall_consistency:.2f}). "
            f"Found {total_matches} matching elements and {total_conflicts} potential conflicts."
        )
        
        return summary
    
    def _extract_consistencies(self, comparison_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all consistency findings."""
        consistencies = []
        
        for analysis_type, comparison in comparison_results.items():
            for match in comparison.get("matching_elements", []):
                consistencies.append({
                    "analysis_type": analysis_type,
                    "type": match.get("similarity_type", "match"),
                    "analysis_finding": match.get("analysis_claim") or match.get("analysis_evidence"),
                    "pv_finding": match.get("pv_item"),
                    "confidence": "high" if comparison.get("consistency_score", 0) > 0.7 else "medium"
                })
        
        return consistencies
    
    def _extract_discrepancies(self, comparison_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all discrepancy findings."""
        discrepancies = []
        
        for analysis_type, comparison in comparison_results.items():
            for conflict in comparison.get("conflicting_elements", []):
                discrepancies.append({
                    "analysis_type": analysis_type,
                    "issue": conflict.get("issue"),
                    "analysis_finding": conflict.get("analysis_claim"),
                    "severity": "high" if conflict.get("analysis_confidence", 0) > 0.8 else "medium"
                })
        
        return discrepancies
    
    def _generate_recommendations(self, comparison_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on comparison results."""
        recommendations = []
        
        # Count high-confidence conflicts
        high_confidence_conflicts = 0
        for comparison in comparison_results.values():
            for conflict in comparison.get("conflicting_elements", []):
                if conflict.get("analysis_confidence", 0) > 0.8:
                    high_confidence_conflicts += 1
        
        if high_confidence_conflicts > 0:
            recommendations.append(
                f"Review {high_confidence_conflicts} high-confidence findings that conflict with PV report"
            )
        
        # Check for missing analysis types in PV
        no_comparison_count = sum(
            1 for comp in comparison_results.values()
            if comp.get("status") == "no_comparison_data"
        )
        
        if no_comparison_count > 0:
            recommendations.append(
                f"Consider updating PV report with insights from {no_comparison_count} analysis areas"
            )
        
        # Overall consistency recommendations
        overall_consistency = self._calculate_overall_consistency(comparison_results)
        if overall_consistency < 0.5:
            recommendations.append(
                "Low consistency detected - consider revisiting assumptions or PV report"
            )
        
        return recommendations