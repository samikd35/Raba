# Market Research Analysis Module
## Assumption-Driven Analysis Integrated with VMP Workflow

---

## Overview

Market Research Analysis module that validates VMP project assumptions using uploaded research data (PDF interviews, CSV surveys). **Follows exact same patterns as existing VMP services** for seamless integration.

### Key Features
- **Assumption-Driven**: Validates specific assumptions from VMP projects
- **VMP Integration**: Uses same adapters, context loading, and storage patterns
- **LangGraph Orchestration**: Multi-agent analysis workflow
- **Structured Reports**: Follows exact report format specified
- **Project Lifecycle**: Integrates as Phase 6 of VMP workflow

---

## 1. Project Structure (Following VMP Pattern)

```
Backend/src/market_research/
├── __init__.py
├── services/
│   ├── __init__.py
│   ├── market_research_analysis_service.py  # Main service (follows VMP pattern)
│   ├── document_parser_service.py           # PDF/CSV parsing
│   └── correlation_engine.py                # Maps research data to assumptions
├── agents/
│   ├── __init__.py
│   ├── base_agent.py                        # Base analysis agent
│   ├── pain_analysis_agent.py               # Pain point validation
│   ├── size_frequency_agent.py              # Problem magnitude analysis
│   ├── solution_analysis_agent.py           # Current solutions analysis
│   ├── gains_analysis_agent.py              # Benefits validation
│   ├── jtbd_analysis_agent.py               # Jobs-to-be-done validation
│   ├── validator_agent.py                   # Accuracy assessment
│   ├── comparison_agent.py                  # PV report correlation
│   └── report_synthesizer_agent.py          # Final report generation
├── models/
│   ├── __init__.py
│   ├── state.py                             # LangGraph state definition
│   └── outputs.py                           # Pydantic output models
└── api/
    ├── __init__.py
    └── endpoints.py                         # API endpoints (added to VMP router)
```

---

## 2. Core State (models/state.py)

```python
from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated
import operator

class AssumptionAnalysisState(TypedDict):
    """
    LangGraph state for assumption-driven market research analysis.
    
    FOLLOWS VMP PATTERN: Uses project context from VMP infrastructure
    """
    
    # Project context (SAME AS VMP SERVICES)
    project_id: str
    tenant_id: str
    research_document_id: str
    
    # VMP context (loaded using same patterns as field_prep_service)
    project_context: Dict[str, Any]  # Full VMP project data
    current_assumption: Dict[str, Any]  # Current assumption being analyzed
    target_persona: Dict[str, Any]     # Persona for current assumption
    
    # Analysis results per assumption (accumulated)
    assumption_analyses: Annotated[List[Dict], operator.add]
    
    # Report generation
    report_sections: Dict[str, Any]
    final_report: str
    
    # Control flow
    current_step: str
    processed_assumptions: List[str]
    errors: Annotated[List[str], operator.add]
```

---

## 3. Main Service (services/market_research_analysis_service.py)

