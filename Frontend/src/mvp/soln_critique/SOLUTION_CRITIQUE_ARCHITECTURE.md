# Solution Critique - Architecture Reference Documentation

## Overview

The **Solution Critique** feature is an AI-powered reality-check system that analyzes proposed solutions using VPC v2, VPS, and BMC data combined with web research to provide evidence-based critiques across 5 critical dimensions.

**Think of it as:** A brutally honest advisor that saves founders time by identifying viability issues before they waste resources.

---

## System Architecture

### High-Level Flow

```
User Request (POST /api/v2/vmp/projects/{project_id}/solution-critique/generate)
    ↓
1. Context Preparation Node
    ↓ (Load VPC v2, VPS, BMC from vmp_projects.mvp_data)
    ↓
2. Research Query Planning Node
    ↓ (Generate 15-20 targeted search queries)
    ↓
3. Web Research Execution Node
    ↓ (Execute Brave Search API in parallel batches)
    ↓
4. PARALLEL CRITIQUE GENERATION (5 agents run simultaneously)
    ├─→ Market Viability Critique Agent
    ├─→ Operational Feasibility Critique Agent
    ├─→ Business Model Critique Agent
    ├─→ Competitive Differentiation Critique Agent
    └─→ Technical Scalability Critique Agent
    ↓ (All agents complete)
    ↓
5. Critique Report Synthesizer
    ↓ (Generate structured JSON report)
    ↓
6. Store to Database (vmp_projects.soln_critique_data)
    ↓
Response: Complete critique report (JSON)
```

---

## LangGraph Workflow Architecture

### Node Structure

```python
class SolutionCritiqueState(TypedDict):
    # Project context
    project_id: str
    tenant_id: str
    user_id: str
    session_id: str
    geography: str
    industry: str
    solution_description: str
    
    # Input data (snapshots from project)
    vpc_data: Dict[str, Any]
    vps_data: Dict[str, Any]
    bmc_data: Dict[str, Any]
    
    # Research phase
    research_queries: List[Dict[str, Any]]
    search_results: Dict[str, List[Dict[str, Any]]]
    
    # Critique results (parallel processing)
    market_critique: Optional[Dict[str, Any]]
    operational_critique: Optional[Dict[str, Any]]
    business_model_critique: Optional[Dict[str, Any]]
    competitive_critique: Optional[Dict[str, Any]]
    technical_critique: Optional[Dict[str, Any]]
    
    # Final output
    all_critiques: List[Dict[str, Any]]
    final_report: Dict[str, Any]  # JSON structure
    
    # Metadata
    status: str
    completed_at: Optional[str]
    error: Optional[str]
```

### Workflow Graph

```python
workflow = StateGraph(SolutionCritiqueState)

# Sequential preparation nodes
workflow.add_node("prepare_context", prepare_context_node)
workflow.add_node("plan_queries", plan_research_queries_node)
workflow.add_node("execute_research", execute_web_research_node)

# PARALLEL critique nodes (all run simultaneously)
workflow.add_node("market_critique", market_viability_critique_node)
workflow.add_node("operational_critique", operational_feasibility_critique_node)
workflow.add_node("business_model_critique", business_model_critique_node)
workflow.add_node("competitive_critique", competitive_differentiation_critique_node)
workflow.add_node("technical_critique", technical_scalability_critique_node)

# Sequential synthesis node
workflow.add_node("synthesize_report", synthesize_critique_report_node)

# Define edges
workflow.set_entry_point("prepare_context")
workflow.add_edge("prepare_context", "plan_queries")
workflow.add_edge("plan_queries", "execute_research")

# PARALLEL EXECUTION: All critique agents run simultaneously after research
workflow.add_edge("execute_research", "market_critique")
workflow.add_edge("execute_research", "operational_critique")
workflow.add_edge("execute_research", "business_model_critique")
workflow.add_edge("execute_research", "competitive_critique")
workflow.add_edge("execute_research", "technical_critique")

# All critiques converge to synthesis
workflow.add_edge("market_critique", "synthesize_report")
workflow.add_edge("operational_critique", "synthesize_report")
workflow.add_edge("business_model_critique", "synthesize_report")
workflow.add_edge("competitive_critique", "synthesize_report")
workflow.add_edge("technical_critique", "synthesize_report")

workflow.add_edge("synthesize_report", END)
```

---

## Agent Architecture

### 1. Context Preparation Agent

**Purpose:** Load and structure project data for analysis

**Actions:**
- Load VPC v2 data from `vmp_projects.vpc_data`
- Load VPS data from `vmp_projects.mvp_data.vps_v2` (or v1 if v2 not available)
- Load BMC data from `vmp_projects.mvp_data.bmc`
- Extract key metadata: geography, industry, solution description
- Validate all required data is present

