"""
Query planner for web research
Generates targeted search queries using Azure OpenAI gpt-5-mini
"""
import logging
import json
from typing import Dict, Any, List
from datetime import datetime

from src.market_research.utils.ai_service_wrapper import get_ai_service_wrapper
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class QueryPlanner:
    """Plans web research queries using Azure OpenAI gpt-5-mini"""
    
    def __init__(self):
        # AI service configured for ModelUseCase.REPORT_GENERATION (Azure gpt-5-mini)
        self.ai_service = get_ai_service_wrapper()
    
    async def plan_research_queries(
        self,
        context: Dict[str, Any],
        tenant_id: str,
        user_id: str,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Generate targeted search queries based on solution context
        
        Args:
            context: Project context with VPC, VPS, BMC data
            tenant_id: Tenant ID for monitoring
            user_id: User ID for monitoring
            project_id: Project ID for monitoring
            
        Returns:
            List of query objects with category, query text, priority, and rationale
        """
        try:
            logger.info(f"🔍 Planning research queries for project {project_id}")
            
            # Create monitoring context
            monitoring_context = AIUsageContext(
                tenant_id=tenant_id,
                user_id=user_id,
                feature_id="solution_critique",
                workflow_name="solution_critique_workflow",
                step_name="query_planning",
                project_id=project_id
            )
            
            # Build prompt
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(context)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Generate queries
            logger.info("🤖 Generating search queries with Azure GPT-4.1 (gpt41 deployment)...")
            response = await self.ai_service.generate_analysis_response(
                messages=messages,
                temperature=0.3,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                json_mode=True,
                monitoring_context=monitoring_context
            )
            
            # Parse response
            queries_data = json.loads(response['content'])
            queries = queries_data.get('queries', [])
            
            logger.info(f"✅ Generated {len(queries)} research queries")
            
            # Log query breakdown by category
            categories = {}
            for query in queries:
                cat = query.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            logger.info(f"   Query breakdown: {categories}")
            
            return queries
            
        except Exception as e:
            logger.error(f"❌ Query planning failed: {e}")
            logger.warning("   Falling back to default queries...")
            return self._get_fallback_queries(context)
    
    def _build_system_prompt(self) -> str:
        """System prompt for query planning"""
        return """You are a research query planner for solution critique analysis.

Your task is to generate 15-20 targeted web search queries to validate a proposed business solution.

Generate queries in these categories:
1. **Market Research** (3-4 queries) - market size, demand, customer behavior
2. **Regulatory & Compliance** (3-4 queries) - regulations, licensing, compliance
3. **Competition** (3-4 queries) - competitors, alternatives, market leaders
4. **Operational/Logistics** (2-3 queries) - supply chain, infrastructure, resources
5. **Technology/Innovation** (2-3 queries) - tech trends, platform best practices

Requirements:
- Queries must be specific and include geography when relevant
- Prioritize queries (high/medium/low) based on criticality
- Include rationale explaining why each query is important
- Keep queries concise (< 100 characters)
- Focus on finding evidence to validate or challenge key assumptions

Output JSON format:
{
  "queries": [
    {
      "id": "query-001",
      "category": "market",
      "query": "Rwanda pet food market size 2024",
      "priority": "high",
      "rationale": "Validate market demand assumption"
    }
  ]
}

Generate queries that will help identify:
- Unvalidated assumptions
- Regulatory barriers
- Competitive threats
- Operational challenges
- Market size realities
"""
    
    def _build_user_prompt(self, context: Dict[str, Any]) -> str:
        """User prompt with solution context"""
        geography = context.get('geography', 'Not specified')
        industry = context.get('industry', 'Not specified')
        solution = context.get('solution_description', '')
        
        bmc = context.get('bmc_data', {})
        customer_segments = bmc.get('customer_segments', [])
        value_props = bmc.get('value_propositions', [])
        key_activities = bmc.get('key_activities', [])
        
        return f"""Generate research queries for this solution:

**Geography:** {geography}
**Industry:** {industry}

**Solution Description:**
{solution}

**Target Customers:**
{json.dumps(customer_segments, indent=2) if customer_segments else 'Not specified'}

**Value Propositions:**
{json.dumps(value_props, indent=2) if value_props else 'Not specified'}

**Key Activities:**
{json.dumps(key_activities, indent=2) if key_activities else 'Not specified'}

Generate 15-20 targeted search queries to validate this solution's viability.
Focus on evidence that could confirm or challenge key assumptions.
Include geography-specific queries when relevant.
Prioritize queries that address critical business viability questions.
"""
    
    def _get_fallback_queries(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback queries if AI generation fails"""
        geography = context.get('geography', 'region')
        industry = context.get('industry', 'industry')
        
        logger.info(f"   Using fallback queries for {geography} {industry}")
        
        return [
            {
                "id": "query-001",
                "category": "market",
                "query": f"{geography} {industry} market size 2024",
                "priority": "high",
                "rationale": "Market size validation"
            },
            {
                "id": "query-002",
                "category": "market",
                "query": f"{industry} consumer trends {geography}",
                "priority": "high",
                "rationale": "Customer behavior validation"
            },
            {
                "id": "query-003",
                "category": "regulatory",
                "query": f"{geography} {industry} regulations",
                "priority": "high",
                "rationale": "Regulatory compliance check"
            },
            {
                "id": "query-004",
                "category": "regulatory",
                "query": f"{industry} licensing requirements {geography}",
                "priority": "medium",
                "rationale": "Operational legality"
            },
            {
                "id": "query-005",
                "category": "competition",
                "query": f"{industry} competitors {geography}",
                "priority": "high",
                "rationale": "Competitive landscape"
            },
            {
                "id": "query-006",
                "category": "competition",
                "query": f"{industry} market leaders {geography}",
                "priority": "medium",
                "rationale": "Incumbent analysis"
            },
            {
                "id": "query-007",
                "category": "operational",
                "query": f"{industry} supply chain {geography}",
                "priority": "medium",
                "rationale": "Operational feasibility"
            },
            {
                "id": "query-008",
                "category": "operational",
                "query": f"{geography} infrastructure challenges",
                "priority": "medium",
                "rationale": "Infrastructure assessment"
            },
            {
                "id": "query-009",
                "category": "technology",
                "query": f"{industry} technology trends 2024",
                "priority": "low",
                "rationale": "Technology landscape"
            },
            {
                "id": "query-010",
                "category": "technology",
                "query": f"{industry} digital transformation {geography}",
                "priority": "low",
                "rationale": "Tech adoption patterns"
            }
        ]