```python
from typing import Dict, Any, List, Optional
from fastapi import UploadFile

# Import VMP adapters (SAME AS ALL VMP SERVICES)
from ..adapters.auth_adapter import get_yuba_auth_adapter
from ..adapters.vector_adapter import get_yuba_vector_adapter
from ..adapters.database_adapter import get_yuba_database_adapter

class MarketResearchAnalysisService:
    """
    Market Research Analysis Service integrated with VMP infrastructure.
    
    FOLLOWS EXACT SAME PATTERN as FieldPrepService and IntegratedVMPService
    """
    
    def __init__(self):
        # Same adapters as all VMP services
        self.db_adapter = get_yuba_database_adapter()
        self.vector_adapter = get_yuba_vector_adapter()
        self.auth_adapter = get_yuba_auth_adapter()
        
        # Analysis-specific components
        self.document_parser = DocumentParserService()
        self.correlation_engine = CorrelationEngine()
        self.analysis_graph = build_assumption_analysis_graph()
    
    async def analyze_market_research(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        pdf_file: Optional[UploadFile] = None,
        csv_file: Optional[UploadFile] = None,
        target_assumptions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for market research analysis.
        
        FOLLOWS SAME PATTERN as field_prep_service.generate_hypothesis()
        """
        try:
            # 1. Get project context (SAME AS VMP PATTERN)
            project_context = await self._get_project_context_for_analysis(project_id, tenant_id)
            if not project_context['success']:
                return project_context
            
            # 2. Validate project readiness
            validation_result = self._validate_project_readiness(project_context['data'])
            if not validation_result['ready']:
                return {
                    'success': False,
                    'error': f"Project not ready: {', '.join(validation_result['missing'])}"
                }
            
            # 3. Process research documents
            research_doc_id = await self._process_research_documents(
                project_id, pdf_file, csv_file
            )
            
            # 4. Run assumption-driven analysis
            analysis_result = await self._run_assumption_analysis(
                project_context=project_context['data'],
                research_doc_id=research_doc_id,
                target_assumptions=target_assumptions
            )
            
            # 5. Store results (SAME PATTERN as field prep)
            await self._store_analysis_results(project_id, user_id, analysis_result)
            
            return {
                'success': True,
                'analysis_session_id': analysis_result['session_id'],
                'assumptions_analyzed': len(analysis_result['assumption_analyses']),
                'report_preview': analysis_result['final_report'][:500] + "...",
                'message': f"Analyzed {len(analysis_result['assumption_analyses'])} assumptions"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Analysis failed: {str(e)}"
            }
    
    async def _get_project_context_for_analysis(self, project_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Get project context for analysis.
        
        FOLLOWS EXACT SAME PATTERN as field_prep_service._get_project_context_personas_only()
        """
        try:
            # Get project data (same as VMP pattern)
            project_data = await self.db_adapter.get_vmp_project(project_id, tenant_id)
            if not project_data:
                return {'success': False, 'error': "Project not found"}
            
            # Extract personas (same method as field prep)
            personas = await self.db_adapter.get_project_personas(project_id)
            
            # Extract customer profile from vpc_data (same nested structure)
            vpc_data = project_data.get('vpc_data', {})
            vpcs = vpc_data.get('vpcs', {})
            
            # Combine customer profiles (same logic as field prep)
            combined_customer_profile = {'jtbd': [], 'pains': [], 'gains': []}
            for persona_id, vpc_info in vpcs.items():
                persona_customer_profile = vpc_info.get('customer_profile', {})
                if persona_customer_profile:
                    combined_customer_profile['jtbd'].extend(
                        persona_customer_profile.get('jobs_to_be_done', [])
                    )
                    combined_customer_profile['pains'].extend(
                        persona_customer_profile.get('pains', [])
                    )
                    combined_customer_profile['gains'].extend(
                        persona_customer_profile.get('gains', [])
                    )
            
            # Get field prep data (hypotheses, assumptions, questionnaires)
            field_prep_data = project_data.get('field_prep_data', {})
            
            # Get dual vector store context (same as VMP pattern)
            context_data = await self.vector_adapter.dual_context_search(
                project_id=project_id,
                query="market research customer validation analysis",
                max_results_per_store=10
            )
            
            return {
                'success': True,
                'data': {
                    'project_id': project_id,
                    'personas': personas,
                    'customer_profile': combined_customer_profile,
                    'hypotheses': field_prep_data.get('hypotheses', []),
                    'assumptions': field_prep_data.get('assumptions', []),
                    'questionnaires': field_prep_data.get('questionnaires', []),
                    'pv_report_context': context_data.get('pv_report_context', []),
                    'actionable_insights_context': context_data.get('actionable_insights_context', []),
                    'project_data': project_data
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f"Failed to get project context: {str(e)}"}
```

---

## 4. LangGraph Workflow (services/orchestrator.py)

```python
from langgraph.graph import StateGraph, END
from ..agents import (
    PainAnalysisAgent, SizeFrequencyAgent, SolutionAnalysisAgent,
    GainsAnalysisAgent, JTBDAnalysisAgent, ValidatorAgent,
    ComparisonAgent, ReportSynthesizerAgent
)
from ..models.state import AssumptionAnalysisState

def build_assumption_analysis_graph():
    """
    Build LangGraph workflow for assumption-driven analysis.
    
    ASSUMPTION-DRIVEN FLOW: For each assumption → 5 analysis types → validation → report
    """
    workflow = StateGraph(AssumptionAnalysisState)
    
    # Core analysis nodes (one per assumption)
    workflow.add_node("initialize", initialize_analysis)
    workflow.add_node("pain_analysis", PainAnalysisAgent().analyze_for_assumption)
    workflow.add_node("size_analysis", SizeFrequencyAgent().analyze_for_assumption)
    workflow.add_node("solution_analysis", SolutionAnalysisAgent().analyze_for_assumption)
    workflow.add_node("gains_analysis", GainsAnalysisAgent().analyze_for_assumption)
    workflow.add_node("jtbd_analysis", JTBDAnalysisAgent().analyze_for_assumption)
    
    # Validation and comparison
    workflow.add_node("validate_assumption", ValidatorAgent().validate)
    workflow.add_node("pv_comparison", ComparisonAgent().compare_with_pv_report)
    
    # Report generation
    workflow.add_node("synthesize_report", ReportSynthesizerAgent().synthesize)
    
    # Entry point
    workflow.set_entry_point("initialize")
    
    # Sequential analysis for each assumption
    workflow.add_edge("initialize", "pain_analysis")
    workflow.add_edge("pain_analysis", "size_analysis")
    workflow.add_edge("size_analysis", "solution_analysis")
    workflow.add_edge("solution_analysis", "gains_analysis")
    workflow.add_edge("gains_analysis", "jtbd_analysis")
    workflow.add_edge("jtbd_analysis", "validate_assumption")
    workflow.add_edge("validate_assumption", "pv_comparison")
    
    # Conditional: next assumption or synthesize report
    workflow.add_conditional_edges(
        "pv_comparison",
        route_next_assumption,
        {
            "next_assumption": "pain_analysis",  # Process next assumption
            "synthesize": "synthesize_report"     # All assumptions done
        }
    )
    
    workflow.add_edge("synthesize_report", END)
    
    return workflow.compile()

def route_next_assumption(state: AssumptionAnalysisState) -> str:
    """Route to next assumption or report synthesis."""
    assumptions = state['project_context']['assumptions']
    processed = state['processed_assumptions']
    
    if len(processed) < len(assumptions):
        return "next_assumption"
    else:
        return "synthesize"
```