**Output:**
```json
{
  "geography": "Kigali, Rwanda",
  "industry": "Pet food marketplace",
  "solution_description": "Extracted from VPS",
  "vpc_data": { "customer_profile": {...}, "value_map": {...} },
  "vps_data": { "statement": "...", "components": [...] },
  "bmc_data": { "value_propositions": [...], "customer_segments": [...], ... }
}
```

---

### 2. Research Query Planning Agent

**Purpose:** Generate targeted web search queries

**AI Model:** GPT-4.1 (Azure OpenAI)

**Strategy:**
- Analyzes solution context (geography, industry, VPS, BMC)
- Generates 15-20 queries across 5 categories
- Prioritizes queries (high/medium/low)

**Query Categories:**

1. **Market Research** (3-4 queries)
   - `"{geography} {industry} market size 2024"`
   - `"{customer_segment} behavior trends {country}"`
   - `"{industry} consumer preferences {geography}"`

2. **Regulatory & Compliance** (3-4 queries)
   - `"{industry} regulations {country}"`
   - `"{geography} business licensing requirements"`
   - `"{specific_activity} compliance {country}"`

3. **Competition** (3-4 queries)
   - `"{industry} competitors {geography}"`
   - `"alternatives to {solution_type} {geography}"`
   - `"{industry} market leaders {country}"`

4. **Operational/Logistics** (2-3 queries)
   - `"{industry} supply chain {geography}"`
   - `"{resource_type} availability {country}"`
   - `"{operational_requirement} infrastructure {geography}"`

5. **Technology/Innovation** (2-3 queries)
   - `"{industry} technology trends 2024"`
   - `"{solution_type} platform best practices"`
   - `"{industry} digital transformation {country}"`

**Output:**
```json
{
  "research_queries": [
    {
      "id": "query-001",
      "category": "market",
      "query": "Kigali Rwanda pet food market size 2024",
      "priority": "high",
      "rationale": "Need to validate market demand assumption"
    },
    ...
  ]
}
```

---

### 3. Web Research Execution Agent

**Purpose:** Execute Brave Search API calls and collect results

**Service:** `BraveSearchProvider` (from `/src/mint/providers/search.py`)

**Strategy:**
- Execute queries in parallel batches (5-10 at a time)
- Collect top 5-10 results per query
- Extract: title, URL, snippet, published_date
- De-duplicate results across queries
- Retry logic for rate limits (exponential backoff)

**Rate Limiting:**
- Brave Search API: Configurable limit
- Batch size: 5-10 queries
- Delay between batches: 1-2 seconds

**Output:**
```json
{
  "search_results": {
    "market": [
      {
        "query": "Kigali Rwanda pet food market size 2024",
        "results": [
          {
            "title": "Rwanda Pet Food Market Analysis 2024",
            "url": "https://example.com/report",
            "snippet": "The Rwanda pet food market is estimated at $X million...",
            "source": "brave",
            "position": 1,
            "published_date": "2024-01-15"
          }
        ]
      }
    ],
    "regulatory": [...],
    "competition": [...],
    "operational": [...],
    "technology": [...]
  }
}
```

---

### 4. Critique Agents (5 Parallel Agents)

All critique agents follow the same pattern but focus on different dimensions.

#### Common Agent Structure

**AI Model:** GPT-4.1 (Azure OpenAI)
**AI Monitoring:** Integrated via `monitor.tokens.service`
**Output Format:** Structured JSON (no markdown)

**Input:**
- Project context (VPC, VPS, BMC)
- Relevant web search results (filtered by category)

**Output Structure:**
```json
{
  "critique_id": "market-001",
  "dimension": "market_viability",
  "title": "Unvalidated Customer Demand Assumption",
  "severity": "high",  // high | medium | low
  "problem": "The solution assumes dog owners in Kigali are willing to pay premium prices for raw meat delivery without market validation [1]. Only 15% of Kigali households own pets [2], raising questions about market size assumptions. The target customer segment lacks quantification and addressable market estimates [3], creating uncertainty about revenue potential [4].",
  "sources": [
    {
      "id": 1,
      "type": "bmc",
      "field": "customer_segments",
      "content": "Dog owners in Kigali",
      "issue": "No market size quantification"
    },
    {
      "id": 2,
      "type": "web",
      "title": "Rwanda Pet Ownership Survey 2023",
      "url": "https://example.com/survey",
      "snippet": "15% of Kigali households own pets",
      "relevance": 0.92
    },
    {
      "id": 3,
      "type": "bmc",
      "field": "revenue_streams",
      "content": "Commission on raw meat sales",
      "issue": "No pricing validation"
    },
    {
      "id": 4,
      "type": "web",
      "title": "African Pet Food Market Report",
      "url": "https://example.com/market-report",
      "snippet": "80% of pet food sales in East Africa are dry kibble, not fresh meat",
      "relevance": 0.88
    }
  ],
  "impact": "Without validated demand [1][2], significant risk of building a product nobody wants. Market evidence suggests 80% preference for alternative products [4], creating estimated 70% probability of market mismatch.",
  "suggestions": [
    {
      "type": "validation",
      "action": "Conduct customer interviews with 20+ dog owners in Kigali to validate willingness to pay and preferred product format",
      "priority": "immediate",
      "effort": "low",
      "impact": "high",
      "rationale": "Address fundamental demand assumption [1][2] before investing in operations",
      "supporting_sources": [1, 2]
    },
    {
      "type": "alternative",
      "action": "Pivot to shelf-stable pet food instead of fresh meat delivery",
      "priority": "consider",
      "effort": "medium",
      "impact": "medium",
      "rationale": "Market evidence shows 80% preference for dry kibble [4], aligning with validated demand patterns",
      "supporting_sources": [4]
    }
  ],
  "confidence": 0.85,
  "citation_count": 6
}
```

