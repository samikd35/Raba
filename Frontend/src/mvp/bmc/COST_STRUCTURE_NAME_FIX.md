# Cost Structure Name Field Fix

## Issue
Cost Structure block was using `category` field instead of `name` field, creating inconsistency with all other BMC blocks.

## Root Cause
The cost structure schema was originally designed with a `category` field while all other blocks use `name` for their display labels.

## Solution
Changed cost structure to use `name` field for consistency across all 9 BMC blocks.

## Files Modified

### 1. `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/bmc/prompts/bmc_prompts.py`
**Before:**
```python
"cost_categories": [
  {
    "id": "cost-001",
    "category": "Cost Category Name (1-6 words, preferably 1-3 for BMC visuals)",
    "type": "fixed|variable",
    ...
  }
]
```

**After:**
```python
"cost_categories": [
  {
    "id": "cost-001",
    "name": "Cost Category Name (1-6 words, preferably 1-3 for BMC visuals)",
    "type": "fixed|variable",
    ...
  }
]
```

### 2. `/Users/samikd/MyProjects/Yuba/Backend/src/mvp/bmc/agents/bmc_agent.py`
**Before:**
```python
"properties": {
    "id": {"type": "string"},
    "category": {"type": "string"},
    "type": {"type": "string"},
    ...
},
"required": ["id", "category", "type", ...]
```

**After:**
```python
"properties": {
    "id": {"type": "string"},
    "name": {"type": "string"},
    "type": {"type": "string"},
    ...
},
"required": ["id", "name", "type", ...]
```

## Impact
- ✅ All 9 BMC blocks now consistently use `name` field
- ✅ Frontend can rely on `name` field for all block items
- ✅ Improved data structure consistency
- ⚠️ **Breaking Change**: Existing cost structure data using `category` will need migration

## Migration Note
If you have existing BMC data with cost structure using `category`, you'll need to:
1. Regenerate the cost structure block, OR
2. Manually rename the `category` field to `name` in your database

## Testing
Next BMC generation will produce cost structure with `name` field:
```json
{
  "cost_structure": {
    "cost_categories": [
      {
        "id": "cost-001",
        "name": "Weather Data Acquisition",  // ✅ Now uses 'name'
        "type": "fixed",
        ...
      }
    ]
  }
}
```

## Status
✅ **COMPLETE** - Cost structure now uses `name` field consistently with all other blocks.
