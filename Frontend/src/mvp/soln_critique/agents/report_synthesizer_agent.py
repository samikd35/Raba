"""
Critique Report Synthesizer Agent
Synthesizes all critiques into final structured JSON report using Azure OpenAI gpt-5-mini
"""
import logging
import json
import re
from typing import Dict, Any, List
from datetime import datetime

from src.market_research.utils.ai_service_wrapper import get_ai_service_wrapper
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class CritiqueReportSynthesizerAgent:
    """Synthesizes all critiques into final report with global sources
    
    Uses Azure OpenAI gpt-5-mini for executive summary generation
    """
    
    def __init__(self):
        # AI service configured for ModelUseCase.REPORT_GENERATION (Azure gpt-5-mini)
        self.ai_service = get_ai_service_wrapper()
    
    async def synthesize_report(
        self,
        all_critiques: List[Dict[str, Any]],
        context: Dict[str, Any],
        search_metadata: Dict[str, Any],
        tenant_id: str,
        user_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Generate final structured JSON report
        
        Args:
            all_critiques: List of critique objects from all 5 agents
            context: Project context
            search_metadata: Metadata about search queries executed
            tenant_id: Tenant ID for monitoring
            user_id: User ID for monitoring
            project_id: Project ID for monitoring
            
        Returns:
            Complete critique report with global sources and citations
        """
        try:
            logger.info(f"📊 Synthesizing critique report from {len(all_critiques)} critiques")
            
            # Step 1: De-duplicate and renumber sources globally
            global_sources, source_mapping = self._create_global_sources(all_critiques)
            logger.info(f"   Created global sources list: {len(global_sources)} unique sources")
            
            # Step 2: Renumber citations in all critiques
            updated_critiques = self._renumber_citations(all_critiques, source_mapping)
            
            # Step 3: Calculate severity distribution
            severity_dist = self._calculate_severity_distribution(updated_critiques)
            
            # Step 4: Create monitoring context
            monitoring_context = AIUsageContext(
                tenant_id=tenant_id,
                user_id=user_id,
                feature_id="solution_critique",
                workflow_name="solution_critique_workflow",
                step_name="report_synthesis",
                project_id=project_id
            )
            
            # Step 5: Generate executive summary with AI
            executive_summary = await self._generate_executive_summary(
                updated_critiques,
                context,
                severity_dist,
                monitoring_context
            )
            
            # Step 6: Group critiques by dimension
            critiques_by_dimension = self._group_by_dimension(updated_critiques)
            
            # Step 7: Extract prioritized actions
            prioritized_actions = self._extract_prioritized_actions(updated_critiques)
            
            # Step 8: Build final report structure
            final_report = {
                'project_id': context.get('project_id'),
                'session_id': context.get('session_id'),
                'generated_at': datetime.utcnow().isoformat(),
                'executive_summary': executive_summary,
                'critiques_by_dimension': critiques_by_dimension,
                'all_critiques': updated_critiques,
                'sources': global_sources,  # Global sources list
                'prioritized_actions': prioritized_actions,
                'metadata': {
                    'total_critiques': len(updated_critiques),
                    'severity_distribution': severity_dist,
                    'dimensions_analyzed': 6,
                    'total_sources': len(global_sources),
                    'total_citations': self._count_total_citations(updated_critiques),
                    'ai_model': 'Azure OpenAI gpt-5-mini',
                    'geography': context.get('geography'),
                    'industry': context.get('industry')
                }
            }
            
            logger.info(f"✅ Critique report synthesized successfully")
            logger.info(f"   Total critiques: {len(updated_critiques)}")
            logger.info(f"   Global sources: {len(global_sources)}")
            logger.info(f"   Total citations: {final_report['metadata']['total_citations']}")
            
            return final_report
            
        except Exception as e:
            logger.error(f"❌ Report synthesis failed: {e}")
            raise
    
    def _create_global_sources(
        self,
        critiques: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[tuple, int]]:
        """
        Create global sources list and mapping from critique-local to global IDs
        
        Returns:
            (global_sources, source_mapping)
            source_mapping: {(critique_id, local_source_id): global_source_id}
        """
        global_sources = []
        source_mapping = {}
        global_id = 1
        
        # Track seen sources to avoid duplicates
        seen_sources = {}
        
        for critique in critiques:
            critique_id = critique.get('critique_id')
            local_sources = critique.get('sources', [])
            
            for local_source in local_sources:
                local_id = local_source.get('id')
                source_type = local_source.get('type')
                
                # Create unique key for deduplication
                if source_type == 'web':
                    source_key = ('web', local_source.get('url'))
                elif source_type == 'bmc':
                    source_key = ('bmc', local_source.get('field'))
                elif source_type == 'vpc':
                    source_key = ('vpc', local_source.get('field'))
                elif source_type == 'vps':
                    source_key = ('vps', local_source.get('field'))
                else:
                    source_key = (source_type, str(local_source))
                
                # Check if source already exists
                if source_key in seen_sources:
                    # Reuse existing global ID
                    source_mapping[(critique_id, local_id)] = seen_sources[source_key]
                else:
                    # Add new source
                    new_source = {**local_source, 'id': global_id}
                    global_sources.append(new_source)
                    seen_sources[source_key] = global_id
                    source_mapping[(critique_id, local_id)] = global_id
                    global_id += 1
        
        return global_sources, source_mapping
    
    def _renumber_citations(
        self,
        critiques: List[Dict[str, Any]],
        source_mapping: Dict[tuple, int]
    ) -> List[Dict[str, Any]]:
        """Renumber citations in critiques using global source IDs"""
        updated_critiques = []
        
        for critique in critiques:
            critique_id = critique.get('critique_id')
            updated_critique = critique.copy()
            
            # Renumber citations in problem text
            problem_text = critique.get('problem', '')
            updated_critique['problem'] = self._renumber_text(
                problem_text, critique_id, source_mapping
            )
            
            # Renumber citations in impact text
            impact_text = critique.get('impact', '')
            updated_critique['impact'] = self._renumber_text(
                impact_text, critique_id, source_mapping
            )
            
            # Update suggestions with global source IDs
            suggestions = critique.get('suggestions', [])
            updated_suggestions = []
            for suggestion in suggestions:
                updated_suggestion = suggestion.copy()
                
                # Renumber rationale
                if 'rationale' in suggestion:
                    updated_suggestion['rationale'] = self._renumber_text(
                        suggestion['rationale'], critique_id, source_mapping
                    )
                
                # Renumber supporting_sources
                if 'supporting_sources' in suggestion:
                    local_sources = suggestion['supporting_sources']
                    global_sources = [
                        source_mapping.get((critique_id, local_id), local_id)
                        for local_id in local_sources
                    ]
                    updated_suggestion['supporting_sources'] = global_sources
                
                updated_suggestions.append(updated_suggestion)
            
            updated_critique['suggestions'] = updated_suggestions
            updated_critiques.append(updated_critique)
        
        return updated_critiques
    
    def _renumber_text(
        self,
        text: str,
        critique_id: str,
        source_mapping: Dict[tuple, int]
    ) -> str:
        """Renumber citations in text from local to global IDs"""
        if not text:
            return text
        
        def replace_citation(match):
            local_id = int(match.group(1))
            global_id = source_mapping.get((critique_id, local_id), local_id)
            return f"[{global_id}]"
        
        return re.sub(r'\[(\d+)\]', replace_citation, text)
    
    def _calculate_severity_distribution(
        self,
        critiques: List[Dict]
    ) -> Dict[str, int]:
        """Calculate severity distribution"""
        dist = {'high': 0, 'medium': 0, 'low': 0}
        for critique in critiques:
            severity = critique.get('severity', 'medium')
            if severity in dist:
                dist[severity] += 1
        return dist
    
    async def _generate_executive_summary(
        self,
        critiques: List[Dict],
        context: Dict,
        severity_dist: Dict,
        monitoring_context: AIUsageContext
    ) -> Dict[str, Any]:
        """Generate executive summary using AI"""
        try:
            system_prompt = self._build_summary_system_prompt()
            user_prompt = self._build_summary_user_prompt(critiques, context, severity_dist)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.ai_service.generate_analysis_response(
                messages=messages,
                temperature=0.2,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                json_mode=True,
                monitoring_context=monitoring_context
            )
            
            summary_data = json.loads(response['content'])
            summary_data['severity_distribution'] = severity_dist
            summary_data['total_critiques'] = len(critiques)
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            # Return fallback summary
            return self._get_fallback_summary(critiques, severity_dist)
    
    def _build_summary_system_prompt(self) -> str:
        return """<role>
You are a startup advisor synthesizing solution critiques into an executive summary.
</role>

<task>
Generate a concise executive summary with citations [N] from the provided critiques.
</task>

<output_schema>
{
  "overall_viability": "high_risk | moderate_risk | low_risk",
  "top_3_risks": ["Risk 1 with citation [N]", "Risk 2 with citation [N]", "Risk 3 with citation [N]"],
  "overall_confidence": 0.75,
  "recommendation": "Brief strategic recommendation with citations [N][N]",
  "key_insights": ["Insight 1", "Insight 2", "Insight 3"]
}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""
    
    def _build_summary_user_prompt(
        self,
        critiques: List[Dict],
        context: Dict,
        severity_dist: Dict
    ) -> str:
        # Extract key issues from critiques
        high_severity_issues = [
            c.get('title', '') for c in critiques if c.get('severity') == 'high'
        ]
        
        return f"""<task>
Synthesize these solution critiques into an executive summary.
</task>

<solution_context>
Solution: {context.get('solution_description', '')}
Geography: {context.get('geography')}
Industry: {context.get('industry')}
</solution_context>

<severity_distribution>
High: {severity_dist['high']}
Medium: {severity_dist['medium']}
Low: {severity_dist['low']}
</severity_distribution>

<high_severity_issues>
{json.dumps(high_severity_issues, indent=2)}
</high_severity_issues>

<all_critiques>
{json.dumps([{
    'dimension': c['dimension'],
    'title': c['title'],
    'severity': c['severity']
} for c in critiques], indent=2)}
</all_critiques>

<instructions>
Generate executive summary with overall viability assessment and strategic recommendation.
</instructions>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""
    
    def _get_fallback_summary(self, critiques: List[Dict], severity_dist: Dict) -> Dict:
        """Fallback summary if AI generation fails"""
        high_count = severity_dist.get('high', 0)
        
        if high_count >= 3:
            viability = "high_risk"
        elif high_count >= 1:
            viability = "moderate_risk"
        else:
            viability = "low_risk"
        
        return {
            'overall_viability': viability,
            'top_3_risks': [
                c.get('title', 'Unknown issue')
                for c in critiques if c.get('severity') == 'high'
            ][:3],
            'overall_confidence': 0.70,
            'recommendation': "Address high-severity issues before proceeding.",
            'key_insights': []
        }
    
    def _group_by_dimension(
        self,
        critiques: List[Dict]
    ) -> Dict[str, Any]:
        """Group critiques by dimension"""
        grouped = {}
        
        for critique in critiques:
            dimension = critique.get('dimension')
            if dimension not in grouped:
                grouped[dimension] = {
                    'summary': f"{dimension.replace('_', ' ').title()} analysis",
                    'critiques': [],
                    'dimension_severity': 'low',
                    'citation_count': 0
                }
            
            grouped[dimension]['critiques'].append(critique)
            grouped[dimension]['citation_count'] += critique.get('citation_count', 0)
        
        # Determine dimension severity (highest critique severity)
        for dimension, data in grouped.items():
            severities = [c.get('severity') for c in data['critiques']]
            if 'high' in severities:
                data['dimension_severity'] = 'high'
            elif 'medium' in severities:
                data['dimension_severity'] = 'medium'
        
        return grouped
    
    def _extract_prioritized_actions(
        self,
        critiques: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """Extract and prioritize all suggestions"""
        prioritized = {
            'immediate': [],
            'short_term': [],
            'long_term': []
        }
        
        for critique in critiques:
            suggestions = critique.get('suggestions', [])
            for suggestion in suggestions:
                priority = suggestion.get('priority', 'short_term')
                
                if priority == 'immediate':
                    prioritized['immediate'].append(suggestion)
                elif priority in ['short_term', 'consider']:
                    prioritized['short_term'].append(suggestion)
                else:
                    prioritized['long_term'].append(suggestion)
        
        return prioritized
    
    def _count_total_citations(self, critiques: List[Dict]) -> int:
        """Count total citations across all critiques"""
        return sum(c.get('citation_count', 0) for c in critiques)