---

#### 4.1 Market Viability Critique Agent

**Focus Areas:**
- Customer demand validation
- Market size vs. TAM claims
- Price sensitivity
- Customer willingness to switch
- Market growth trends

**BMC Fields Analyzed:**
- Customer Segments
- Value Propositions
- Revenue Streams (pricing)

**VPC Fields Analyzed:**
- Customer Profile (Jobs, Pains, Gains)
- Value Map alignment

**Web Search Categories Used:**
- Market research
- Competition (for market share data)

---

#### 4.2 Operational Feasibility Critique Agent

**Focus Areas:**
- Supply chain complexity
- Regulatory compliance
- Licensing requirements
- Resource availability
- Infrastructure gaps
- Operational costs

**BMC Fields Analyzed:**
- Key Activities
- Key Resources
- Key Partnerships

**VPC Fields Analyzed:**
- Products/Services (operational requirements)

**Web Search Categories Used:**
- Regulatory & compliance
- Operational/logistics

---

#### 4.3 Business Model Critique Agent

**Focus Areas:**
- Revenue model clarity
- Cost structure completeness
- Profit margins
- CAC vs. LTV
- Unit economics
- Monetization strategy

**BMC Fields Analyzed:**
- Revenue Streams
- Cost Structure
- Key Resources (cost drivers)

**VPC Fields Analyzed:**
- Value Map (pricing implications)

**Web Search Categories Used:**
- Competition (pricing benchmarks)
- Market (revenue models in industry)

---

#### 4.4 Competitive Differentiation Critique Agent

**Focus Areas:**
- Unique value proposition strength
- Competitive advantages
- Barrier to entry
- Feature parity with alternatives
- Defensibility

**BMC Fields Analyzed:**
- Value Propositions
- Customer Relationships
- Channels

**VPC Fields Analyzed:**
- Value Map (differentiation)
- Gain Creators (uniqueness)

**Web Search Categories Used:**
- Competition
- Technology (innovation gaps)

---

#### 4.5 Technical Scalability Critique Agent

**Focus Areas:**
- Platform scalability
- Technology stack appropriateness
- Multi-vendor/multi-user complexity
- Data integrity
- Infrastructure requirements
- Technical debt risks

**BMC Fields Analyzed:**
- Key Resources (technology)
- Key Activities (technical complexity)

**VPC Fields Analyzed:**
- Products/Services (technical requirements)

**Web Search Categories Used:**
- Technology/innovation
- Operational (infrastructure)

---

### 5. Critique Report Synthesizer Agent

**Purpose:** Generate final structured JSON report

**AI Model:** GPT-4.1 (Azure OpenAI)

**Actions:**
- Aggregate all 5 critique dimensions
- Calculate severity distribution
- Generate executive summary
- Prioritize recommendations
- Create overall viability assessment

**Output Structure:**
```json
{
  "project_id": "uuid",
  "session_id": "uuid",
  "generated_at": "2024-01-20T10:30:00Z",
  "executive_summary": {
    "overall_viability": "moderate_risk",  // high_risk | moderate_risk | low_risk
    "total_critiques": 12,
    "severity_distribution": {
      "high": 5,
      "medium": 4,
      "low": 3
    },
    "top_3_risks": [
      "Unvalidated customer demand [1][2]",
      "Complex regulatory environment [5][6]",
      "Unclear path to profitability [8][9]"
    ],
    "overall_confidence": 0.78,
    "recommendation": "Conduct market validation before proceeding [1][2]. Address high-severity issues immediately, particularly regulatory compliance requirements [5][6] and revenue model clarity [8][9].",
    "total_citations": 45
  },
  "critiques_by_dimension": {
    "market_viability": {
      "summary": "Significant market validation gaps identified [1][2][3][4]",
      "critiques": [...],
      "dimension_severity": "high",
      "citation_count": 15
    },
    "operational_feasibility": {...},
    "business_model": {...},
    "competitive_differentiation": {...},
    "technical_scalability": {...}
  },
  "all_critiques": [
    {
      "critique_id": "market-001",
      "dimension": "market_viability",
      "problem": "Text with [1][2] citations...",
      "sources": [...],
      "citation_count": 6,
      ...
    }
  ],
  "sources": [
    {
      "id": 1,
      "type": "web",
      "title": "Rwanda Pet Ownership Survey 2023",
      "url": "https://example.com/survey",
      "snippet": "15% of Kigali households own pets",
      "accessed_at": "2024-01-20T10:30:00Z"
    },
    {
      "id": 2,
      "type": "bmc",
      "field": "customer_segments",
      "content": "Dog owners in Kigali",
      "issue": "No market size quantification"
    },
    ...
  ],
  "prioritized_actions": {
    "immediate": [
      {
        "action": "Conduct customer interviews [1][2]",
        "supporting_sources": [1, 2],
        ...
      }
    ],
    "short_term": [...],
    "long_term": [...]
  },
  "metadata": {
    "queries_executed": 18,
    "web_sources_analyzed": 85,
    "total_sources": 45,
    "total_citations": 127,
    "ai_model": "gpt-4.1",
    "processing_time_seconds": 45
  }
}
```

