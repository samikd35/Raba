# Module 3 VPS Implementation Roadmap

## 🎯 Overview
Implementation guide for VPS (Value Proposition Statement) Generator - First feature of Module 3 MVP Development Suite.

## 📊 System Architecture Understanding

### Existing Infrastructure to Leverage

1. **Database**: `vmp_projects` table with JSONB columns pattern
2. **AI Service**: `OpenAIProvider` with Azure OpenAI + fallback
3. **Credit System**: `CreditService` with super admin bypass
4. **Vector Storage**: RAG via `VectorStorageService`
5. **Auth**: `get_current_user` dependency
6. **Adapters**: `YubaDatabaseAdapter`, `VectorAdapter`

### Key Patterns Identified

```python
# Super Admin Bypass Pattern (from memories)
user_roles = current_user.get("roles", [])
is_super_admin = len(user_roles) > 0 and user_roles[0] == "super_admin"

if not is_super_admin:
    # Check and consume credits
else:
    logger.info(f"Super admin bypassing credit check")

# Database JSONB Pattern
# vpc_data, field_prep_data, analysis_data → mvp_data (same pattern)

# AI Service Pattern
from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig

config = LLMConfig(model_name="gpt-4o", temperature=0.7)
provider = OpenAIProvider(config)
response = await provider.generate_chat(messages, response_format)

# Vector Search Pattern (from persona identification)
results = await vector_adapter.search(
    query=query,
    document_id=report_id,
    tenant_id=tenant_id,
    top_k=10
)
```

## 🗂️ File Structure

```
/Backend/src/mvp/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── endpoints.py          # FastAPI routes
│   └── models.py             # Pydantic models
├── services/
│   ├── __init__.py
│   └── vps_service.py        # Business logic
├── agents/
│   ├── __init__.py
│   └── vps_agent.py          # AI agent
├── prompts/
│   ├── __init__.py
│   └── vps_prompts.py        # Prompt templates
├── utils/
│   ├── __init__.py
│   ├── context_loader.py     # Load VPC/PV data
│   └── validation.py         # Data validation
└── docs/
    ├── MODULE_3_MVP_DEVELOPMENT_PLAN.md (exists)
    ├── vpc.md (exists)
    └── IMPLEMENTATION_ROADMAP.md (this file)
```

## 📋 Implementation Checklist

### Week 1: Foundation & VPS

#### Day 1-2: Database & Adapters
- [ ] Run database migration (add `mvp_data` column)
- [ ] Extend `YubaDatabaseAdapter` with MVP methods:
  - `get_mvp_data(project_id, tenant_id)`
  - `save_vps_v1(project_id, tenant_id, vps_data)`
  - `update_mvp_component(project_id, tenant_id, path, data)`
- [ ] Test database operations

#### Day 3: Context Loader
- [ ] Create `MVPContextLoader` class
- [ ] Implement `load_vps_context()` method
- [ ] Implement vector search for PV report + insights
- [ ] Implement `format_context_for_prompt()` method
- [ ] Test with real project data

#### Day 4: VPS Agent
- [ ] Create `VPSGenerationAgent` class
- [ ] Design prompt templates (system + user)
- [ ] Implement `generate_vps()` method
- [ ] Add structured output schema
- [ ] Test with sample context

#### Day 5: Service Layer
- [ ] Create `VPSService` class
- [ ] Implement orchestration logic
- [ ] Add validation and error handling
- [ ] Test end-to-end generation

### Week 2: API & Integration

#### Day 1: API Endpoints
- [ ] Create FastAPI router
- [ ] Implement POST `/projects/{id}/vps/v1/generate`
- [ ] Implement GET `/projects/{id}/vps/v1`
- [ ] Implement PUT `/projects/{id}/vps/v1`
- [ ] Add credit checks with super admin bypass

#### Day 2: Testing & Documentation
- [ ] Unit tests for agent
- [ ] Integration tests for API
- [ ] Test with real VPM projects
- [ ] API documentation
- [ ] User guide

## 🔧 Key Implementation Details

### Database Migration

```sql
ALTER TABLE vmp_projects 
ADD COLUMN IF NOT EXISTS mvp_data JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_vmp_projects_mvp_data 
ON vmp_projects USING gin(mvp_data);
```

### MVP Data Structure

```json
{
  "vps_v1": {
    "primary_statement": "...",
    "extended_statement": "...",
    "key_differentiators": [...],
    "generation_metadata": {...}
  },
  "current_version": {"vps": "v1"}
}
```

### API Endpoints

```
POST   /api/v2/mvp/projects/{project_id}/vps/v1/generate
GET    /api/v2/mvp/projects/{project_id}/vps/v1
PUT    /api/v2/mvp/projects/{project_id}/vps/v1
```

### Credit Cost

- **VPS v1 Generation**: 1 credit
- **Super Admin**: Bypassed
- **Feature ID**: `vps_generation_v1`

## 🔗 Integration Points

### With VPM Module
- Uses same `vmp_projects` table
- Requires completed VPC 2.0 data
- Requires identified personas
- Uses same vector storage for RAG

### With Credit System
- Checks credits before generation
- Consumes 1 credit on success
- Bypasses for super admins
- Idempotent consumption

### With AI Service
- Uses `OpenAIProvider` (Azure + fallback)
- Model: `gpt-4o` (primary) or `gpt-4o-mini` (fallback)
- Temperature: 0.7 (balanced creativity)
- Structured output with JSON schema

## 📚 Reference Files

### Study These Files First
1. `/src/vpm/adapters/database_adapter.py` - Database patterns
2. `/src/vpm/services/field_prep_service.py` - Service orchestration
3. `/src/vpm/api/endpoints.py` - API endpoint patterns
4. `/src/mint/api/credit/service.py` - Credit system
5. `/src/mint/api/ai/providers.py` - AI service usage
6. `/src/market_research/utils/ai_service_wrapper.py` - AI wrapper

### Key Patterns to Follow
- **Tenant isolation**: Always filter by `tenant_id`
- **User ownership**: Check `user_id` for modifications
- **Error handling**: Try-except with logging
- **Super admin bypass**: Check `roles[0] == "super_admin"`
- **JSONB updates**: Get → Modify → Save pattern
- **Vector search**: Use dual context (PV + insights)

## 🚀 Next Steps After VPS

Once VPS is complete and tested:
1. BMC (Business Model Canvas) - 9 agents
2. Solution Critique - 6-dimensional analysis
3. Refinement features (VPC 3.0, VPS v2, BMC v2)

## ✅ Definition of Done

VPS feature is complete when:
- [ ] Database migration successful
- [ ] All adapter methods working
- [ ] Context loader tested with real data
- [ ] VPS agent generates quality output
- [ ] All 3 API endpoints functional
- [ ] Credit system integrated correctly
- [ ] Super admin bypass working
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] Tested with 3+ real VPM projects

## 📞 Support Resources

- **Database Schema**: `/Backend/docs/tables.sql`
- **VPM Workflow**: Memories show complete flow
- **Credit System**: Memory shows super admin pattern
- **AI Service**: Multiple examples in codebase
- **Vector Search**: Used in persona identification

---

**Ready to start implementation!** 🎉
