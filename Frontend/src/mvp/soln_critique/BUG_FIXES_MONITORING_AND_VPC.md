# Bug Fixes: AI Monitoring & VPC Context Loading

## Issues Fixed

### 1. ✅ AIUsageContext Validation Error
**Error**: All 6 critique agents were failing with:
```
1 validation error for AIUsageContext
feature_id
  Field required [type=missing, input_value={...}, input_type=dict]
```

**Root Cause**: The `AIUsageContext` model requires `feature_id` as a mandatory field, but the code was using the old parameter names (`feature_name`, `operation_name`).

**Solution**: Updated all AIUsageContext instantiations to use correct parameter names:

#### Files Modified:
1. **`agents/base_critique_agent.py`**
```python
# OLD (BROKEN):
monitoring_context = AIUsageContext(
    tenant_id=tenant_id,
    user_id=user_id,
    feature_name="solution_critique",  # ❌ Wrong parameter
    operation_name=f"{self.dimension}_critique",  # ❌ Wrong parameter
    project_id=project_id
)

# NEW (FIXED):
monitoring_context = AIUsageContext(
    tenant_id=tenant_id,
    user_id=user_id,
    feature_id="solution_critique",  # ✅ Correct
    workflow_name="solution_critique_workflow",  # ✅ Correct
    step_name=f"{self.dimension}_critique",  # ✅ Correct
    project_id=project_id
)
```

2. **`services/query_planner.py`**
```python
# Updated to use: feature_id, workflow_name, step_name
monitoring_context = AIUsageContext(
    tenant_id=tenant_id,
    user_id=user_id,
    feature_id="solution_critique",
    workflow_name="solution_critique_workflow",
    step_name="query_planning",
    project_id=project_id
)
```

3. **`agents/report_synthesizer_agent.py`**
```python
# Updated to use: feature_id, workflow_name, step_name
monitoring_context = AIUsageContext(
    tenant_id=tenant_id,
    user_id=user_id,
    feature_id="solution_critique",
    workflow_name="solution_critique_workflow",
    step_name="report_synthesis",
    project_id=project_id
)
```

---

### 2. ✅ VPC Context Loading - 400 Bad Request
**Error**: API returning 400 with:
```json
{
  "detail": {
    "success": false,
    "error": "missing_required_data",
    "message": "VPC not generated. Please complete VPC before running solution critique.",
    "details": {"missing": ["vpc"]}
  }
}
```

**Root Cause**: The solution critique context loader was using **stricter VPC validation** than VPS and BMC context loaders. It required `vpc_data.customer_profile` to exist at the root level, but VPC 2.0 stores data in different structures:
- `vpc_data.value_map_selections` (not `value_map`)
- VPC 2.0 can have flexible structures

**Solution**: Aligned VPC validation with VPS/BMC approach - flexible VPC 2.0 support.

#### Files Modified:
1. **`services/context_loader.py`**
```python
# OLD (BROKEN):
vpc_data = project_data.get('vpc_data', {})
if not vpc_data or not vpc_data.get('customer_profile'):
    return {}, "VPC not generated..."

# NEW (FIXED - Flexible VPC 2.0 validation):
vpc_data = project_data.get('vpc_data', {})

# Validate VPC - check for VPC 2.0 completion
# VPC 2.0 can have customer_profile at root or nested structure
has_customer_profile = (
    vpc_data.get('customer_profile') or 
    vpc_data.get('jobs_to_be_done') or 
    vpc_data.get('pains') or 
    vpc_data.get('gains') or
    len(vpc_data) > 0  # If vpc_data has any content, consider it valid
)

if not has_customer_profile:
    return {}, "VPC not generated..."

# Normalize VPC data structure for consistent access
normalized_vpc = {
    'customer_profile': vpc_data.get('customer_profile', {}),
    'value_map': vpc_data.get('value_map_selections') or vpc_data.get('value_map', {})
}

context = {
    # ... other fields
    'vpc_data': normalized_vpc,  # Use normalized structure
    # ...
}
```