---

## Database Storage

### Column Addition to vmp_projects

```sql
ALTER TABLE vmp_projects 
ADD COLUMN soln_critique_data JSONB DEFAULT NULL;
```

### Storage Structure

```json
{
  "session_id": "uuid",
  "status": "completed",  // processing | completed | failed
  "generated_at": "2024-01-20T10:30:00Z",
  "completed_at": "2024-01-20T10:31:15Z",
  
  "input_snapshots": {
    "vpc_snapshot": {...},
    "vps_snapshot": {...},
    "bmc_snapshot": {...}
  },
  
  "research_data": {
    "queries": [...],
    "search_results_count": 85
  },
  
  "critique_report": {
    // Full JSON report from synthesizer
  },
  
  "error": null
}
```

---

## AI Service Integration

### AI Service Wrapper

Reuses existing `AIServiceWrapper` from `/src/market_research/utils/ai_service_wrapper.py`

**Features:**
- Azure OpenAI GPT-4.1 integration
- Token monitoring
- Circuit breaker pattern
- Retry logic with exponential backoff
- AI usage monitoring via `monitor.tokens.service`

**Usage:**
```python
from src.market_research.utils.ai_service_wrapper import get_ai_service_wrapper

ai_service = get_ai_service_wrapper()

# Create monitoring context
monitoring_context = AIUsageContext(
    tenant_id=tenant_id,
    user_id=user_id,
    feature_name="solution_critique",
    operation_name="market_viability_critique",
    project_id=project_id
)

# Generate critique with monitoring
response = await ai_service.generate_analysis_response(
    messages=[...],
    model="gpt-4",
    temperature=0.1,
    json_mode=True,  # Force JSON output
    monitoring_context=monitoring_context
)
```

---

## Web Search Integration

### Brave Search Provider

Reuses existing `BraveSearchProvider` from `/src/mint/providers/search.py`

**Features:**
- Async search execution
- Rate limit handling with retry
- Result de-duplication
- Error handling

**Usage:**
```python
from src.mint.providers.search import BraveSearchProvider, SearchConfig

# Initialize provider
search_config = SearchConfig(
    provider_name="brave",
    api_key_env_var="BRAVE_API_KEY",
    num_results=10,
    safe_search=True
)
search_provider = BraveSearchProvider(search_config)

# Execute search
results = await search_provider.search(query="Kigali pet food market 2024")

# Results format
for result in results:
    print(result.title)
    print(result.url)
    print(result.snippet)
```

---

## API Endpoints

### 1. Generate Solution Critique

```
POST /api/v2/vmp/projects/{project_id}/solution-critique/generate
```

**Request:**
```json
{
  "force_regenerate": false  // Optional: regenerate even if exists
}
```

**Response (202 Accepted - Async):**
```json
{
  "success": true,
  "session_id": "uuid",
  "status": "processing",
  "message": "Solution critique generation started",
  "estimated_completion_seconds": 60
}
```

---

### 2. Get Critique Status

```
GET /api/v2/vmp/projects/{project_id}/solution-critique/status
```

**Response:**
```json
{
  "success": true,
  "status": "completed",  // processing | completed | failed
  "session_id": "uuid",
  "started_at": "2024-01-20T10:30:00Z",
  "completed_at": "2024-01-20T10:31:15Z",
  "progress": {
    "current_step": "synthesize_report",
    "steps_completed": 8,
    "total_steps": 9
  }
}
```

---

### 3. Get Critique Results

```
GET /api/v2/vmp/projects/{project_id}/solution-critique/results
```

