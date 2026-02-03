# Market Research Analysis - Revised Architecture
## Assumption-Driven Multi-Agent System

---

## Executive Summary

**Key Changes Based on Feedback**:
1. **Assumption-Driven**: Analysis focuses on validating specific assumptions from VMP project
2. **No External Research**: Remove Tavily, use deeper PV report analysis instead
3. **Enhanced Context**: Include personas, customer profiles, hypotheses, assumptions from VMP
4. **Hybrid Database**: Extend vmp_projects + dedicated analysis sessions table
5. **Fixed Report Format**: Follows exact structure provided

---

## Revised Architecture

### Core Principle: Assumption Validation
```
Market Research Data (unstructured) 
    ↓
Correlation Engine (finds relevant data for each assumption)
    ↓
5 Analysis Agents (Pain, Size, Solution, Gains, JTBD)
    ↓
Assumption Validation (validates/partially validates/invalidates)
    ↓
Structured Report (follows exact format)
```

---

## 1. Enhanced State Management

```python
from typing import TypedDict, List, Dict, Any
from typing_extensions import Annotated
import operator

class AssumptionAnalysisState(TypedDict):
    # Project context
    project_id: str
    research_document_id: str
    
    # VMP context (ENHANCED)
    project_context: Dict[str, Any]  # Full VMP data
    current_assumption: Dict[str, Any]  # Current assumption being analyzed
    target_persona: Dict[str, Any]     # Persona for current assumption
    
    # Analysis results per assumption
    assumption_analyses: Annotated[List[Dict], operator.add]
    
    # Final report
    report_sections: Dict[str, Any]
    final_report: str
    
    # Control
    current_step: str
    processed_assumptions: List[str]
```

### Enhanced Context Loading (Following VMP Pattern)
```python
async def _get_project_context_for_analysis(self, project_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Get project context for market research analysis.
    
    FOLLOWS EXACT SAME PATTERN as field_prep_service._get_project_context_personas_only()
    """
    try:
        # Get project data from database (same as VMP pattern)
        project_data = await self.db_adapter.get_vmp_project(project_id, tenant_id)
        if not project_data:
            return {
                'success': False,
                'error': "Project not found"
            }
        
        # Extract personas using same method as field prep service
        personas = await self.db_adapter.get_project_personas(project_id)
        print(f"🔍 DEBUG: [ANALYSIS] Retrieved {len(personas)} personas for project {project_id}")
        
        # Extract customer profile from vpc_data (same nested structure)
        vpc_data = project_data.get('vpc_data', {})
        vpcs = vpc_data.get('vpcs', {})
        
        # Combine customer profiles from all personas (same logic)
        combined_customer_profile = {
            'jtbd': [],
            'pains': [],
            'gains': []
        }
        
        for persona_id, vpc_info in vpcs.items():
            persona_customer_profile = vpc_info.get('customer_profile', {})
            if persona_customer_profile:
                combined_customer_profile['jtbd'].extend(persona_customer_profile.get('jobs_to_be_done', []))
                combined_customer_profile['pains'].extend(persona_customer_profile.get('pains', []))
                combined_customer_profile['gains'].extend(persona_customer_profile.get('gains', []))
        
        # Get field prep data (hypotheses, assumptions, questionnaires)
        field_prep_data = project_data.get('field_prep_data', {})
        hypotheses = field_prep_data.get('hypotheses', [])
        assumptions = field_prep_data.get('assumptions', [])
        questionnaires = field_prep_data.get('questionnaires', [])
        
        print(f"🔍 DEBUG: [ANALYSIS] Found {len(hypotheses)} hypotheses, {len(assumptions)} assumptions")
        
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
                'project_data': project_data,
                
                # Core VMP context (SAME AS FIELD PREP)
                'personas': personas,
                'customer_profile': combined_customer_profile,
                'hypotheses': hypotheses,
                'assumptions': assumptions,
                'questionnaires': questionnaires,
                
                # Vector contexts
                'pv_report_context': context_data.get('pv_report_context', []),
                'actionable_insights_context': context_data.get('actionable_insights_context', []),
                
                # VPC data for reference
                'vpc_data': vpc_data
            }
        }
        
    except Exception as e:
        print(f"❌ ERROR: Failed to get project context for analysis: {str(e)}")
        return {
            'success': False,
            'error': f"Failed to get project context: {str(e)}"
        }
```

