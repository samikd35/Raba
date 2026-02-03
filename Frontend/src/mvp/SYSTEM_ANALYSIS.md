# System Architecture Analysis for Module 3 Implementation

## 🔍 Comprehensive System Understanding

### 1. Database Architecture

#### Primary Table: `vmp_projects`
```sql
CREATE TABLE public.vmp_projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid NOT NULL REFERENCES user_profiles(id),
  name text NOT NULL,
  description text,
  pv_report_id uuid NOT NULL REFERENCES documents(id),
  status text DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived', 'deleted')),
  current_step text DEFAULT 'persona_identification',
  
  -- JSONB Data Columns (Our Pattern)
  vpc_data jsonb DEFAULT '{}'::jsonb,           -- VPC 2.0 data
  field_prep_data jsonb DEFAULT '{}'::jsonb,    -- Hypotheses, assumptions
  analysis_data jsonb DEFAULT '{}'::jsonb,      -- Market research results
  mvp_data jsonb DEFAULT '{}'::jsonb,           -- ⭐ ADD THIS for Module 3
  
  -- Other fields
  personas jsonb DEFAULT '[]'::jsonb,
  research_documents_data jsonb DEFAULT '{}'::jsonb,
  settings jsonb DEFAULT '{}'::jsonb,
  vpc_v2_data jsonb DEFAULT '{}'::jsonb,
  refined_problem_statement text,
  vpc_image_url text,
  analysis_status varchar DEFAULT 'not_started',
  
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  parent_project_id uuid REFERENCES projects(id)
);

-- Index for JSONB queries
CREATE INDEX idx_vmp_projects_mvp_data ON vmp_projects USING gin(mvp_data);
```

#### Key Insights:
- **Pattern**: All feature data stored in JSONB columns
- **Tenant Isolation**: Every query MUST filter by `tenant_id`
- **User Tracking**: `user_id` for audit, but projects shared within tenant
- **JSONB Benefits**: Flexible schema, efficient queries with GIN index

### 2. Existing Services Architecture

#### A. Database Adapter (`/src/vpm/adapters/database_adapter.py`)

**Class**: `YubaDatabaseAdapter`

**Key Methods We'll Extend**:
```python
class YubaDatabaseAdapter:
    def __init__(self, use_service_role: bool = False):
        self.supabase = get_service_role_client() if use_service_role else get_supabase_client()
        self.vector_service = VectorStorageService()
    
    # Existing methods we'll mirror:
    async def get_project_detail(project_id, tenant_id)
    async def save_customer_profile_selections(project_id, tenant_id, selections)
    async def save_final_vpc(project_id, tenant_id, vpc_data)
    
    # NEW methods we'll add:
    async def get_mvp_data(project_id, tenant_id)
    async def save_vps_v1(project_id, tenant_id, vps_data)
    async def save_bmc_v1(project_id, tenant_id, bmc_data)
    async def save_critique(project_id, tenant_id, critique_data)
    async def update_mvp_component(project_id, tenant_id, component, data)
```

**Pattern to Follow**:
```python
# 1. Query with tenant isolation
response = self.supabase.client.table('vmp_projects').select(
    'id, mvp_data, vpc_data, personas'
).eq('id', project_id).eq('tenant_id', tenant_id).execute()

# 2. Check results
if not response.data:
    return None

# 3. Process and return
return response.data[0]
```

#### B. AI Service (`/src/mint/api/ai/providers.py`)

**Class**: `OpenAIProvider`

**Usage Pattern**:
```python
from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig

# Initialize
config = LLMConfig(
    provider_name="openai",
    model_name="gpt-4o",  # or "gpt-4o-mini" for faster/cheaper
    temperature=0.7,
    max_tokens=2000
)
provider = OpenAIProvider(config)

# Generate with structured output
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
]

response_schema = {
    "type": "object",
    "properties": {
        "primary_statement": {"type": "string"},
        "extended_statement": {"type": "string"},
        "key_differentiators": {"type": "array"}
    },
    "required": ["primary_statement", "extended_statement", "key_differentiators"]
}

response = await provider.generate_chat(
    messages=messages,
    response_format={"type": "json_schema", "json_schema": {"schema": response_schema}}
)

# Parse response
result = json.loads(response.content)
```

**Key Features**:
- Azure OpenAI primary, OpenAI fallback
- Structured output with JSON schema
- Automatic retry with exponential backoff
- Token usage tracking
- Error handling built-in

#### C. Credit Service (`/src/mint/api/credit/service.py`)

**Class**: `CreditService`

**Super Admin Bypass Pattern** (from memories):
```python
from src.mint.api.credit.service import CreditService

credit_service = CreditService()

# 1. Detect super admin
user_roles = current_user.get("roles", [])
is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"

# 2. Check credits (bypass for super admin)
if not is_super_admin:
    has_credits = credit_service.has_sufficient_credits_for_feature(
        tenant_id=tenant_id,
        feature_id="vps_generation_v1",
        plan_type="standard"
    )
    if not has_credits:
        raise HTTPException(status_code=402, detail="insufficient_credits")
else:
    logger.info(f"Super admin {user_id} bypassing credit check")

# 3. Consume credits (bypass for super admin)
if not is_super_admin:
    credit_service.consume_feature(
        tenant_id=tenant_id,
        user_id=user_id,
        feature_id="vps_generation_v1",
        request_id=f"vps_{project_id}_{timestamp}",
        reason="VPS v1 generation",
        project_id=project_id
    )
```

**Credit Costs for Module 3**:
- VPS v1: 1 credit
- BMC v1: 3 credits
- Critique: 2 credits
- VPC 3.0: 2 credits
- VPS v2: 1 credit
- BMC v2: 3 credits