**Response:**
```json
{
  "success": true,
  "data": {
    // Full critique report JSON
    "executive_summary": {...},
    "critiques_by_dimension": {...},
    "all_critiques": [...],
    "prioritized_actions": {...}
  },
  "metadata": {
    "generated_at": "2024-01-20T10:30:00Z",
    "queries_executed": 18,
    "web_sources_analyzed": 85
  }
}
```

---

## Error Handling

### Error Scenarios

1. **Missing Required Data**
   - VPC v2 not generated
   - VPS not available
   - BMC not completed

**Response:** 400 Bad Request
```json
{
  "success": false,
  "error": "missing_required_data",
  "message": "BMC must be completed before generating solution critique",
  "missing": ["bmc"]
}
```

2. **Web Search API Failure**
   - Brave API down
   - Rate limit exceeded
   - Network error

**Handling:** 
- Retry with exponential backoff
- Continue with partial results if some queries succeed
- Log failures for monitoring

3. **AI Service Failure**
   - OpenAI API error
   - Token limit exceeded
   - Timeout

**Handling:**
- Circuit breaker pattern
- Retry failed agents
- Mark as failed if critical agents fail

---

## Performance Characteristics

### Expected Timing

- **Context Preparation:** 2-3 seconds
- **Query Planning:** 3-5 seconds
- **Web Research:** 15-20 seconds (parallel batches)
- **Parallel Critiques:** 20-25 seconds (5 agents simultaneously)
- **Report Synthesis:** 5-8 seconds
- **Total:** 45-60 seconds

### Resource Usage

- **API Calls:**
  - Web search: 15-20 queries
  - AI calls: 6-7 (planning + 5 critiques + synthesis)
  
- **Token Usage:**
  - Per critique agent: ~3,000-5,000 tokens
  - Total: ~25,000-35,000 tokens per analysis

- **Memory:**
  - Parallel processing: ~50-100MB peak
  - State management: Minimal (LangGraph handles)

---

## Citation System (Following PV Report Best Practices)

### Overview

**Inspired by PV Report Implementation:** The solution critique uses strict numbered citation system [1], [2], [3], etc., identical to the PV report generator for consistency and reliability.

### Citation Requirements

**MANDATORY for all critique agents:**
1. **Every factual claim must have a citation** - No unsupported statements
2. **Numbered citations** - Use [1], [2], [3] format embedded in text
3. **Sources section** - Master list of all sources at critique and report level
4. **Citation tracking** - Track citation_count for validation

### Citation Format

#### In-Text Citations
```
"The solution assumes market demand without validation [1]. Only 15% of households 
in the target geography own pets [2], raising questions about market size [3]."
```

#### Sources Section
```json
{
  "sources": [
    {
      "id": 1,
      "type": "bmc",
      "field": "customer_segments",
      "content": "Dog owners in target city",
      "issue": "No quantification provided"
    },
    {
      "id": 2,
      "type": "web",
      "title": "Pet Ownership Survey 2023",
      "url": "https://example.com/survey",
      "snippet": "15% of households own pets",
      "relevance": 0.92,
      "accessed_at": "2024-01-20T10:30:00Z"
    },
    {
      "id": 3,
      "type": "vpc",
      "field": "customer_profile.pains",
      "content": "High cost of pet food",
      "context": "Customer pain point identified"
    }
  ]
}
```

### Source Types

#### 1. Web Sources
```json
{
  "id": 1,
  "type": "web",
  "title": "Document title",
  "url": "Full URL",
  "snippet": "Relevant excerpt (max 200 chars)",
  "relevance": 0.85,
  "accessed_at": "ISO timestamp"
}
```

#### 2. BMC Sources
```json
{
  "id": 2,
  "type": "bmc",
  "field": "revenue_streams" | "cost_structure" | "customer_segments" | etc.,
  "content": "Actual BMC content",
  "issue": "Critique-specific issue identified"
}
```

#### 3. VPC Sources
```json
{
  "id": 3,
  "type": "vpc",
  "field": "customer_profile.jobs_to_be_done" | "value_map.pain_relievers" | etc.,
  "content": "Actual VPC content",
  "context": "How it relates to critique"
}
```

#### 4. VPS Sources
```json
{
  "id": 4,
  "type": "vps",
  "field": "statement" | "components",
  "content": "VPS content excerpt",
  "context": "Relevance to critique"
}
```

### Citation Workflow

#### Step 1: Collect Sources (Per Critique Agent)
```python
sources = []
source_id = 1

# From web research
for result in web_results:
    sources.append({
        "id": source_id,
        "type": "web",
        "title": result['title'],
        "url": result['url'],
        "snippet": result['snippet'][:200],
        "relevance": result.get('relevance', 0.0)
    })
    source_id += 1

# From BMC
for field, content in bmc_issues.items():
    sources.append({
        "id": source_id,
        "type": "bmc",
        "field": field,
        "content": content,
        "issue": "Identified gap/issue"
    })
    source_id += 1
```

