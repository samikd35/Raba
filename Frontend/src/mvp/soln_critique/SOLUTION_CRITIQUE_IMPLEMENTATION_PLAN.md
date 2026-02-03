# Solution Critique - Step-by-Step Implementation Plan

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Foundation Setup](#phase-1-foundation-setup)
3. [Phase 2: Core Services](#phase-2-core-services)
4. [Phase 3: Critique Agents](#phase-3-critique-agents)
5. [Phase 4: Workflow Orchestration](#phase-4-workflow-orchestration)
6. [Phase 5: API Layer](#phase-5-api-layer)
7. [Phase 6: Testing & Validation](#phase-6-testing--validation)
8. [Implementation Checklist](#implementation-checklist)

---

## Prerequisites

### Required Knowledge
- ✅ LangGraph workflow patterns (see market_research implementation)
- ✅ Azure OpenAI GPT-4.1 integration
- ✅ Brave Search API usage
- ✅ FastAPI async endpoint patterns
- ✅ PostgreSQL JSONB operations

### Required Environment Variables
```bash
# Azure OpenAI (already configured)
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=...

# Brave Search (already configured)
BRAVE_API_KEY=...

# Database (already configured)
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

### Database Migration
```sql
-- Execute this migration first
ALTER TABLE vmp_projects 
ADD COLUMN IF NOT EXISTS soln_critique_data JSONB DEFAULT NULL;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_vmp_projects_soln_critique 
ON vmp_projects USING gin (soln_critique_data);
```

---

## Phase 1: Foundation Setup

### Task 1.1: Create Folder Structure
**Estimated Time:** 10 minutes

Create the following structure:
```
/Backend/src/mvp/soln_critique/
├── __init__.py
├── agents/
│   ├── __init__.py
│   ├── base_critique_agent.py
│   ├── market_viability_agent.py
│   ├── operational_feasibility_agent.py
│   ├── business_model_agent.py
│   ├── competitive_differentiation_agent.py
│   ├── technical_scalability_agent.py
│   └── report_synthesizer_agent.py
├── services/
│   ├── __init__.py
│   ├── critique_workflow.py
│   ├── context_loader.py
│   ├── query_planner.py
│   └── web_researcher.py
├── models/
│   ├── __init__.py
│   ├── state_models.py
│   └── response_models.py
├── prompts/
│   ├── __init__.py
│   ├── query_planning_prompt.py
│   ├── market_viability_prompt.py
│   ├── operational_feasibility_prompt.py
│   ├── business_model_prompt.py
│   ├── competitive_differentiation_prompt.py
│   ├── technical_scalability_prompt.py
│   └── synthesizer_prompt.py
└── api/
    ├── __init__.py
    └── endpoints.py
```

**Commands:**
```bash
cd /Users/samikd/MyProjects/Yuba/Backend/src/mvp/soln_critique
mkdir -p agents services models prompts api
touch __init__.py agents/__init__.py services/__init__.py models/__init__.py prompts/__init__.py api/__init__.py
```

---

### Task 1.2: Create State Models
**Estimated Time:** 30 minutes
**File:** `models/state_models.py`

```python
"""
State models for Solution Critique workflow
"""
from typing import Dict, Any, List, Optional, TypedDict


class SolutionCritiqueState(TypedDict):
    """LangGraph state for solution critique workflow"""
    
    # Project context
    project_id: str
    tenant_id: str
    user_id: str
    session_id: str
    geography: str
    industry: str
    solution_description: str
    
    # Input data (snapshots)
    vpc_data: Dict[str, Any]
    vps_data: Dict[str, Any]
    bmc_data: Dict[str, Any]
    
    # Research phase
    research_queries: List[Dict[str, Any]]
    search_results: Dict[str, List[Dict[str, Any]]]
    
    # Critique results (parallel)
    market_critique: Optional[Dict[str, Any]]
    operational_critique: Optional[Dict[str, Any]]
    business_model_critique: Optional[Dict[str, Any]]
    competitive_critique: Optional[Dict[str, Any]]
    technical_critique: Optional[Dict[str, Any]]
    
    # Final output
    all_critiques: List[Dict[str, Any]]
    final_report: Optional[Dict[str, Any]]
    
    # Metadata
    status: str
    completed_at: Optional[str]
    error: Optional[str]


class CritiqueResult(TypedDict):
    """Individual critique result structure"""
    critique_id: str
    dimension: str
    title: str
    severity: str  # high | medium | low
    problem: str
    evidence: List[Dict[str, Any]]
    impact: str
    suggestions: List[Dict[str, Any]]
    confidence: float


class SearchQuery(TypedDict):
    """Web search query structure"""
    id: str
    category: str
    query: str
    priority: str  # high | medium | low
    rationale: str
```

**Testing:**
```python
# Add to models/__init__.py
from .state_models import (
    SolutionCritiqueState,
    CritiqueResult,
    SearchQuery
)

__all__ = [
    'SolutionCritiqueState',
    'CritiqueResult',
    'SearchQuery'
]
```

---

### Task 1.3: Create Response Models
**Estimated Time:** 20 minutes
**File:** `models/response_models.py`

```python
"""
Pydantic models for API responses
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class CritiqueGenerateRequest(BaseModel):
    """Request to generate solution critique"""
    force_regenerate: bool = Field(
        default=False,
        description="Force regeneration even if critique exists"
    )


class CritiqueGenerateResponse(BaseModel):
    """Response for critique generation request"""
    success: bool
    session_id: str
    status: str
    message: str
    estimated_completion_seconds: int = Field(default=60)


class CritiqueStatusResponse(BaseModel):
    """Response for critique status check"""
    success: bool
    status: str  # processing | completed | failed
    session_id: str
    started_at: Optional[str]
    completed_at: Optional[str]
    progress: Optional[Dict[str, Any]]
    error: Optional[str]


class CritiqueResultsResponse(BaseModel):
    """Response for critique results"""
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]
```

**Testing:**
```python
# Add to models/__init__.py
from .response_models import (
    CritiqueGenerateRequest,
    CritiqueGenerateResponse,
    CritiqueStatusResponse,
    CritiqueResultsResponse
)
```

---

## Phase 2: Core Services

### Task 2.1: Create Context Loader Service
**Estimated Time:** 45 minutes
**File:** `services/context_loader.py`

**Purpose:** Load VPC, VPS, and BMC data from project

```python
"""
Context loader for solution critique
Loads VPC v2, VPS, and BMC data from vmp_projects
"""
import logging
from typing import Dict, Any, Optional, Tuple
from src.mvp.adapters.database_adapter import MVPDatabaseAdapter

logger = logging.getLogger(__name__)


class ContextLoader:
    """Loads project context for solution critique"""
    
    def __init__(self):
        self.db_adapter = MVPDatabaseAdapter(use_service_role=True)
    
    async def load_project_context(
        self,
        project_id: str,
        tenant_id: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Load all required context for solution critique
        
        Returns:
            (context_dict, error_message)
        """
        try:
            # Load project data
            project_data = await self.db_adapter.get_project(project_id, tenant_id)
            if not project_data:
                return {}, "Project not found"
            
            # Load MVP data
            mvp_data = await self.db_adapter.get_mvp_data(project_id, tenant_id)
            if not mvp_data:
                return {}, "MVP data not found"
            
            # Extract VPS (prefer v2, fallback to v1)
            vps_data = mvp_data.get('vps_v2')
            if not vps_data:
                vps_data = mvp_data.get('vps_v1')
            
            if not vps_data:
                return {}, "VPS not generated. Please generate VPS first."
            
            # Extract BMC
            bmc_data = mvp_data.get('bmc')
            if not bmc_data:
                return {}, "BMC not generated. Please complete BMC first."
            
            # Load VPC data
            vpc_data = project_data.get('vpc_data', {})
            if not vpc_data or not vpc_data.get('customer_profile'):
                return {}, "VPC not generated. Please complete VPC first."
            
            # Extract metadata
            geography = self._extract_geography(vps_data, bmc_data)
            industry = self._extract_industry(vps_data, bmc_data)
            solution_description = self._extract_solution_description(vps_data)
            
            context = {
                'project_id': project_id,
                'tenant_id': tenant_id,
                'geography': geography,
                'industry': industry,
                'solution_description': solution_description,
                'vpc_data': vpc_data,
                'vps_data': vps_data,
                'bmc_data': bmc_data,
                'status': 'context_loaded'
            }
            
            logger.info(f"✅ Context loaded for project {project_id}")
            return context, None
            
        except Exception as e:
            logger.error(f"❌ Failed to load context: {e}")
            return {}, f"Failed to load context: {str(e)}"
    
    def _extract_geography(self, vps_data: Dict, bmc_data: Dict) -> str:
        """Extract geography from VPS or BMC"""
        # Try VPS metadata
        if 'metadata' in vps_data and 'geography' in vps_data['metadata']:
            return vps_data['metadata']['geography']
        
        # Try BMC customer segments
        customer_segments = bmc_data.get('customer_segments', [])
        for segment in customer_segments:
            if 'geography' in segment:
                return segment['geography']
        
        return "Not specified"
    
    def _extract_industry(self, vps_data: Dict, bmc_data: Dict) -> str:
        """Extract industry from VPS or BMC"""
        # Try VPS metadata
        if 'metadata' in vps_data and 'industry' in vps_data['metadata']:
            return vps_data['metadata']['industry']
        
        # Try VPS statement analysis
        statement = vps_data.get('statement', '')
        # Simple heuristic: look for industry keywords
        # This can be improved with AI extraction
        
        return "Not specified"
    
    def _extract_solution_description(self, vps_data: Dict) -> str:
        """Extract solution description from VPS"""
        return vps_data.get('statement', 'No solution description available')
```

**Testing:**
```python
# Test script
async def test_context_loader():
    loader = ContextLoader()
    context, error = await loader.load_project_context(
        project_id="test-project-id",
        tenant_id="test-tenant-id"
    )
    assert error is None
    assert 'vpc_data' in context
    assert 'vps_data' in context
    assert 'bmc_data' in context
```

---

### Task 2.2: Create Query Planner Service
**Estimated Time:** 1 hour
**File:** `services/query_planner.py`

```python
"""
Query planner for web research
Generates targeted search queries using GPT-4.1
"""
import logging
import json
from typing import Dict, Any, List
from datetime import datetime

from src.market_research.utils.ai_service_wrapper import get_ai_service_wrapper
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class QueryPlanner:
    """Plans web research queries using AI"""
    
    def __init__(self):
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
        
        Returns list of query objects
        """
        try:
            logger.info(f"🔍 Planning research queries for project {project_id}")
            
            # Create monitoring context
            monitoring_context = AIUsageContext(
                tenant_id=tenant_id,
                user_id=user_id,
                feature_name="solution_critique",
                operation_name="query_planning",
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
            response = await self.ai_service.generate_analysis_response(
                messages=messages,
                model="gpt-4",
                temperature=0.3,
                max_tokens=2000,
                json_mode=True,
                monitoring_context=monitoring_context
            )
            
            # Parse response
            queries_data = json.loads(response['content'])
            queries = queries_data.get('queries', [])
            
            logger.info(f"✅ Generated {len(queries)} research queries")
            return queries
            
        except Exception as e:
            logger.error(f"❌ Query planning failed: {e}")
            return self._get_fallback_queries(context)
    
    def _build_system_prompt(self) -> str:
        """System prompt for query planning"""
        return """You are a research query planner for solution critique analysis.

Your task is to generate 15-20 targeted web search queries to validate a proposed business solution.

Generate queries in these categories:
1. Market Research (3-4 queries) - market size, demand, customer behavior
2. Regulatory & Compliance (3-4 queries) - regulations, licensing, compliance
3. Competition (3-4 queries) - competitors, alternatives, market leaders
4. Operational/Logistics (2-3 queries) - supply chain, infrastructure, resources
5. Technology/Innovation (2-3 queries) - tech trends, platform best practices

Requirements:
- Queries must be specific and include geography when relevant
- Prioritize queries (high/medium/low)
- Include rationale for each query
- Keep queries concise (< 100 characters)

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
"""
    
    def _build_user_prompt(self, context: Dict[str, Any]) -> str:
        """User prompt with solution context"""
        geography = context.get('geography', 'Not specified')
        industry = context.get('industry', 'Not specified')
        solution = context.get('solution_description', '')
        
        bmc = context.get('bmc_data', {})
        customer_segments = bmc.get('customer_segments', [])
        value_props = bmc.get('value_propositions', [])
        
        return f"""Generate research queries for this solution:

**Geography:** {geography}
**Industry:** {industry}

**Solution Description:**
{solution}

**Target Customers:**
{json.dumps(customer_segments, indent=2)}

**Value Propositions:**
{json.dumps(value_props, indent=2)}

Generate 15-20 targeted search queries to validate this solution's viability.
Focus on evidence that could confirm or challenge key assumptions.
"""
    
    def _get_fallback_queries(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback queries if AI generation fails"""
        geography = context.get('geography', 'region')
        industry = context.get('industry', 'industry')
        
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
                "category": "regulatory",
                "query": f"{geography} {industry} regulations",
                "priority": "high",
                "rationale": "Regulatory compliance check"
            },
            {
                "id": "query-003",
                "category": "competition",
                "query": f"{industry} competitors {geography}",
                "priority": "high",
                "rationale": "Competitive landscape"
            }
        ]
```

Continued in next message due to length...