---

## 2. Market Research Analysis Service (Following VMP Pattern)

### Service Architecture Integration
```python
class MarketResearchAnalysisService:
    """
    Market Research Analysis Service integrated with VMP infrastructure.
    
    FOLLOWS EXACT SAME PATTERN as FieldPrepService and IntegratedVMPService
    """
    
    def __init__(self):
        # Same adapters as VMP services
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
            print(f"🔍 DEBUG: [ANALYSIS] Starting market research analysis for project: {project_id}")
            
            # 1. Get project context (SAME AS VMP PATTERN)
            project_context = await self._get_project_context_for_analysis(project_id, tenant_id)
            if not project_context['success']:
                return project_context
            
            # 2. Validate project has required data
            validation_result = self._validate_project_readiness(project_context['data'])
            if not validation_result['ready']:
                return {
                    'success': False,
                    'error': f"Project not ready for analysis: {validation_result['missing']}"
                }
            
            # 3. Parse and store research documents
            research_doc_id = await self._process_research_documents(
                project_id, pdf_file, csv_file
            )
            
            # 4. Run assumption-driven analysis
            analysis_result = await self._run_assumption_analysis(
                project_context=project_context['data'],
                research_doc_id=research_doc_id,
                target_assumptions=target_assumptions
            )
            
            # 5. Store results in project (SAME PATTERN as field prep)
            await self._store_analysis_results(
                project_id=project_id,
                user_id=user_id,
                analysis_result=analysis_result
            )
            
            return {
                'success': True,
                'analysis_session_id': analysis_result['session_id'],
                'assumptions_analyzed': len(analysis_result['assumption_analyses']),
                'report_preview': analysis_result['final_report'][:500] + "...",
                'message': f"Analyzed {len(analysis_result['assumption_analyses'])} assumptions successfully"
            }
            
        except Exception as e:
            print(f"❌ ERROR: Market research analysis failed: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to analyze market research: {str(e)}"
            }
    
    def _validate_project_readiness(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate project has required data for analysis.
        
        SAME VALIDATION PATTERN as field prep service
        """
        missing_requirements = []
        
        # Check personas
        personas = project_data.get('personas', [])
        if not personas:
            missing_requirements.append("Personas must be identified first")
        
        # Check customer profile
        customer_profile = project_data.get('customer_profile', {})
        if not any([
            customer_profile.get('jtbd', []),
            customer_profile.get('pains', []),
            customer_profile.get('gains', [])
        ]):
            missing_requirements.append("Customer profile must be completed first")
        
        # Check assumptions
        assumptions = project_data.get('assumptions', [])
        if not assumptions:
            missing_requirements.append("Assumptions must be generated first")
        
        return {
            'ready': len(missing_requirements) == 0,
            'missing': missing_requirements
        }
    
    async def _store_analysis_results(
        self,
        project_id: str,
        user_id: str,
        analysis_result: Dict[str, Any]
    ) -> bool:
        """
        Store analysis results in project data.
        
        FOLLOWS SAME PATTERN as field prep service storage
        """
        try:
            # Get current project data
            from src.mint.api.system.core.supabase_client import get_service_role_client
            supabase = get_service_role_client()
            
            project_result = supabase.client.table('vmp_projects').select('*').eq('id', project_id).single().execute()
            if not project_result.data:
                return False
            
            project_data = project_result.data
            
            # Update project with analysis data (SAME PATTERN as field_prep_data)
            analysis_data = project_data.get('analysis_data', {})
            analysis_data.update({
                'session_id': analysis_result['session_id'],
                'assumption_analyses': analysis_result['assumption_analyses'],
                'final_report': analysis_result['final_report'],
                'analyzed_at': datetime.utcnow().isoformat(),
                'stage': 'analysis_completed'
            })
            
            # Update project status
            result = supabase.client.table('vmp_projects').update({
                'analysis_data': analysis_data,
                'analysis_status': 'completed',
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ ERROR: Failed to store analysis results: {str(e)}")
            return False
```

