"""
LangGraph workflow for solution critique
Orchestrates all agents with parallel critique generation
"""
import logging
import asyncio
import uuid
from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END

from ..models.state_models import SolutionCritiqueState
from ..agents.market_viability_agent import MarketViabilityCritiqueAgent
from ..agents.operational_feasibility_agent import OperationalFeasibilityCritiqueAgent
from ..agents.business_model_agent import BusinessModelCritiqueAgent
from ..agents.competitive_differentiation_agent import CompetitiveDifferentiationCritiqueAgent
from ..agents.technical_scalability_agent import TechnicalScalabilityCritiqueAgent
from ..agents.dominant_business_logic_agent import DominantBusinessLogicCritiqueAgent
from ..agents.report_synthesizer_agent import CritiqueReportSynthesizerAgent
from .context_loader import ContextLoader
from .query_planner import QueryPlanner
from .web_researcher import WebResearcher
from src.mvp.adapters.database_adapter import MVPDatabaseAdapter

logger = logging.getLogger(__name__)


class SolutionCritiqueWorkflow:
    """LangGraph workflow for solution critique with parallel agent execution"""
    
    def __init__(self):
        # Services
        self.context_loader = ContextLoader()
        self.query_planner = QueryPlanner()
        self.web_researcher = WebResearcher()
        self.db_adapter = MVPDatabaseAdapter(use_service_role=True)
        
        # Agents (parallel execution for critique agents)
        self.market_agent = MarketViabilityCritiqueAgent()
        self.operational_agent = OperationalFeasibilityCritiqueAgent()
        self.business_model_agent = BusinessModelCritiqueAgent()
        self.competitive_agent = CompetitiveDifferentiationCritiqueAgent()
        self.technical_agent = TechnicalScalabilityCritiqueAgent()
        self.dominant_logic_agent = DominantBusinessLogicCritiqueAgent()
        self.synthesizer_agent = CritiqueReportSynthesizerAgent()
        
        # Build workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow with parallel critique execution"""
        logger.info("🔨 Building LangGraph workflow...")
        
        workflow = StateGraph(SolutionCritiqueState)
        
        # Add nodes
        workflow.add_node("prepare_context", self._prepare_context_node)
        workflow.add_node("plan_queries", self._plan_queries_node)
        workflow.add_node("execute_research", self._execute_research_node)
        
        # PARALLEL critique nodes (all run simultaneously)
        workflow.add_node("market_critique", self._market_critique_node)
        workflow.add_node("operational_critique", self._operational_critique_node)
        workflow.add_node("business_model_critique", self._business_model_critique_node)
        workflow.add_node("competitive_critique", self._competitive_critique_node)
        workflow.add_node("technical_critique", self._technical_critique_node)
        workflow.add_node("dominant_logic_critique", self._dominant_logic_critique_node)
        
        workflow.add_node("synthesize_report", self._synthesize_report_node)
        workflow.add_node("save_to_database", self._save_to_database_node)
        
        # Define edges (sequential → parallel → sequential)
        workflow.set_entry_point("prepare_context")
        workflow.add_edge("prepare_context", "plan_queries")
        workflow.add_edge("plan_queries", "execute_research")
        
        # PARALLEL EXECUTION: All 6 critique agents run after research
        workflow.add_edge("execute_research", "market_critique")
        workflow.add_edge("execute_research", "operational_critique")
        workflow.add_edge("execute_research", "business_model_critique")
        workflow.add_edge("execute_research", "competitive_critique")
        workflow.add_edge("execute_research", "technical_critique")
        workflow.add_edge("execute_research", "dominant_logic_critique")
        
        # All critiques converge to synthesis (waits for all to complete)
        workflow.add_edge("market_critique", "synthesize_report")
        workflow.add_edge("operational_critique", "synthesize_report")
        workflow.add_edge("business_model_critique", "synthesize_report")
        workflow.add_edge("competitive_critique", "synthesize_report")
        workflow.add_edge("technical_critique", "synthesize_report")
        workflow.add_edge("dominant_logic_critique", "synthesize_report")
        
        workflow.add_edge("synthesize_report", "save_to_database")
        workflow.add_edge("save_to_database", END)
        
        logger.info("✅ LangGraph workflow built successfully")
        logger.info("   Nodes: 12 (3 sequential + 6 parallel + 2 sequential)")
        return workflow.compile()
    
    async def run_critique(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Run complete solution critique workflow"""
        try:
            session_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            
            logger.info(f"🚀 Starting solution critique workflow")
            logger.info(f"   Project: {project_id}")
            logger.info(f"   Session: {session_id}")
            logger.info(f"   Started: {start_time.isoformat()}")
            
            # Initialize state
            initial_state = {
                'project_id': project_id,
                'tenant_id': tenant_id,
                'user_id': user_id,
                'session_id': session_id,
                'status': 'processing',
                'geography': '',
                'industry': '',
                'solution_description': '',
                'vpc_data': {},
                'vps_data': {},
                'bmc_data': {},
                'research_queries': [],
                'search_results': {},
                'market_critique': None,
                'operational_critique': None,
                'business_model_critique': None,
                'competitive_critique': None,
                'technical_critique': None,
                'dominant_logic_critique': None,
                'all_critiques': [],
                'final_report': None,
                'completed_at': None,
                'error': None
            }
            
            # Run workflow
            logger.info("⚙️  Executing LangGraph workflow...")
            final_state = await self.workflow.ainvoke(initial_state)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ Solution critique workflow completed")
            logger.info(f"   Duration: {duration:.1f} seconds")
            logger.info(f"   Critiques generated: {len(final_state.get('all_critiques', []))}")
            logger.info(f"   Status: {final_state.get('status')}")
            
            return final_state
            
        except Exception as e:
            logger.error(f"❌ Solution critique workflow failed: {e}")
            raise
    
    # ==================== WORKFLOW NODES ====================
    
    async def _prepare_context_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Load project context (VPC, VPS, BMC)"""
        logger.info("📋 Step 1/9: Preparing context...")
        
        try:
            context, error = await self.context_loader.load_project_context(
                state['project_id'],
                state['tenant_id']
            )
            
            if error:
                state['error'] = error
                state['status'] = 'failed'
                logger.error(f"   ❌ Context loading failed: {error}")
                return state
            
            # Update state with context
            state.update(context)
            logger.info(f"   ✅ Context loaded")
            
        except Exception as e:
            logger.error(f"   ❌ Context preparation failed: {e}")
            state['error'] = str(e)
            state['status'] = 'failed'
        
        return state
    
    async def _plan_queries_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Plan research queries"""
        logger.info("🔍 Step 2/9: Planning research queries...")
        
        try:
            queries = await self.query_planner.plan_research_queries(
                context=state,
                tenant_id=state['tenant_id'],
                user_id=state['user_id'],
                project_id=state['project_id']
            )
            
            state['research_queries'] = queries
            logger.info(f"   ✅ Generated {len(queries)} queries")
            
        except Exception as e:
            logger.error(f"   ❌ Query planning failed: {e}")
            state['error'] = str(e)
            state['status'] = 'failed'
        
        return state
    
    async def _execute_research_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Execute web research"""
        logger.info("🌐 Step 3/9: Executing web research...")
        
        try:
            results = await self.web_researcher.execute_research(
                state['research_queries']
            )
            
            state['search_results'] = results
            
            # Count total results
            total_results = sum(
                sum(len(q.get('results', [])) for q in cat_results)
                for cat_results in results.values()
            )
            logger.info(f"   ✅ Collected {total_results} search results")
            
        except Exception as e:
            logger.error(f"   ❌ Web research failed: {e}")
            state['error'] = str(e)
            state['status'] = 'failed'
        
        return state
    
    async def _market_critique_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Market viability critique (PARALLEL)"""
        logger.info("📊 Step 4a/9: Generating market viability critique...")
        
        try:
            critique = await self.market_agent.generate_critique(
                context=state,
                search_results=state['search_results'],
                tenant_id=state['tenant_id'],
                user_id=state['user_id'],
                project_id=state['project_id']
            )
            
            if critique:
                logger.info(f"   ✅ Market critique generated")
            else:
                logger.warning(f"   ⚠️  Market critique failed")
                
        except Exception as e:
            logger.error(f"   ❌ Market critique failed: {e}")
            critique = None
        
        # Only return the key this node modifies
        return {'market_critique': critique}
    
    async def _operational_critique_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Operational feasibility critique (PARALLEL)"""
        logger.info("⚙️  Step 4b/9: Generating operational feasibility critique...")
        
        try:
            critique = await self.operational_agent.generate_critique(
                context=state,
                search_results=state['search_results'],
                tenant_id=state['tenant_id'],
                user_id=state['user_id'],
                project_id=state['project_id']
            )
            
            if critique:
                logger.info(f"   ✅ Operational critique generated")
            else:
                logger.warning(f"   ⚠️  Operational critique failed")
                
        except Exception as e:
            logger.error(f"   ❌ Operational critique failed: {e}")
            critique = None
        
        # Only return the key this node modifies
        return {'operational_critique': critique}
    
    async def _business_model_critique_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Business model critique (PARALLEL)"""
        logger.info("💰 Step 4c/9: Generating business model critique...")
        
        try:
            critique = await self.business_model_agent.generate_critique(
                context=state,
                search_results=state['search_results'],
                tenant_id=state['tenant_id'],
                user_id=state['user_id'],
                project_id=state['project_id']
            )
            
            if critique:
                logger.info(f"   ✅ Business model critique generated")
            else:
                logger.warning(f"   ⚠️  Business model critique failed")
                
        except Exception as e:
            logger.error(f"   ❌ Business model critique failed: {e}")
            critique = None
        
        # Only return the key this node modifies
        return {'business_model_critique': critique}
    
    async def _competitive_critique_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Competitive differentiation critique (PARALLEL)"""
        logger.info("🏆 Step 4d/9: Generating competitive differentiation critique...")
        
        try:
            critique = await self.competitive_agent.generate_critique(
                context=state,
                search_results=state['search_results'],
                tenant_id=state['tenant_id'],
                user_id=state['user_id'],
                project_id=state['project_id']
            )
            
            if critique:
                logger.info(f"   ✅ Competitive critique generated")
            else:
                logger.warning(f"   ⚠️  Competitive critique failed")
                
        except Exception as e:
            logger.error(f"   ❌ Competitive critique failed: {e}")
            critique = None
        
        # Only return the key this node modifies
        return {'competitive_critique': critique}
    
    async def _technical_critique_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Technical scalability critique (PARALLEL)"""
        logger.info("🔧 Step 4e/9: Generating technical scalability critique...")
        
        try:
            critique = await self.technical_agent.generate_critique(
                context=state,
                search_results=state['search_results'],
                tenant_id=state['tenant_id'],
                user_id=state['user_id'],
                project_id=state['project_id']
            )
            
            if critique:
                logger.info(f"   ✅ Technical critique generated")
            else:
                logger.warning(f"   ⚠️  Technical critique failed")
                
        except Exception as e:
            logger.error(f"   ❌ Technical critique failed: {e}")
            critique = None
        
        # Only return the key this node modifies
        return {'technical_critique': critique}
    
    async def _dominant_logic_critique_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Dominant business logic critique (PARALLEL)"""
        logger.info("🎯 Step 4f/9: Generating dominant business logic critique...")
        
        try:
            critique = await self.dominant_logic_agent.generate_critique(
                context=state,
                search_results=state['search_results'],
                tenant_id=state['tenant_id'],
                user_id=state['user_id'],
                project_id=state['project_id']
            )
            
            if critique:
                logger.info(f"   ✅ Dominant logic critique generated")
            else:
                logger.warning(f"   ⚠️  Dominant logic critique failed")
                
        except Exception as e:
            logger.error(f"   ❌ Dominant logic critique failed: {e}")
            critique = None
        
        # Only return the key this node modifies
        return {'dominant_logic_critique': critique}
    
    async def _synthesize_report_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Synthesize final report (waits for all critiques)"""
        logger.info("📝 Step 5/9: Synthesizing critique report...")
        
        try:
            # Collect all successful critiques
            all_critiques = [
                critique for critique in [
                    state.get('market_critique'),
                    state.get('operational_critique'),
                    state.get('business_model_critique'),
                    state.get('competitive_critique'),
                    state.get('technical_critique'),
                    state.get('dominant_logic_critique')
                ] if critique is not None
            ]
            
            if not all_critiques:
                raise ValueError("No critiques generated successfully")
            
            state['all_critiques'] = all_critiques
            logger.info(f"   Collected {len(all_critiques)} successful critiques")
            
            # Prepare search metadata
            search_metadata = {
                'queries_executed': len(state.get('research_queries', [])),
                'web_sources_analyzed': sum(
                    sum(len(q.get('results', [])) for q in cat_results)
                    for cat_results in state.get('search_results', {}).values()
                )
            }
            
            # Synthesize report
            final_report = await self.synthesizer_agent.synthesize_report(
                all_critiques=all_critiques,
                context=state,
                search_metadata=search_metadata,
                tenant_id=state['tenant_id'],
                user_id=state['user_id'],
                project_id=state['project_id']
            )
            
            state['final_report'] = final_report
            state['status'] = 'completed'
            state['completed_at'] = datetime.utcnow().isoformat()
            
            logger.info(f"   ✅ Report synthesized")
            
        except Exception as e:
            logger.error(f"   ❌ Report synthesis failed: {e}")
            state['error'] = str(e)
            state['status'] = 'failed'
        
        return state
    
    async def _save_to_database_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Save critique to database"""
        logger.info("💾 Step 6/9: Saving to database...")
        
        try:
            # Prepare data for storage
            critique_data = {
                'session_id': state['session_id'],
                'status': state['status'],
                'generated_at': state.get('final_report', {}).get('generated_at'),
                'completed_at': state['completed_at'],
                'critique_report': state.get('final_report'),
                'error': state.get('error')
            }
            
            # Save to database
            from datetime import datetime
            response = self.db_adapter.supabase.client.table('vmp_projects').update({
                'soln_critique_data': critique_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', state['project_id']).eq('tenant_id', state['tenant_id']).execute()
            
            if response.data:
                logger.info(f"   ✅ Saved to database")
                
                # 📊 WORKFLOW STATUS: Mark Solution Critique as completed
                if state['status'] == 'completed':
                    try:
                        from src.vpm.services.workflow_status_service import get_workflow_status_service, WorkflowStage
                        workflow_service = get_workflow_status_service()
                        workflow_service.set_stage_completed(
                            project_id=state['project_id'],
                            tenant_id=state['tenant_id'],
                            stage=WorkflowStage.SOLUTION_CRITIQUE
                        )
                        logger.info(f"   ✅ Workflow status updated")
                    except Exception as status_error:
                        logger.warning(f"   ⚠️ Workflow status update failed (non-blocking): {status_error}")
            else:
                logger.warning(f"   ⚠️  Database save may have failed")
            
            # ✅ AUTOMATIC: Prepare report for chat (AFTER database save)
            # This is NON-BLOCKING - errors won't fail the workflow
            if state['status'] == 'completed' and state.get('final_report'):
                try:
                    logger.info("💬 AUTO-PREPARE: Chunking critique report for chat functionality...")
                    
                    from ..services.critique_report_chunking_service import CritiqueReportChunkingService
                    chunking_service = CritiqueReportChunkingService()
                    
                    chunk_result = await chunking_service.chunk_and_embed_report(
                        project_id=state['project_id'],
                        tenant_id=state['tenant_id']
                    )
                    
                    if chunk_result["success"]:
                        logger.info(f"✅ AUTO-PREPARE: Chat ready with {chunk_result['chunk_count']} chunks")
                    else:
                        logger.warning(f"⚠️ AUTO-PREPARE: Failed - {chunk_result.get('message', 'Unknown error')}")
                        
                except Exception as e:
                    # Non-blocking - chat preparation failure doesn't fail workflow
                    logger.error(f"❌ AUTO-PREPARE: Error preparing chat: {e}")
                    logger.info("   Workflow continues despite chat preparation error")
            
        except Exception as e:
            logger.error(f"   ❌ Database save failed: {e}")
            # Don't fail the workflow, just log the error
        
        return state