#### Step 2: Generate Critique with Citations
```python
prompt = f"""
Generate critique using numbered citations [1], [2], [3], etc.

SOURCES:
[1] {sources[0]['title']} - {sources[0]['snippet']}
[2] {sources[1]['field']} - {sources[1]['content']}
[3] {sources[2]['title']} - {sources[2]['snippet']}

Requirements:
- Every claim must have citation
- Use [1][2] for multiple sources supporting same claim
- Minimum 5 citations per critique
- Track exact citation numbers used
"""
```

#### Step 3: Validate Citations
```python
def validate_citations(critique_text, sources):
    """Ensure all citations reference valid sources"""
    import re
    
    # Extract citation numbers [1], [2], etc.
    citations = re.findall(r'\[(\d+)\]', critique_text)
    max_source_id = len(sources)
    
    for citation_num in citations:
        if int(citation_num) > max_source_id:
            raise ValueError(f"Citation [{citation_num}] exceeds available sources")
    
    return len(set(citations))  # Return unique citation count
```

#### Step 4: Aggregate Sources in Synthesis
```python
def synthesize_sources(all_critiques):
    """Combine and renumber sources across all critiques"""
    global_sources = []
    source_mapping = {}  # Old ID -> New ID
    new_id = 1
    
    for critique in all_critiques:
        for source in critique['sources']:
            # Check for duplicates (same URL or same BMC field)
            duplicate_id = find_duplicate_source(source, global_sources)
            
            if duplicate_id:
                source_mapping[source['id']] = duplicate_id
            else:
                global_sources.append({**source, 'id': new_id})
                source_mapping[source['id']] = new_id
                new_id += 1
        
        # Update critique text with new citation numbers
        critique['problem'] = renumber_citations(
            critique['problem'], 
            source_mapping
        )
    
    return global_sources
```

### AI Prompt Requirements

**All critique agents must include:**

```python
CITATION_REQUIREMENTS = """
CRITICAL CITATION REQUIREMENTS (Following PV Report Standards):

1. **Numbered Citations**: Use [1], [2], [3] format throughout your critique
2. **Every Claim Must Cite**: No statement without supporting source
3. **Multiple Sources**: Use [1][2] when multiple sources support same claim
4. **Minimum Citations**: Include at least 5-8 citations per critique
5. **Source Accuracy**: Ensure citation numbers match provided source list

Citation Format Examples:
- Single source: "Market size is limited [1]"
- Multiple sources: "Demand is unvalidated [1][2]"
- Sequential: "Issue affects 15% of market [3], creating barriers [4]"

SOURCES PROVIDED:
[1] {source_1_description}
[2] {source_2_description}
[3] {source_3_description}
...

Your critique must:
- Embed [N] citations naturally in text
- Reference specific source numbers
- Track total citations used
- Ensure all sources are utilized
"""
```

### Validation & Quality Control

#### Citation Coverage Check
```python
def check_citation_coverage(critique):
    """Ensure minimum citation standards"""
    citation_count = critique.get('citation_count', 0)
    word_count = len(critique['problem'].split())
    
    # Minimum 1 citation per 50 words
    min_citations = max(5, word_count // 50)
    
    if citation_count < min_citations:
        logger.warning(
            f"Low citation coverage: {citation_count} citations "
            f"for {word_count} words (min: {min_citations})"
        )
```

#### Source Utilization Check
```python
def check_source_utilization(critique):
    """Ensure sources are actually used"""
    import re
    
    citations = set(re.findall(r'\[(\d+)\]', critique['problem']))
    available_sources = set(range(1, len(critique['sources']) + 1))
    
    unused_sources = available_sources - citations
    if unused_sources:
        logger.warning(f"Unused sources: {unused_sources}")
```

### Example Complete Critique with Citations