---

## 3. Assumption-Driven Workflow

### LangGraph Flow
```python
def build_assumption_analysis_graph():
    workflow = StateGraph(AssumptionAnalysisState)
    
    # Core nodes
    workflow.add_node("initialize", initialize_analysis)
    workflow.add_node("pain_analysis", PainAnalysisAgent().analyze_for_assumption)
    workflow.add_node("size_analysis", SizeFrequencyAgent().analyze_for_assumption)
    workflow.add_node("solution_analysis", SolutionAnalysisAgent().analyze_for_assumption)
    workflow.add_node("gains_analysis", GainsAnalysisAgent().analyze_for_assumption)
    workflow.add_node("jtbd_analysis", JTBDAnalysisAgent().analyze_for_assumption)
    workflow.add_node("validate_assumption", AssumptionValidator().validate)
    workflow.add_node("pv_comparison", PVComparisonAgent().compare)
    workflow.add_node("synthesize_report", ReportSynthesizer().synthesize)
    
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
    
    # Conditional: next assumption or synthesize
    workflow.add_conditional_edges(
        "pv_comparison",
        route_next_assumption,
        {
            "next_assumption": "pain_analysis",
            "synthesize": "synthesize_report"
        }
    )
    
    workflow.add_edge("synthesize_report", END)
    
    return workflow.compile()
```

---

## 3. Correlation Engine

### Core Challenge: Map Unstructured Research → Specific Assumptions

```python
class CorrelationEngine:
    """Maps market research data to specific assumptions."""
    
    async def find_relevant_data_for_assumption(
        self,
        assumption: Dict[str, Any],
        research_document_id: str,
        analysis_type: str  # 'pain', 'size', 'solution', 'gains', 'jtbd'
    ) -> List[Dict[str, Any]]:
        """
        Find market research data relevant to a specific assumption.
        
        This is the KEY function that creates correlation between
        assumptions and unstructured market data.
        """
        
        assumption_text = assumption['text']
        persona_name = assumption['persona_name']
        
        # Create targeted search query
        search_query = self._create_correlation_query(
            assumption_text=assumption_text,
            persona_name=persona_name,
            analysis_type=analysis_type
        )
        
        # Semantic search in market research data
        relevant_chunks = await self.vector_store.retrieve_research_context(
            query=search_query,
            document_id=research_document_id,
            limit=20
        )
        
        # Filter and rank by relevance to assumption
        filtered_chunks = await self._filter_by_assumption_relevance(
            chunks=relevant_chunks,
            assumption=assumption,
            analysis_type=analysis_type
        )
        
        return filtered_chunks
    
    def _create_correlation_query(
        self,
        assumption_text: str,
        persona_name: str,
        analysis_type: str
    ) -> str:
        """Create search query to find data relevant to assumption."""
        
        type_keywords = {
            'pain': 'problems challenges difficulties frustrations obstacles pain points',
            'size': 'frequency percentage statistics how often how many numbers data',
            'solution': 'current solutions alternatives workarounds existing tools methods',
            'gains': 'benefits advantages value outcomes results improvements',
            'jtbd': 'tasks jobs goals objectives trying to accomplish need to do'
        }
        
        keywords = type_keywords.get(analysis_type, '')
        
        return f"""
        {assumption_text}
        {persona_name}
        {keywords}
        """
```

---

## 4. Assumption-Focused Analysis Agents

