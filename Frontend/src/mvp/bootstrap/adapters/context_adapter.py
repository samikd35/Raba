"""
Bootstrap Context Adapter

Adapts bootstrap enhanced_context to the format expected by existing
VPS v1 and BMC v1 generation agents.

This allows bootstrap projects to use the same generation pipeline
as normal workflow projects, ensuring consistent output quality.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BootstrapContextAdapter:
    """
    Adapts bootstrap enhanced_context to VPS/BMC context format.
    
    The VPS and BMC agents expect specific context structures based on
    the normal workflow (PV Report, VPC, Personas, etc.). This adapter
    transforms the bootstrap enhanced_context to match those expectations.
    """
    
    def __init__(self):
        """Initialize context adapter."""
        logger.info("Bootstrap Context Adapter initialized")
    
    def adapt_for_vps(
        self,
        enhanced_context: Dict[str, Any],
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Transform bootstrap enhanced_context into VPS context format.
        
        VPS v1 expects:
        - customer_profile: { jobs_to_be_done, pains, gains }
        - value_map: { products_services, pain_relievers, gain_creators }
        - personas: [...]
        - pv_report_insights: [...]
        - hypotheses: [...]
        - assumptions: [...]
        - market_research_analysis: [...]
        - context_completeness: float
        
        Args:
            enhanced_context: Bootstrap enhanced context (draft or confirmed)
            project_id: Project ID
            tenant_id: Tenant ID
            
        Returns:
            Context dict in VPS-expected format
        """
        try:
            # Get the context to use (confirmed takes precedence over draft)
            context_data = enhanced_context.get("confirmed") or enhanced_context.get("draft") or {}
            metadata = enhanced_context.get("metadata", {})
            
            logger.info(f"🔄 Adapting bootstrap context for VPS generation")
            
            # Extract customer segments
            customer_segments = context_data.get("CustomerSegments", [])
            primary_segment = customer_segments[0] if customer_segments else "Target Customer"
            
            # Extract problem definition
            problem = context_data.get("Problem", {})
            
            # Build customer profile (from bootstrap context)
            customer_profile = self._build_customer_profile(context_data, problem)
            
            # Build value map (from bootstrap context)
            value_map = self._build_value_map(context_data)
            
            # Build personas from customer segments
            personas = self._build_personas(customer_segments, problem)
            
            # Extract insights from research
            pv_report_insights = self._extract_insights(context_data)
            
            # Build hypotheses from business model seeds
            hypotheses = self._build_hypotheses(context_data)
            
            # Build assumptions from constraints and risks
            assumptions = self._build_assumptions(context_data)
            
            # Get research analysis
            market_research_analysis = self._get_research_analysis(context_data)
            
            # Calculate context completeness
            completeness = self._calculate_completeness(context_data)
            
            # Extract project name from idea summary or use default
            idea_summary = context_data.get("IdeaSummary", "")
            project_name = idea_summary[:50] + "..." if len(idea_summary) > 50 else idea_summary
            if not project_name:
                project_name = "Bootstrap Project"
            
            vps_context = {
                "project_id": project_id,
                "tenant_id": tenant_id,
                "project_name": project_name,
                "project_description": idea_summary,
                "context_mode": "bootstrap",
                
                # Core VPS inputs
                "customer_profile": customer_profile,
                "value_map": value_map,
                "personas": personas,
                "persona_count": len(personas),
                "primary_persona": personas[0] if personas else None,
                
                # Supporting context
                "pv_report_insights": pv_report_insights,
                "hypotheses": hypotheses,
                "assumptions": assumptions,
                "market_research_analysis": market_research_analysis,
                
                # Metadata
                "context_completeness": completeness,
                "context_source": "bootstrap",
                "idea_summary": idea_summary,
                "differentiation": context_data.get("Differentiation", []),
                
                # Timestamps
                "loaded_at": datetime.utcnow().isoformat(),
                "loaded_for": "vps_generation"
            }
            
            logger.info(f"✅ VPS context adapted with {completeness:.0%} completeness")
            logger.info(f"   Personas: {len(personas)}")
            logger.info(f"   Hypotheses: {len(hypotheses)}")
            logger.info(f"   Research insights: {len(pv_report_insights)}")
            
            return vps_context
            
        except Exception as e:
            logger.error(f"❌ Error adapting context for VPS: {e}")
            raise
    
    def adapt_for_bmc(
        self,
        enhanced_context: Dict[str, Any],
        vps_v1: Dict[str, Any],
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Transform bootstrap enhanced_context + VPS v1 into BMC context format.
        
        BMC expects all VPS context PLUS:
        - vps_v1: The generated VPS v1 data
        
        Args:
            enhanced_context: Bootstrap enhanced context
            vps_v1: Generated VPS v1 data
            project_id: Project ID
            tenant_id: Tenant ID
            
        Returns:
            Context dict in BMC-expected format
        """
        try:
            logger.info(f"🔄 Adapting bootstrap context for BMC generation")
            
            # Start with VPS context
            bmc_context = self.adapt_for_vps(enhanced_context, project_id, tenant_id)
            
            # Add VPS v1
            bmc_context["vps_v1"] = vps_v1
            bmc_context["loaded_for"] = "bmc_generation"
            
            # Add business model seeds from enhanced context
            context_data = enhanced_context.get("confirmed") or enhanced_context.get("draft") or {}
            bmc_context["business_model_seeds"] = context_data.get("BusinessModelSeeds", {})
            bmc_context["alternatives_and_competition"] = context_data.get("AlternativesAndCompetition", {})
            
            logger.info(f"✅ BMC context adapted with VPS v1 included")
            
            return bmc_context
            
        except Exception as e:
            logger.error(f"❌ Error adapting context for BMC: {e}")
            raise
    
    def _build_customer_profile(
        self,
        context_data: Dict[str, Any],
        problem: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build customer profile from bootstrap context."""
        # Jobs to be done - derived from problem
        jobs_to_be_done = []
        if problem.get("what"):
            jobs_to_be_done.append({
                "id": "jtbd-1",
                "description": f"Solve: {problem.get('what', 'their core problem')}",
                "importance": "high",
                "frequency": "regular"
            })
        
        # Add solution-oriented JTBD
        solution = context_data.get("SolutionOverview", "")
        if solution:
            jobs_to_be_done.append({
                "id": "jtbd-2",
                "description": f"Access: {solution[:150]}..." if len(solution) > 150 else solution,
                "importance": "high",
                "frequency": "regular"
            })
        
        # Pains - derived from problem
        pains = []
        if problem.get("what"):
            pains.append({
                "id": "pain-1",
                "description": problem.get("what", ""),
                "severity": "high",
                "frequency": "regular"
            })
        if problem.get("why_now"):
            pains.append({
                "id": "pain-2",
                "description": problem.get("why_now", ""),
                "severity": "medium",
                "frequency": "situational"
            })
        
        # Gains - derived from differentiation and solution
        gains = []
        differentiators = context_data.get("Differentiation", [])
        for i, diff in enumerate(differentiators[:3]):
            gains.append({
                "id": f"gain-{i+1}",
                "description": diff,
                "importance": "high" if i == 0 else "medium"
            })
        
        return {
            "jobs_to_be_done": jobs_to_be_done,
            "pains": pains,
            "gains": gains
        }
    
    def _build_value_map(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build value map from bootstrap context."""
        solution = context_data.get("SolutionOverview", "")
        differentiators = context_data.get("Differentiation", [])
        
        # Products/Services
        products_services = []
        if solution:
            products_services.append({
                "id": "ps-1",
                "name": "Core Solution",
                "description": solution[:200] if len(solution) > 200 else solution
            })
        
        # Pain Relievers - from differentiators
        pain_relievers = []
        for i, diff in enumerate(differentiators[:3]):
            pain_relievers.append({
                "id": f"pr-{i+1}",
                "description": diff
            })
        
        # Gain Creators - from business model seeds
        gain_creators = []
        bm_seeds = context_data.get("BusinessModelSeeds", {})
        if bm_seeds.get("revenue_model"):
            gain_creators.append({
                "id": "gc-1",
                "description": f"Value delivered through: {bm_seeds['revenue_model']}"
            })
        
        return {
            "products_services": products_services,
            "pain_relievers": pain_relievers,
            "gain_creators": gain_creators
        }
    
    def _build_personas(
        self,
        customer_segments: List[str],
        problem: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build personas from customer segments."""
        personas = []
        
        for i, segment in enumerate(customer_segments[:2]):  # Max 2 personas
            personas.append({
                "id": f"persona-{i+1}",
                "name": segment[:50] if len(segment) > 50 else segment,
                "description": f"{segment}. They experience: {problem.get('what', 'the core problem')}",
                "demographics": {
                    "segment": segment,
                    "geography": problem.get("where", "Target market")
                },
                "behaviors": [],
                "goals": [problem.get("what", "Solve their problem")],
                "frustrations": [problem.get("what", "Current problem")],
                "evidence_source": "bootstrap_context"
            })
        
        # Ensure at least one persona
        if not personas:
            personas.append({
                "id": "persona-1",
                "name": problem.get("who", "Target Customer"),
                "description": f"Primary customer experiencing: {problem.get('what', 'the problem')}",
                "demographics": {"geography": problem.get("where", "Target market")},
                "behaviors": [],
                "goals": [],
                "frustrations": [problem.get("what", "")],
                "evidence_source": "bootstrap_context"
            })
        
        return personas
    
    def _extract_insights(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract insights from research section."""
        insights = []
        
        research = context_data.get("Research", {})
        sources = research.get("sources", [])
        
        for source in sources[:5]:  # Top 5 sources as insights
            if source.get("snippet"):
                insights.append({
                    "id": f"insight-{source.get('n', 0)}",
                    "content": source.get("snippet", ""),
                    "source": source.get("title", "Web Research"),
                    "url": source.get("url", ""),
                    "confidence": 0.7
                })
        
        # Add idea summary as insight
        if context_data.get("IdeaSummary"):
            insights.insert(0, {
                "id": "insight-summary",
                "content": context_data["IdeaSummary"],
                "source": "User Input",
                "confidence": 1.0
            })
        
        return insights
    
    def _build_hypotheses(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build hypotheses from business model seeds."""
        hypotheses = []
        
        bm_seeds = context_data.get("BusinessModelSeeds", {})
        
        if bm_seeds.get("revenue_model"):
            hypotheses.append({
                "id": "hyp-revenue",
                "category": "revenue",
                "statement": f"Customers will pay through: {bm_seeds['revenue_model']}",
                "status": "to_validate"
            })
        
        if bm_seeds.get("pricing_hypothesis"):
            hypotheses.append({
                "id": "hyp-pricing",
                "category": "pricing",
                "statement": bm_seeds["pricing_hypothesis"],
                "status": "to_validate"
            })
        
        # Add differentiation hypotheses
        for i, diff in enumerate(context_data.get("Differentiation", [])[:2]):
            hypotheses.append({
                "id": f"hyp-diff-{i+1}",
                "category": "differentiation",
                "statement": f"Our differentiation: {diff}",
                "status": "to_validate"
            })
        
        return hypotheses
    
    def _build_assumptions(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build assumptions from constraints and risks."""
        assumptions = []
        
        constraints = context_data.get("ConstraintsAndRisks", [])
        
        for i, constraint in enumerate(constraints[:5]):
            assumptions.append({
                "id": f"assumption-{i+1}",
                "statement": constraint,
                "category": "risk",
                "priority": "high" if i < 2 else "medium",
                "status": "to_validate"
            })
        
        return assumptions
    
    def _get_research_analysis(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get market research analysis from context."""
        analysis = []
        
        # Competition analysis
        competition = context_data.get("AlternativesAndCompetition", {})
        if competition:
            direct = competition.get("direct_competitors", [])
            indirect = competition.get("indirect_alternatives", [])
            
            if direct or indirect:
                analysis.append({
                    "type": "competitive_analysis",
                    "findings": {
                        "direct_competitors": direct,
                        "indirect_alternatives": indirect,
                        "differentiation": competition.get("differentiation_summary", "")
                    }
                })
        
        # Research body as analysis
        research = context_data.get("Research", {})
        if research.get("body"):
            analysis.append({
                "type": "market_research",
                "findings": {
                    "summary": research["body"],
                    "source_count": len(research.get("sources", []))
                }
            })
        
        return analysis
    
    def _calculate_completeness(self, context_data: Dict[str, Any]) -> float:
        """Calculate context completeness score."""
        scores = []
        
        # Core fields (weighted heavily)
        scores.append(1.0 if context_data.get("IdeaSummary") else 0.0)
        scores.append(1.0 if context_data.get("CustomerSegments") else 0.0)
        scores.append(1.0 if context_data.get("Problem", {}).get("what") else 0.0)
        scores.append(1.0 if context_data.get("SolutionOverview") else 0.0)
        
        # Supporting fields
        scores.append(0.5 if context_data.get("Differentiation") else 0.0)
        scores.append(0.5 if context_data.get("BusinessModelSeeds") else 0.0)
        scores.append(0.5 if context_data.get("Research", {}).get("sources") else 0.0)
        
        # Calculate weighted average (core fields = 60%, supporting = 40%)
        core_weight = 0.6
        support_weight = 0.4
        
        core_score = sum(scores[:4]) / 4
        support_score = sum(scores[4:]) / 3 if len(scores) > 4 else 0
        
        return (core_score * core_weight) + (support_score * support_weight)


def get_bootstrap_context_adapter() -> BootstrapContextAdapter:
    """Factory function for BootstrapContextAdapter."""
    return BootstrapContextAdapter()
