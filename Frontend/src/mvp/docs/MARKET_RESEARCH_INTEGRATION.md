# Market Research Analysis Integration with VPS Generator

## 🎯 Overview

The VPS Generator now integrates with the **Market Research Analysis** module to leverage comprehensive market insights that have been analyzed and embedded for RAG-based retrieval.

---

## 📊 What is Market Research Analysis?

The Market Research Analysis module provides:

1. **Document Upload & Processing**
   - Users upload research documents (PDFs, CSVs)
   - Documents are chunked and embedded
   - Stored in vector database for semantic search

2. **AI-Powered Analysis**
   - Comprehensive analysis of uploaded research
   - Generates detailed analysis report covering:
     - Customer insights
     - Pain point analysis
     - Gain/benefit analysis
     - Market opportunities
     - Competitive landscape
     - Recommendations

3. **Chat Functionality**
   - Analysis report is chunked and embedded
   - Enables conversational queries via RAG
   - Provides grounded responses with citations

---

## 🔗 Integration with VPS Generator

### Data Flow

```
Market Research Analysis
    ↓
Analysis Report Generated
    ↓
Report Chunked & Embedded (via /prepare-report)
    ↓
Stored in Vector Database (chunk_type: "analysis_report")
    ↓
VPS Context Loader
    ↓
RAG Retrieval (top 10 relevant chunks)
    ↓
Included in VPS Generation Context
    ↓
AI generates evidence-based VPS
```

### API Endpoints Used

#### 1. Prepare Report for Chat
```http
POST /api/v1/market-research/analysis/chat/projects/{project_id}/prepare-report
```

**Purpose**: Chunks and embeds the analysis report to enable RAG retrieval

**When to call**: After market research analysis is complete

**What it does**:
- Takes the generated analysis report
- Chunks it into semantic sections
- Generates embeddings for each chunk
- Stores chunks with `chunk_type: "analysis_report"`
- Enables both chat functionality AND VPS context loading

#### 2. Chat with Analysis (Optional)
```http
POST /api/v1/market-research/analysis/chat/projects/{project_id}/message
```

**Purpose**: Conversational interface to query the analysis

**Not required for VPS**: VPS generator directly accesses the embedded chunks

---

## 🔍 How VPS Retrieves Analysis Data

### Context Loader Implementation

Located in: `/src/mvp/utils/context_loader.py`

**New Method**: `_load_market_research_analysis()`

```python
async def _load_market_research_analysis(
    self,
    project_id: str,
    tenant_id: str,
    max_chunks: int = 10
) -> List[Dict[str, Any]]:
    """
    Load market research analysis report chunks via vector search.
    
    Steps:
    1. Retrieve all analysis_report chunks for project
    2. Generate query embedding for VPS context
    3. Calculate similarity scores
    4. Return top 10 most relevant chunks (threshold: 0.7)
    """
```

### Query Used for Retrieval

```python
query = "value proposition customer insights pain points gains solutions market analysis competitive advantage"
```

This query is optimized to retrieve chunks most relevant to value proposition development.

### Similarity Threshold

- **Threshold**: 0.7 (70% similarity)
- **Max Chunks**: 10
- **Actual Retrieved**: Typically 5-8 high-relevance chunks

---

## 📋 Data Structure

### Analysis Chunk Format

```json
{
  "content": "Market analysis shows that 73% of customers cite high transaction fees as their primary pain point...",
  "relevance_score": 0.85,
  "section": "Pain Point Analysis",
  "source": "market_research_analysis"
}
```

### Context Integration

The analysis chunks are added to the VPS context:

```python
context = {
    "project_id": "...",
    "customer_profile": {...},
    "value_map": {...},
    "pv_report_insights": [...],
    "actionable_insights": [...],
    "market_research_analysis": [  # NEW
        {
            "content": "...",
            "relevance_score": 0.85,
            "section": "Customer Insights",
            "source": "market_research_analysis"
        },
        ...
    ]
}
```

---

## 📝 Prompt Integration

### Context Formatting

The market research analysis is formatted in the prompt as:

```markdown
# MARKET RESEARCH ANALYSIS INSIGHTS
*Key findings from the comprehensive market research analysis report*

1. [Customer Insights] Market analysis shows that 73% of customers...
   (Relevance: 0.85)

2. [Pain Point Analysis] Primary pain points identified include...
   (Relevance: 0.82)

3. [Market Opportunities] Significant opportunity exists in...
   (Relevance: 0.80)
```

### Evidence Source

Differentiators can now cite `market_research_analysis` as evidence:

```json
{
  "title": "Data-Driven Pain Relief",
  "description": "Our solution addresses the top 3 customer pain points identified in comprehensive market research: high fees (73%), slow delivery (67%), and lack of transparency (61%).",
  "evidence_source": "market_research_analysis"
}
```

---

## 🎯 Benefits

### 1. Richer Context
- Comprehensive market insights beyond just VPC and PV report
- Detailed customer pain/gain analysis
- Competitive landscape understanding
- Market opportunity identification