### Pain Analysis Agent (Revised)
```python
class PainAnalysisAgent:
    """Analyze pain points for specific assumption validation."""
    
    async def analyze_for_assumption(self, state: AssumptionAnalysisState) -> AssumptionAnalysisState:
        """Analyze pain points to validate current assumption."""
        
        assumption = state['current_assumption']
        persona = state['target_persona']
        
        print(f"🔍 [Pain Analysis] Assumption: {assumption['text'][:60]}...")
        
        # Find relevant market research data for this assumption
        correlation_engine = CorrelationEngine()
        relevant_data = await correlation_engine.find_relevant_data_for_assumption(
            assumption=assumption,
            research_document_id=state['research_document_id'],
            analysis_type='pain'
        )
        
        if len(relevant_data) < 2:
            # Insufficient data for this assumption
            analysis_result = self._create_insufficient_data_response(assumption, persona)
        else:
            # Perform full analysis
            analysis_result = await self._analyze_pain_points(
                assumption=assumption,
                persona=persona,
                research_data=relevant_data,
                project_context=state['project_context']
            )
        
        # Store result
        state['assumption_analyses'].append({
            "assumption_id": assumption['id'],
            "assumption_text": assumption['text'],
            "persona_name": persona['name'],
            "analysis_type": "pain_points",
            "analysis": analysis_result,
            "data_chunks_used": len(relevant_data)
        })
        
        return state
    
    async def _analyze_pain_points(
        self,
        assumption: Dict,
        persona: Dict,
        research_data: List[Dict],
        project_context: Dict
    ) -> Dict[str, Any]:
        """Perform detailed pain point analysis for assumption."""
        
        # Get expected pains from customer profile
        expected_pains = self._get_expected_pains(persona['id'], project_context)
        
        # Format research context
        research_context = "\n\n".join([
            f"Finding {i+1}: {chunk['content']}"
            for i, chunk in enumerate(research_data)
        ])
        
        # Create assumption-focused prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are analyzing market research data to validate a specific assumption about pain points.

Your task:
1. Analyze the research data for pain points related to the assumption
2. Build a claim about what the data suggests
3. Assess accuracy level (high/medium/low) based on evidence strength
4. Focus specifically on validating or invalidating the given assumption

The assumption you're testing: {assumption_text}
Target persona: {persona_name}"""),
            ("user", """
ASSUMPTION TO VALIDATE: {assumption_text}

PERSONA: {persona_name} - {persona_description}

EXPECTED PAIN POINTS (from Customer Profile):
{expected_pains}

MARKET RESEARCH DATA:
{research_context}

ANALYSIS TASK:
1. What pain points does the research data reveal for {persona_name}?
2. Do these pain points support or contradict the assumption?
3. What is your confidence level in this finding?
4. Provide specific evidence quotes and any statistical data.

Generate a claim about pain points and assess how well it validates the assumption.""")
        ])
        
        # Use structured output
        structured_llm = self.llm.with_structured_output(PainAnalysisOutput)
        chain = prompt | structured_llm
        
        result = await chain.ainvoke({
            "assumption_text": assumption['text'],
            "persona_name": persona['name'],
            "persona_description": persona['description'],
            "expected_pains": self._format_expected_pains(expected_pains),
            "research_context": research_context
        })
        
        return result.model_dump()
```

---

## 5. Database Schema (Hybrid Approach)

### Extend vmp_projects
```sql
-- Add analysis tracking to main project table
ALTER TABLE vmp_projects ADD COLUMN analysis_status VARCHAR(50) DEFAULT 'not_started';
-- Values: 'not_started', 'processing', 'completed', 'failed'

ALTER TABLE vmp_projects ADD COLUMN analysis_summary JSONB;
-- Structure: {
--   "total_assumptions": 3,
--   "validated": 1,
--   "partially_validated": 1,
--   "invalidated": 1,
--   "last_analysis_date": "2025-01-01T12:00:00Z"
-- }
```

