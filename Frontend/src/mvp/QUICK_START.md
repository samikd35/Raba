# Module 3 VPS - Quick Start Guide

## 🚀 Start Here

This guide gets you started implementing the VPS (Value Proposition Statement) Generator.

## 📋 Prerequisites Checklist

Before starting, verify:
- [ ] You have access to the database
- [ ] You understand the `vmp_projects` table structure
- [ ] You've reviewed `/Backend/docs/tables.sql`
- [ ] You've read `SYSTEM_ANALYSIS.md`
- [ ] You've read `IMPLEMENTATION_ROADMAP.md`

## 🎯 Step-by-Step Implementation

### Step 1: Database Migration (15 minutes)

**Run this SQL**:
```sql
-- Connect to your database first
-- Then run:

ALTER TABLE vmp_projects 
ADD COLUMN IF NOT EXISTS mvp_data JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_vmp_projects_mvp_data 
ON vmp_projects USING gin(mvp_data);

-- Verify
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'vmp_projects' AND column_name = 'mvp_data';
```

**Expected Output**:
```
column_name | data_type | column_default
mvp_data    | jsonb     | '{}'::jsonb
```

### Step 2: Extend Database Adapter (1-2 hours)

**File**: `/Users/samikd/MyProjects/Yuba/Backend/src/vpm/adapters/database_adapter.py`

**Add these methods to `YubaDatabaseAdapter` class**:

```python
def get_mvp_data(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get MVP data for a project."""
    try:
        response = self.supabase.client.table('vmp_projects').select(
            'mvp_data'
        ).eq('id', project_id).eq('tenant_id', tenant_id).execute()
        
        if not response.data:
            return None
        return response.data[0].get('mvp_data', {})
    except Exception as e:
        print(f"Error fetching MVP data: {e}")
        return None


def save_vps_v1(self, project_id: str, tenant_id: str, vps_data: Dict[str, Any]) -> bool:
    """Save VPS v1 data."""
    try:
        current_mvp_data = self.get_mvp_data(project_id, tenant_id) or {}
        current_mvp_data['vps_v1'] = vps_data
        current_mvp_data['current_version'] = current_mvp_data.get('current_version', {})
        current_mvp_data['current_version']['vps'] = 'v1'
        
        response = self.supabase.client.table('vmp_projects').update({
            'mvp_data': current_mvp_data,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', project_id).eq('tenant_id', tenant_id).execute()
        
        return len(response.data) > 0
    except Exception as e:
        print(f"Error saving VPS v1: {e}")
        return False
```

**Test it**:
```python
# In Python console or test file
from src.vpm.adapters.database_adapter import YubaDatabaseAdapter

adapter = YubaDatabaseAdapter(use_service_role=True)

# Test get (should return empty dict for new projects)
mvp_data = adapter.get_mvp_data("your-project-id", "your-tenant-id")
print(mvp_data)  # Should print: {}

# Test save
test_vps = {
    "primary_statement": "Test statement",
    "extended_statement": "Test extended",
    "key_differentiators": []
}
success = adapter.save_vps_v1("your-project-id", "your-tenant-id", test_vps)
print(f"Save successful: {success}")  # Should print: True

# Verify
mvp_data = adapter.get_mvp_data("your-project-id", "your-tenant-id")
print(mvp_data)  # Should show your test data
```

### Step 3: Create Directory Structure (5 minutes)

```bash
cd /Users/samikd/MyProjects/Yuba/Backend/src/mvp

# Create directories
mkdir -p api services agents prompts utils

# Create __init__.py files
touch __init__.py
touch api/__init__.py
touch services/__init__.py
touch agents/__init__.py
touch prompts/__init__.py
touch utils/__init__.py

# Verify structure
tree -L 2
```

**Expected Structure**:
```
mvp/
├── __init__.py
├── api/
│   └── __init__.py
├── services/
│   └── __init__.py
├── agents/
│   └── __init__.py
├── prompts/
│   └── __init__.py
├── utils/
│   └── __init__.py
└── docs/
    ├── MODULE_3_MVP_DEVELOPMENT_PLAN.md
    ├── SYSTEM_ANALYSIS.md
    ├── IMPLEMENTATION_ROADMAP.md
    └── QUICK_START.md (this file)
```

### Step 4: Create Context Loader (2-3 hours)

**File**: `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/utils/context_loader.py`

**Start with this skeleton**:
```python
"""Context Loader for MVP Module"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class MVPContextLoader:
    """Load context data for MVP generation."""
    
    def __init__(self, db_adapter, vector_adapter):
        self.db_adapter = db_adapter
        self.vector_adapter = vector_adapter
    
    async def load_vps_context(self, project_id: str, tenant_id: str) -> Dict[str, Any]:
        """Load all context needed for VPS generation."""
        # TODO: Implement
        # 1. Get project details
        # 2. Extract VPC data, personas, field prep
        # 3. Load PV report via vector search
        # 4. Load actionable insights
        # 5. Return structured context
        pass
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Format context for AI prompt."""
        # TODO: Implement
        # Format as markdown with sections
        pass
```

**Reference**: Look at `/src/vpm/services/field_prep_service.py` for similar context loading patterns.

### Step 5: Create VPS Agent (2-3 hours)

**File**: `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/agents/vps_agent.py`