```json
{
  "critique_id": "market-001",
  "dimension": "market_viability",
  "title": "Unvalidated Market Demand with Questionable Size Assumptions",
  "severity": "high",
  "problem": "The solution assumes customers in the target geography are willing to pay for the proposed service without market validation [1]. Research indicates only 15% of households in the region would be potential customers [2], significantly below the 40% market penetration assumed in revenue projections [3]. The customer segment definition lacks specificity [4], making it difficult to estimate addressable market size [5]. Competition analysis shows 80% market share held by established alternatives [6], creating high barriers to entry [7]. These factors combined suggest the market opportunity is substantially smaller than projected [8].",
  "sources": [
    {
      "id": 1,
      "type": "bmc",
      "field": "value_propositions",
      "content": "Premium service for target customers",
      "issue": "No validation data or customer research cited"
    },
    {
      "id": 2,
      "type": "web",
      "title": "Market Research Report 2024",
      "url": "https://example.com/report",
      "snippet": "Only 15% of households show purchasing intent for premium services",
      "relevance": 0.91,
      "accessed_at": "2024-01-20T10:30:00Z"
    },
    {
      "id": 3,
      "type": "bmc",
      "field": "revenue_streams",
      "content": "Target 40% market penetration in year 1",
      "issue": "Assumptions not backed by market data"
    },
    {
      "id": 4,
      "type": "bmc",
      "field": "customer_segments",
      "content": "Urban professionals aged 25-45",
      "issue": "Too broad, no geographic or income specificity"
    },
    {
      "id": 5,
      "type": "vpc",
      "field": "customer_profile.jobs_to_be_done",
      "content": "Need convenient service access",
      "context": "Generic JTBD without market sizing"
    },
    {
      "id": 6,
      "type": "web",
      "title": "Competitive Landscape Analysis",
      "url": "https://example.com/competition",
      "snippet": "Three established players control 80% of market share",
      "relevance": 0.88,
      "accessed_at": "2024-01-20T10:30:00Z"
    },
    {
      "id": 7,
      "type": "web",
      "title": "Market Entry Barriers Study",
      "url": "https://example.com/barriers",
      "snippet": "High customer acquisition costs averaging $150 per customer",
      "relevance": 0.85,
      "accessed_at": "2024-01-20T10:30:00Z"
    },
    {
      "id": 8,
      "type": "bmc",
      "field": "key_assumptions",
      "content": "Large addressable market with unmet needs",
      "issue": "Contradicted by market research findings"
    }
  ],
  "impact": "Operating with unvalidated market assumptions [1][3] creates high risk of misallocated resources. With actual addressable market potentially 60% smaller than projected [2][8] and strong incumbent competition [6][7], probability of achieving revenue targets is estimated at less than 30%.",
  "suggestions": [
    {
      "type": "validation",
      "action": "Conduct customer interviews with 50+ target customers to validate demand and willingness to pay",
      "priority": "immediate",
      "effort": "medium",
      "impact": "high",
      "rationale": "Address fundamental market demand assumption [1] and refine customer segment definition [4][5]",
      "supporting_sources": [1, 4, 5]
    },
    {
      "type": "alternative",
      "action": "Pivot to underserved niche segment to avoid direct competition",
      "priority": "consider",
      "effort": "medium",
      "impact": "high",
      "rationale": "Given 80% incumbent market share [6] and high CAC [7], targeting overlooked segment reduces competitive pressure",
      "supporting_sources": [6, 7]
    },
    {
      "type": "optimization",
      "action": "Revise revenue projections based on realistic 15% addressable market",
      "priority": "immediate",
      "effort": "low",
      "impact": "medium",
      "rationale": "Align financial models with market research findings [2][3] to set achievable targets",
      "supporting_sources": [2, 3, 8]
    }
  ],
  "confidence": 0.87,
  "citation_count": 15,
  "unique_sources_used": 8,
  "citations_per_100_words": 8.5
}
```

---

## Quality Assurance

### Severity Scoring Rules

**High Severity:**
- Violates regulations
- No clear revenue model
- Unvalidated critical assumption
- Operational impossibility
- Legal/compliance blocker

**Medium Severity:**
- Competitive disadvantage
- High operational complexity
- Questionable market fit
- Scalability concerns

**Low Severity:**
- Feature gaps
- Minor inefficiencies
- Nice-to-have improvements
- Optimization opportunities

### Evidence Quality Standards

**Web Evidence:**
- Must have URL and snippet
- Relevance score > 0.70
- Prefer recent sources (< 2 years)
- Multiple sources for critical claims

**Project Data Evidence:**
- Must specify exact field path
- Quote actual content
- Explain issue clearly

---

## Monitoring & Observability

### AI Usage Monitoring

All AI calls tracked via `monitor.tokens.service`:
- Provider: Azure OpenAI
- Model: gpt-4.1
- Token usage (prompt + completion)
- Latency
- Success/failure status

### Metrics Tracked

- Critique generation success rate
- Average processing time
- Web search query success rate
- AI agent failure rate
- Severity distribution trends

---

## Security & Access Control

### Authentication
- Requires valid user authentication
- Tenant-based access control

### Data Privacy
- Input snapshots stored for audit
- Web search results not permanently stored
- AI interactions logged for monitoring

---

## Future Enhancements

### V2 Considerations

1. **Interactive Refinement:** Allow users to ask follow-up questions
2. **Dimension Selection:** Let users choose specific dimensions to analyze
3. **Custom Query Addition:** Allow users to add specific research queries
4. **Historical Comparison:** Compare critiques over multiple iterations
5. **Export Formats:** PDF, Word, PowerPoint exports
6. **Integration with Field Prep:** Link critique suggestions to validation questionnaires

---

## References

### Existing Components Reused

1. **AI Service:** `/src/market_research/utils/ai_service_wrapper.py`
2. **Search Provider:** `/src/mint/providers/search.py`
3. **Database Adapter:** `/src/mvp/adapters/database_adapter.py`
4. **AI Monitoring:** `/monitor/tokens/service.py`
5. **VPM Database Adapter:** `/src/vpm/adapters/database_adapter.py`

