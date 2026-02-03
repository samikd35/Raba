# BMC Implementation Bug Fix

## Issue
```
Failed to generate BMC: No module named 'src.mint.api.system.core.ai_service'
```

## Root Cause
The BMC agent was using incorrect import paths and API methods that didn't match the existing Yuba codebase patterns.

## Fixes Applied

### 1. Fixed Import Paths
**Before:**
```python
from src.mint.api.system.core.ai_service import OpenAIProvider
```

**After:**
```python
from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig
```

### 2. Fixed Provider Initialization
**Before:**
```python
self.ai_provider = ai_provider or OpenAIProvider()
self.model = "gpt-4"
self.temperature = 0.7
self.max_tokens = 3000
```

**After:**
```python
if ai_provider is None:
    config = LLMConfig(
        provider_name="openai",
        model_name="gpt-4",
        temperature=0.7,
        max_tokens=3000
    )
    ai_provider = OpenAIProvider(config)

self.ai_provider = ai_provider
```

### 3. Fixed API Method Calls
**Before:**
```python
response = await self.ai_provider.chat_completion(
    messages=messages,
    model=self.model,
    temperature=self.temperature,
    max_tokens=self.max_tokens,
    response_format={...}
)
segments_data = json.loads(response.choices[0].message.content)
```

**After:**
```python
response = await self.ai_provider.generate_chat(
    messages=messages,
    response_format={...}
)
segments_data = json.loads(response.content)
```

### 4. Fixed Model Reference
**Before:**
```python
"model_used": self.model
```

**After:**
```python
"model_used": self.ai_provider.config.model_name
```

## Files Modified
- `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/bmc/agents/bmc_agent.py`
  - Fixed imports (lines 14-15)
  - Fixed initialization (lines 48-58)
  - Fixed all 9 generation methods (replaced `chat_completion` with `generate_chat`)
  - Fixed all response parsing (replaced `response.choices[0].message.content` with `response.content`)
  - Fixed all model references (replaced `self.model` with `self.ai_provider.config.model_name`)

## Pattern Matched
All changes now match the pattern used in `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/agents/vps_agent.py`

## Additional Fix - Vector Adapter Import

### Issue 2
```
Failed to generate BMC: No module named 'src.mint.api.system.core.vector_adapter'
```

### Fix Applied
**File**: `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/bmc/services/bmc_service.py`

**Before:**
```python
from src.mint.api.system.core.vector_adapter import get_yuba_vector_adapter
```

**After:**
```python
from src.vpm.adapters.vector_adapter import get_yuba_vector_adapter
```

## Status
✅ **FIXED** - Both BMC agent and BMC service now use correct import paths consistent with the Yuba codebase.

## Files Modified
1. `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/bmc/agents/bmc_agent.py` - AI provider imports and methods
2. `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/bmc/services/bmc_service.py` - Vector adapter import

## Enhancement - Name Field for BMC Visuals

### Requirement
All BMC items across all 9 blocks must have a `name` field (1-6 words, preferably 1-3) for display on BMC visual canvases.

### Changes Applied

**Files Modified**:
1. `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/bmc/prompts/bmc_prompts.py`
   - Added `name` field requirement to all 9 block prompts
   - Specified constraint: "1-6 words, preferably 1-3 for BMC visuals"
   - Updated JSON schema examples for all blocks

2. `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/bmc/agents/bmc_agent.py`
   - Added `name` field to value propositions schema
   - Added `name` field to customer relationships schema
   - Added `name` field to key partnerships schema
   - Updated required fields arrays to include `name`

**Blocks Updated**:
- ✅ Customer Segments (already had name)
- ✅ Value Propositions (added name)
- ✅ Channels (already had name)
- ✅ Customer Relationships (added name)
- ✅ Revenue Streams (already had name)
- ✅ Key Resources (already had name)
- ✅ Key Activities (already had name)
- ✅ Key Partnerships (added name)
- ✅ Cost Structure (changed from 'category' to 'name' for consistency)

## Testing
✅ **TESTED** - BMC generation working successfully!

Test with:
```bash
POST /api/v2/mvp/projects/{project_id}/bmc/generate
{
  "creativity_level": 0.7
}
```

## Status
✅ **COMPLETE** - All import issues fixed and name field added to all BMC blocks!