#### D. Vector Storage (`/src/vpm/adapters/vector_adapter.py`)

**Usage Pattern** (from persona identification):
```python
from ..adapters.vector_adapter import get_yuba_vector_adapter

vector_adapter = get_yuba_vector_adapter()

# Search PV report
pv_results = await vector_adapter.search(
    query="value proposition customer needs pain points",
    document_id=pv_report_id,
    tenant_id=tenant_id,
    top_k=10
)

# Search actionable insights
insights_results = await vector_adapter.search_insights(
    query="solution opportunity market fit",
    report_id=pv_report_id,
    tenant_id=tenant_id,
    top_k=5
)

# Format results
context = [
    {
        "content": r.get('content'),
        "relevance_score": r.get('score'),
        "source": "pv_report"
    }
    for r in pv_results
]
```

### 3. Workflow Integration Points

#### Current VPM Workflow (from memories):
```
1. PV Report → VMP Project Creation
2. Persona Identification (RAG-based)
3. Customer Profile Generation (RAG-based)
4. Customer Profile Selection (user selects 3 each)
5. Hypothesis Generation (1 per persona)
6. Assumptions Generation (2-3 per hypothesis)
7. Questionnaires Generation (5 per assumption)
8. Market Research Analysis
9. ⭐ VPC 2.0 Construction (post-research)
```

#### Module 3 Insertion Point:
```
... (steps 1-9 above)
10. ⭐ VPS v1 Generation (NEW - Module 3)
11. ⭐ BMC v1 Generation (NEW - Module 3)
12. ⭐ Solution Critique (NEW - Module 3)
13. ⭐ Optional Refinements (NEW - Module 3)
```

### 4. Authentication & Authorization

**Pattern** (from all endpoints):
```python
from src.mint.api.auth_v2.utils import get_current_user

@router.post("/projects/{project_id}/vps/v1/generate")
async def generate_vps_v1(
    project_id: str,
    request: VPSGenerationRequest,
    current_user: dict = Depends(get_current_user)  # ⭐ Required
):
    user_id = current_user["id"]
    tenant_id = current_user["tenant_id"]
    user_roles = current_user.get("roles", [])
    
    # Verify project access (tenant isolation)
    project = await db_adapter.get_project_detail(project_id, tenant_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # ... rest of logic
```

### 5. Error Handling Patterns

**From Existing Codebase**:
```python
import logging

logger = logging.getLogger(__name__)

try:
    # Operation
    result = await some_operation()
    logger.info(f"✅ Success: {operation_name}")
    return result
    
except HTTPException:
    # Re-raise HTTP exceptions
    raise
    
except Exception as e:
    # Log and convert to HTTP exception
    logger.error(f"❌ Error in {operation_name}: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to {operation_name}: {str(e)}"
    )
```

### 6. API Response Patterns

**Standard Response Model**:
```python
from pydantic import BaseModel
from typing import Dict, Any

class StandardResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    message: str

# Usage
return StandardResponse(
    success=True,
    data={"vps_v1": vps_data, "project_id": project_id},
    message="VPS v1 generated successfully"
)
```

### 7. Testing Patterns

**From Existing Tests**:
```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_generate_vps_v1():
    # Arrange
    mock_context = {
        "project_id": "test-id",
        "customer_profile": {...},
        "personas": [...]
    }
    
    # Act
    result = await vps_agent.generate_vps(mock_context)
    
    # Assert
    assert result["primary_statement"]
    assert len(result["key_differentiators"]) == 3
    assert result["generation_metadata"]["confidence_score"] > 0.5
```

## 🎯 Implementation Strategy

### Phase 1: Foundation (Day 1-2)
1. Run database migration
2. Extend `YubaDatabaseAdapter`
3. Test database operations

### Phase 2: Core Logic (Day 3-5)
1. Create `MVPContextLoader`
2. Create `VPSGenerationAgent`
3. Create `VPSService`
4. Test with real data

### Phase 3: API Layer (Day 6-7)
1. Create API endpoints
2. Integrate credit system
3. Add authentication
4. Test end-to-end

### Phase 4: Testing & Docs (Day 8-10)
1. Unit tests
2. Integration tests
3. API documentation
4. User guide

## 📚 Key Learnings from Memories

### Critical Patterns:
1. **Tenant Isolation**: ALWAYS filter by `tenant_id`
2. **Super Admin Bypass**: Check `roles[0] == "super_admin"`
3. **JSONB Updates**: Get → Modify → Save (not direct update)
4. **Vector Search**: Dual context (PV report + insights)
5. **Error Handling**: Try-except with logging
6. **Structured Output**: Use JSON schema for AI responses

### Common Pitfalls to Avoid:
1. ❌ Filtering by both `tenant_id` AND `user_id` (breaks collaboration)
2. ❌ Hardcoding values instead of using parameters
3. ❌ Not checking for super admin before credit operations
4. ❌ Using wrong status/stage locations in JSONB
5. ❌ Not handling empty/missing data gracefully

### Best Practices:
1. ✅ Use existing adapters and services
2. ✅ Follow established patterns
3. ✅ Add comprehensive logging
4. ✅ Test with real project data
5. ✅ Document all assumptions
6. ✅ Handle errors gracefully

## 🚀 Ready to Implement!

All necessary infrastructure exists. We just need to:
1. Add `mvp_data` column
2. Extend adapters with MVP methods
3. Create VPS agent with prompts
4. Build API endpoints
5. Test and deploy

**Next Step**: Start with database migration and adapter extension.