### 2. Evidence-Based VPS
- Quantitative data from analysis (percentages, statistics)
- Validated customer insights
- Market-backed differentiators
- Grounded in actual research

### 3. Consistency
- Same analysis used for chat and VPS generation
- Single source of truth for market insights
- Coherent narrative across modules

### 4. Automatic Updates
- When analysis is regenerated, VPS can leverage new insights
- No manual data transfer needed
- Always uses latest analysis

---

## 🔄 Workflow

### Complete Flow from Research to VPS

1. **Upload Research Documents**
   ```http
   POST /api/v1/market-research/analysis/projects/{project_id}/upload-documents
   ```

2. **Run Market Research Analysis**
   ```http
   POST /api/v1/market-research/analysis/projects/{project_id}/execute
   ```

3. **Prepare Report for Chat** (Enables VPS Integration)
   ```http
   POST /api/v1/market-research/analysis/chat/projects/{project_id}/prepare-report
   ```

4. **Complete VPC 2.0**
   - Generate VPC v2 with candidates
   - Select value map (3 from 5)

5. **Generate VPS** (Now includes analysis insights!)
   ```http
   POST /api/v2/mvp/projects/{project_id}/vps/v1/generate
   ```

---

## 📊 Context Sources Summary

The VPS Generator now uses **5 context sources**:

| Source | Description | Max Items | Threshold |
|--------|-------------|-----------|-----------|
| **VPC Analysis** | Customer profile + value map from VPC v2 | All | N/A |
| **Field Research** | Validated hypotheses and assumptions | 5 | N/A |
| **PV Report** | Problem validation report chunks | 10 | 0.7 |
| **Actionable Insights** | Strategic opportunities from PV | 5 | 0.7 |
| **Market Research Analysis** | Comprehensive analysis report chunks | 10 | 0.7 |

**Total Context**: ~30-40 high-quality evidence items

---

## 🛠️ Technical Implementation

### Dependencies

```python
# Required imports
from src.mint.api.services.storage.chunk_storage_service import get_chunks
from src.mint.api.services.ai.embedding_service import EmbeddingService
import numpy as np
import json
```

### Chunk Storage Service

Uses the same chunk storage service as market research chat:

```python
all_chunks = await get_chunks(
    doc_id=project_id,
    tenant_id=tenant_id,
    chunk_type="analysis_report"  # Filter for analysis chunks
)
```

### Similarity Calculation

```python
# Cosine similarity
similarity = np.dot(query_embedding, chunk_embedding) / (
    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
)
```

---

## ⚠️ Prerequisites

### For VPS to Use Analysis Data:

1. ✅ Market research documents uploaded
2. ✅ Market research analysis executed successfully
3. ✅ **Analysis report prepared for chat** (critical step!)
   - Call `/prepare-report` endpoint
   - This chunks and embeds the analysis
   - Without this, VPS won't find analysis chunks

### Graceful Degradation

If analysis is not available:
- VPS generation still works
- Uses other 4 context sources
- Logs warning: `"No market research analysis chunks found"`
- No error thrown - graceful fallback

---

## 📈 Impact on VPS Quality

### Before Integration
- VPS based on VPC, field research, and PV report
- Limited quantitative market data
- Less comprehensive customer insights

### After Integration
- VPS enriched with detailed market analysis
- Quantitative data from research (percentages, statistics)
- Comprehensive pain/gain understanding
- Competitive landscape awareness
- Market opportunity validation

### Example Improvement

**Before**:
```
"For smallholder farmers who need access to credit, our platform provides flexible micro-loans."
```

**After** (with analysis):
```
"For smallholder farmers who need access to credit, our platform provides flexible micro-loans with 30-day repayment terms. Market research shows 73% of farmers cite high interest rates as their primary barrier, and our flat-fee model reduces costs by 60% compared to traditional lenders."
```

---

## 🔮 Future Enhancements

### Planned Improvements

1. **Section-Specific Retrieval**
   - Target specific analysis sections (e.g., "Pain Analysis", "Gain Analysis")
   - More precise context loading

2. **Weighted Retrieval**
   - Give higher weight to certain sections
   - Prioritize customer insights over competitive analysis

3. **Cross-Reference Validation**
   - Validate VPC elements against analysis findings
   - Flag inconsistencies

4. **Dynamic Query Generation**
   - Generate query based on VPC content
   - More targeted retrieval

---

## 📚 Related Documentation

- **Market Research Analysis**: `/src/market_research/README.md`
- **Chat Service**: `/src/market_research/services/chat_service.py`
- **VPS Implementation**: `/src/mvp/IMPLEMENTATION_COMPLETE.md`
- **Context Loader**: `/src/mvp/utils/context_loader.py`

---

## ✅ Summary

The VPS Generator now seamlessly integrates with Market Research Analysis to:

✅ Leverage comprehensive market insights  
✅ Use quantitative research data  
✅ Ground value propositions in validated analysis  
✅ Provide evidence-based differentiators  
✅ Maintain consistency across modules  
✅ Enable automatic updates when analysis changes  

**Result**: More compelling, evidence-based value proposition statements backed by comprehensive market research.