**Start with this skeleton**:
```python
"""VPS Generation Agent"""

import logging
from typing import Dict, Any
from datetime import datetime
import json

from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig

logger = logging.getLogger(__name__)


class VPSGenerationAgent:
    """Agent for generating Value Proposition Statements."""
    
    def __init__(self, ai_provider: Optional[OpenAIProvider] = None):
        if ai_provider is None:
            config = LLMConfig(
                provider_name="openai",
                model_name="gpt-4o",
                temperature=0.7,
                max_tokens=2000
            )
            ai_provider = OpenAIProvider(config)
        self.ai_provider = ai_provider
    
    async def generate_vps(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate VPS from context."""
        # TODO: Implement
        # 1. Format context
        # 2. Prepare messages
        # 3. Call AI with structured output
        # 4. Parse and validate response
        # 5. Add metadata
        pass
```

### Step 6: Create Prompt Templates (1 hour)

**File**: `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/prompts/vps_prompts.py`

```python
"""Prompt Templates for VPS Generation"""

VPS_SYSTEM_PROMPT = """You are an expert business strategist...

[See IMPLEMENTATION_ROADMAP.md for full prompt]
"""

VPS_USER_PROMPT_TEMPLATE = """Generate a Value Proposition Statement...

{context}

[See IMPLEMENTATION_ROADMAP.md for full prompt]
"""
```

### Step 7: Create Service Layer (2 hours)

**File**: `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/services/vps_service.py`

```python
"""VPS Service - Orchestration Layer"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class VPSService:
    """Service for VPS generation orchestration."""
    
    def __init__(self):
        # Initialize dependencies
        pass
    
    async def generate_vps_v1(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """Generate VPS v1."""
        # TODO: Implement
        # 1. Load context
        # 2. Call agent
        # 3. Save to database
        # 4. Return result
        pass
```

### Step 8: Create API Endpoints (2-3 hours)

**File**: `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/api/endpoints.py`

```python
"""MVP Module API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any

from src.mint.api.auth_v2.utils import get_current_user
from src.mint.api.credit.service import CreditService

router = APIRouter(prefix="/api/v2/mvp", tags=["MVP"])
credit_service = CreditService()


class VPSGenerationRequest(BaseModel):
    creativity_level: float = Field(0.7, ge=0.0, le=1.0)


@router.post("/projects/{project_id}/vps/v1/generate")
async def generate_vps_v1(
    project_id: str,
    request: VPSGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate VPS v1."""
    # TODO: Implement
    # 1. Get user info
    # 2. Check super admin
    # 3. Check/consume credits
    # 4. Call service
    # 5. Return response
    pass
```

### Step 9: Register Router (5 minutes)

**File**: `/Users/samikd/MyProjects/Yuba/Backend/app.py`

```python
# Add import
from src.mvp.api.endpoints import router as mvp_router

# Add router
app.include_router(mvp_router)
```

### Step 10: Test End-to-End (1-2 hours)

**Manual Test**:
```bash
# 1. Start server
python app.py

# 2. Test endpoint
curl -X POST "http://localhost:8000/api/v2/mvp/projects/{project_id}/vps/v1/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"creativity_level": 0.7}'

# 3. Verify response
# Should return VPS data with primary_statement, extended_statement, key_differentiators
```

## 📚 Reference Materials

### Must Read First:
1. `SYSTEM_ANALYSIS.md` - Understand existing infrastructure
2. `IMPLEMENTATION_ROADMAP.md` - Detailed implementation plan
3. `/Backend/docs/tables.sql` - Database schema

### Code References:
1. `/src/vpm/adapters/database_adapter.py` - Database patterns
2. `/src/vpm/services/field_prep_service.py` - Service orchestration
3. `/src/vpm/api/endpoints.py` - API endpoint patterns
4. `/src/mint/api/ai/providers.py` - AI service usage

## 🐛 Troubleshooting

### Database Connection Issues
```python
# Test connection
from src.mint.api.system.core.supabase_client import get_supabase_client
client = get_supabase_client()
print(client.client.table('vmp_projects').select('id').limit(1).execute())
```

### AI Service Issues
```python
# Test AI provider
from src.mint.api.ai.providers import OpenAIProvider
provider = OpenAIProvider()
response = await provider.generate_chat([
    {"role": "user", "content": "Say hello"}
])
print(response.content)
```

### Credit Service Issues
```python
# Test credit check
from src.mint.api.credit.service import CreditService
service = CreditService()
has_credits = service.has_sufficient_credits_for_feature(
    tenant_id="your-tenant-id",
    feature_id="vps_generation_v1",
    plan_type="standard"
)
print(f"Has credits: {has_credits}")
```

## ✅ Completion Checklist

- [ ] Database migration successful
- [ ] Adapter methods working
- [ ] Directory structure created
- [ ] Context loader implemented
- [ ] VPS agent implemented
- [ ] Prompts created
- [ ] Service layer implemented
- [ ] API endpoints created
- [ ] Router registered
- [ ] End-to-end test passing

## 🎉 Next Steps

Once VPS is complete:
1. Review and refine based on testing
2. Add unit tests
3. Add integration tests
4. Document API
5. Move to BMC implementation

---

**Need Help?** Check `SYSTEM_ANALYSIS.md` for detailed patterns and examples.