2. **`api/endpoints.py`** (validation function)
```python
# OLD (BROKEN):
vpc_data = project_data.get('vpc_data', {})
if not vpc_data or not vpc_data.get('customer_profile'):
    return "VPC not generated..."

# NEW (FIXED - Same flexible validation):
vpc_data = project_data.get('vpc_data', {})
has_customer_profile = (
    vpc_data.get('customer_profile') or 
    vpc_data.get('jobs_to_be_done') or 
    vpc_data.get('pains') or 
    vpc_data.get('gains') or
    len(vpc_data) > 0
)
if not has_customer_profile:
    return "VPC not generated..."
```

---

### 3. ⚠️ LangGraph Concurrent Update Error (OBSERVED)
**Error**: 
```
At key 'project_id': Can receive only one value per step. 
Use an Annotated key to handle multiple values.
```

**Analysis**: This error occurs in LangGraph when multiple parallel nodes try to update the same state key with different values. 

**Current Status**: **Monitoring** - The error appeared in logs but may be a transient issue from the AIUsageContext failures. With those fixed, this may resolve itself. If it persists, the solution would be:

1. **Use Annotated reducer for shared keys**:
```python
from typing import Annotated
from operator import add

class SolutionCritiqueState(TypedDict):
    # For keys that multiple nodes might update
    errors: Annotated[List[str], add]  # Combines lists from all nodes
```

2. **Or ensure each parallel node only returns its own unique key**:
```python
async def _market_critique_node(self, state):
    critique = await self.market_agent.generate_critique(...)
    # Only return the key this node modifies
    return {'market_critique': critique}
```

**Action**: Test after applying fixes #1 and #2. If error persists, implement reducer pattern.

---

## Comparison: How VPS and BMC Load VPC Data

### VPS Context Loader (`utils/context_loader.py`)
```python
# Flexible VPC 2.0 validation
vpc_data = project.get('vpc_data', {})

has_customer_profile = (
    vpc_data.get('customer_profile') or 
    vpc_data.get('jobs_to_be_done') or 
    vpc_data.get('pains') or 
    vpc_data.get('gains') or
    len(vpc_data) > 0
)

# Normalizes value_map
context = {
    "customer_profile": vpc_data.get('customer_profile', {}),
    "value_map": vpc_data.get('value_map_selections') or vpc_data.get('value_map', {}),
}
```

### BMC Context Loader (`bmc/utils/bmc_context_loader.py`)
```python
# Uses VPS context loader (inherits flexible validation)
base_context = await self.mvp_context_loader.load_vps_context(
    project_id,
    tenant_id
)
# Adds VPS v1 on top
bmc_context = {
    **base_context,
    "vps_v1": vps_v1
}
```

### Solution Critique Context Loader (BEFORE FIX)
```python
# ❌ TOO STRICT - Required specific structure
vpc_data = project_data.get('vpc_data', {})
if not vpc_data or not vpc_data.get('customer_profile'):
    return {}, "VPC not generated..."
```

### Solution Critique Context Loader (AFTER FIX)
```python
# ✅ ALIGNED with VPS/BMC - Flexible validation
vpc_data = project_data.get('vpc_data', {})

has_customer_profile = (
    vpc_data.get('customer_profile') or 
    vpc_data.get('jobs_to_be_done') or 
    vpc_data.get('pains') or 
    vpc_data.get('gains') or
    len(vpc_data) > 0
)

normalized_vpc = {
    'customer_profile': vpc_data.get('customer_profile', {}),
    'value_map': vpc_data.get('value_map_selections') or vpc_data.get('value_map', {})
}
```

---

## Testing Checklist

- [x] AIUsageContext uses correct parameter names
- [x] VPC validation aligned with VPS/BMC approach
- [x] VPC data normalization handles `value_map_selections`
- [ ] Test complete workflow end-to-end
- [ ] Verify AI monitoring records correctly
- [ ] Confirm all 6 agents execute successfully
- [ ] Check LangGraph concurrent update error is resolved

---

## Summary

**Fixed Issues**:
1. ✅ **AIUsageContext validation** - Updated all 3 files to use `feature_id`, `workflow_name`, `step_name`
2. ✅ **VPC context loading** - Flexible VPC 2.0 validation matching VPS/BMC approach

**Monitoring**:
3. ⚠️ **LangGraph concurrent updates** - May be resolved by fixes #1-2, monitor during testing

**Impact**: Solution critique workflow should now successfully:
- Load VPC v2 data correctly
- Track AI usage properly in monitoring system
- Execute all 6 parallel critique agents
- Generate complete critique reports