---

## 5. API Endpoints (Added to VMP Router)

```python
# Add to existing src/vpm/api/endpoints.py

@router.post("/api/v2/vmp/projects/{project_id}/analyze-market-research")
async def analyze_market_research(
    project_id: str,
    pdf_file: UploadFile = File(None),
    csv_file: UploadFile = File(None),
    target_assumptions: Optional[List[str]] = Body(None),
    user_id: str = Depends(get_current_user)
):
    """
    Analyze market research data for VMP project assumptions.
    
    FOLLOWS EXACT SAME PATTERN as other VMP endpoints
    """
    try:
        # Get tenant_id (SAME AS ALL VMP ENDPOINTS)
        tenant_id = await get_user_tenant_id(user_id)
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")
        
        # Validate files
        if not pdf_file and not csv_file:
            raise HTTPException(
                status_code=400, 
                detail="At least one file (PDF or CSV) must be provided"
            )
        
        # Get service (SAME PATTERN as get_integrated_vmp_service)
        service = get_market_research_analysis_service()
        
        # Run analysis (SAME PATTERN as other VMP operations)
        result = await service.analyze_market_research(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            pdf_file=pdf_file,
            csv_file=csv_file,
            target_assumptions=target_assumptions
        )
        
        if result['success']:
            return {
                "success": True,
                "data": {
                    "analysis_session_id": result['analysis_session_id'],
                    "assumptions_analyzed": result['assumptions_analyzed'],
                    "report_preview": result['report_preview'],
                    "next_step": f"/api/v2/vmp/projects/{project_id}/analysis-report"
                },
                "message": result['message']
            }
        else:
            # Handle errors (SAME AS VMP PATTERN)
            if "not ready" in result['error'].lower():
                raise HTTPException(status_code=400, detail=result['error'])
            else:
                raise HTTPException(status_code=500, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/api/v2/vmp/projects/{project_id}/analysis-report")
async def get_analysis_report(
    project_id: str,
    format: str = Query("markdown", description="Report format: markdown, json"),
    user_id: str = Depends(get_current_user)
):
    """Get market research analysis report."""
    # Implementation follows same pattern as other VMP GET endpoints
    pass

# Service factory (SAME PATTERN as VMP)
def get_market_research_analysis_service():
    return MarketResearchAnalysisService()
```

---

## 6. Database Integration (Extends VMP Schema)

```sql
-- Extend existing vmp_projects table
ALTER TABLE vmp_projects ADD COLUMN analysis_status VARCHAR(50) DEFAULT 'not_started';
ALTER TABLE vmp_projects ADD COLUMN analysis_data JSONB DEFAULT '{}'::jsonb;

-- Structure of analysis_data:
-- {
--   "session_id": "uuid",
--   "assumption_analyses": [...],
--   "final_report": "markdown text",
--   "analyzed_at": "2025-01-01T12:00:00Z",
--   "stage": "analysis_completed"
-- }

-- Optional: Detailed analysis sessions table
CREATE TABLE vmp_analysis_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES vmp_projects(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    
    -- Research files
    pdf_document_id UUID REFERENCES documents(id),
    csv_document_id UUID REFERENCES documents(id),
    
    -- Results
    assumption_analyses JSONB,
    final_report_md TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'processing',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

---

## 7. Environment Variables

```bash
# Same as existing VMP services
OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# No Tavily needed (removed external research)
```

## Key Integration Points

1. **Same Adapters**: Uses `get_yuba_database_adapter()`, `get_yuba_vector_adapter()`
2. **Same Context Loading**: Follows `field_prep_service._get_project_context_personas_only()`
3. **Same Storage Pattern**: Stores results like `field_prep_data` in project
4. **Same API Pattern**: Endpoints follow VMP router structure
5. **Same Error Handling**: Uses VMP error response patterns

This ensures **seamless integration** with the existing VMP workflow! 🚀