### Dedicated Analysis Sessions
```sql
CREATE TABLE vmp_analysis_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES vmp_projects(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    
    -- Uploaded research files
    pdf_document_id UUID REFERENCES documents(id),
    csv_document_id UUID REFERENCES documents(id),
    
    -- Analysis configuration
    analysis_config JSONB DEFAULT '{}'::jsonb,
    -- Structure: {
    --   "target_assumptions": ["assumption-001", "assumption-002"],
    --   "enable_pv_comparison": true,
    --   "analysis_depth": "standard"
    -- }
    
    -- Results
    assumption_analyses JSONB,  -- Detailed analysis per assumption
    report_sections JSONB,      -- Structured report sections
    final_report_md TEXT,       -- Final markdown report
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'processing',
    progress INTEGER DEFAULT 0,  -- 0-100
    current_assumption VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT fk_analysis_project FOREIGN KEY (project_id) REFERENCES vmp_projects(id)
);

CREATE INDEX idx_analysis_sessions_project ON vmp_analysis_sessions(project_id);
CREATE INDEX idx_analysis_sessions_status ON vmp_analysis_sessions(status);
CREATE INDEX idx_analysis_sessions_user ON vmp_analysis_sessions(user_id);
```

---

## 6. Report Format Implementation

### Exact Structure You Specified
```python
class ReportSynthesizer:
    """Generate report in exact format specified."""
    
    async def synthesize(self, state: AssumptionAnalysisState) -> AssumptionAnalysisState:
        """Generate final report following exact format."""
        
        project_context = state['project_context']
        analyses = state['assumption_analyses']
        
        # Group analyses by assumption
        assumption_groups = self._group_analyses_by_assumption(analyses)
        
        # Generate report sections
        sections = []
        
        # Introduction
        intro = self._generate_introduction(project_context)
        sections.append(intro)
        
        # For each assumption (Key Assumption #1, #2, #3)
        for i, (assumption_id, assumption_analyses) in enumerate(assumption_groups.items(), 1):
            assumption_section = await self._generate_assumption_section(
                assumption_number=i,
                assumption_id=assumption_id,
                analyses=assumption_analyses,
                project_context=project_context
            )
            sections.append(assumption_section)
        
        # General conclusion
        conclusion = self._generate_general_conclusion(assumption_groups)
        sections.append(conclusion)
        
        # Combine
        final_report = "\n\n".join(sections)
        
        state['final_report'] = final_report
        
        return state
    
    async def _generate_assumption_section(
        self,
        assumption_number: int,
        assumption_id: str,
        analyses: List[Dict],
        project_context: Dict
    ) -> str:
        """Generate section for one assumption following exact format."""
        
        # Get assumption details
        assumption = self._find_assumption_by_id(assumption_id, project_context)
        
        # Extract analyses by type
        pain_analysis = self._find_analysis_by_type(analyses, 'pain_points')
        size_analysis = self._find_analysis_by_type(analyses, 'size_frequency')
        solution_analysis = self._find_analysis_by_type(analyses, 'solutions')
        gains_analysis = self._find_analysis_by_type(analyses, 'gains')
        jtbd_analysis = self._find_analysis_by_type(analyses, 'jtbd')
        
        section = f"""## Key Assumption #{assumption_number}: {assumption['text']}

### 1. The Target User's Main Pain Points

**Analysis**: {pain_analysis['analysis']['claim']}

**Accuracy Level**: {pain_analysis['analysis']['accuracy_level'].upper()}

**{self._get_validation_header(pain_analysis['analysis']['accuracy_level'])}**:
{self._get_validation_content(pain_analysis)}

**Comparison with Problem Validation Report Findings**:
{self._get_pv_comparison(pain_analysis, 'pain_points')}

### 2. The Problem Size & Frequency

**Analysis**: {size_analysis['analysis']['claim']}

**Accuracy Level**: {size_analysis['analysis']['accuracy_level'].upper()}

**{self._get_validation_header(size_analysis['analysis']['accuracy_level'])}**:
{self._get_validation_content(size_analysis)}

**Comparison with Problem Validation Report Findings**:
{self._get_pv_comparison(size_analysis, 'size_frequency')}

### 3. Ways in Which the Target User is Addressing the Problem

**Analysis**: {solution_analysis['analysis']['claim']}

**Accuracy Level**: {solution_analysis['analysis']['accuracy_level'].upper()}

**{self._get_validation_header(solution_analysis['analysis']['accuracy_level'])}**:
{self._get_validation_content(solution_analysis)}

**Comparison with Problem Validation Report Findings**:
{self._get_pv_comparison(solution_analysis, 'solutions')}

**Conclusion**: {self._generate_assumption_conclusion(assumption_id, analyses)}
"""
        
        return section
    
    def _get_validation_header(self, accuracy_level: str) -> str:
        """Get validation header based on accuracy level."""
        if accuracy_level == 'high':
            return "Supporting Detail"
        elif accuracy_level == 'medium':
            return "Supporting & Debunking Detail"
        else:
            return "Debunking Detail"
```

