# MVP Module Architecture

## Design Principles

### Separation of Concerns
- **MVP Adapter**: Handles MVP-specific data (vps_v1, vps_v2, bmc_v1, bmc_v2, critique)
- **VPM Adapter**: Handles VPM data (vpc_data, personas, field_prep_data) - used for reading context
- **Clear Boundaries**: Each module owns its data domain

### Database Access Pattern

```python
# For MVP operations (write MVP data)
from src.mvp.adapters.database_adapter import get_mvp_database_adapter
mvp_adapter = get_mvp_database_adapter()
mvp_adapter.save_vps_v1(project_id, tenant_id, vps_data, user_id)

# For reading VPM context (read VPC, personas, field prep)
from src.vpm.adapters.database_adapter import get_yuba_database_adapter
vpm_adapter = get_yuba_database_adapter()
project = await vpm_adapter.get_project_detail(project_id, tenant_id)
```

## Module Structure

```
/Backend/src/mvp/
├── adapters/
│   ├── __init__.py
│   └── database_adapter.py      # MVP-specific DB operations
├── agents/
│   ├── __init__.py
│   └── vps_agent.py             # AI agent for VPS generation
├── api/
│   ├── __init__.py
│   ├── endpoints.py             # FastAPI routes
│   └── models.py                # Request/Response models
├── prompts/
│   ├── __init__.py
│   └── vps_prompts.py           # AI prompt templates
├── services/
│   ├── __init__.py
│   └── vps_service.py           # Business logic orchestration
├── utils/
│   ├── __init__.py
│   └── context_loader.py        # Context preparation for AI
└── migrations/
    └── 001_add_mvp_data_column.sql
```

## Data Flow

### VPS Generation Flow

```
1. API Endpoint receives request
   ↓
2. Service Layer validates and orchestrates
   ↓
3. Context Loader gathers data:
   - VPM Adapter → Get VPC, personas, field prep
   - Vector Adapter → Get PV report insights (RAG)
   ↓
4. VPS Agent generates statement (AI)
   ↓
5. MVP Adapter saves result
   ↓
6. Response returned to client
```

### Adapter Responsibilities

**MVP Database Adapter** (`/src/mvp/adapters/database_adapter.py`):
- ✅ Read/Write `mvp_data` column
- ✅ VPS v1/v2 operations
- ✅ BMC v1/v2 operations (future)
- ✅ Critique operations (future)
- ✅ Version tracking
- ✅ Component-level updates

**VPM Database Adapter** (`/src/vpm/adapters/database_adapter.py`):
- ✅ Read `vpc_data`, `personas`, `field_prep_data`
- ✅ Project detail retrieval
- ✅ PV report access
- ❌ Does NOT touch `mvp_data` (MVP's responsibility)

## Benefits of This Architecture

1. **Maintainability**: Clear ownership of data domains
2. **Testability**: Each adapter can be tested independently
3. **Scalability**: Easy to add new MVP features without touching VPM
4. **Separation**: MVP module is self-contained
5. **Reusability**: VPM adapter remains clean for VPM operations

## Database Schema

### mvp_data Structure
```json
{
  "vps_v1": {
    "primary_statement": "...",
    "extended_statement": "...",
    "key_differentiators": [...],
    "generation_metadata": {
      "generated_at": "...",
      "generated_by": "user_id",
      "model_used": "gpt-4o-mini",
      "confidence_score": 0.85
    }
  },
  "vps_v2": { /* same structure */ },
  "bmc_v1": { /* future */ },
  "bmc_v2": { /* future */ },
  "critique": { /* future */ },
  "vpc_v3": { /* future */ },
  "current_version": {
    "vps": "v1",
    "vps_updated_at": "...",
    "bmc": "v1",
    "bmc_updated_at": "..."
  }
}
```

## Integration Points

### With VPM Module
- **Read Only**: Context loader reads VPC, personas, field prep
- **No Writes**: MVP never modifies VPM data
- **Clean Interface**: Uses VPM's public adapter methods

### With Credit System
- **Feature IDs**: `vps_generation_v1`, `vps_generation_v2`, etc.
- **Super Admin Bypass**: Implemented in service layer
- **Consumption Tracking**: Per-feature credit tracking

### With AI Service
- **Provider**: OpenAI (Azure + fallback)
- **Models**: gpt-4o-mini (default), gpt-4o (optional)
- **Structured Output**: JSON schema for consistency

## Future Extensions

### Adding BMC Feature
1. Create `bmc_agent.py` with 9 specialized agents
2. Add BMC methods to MVP adapter
3. Create BMC service and endpoints
4. No changes needed to VPM adapter

### Adding Critique Feature
1. Create `critique_agent.py`
2. Add critique methods to MVP adapter
3. Create critique service and endpoints
4. No changes needed to VPM adapter

This architecture makes adding new features straightforward and maintainable!