### Similar Implementations

1. **Market Research Analysis:** `/src/market_research/services/analysis_workflow.py`
   - LangGraph parallel processing
   - AI service integration
   - Database streaming

2. **BMC Generation:** `/src/mvp/bmc/`
   - Sequential AI generation
   - Context loading
   - Database storage patterns

---

## Appendix: JSON Schema Definitions

### Critique Schema (with Citations)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["critique_id", "dimension", "title", "severity", "problem", "sources", "suggestions", "citation_count"],
  "properties": {
    "critique_id": {"type": "string"},
    "dimension": {
      "type": "string",
      "enum": ["market_viability", "operational_feasibility", "business_model", "competitive_differentiation", "technical_scalability"]
    },
    "title": {"type": "string", "minLength": 10, "maxLength": 200},
    "severity": {
      "type": "string",
      "enum": ["high", "medium", "low"]
    },
    "problem": {
      "type": "string",
      "minLength": 100,
      "description": "Problem description with embedded numbered citations [1], [2], etc."
    },
    "sources": {
      "type": "array",
      "minItems": 5,
      "description": "Numbered list of all sources referenced in critique",
      "items": {
        "type": "object",
        "required": ["id", "type"],
        "properties": {
          "id": {"type": "integer", "minimum": 1},
          "type": {"type": "string", "enum": ["web", "bmc", "vpc", "vps"]},
          "title": {"type": "string"},
          "url": {"type": "string"},
          "snippet": {"type": "string", "maxLength": 200},
          "field": {"type": "string"},
          "content": {"type": "string"},
          "issue": {"type": "string"},
          "context": {"type": "string"},
          "relevance": {"type": "number", "minimum": 0, "maximum": 1},
          "accessed_at": {"type": "string", "format": "date-time"}
        }
      }
    },
    "impact": {
      "type": "string",
      "description": "Impact statement with citations [1][2]"
    },
    "suggestions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "action", "priority", "supporting_sources"],
        "properties": {
          "type": {"type": "string", "enum": ["validation", "alternative", "optimization", "compliance"]},
          "action": {"type": "string"},
          "priority": {"type": "string", "enum": ["immediate", "short_term", "long_term", "consider"]},
          "effort": {"type": "string", "enum": ["low", "medium", "high"]},
          "impact": {"type": "string", "enum": ["low", "medium", "high"]},
          "rationale": {
            "type": "string",
            "description": "Rationale with citations [1][2]"
          },
          "supporting_sources": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Array of source IDs supporting this suggestion"
          }
        }
      }
    },
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "citation_count": {
      "type": "integer",
      "minimum": 5,
      "description": "Total number of citations in critique"
    },
    "unique_sources_used": {
      "type": "integer",
      "description": "Number of unique sources referenced"
    }
  }
}
```

### Source Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "type"],
  "properties": {
    "id": {
      "type": "integer",
      "minimum": 1,
      "description": "Sequential source number used in citations"
    },
    "type": {
      "type": "string",
      "enum": ["web", "bmc", "vpc", "vps"]
    }
  },
  "oneOf": [
    {
      "description": "Web source schema",
      "required": ["title", "url", "snippet"],
      "properties": {
        "type": {"const": "web"},
        "title": {"type": "string"},
        "url": {"type": "string", "format": "uri"},
        "snippet": {"type": "string", "maxLength": 200},
        "relevance": {"type": "number", "minimum": 0, "maximum": 1},
        "accessed_at": {"type": "string", "format": "date-time"}
      }
    },
    {
      "description": "BMC source schema",
      "required": ["field", "content", "issue"],
      "properties": {
        "type": {"const": "bmc"},
        "field": {
          "type": "string",
          "enum": ["value_propositions", "customer_segments", "channels", "customer_relationships", "revenue_streams", "key_resources", "key_activities", "key_partnerships", "cost_structure"]
        },
        "content": {"type": "string"},
        "issue": {"type": "string"}
      }
    },
    {
      "description": "VPC source schema",
      "required": ["field", "content", "context"],
      "properties": {
        "type": {"const": "vpc"},
        "field": {
          "type": "string",
          "pattern": "^(customer_profile|value_map)\\.(jobs_to_be_done|pains|gains|products_services|pain_relievers|gain_creators)$"
        },
        "content": {"type": "string"},
        "context": {"type": "string"}
      }
    },
    {
      "description": "VPS source schema",
      "required": ["field", "content", "context"],
      "properties": {
        "type": {"const": "vps"},
        "field": {
          "type": "string",
          "enum": ["statement", "components", "target_customer", "problem", "solution", "benefit"]
        },
        "content": {"type": "string"},
        "context": {"type": "string"}
      }
    }
  ]
}
```

---

**End of Architecture Reference Documentation**