---

## 7. API Implementation (Following VMP Endpoint Pattern)

```python
# Add to existing VMP endpoints in src/vpm/api/endpoints.py

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
        
        # Get analysis service (SAME PATTERN as get_integrated_vmp_service)
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
            # Handle different error types (SAME AS VMP PATTERN)
            if "not ready" in result['error'].lower():
                raise HTTPException(status_code=400, detail=result['error'])
            elif "credits" in result['error'].lower():
                raise HTTPException(status_code=402, detail=result['error'])
            else:
                raise HTTPException(status_code=500, detail=result['error'])
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze market research: {str(e)}"
        )

@router.get("/api/v2/vmp/projects/{project_id}/analysis-report")
async def get_analysis_report(
    project_id: str,
    format: str = Query("markdown", description="Report format: markdown, json"),
    user_id: str = Depends(get_current_user)
):
    """
    Get market research analysis report for project.
    
    FOLLOWS SAME PATTERN as other VMP GET endpoints
    """
    try:
        tenant_id = await get_user_tenant_id(user_id)
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")
        
        service = get_market_research_analysis_service()
        result = await service.get_analysis_report(project_id, tenant_id, format)
        
        if result['success']:
            return {
                "success": True,
                "data": result['report_data'],
                "message": "Analysis report retrieved successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get analysis report: {str(e)}"
        )

@router.get("/api/v2/vmp/projects/{project_id}/analysis-status")
async def get_analysis_status(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get market research analysis status for project.
    
    SAME PATTERN as field prep progress endpoints
    """
    try:
        tenant_id = await get_user_tenant_id(user_id)
        if not tenant_id:
            raise HTTPException(status_code=400, detail="User tenant not found")
        
        service = get_market_research_analysis_service()
        result = await service.get_analysis_status(project_id, tenant_id)
        
        return {
            "success": True,
            "data": result,
            "message": "Analysis status retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get analysis status: {str(e)}"
        )

# Service factory function (SAME PATTERN as VMP)
def get_market_research_analysis_service():
    """Get market research analysis service instance."""
    return MarketResearchAnalysisService()
```

---

## Key Advantages of This Approach

1. **Assumption-Focused**: Direct validation of specific testable claims
2. **Correlation Engine**: Smart mapping between unstructured data and structured assumptions  
3. **Complete VMP Integration**: Uses all project context (personas, profiles, hypotheses, assumptions)
4. **Exact Report Format**: Follows your specified structure precisely
5. **Multiple Sessions**: Support for iterative analysis as new research comes in
6. **Hybrid Database**: Best of both worlds - simple queries + detailed storage

The system now directly answers: **"Does our market research validate assumption X?"** rather than just analyzing general themes.
