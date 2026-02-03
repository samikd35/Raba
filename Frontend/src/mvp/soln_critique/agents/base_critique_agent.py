"""
Base class for all critique agents
Implements citation system following PV Report standards
"""
import logging
import json
import re
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime

from src.market_research.utils.ai_service_wrapper import get_ai_service_wrapper
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class BaseCritiqueAgent(ABC):
    """Base class for critique agents with citation system
    
    Uses Azure OpenAI gpt-5-mini via get_ai_service_wrapper()
    which is configured for ModelUseCase.REPORT_GENERATION
    """
    
    def __init__(self):
        # AI service uses Azure gpt-5-mini for report generation
        self.ai_service = get_ai_service_wrapper()
        self.dimension = self.get_dimension()
    
    @abstractmethod
    def get_dimension(self) -> str:
        """Return the critique dimension name"""
        pass
    
    @abstractmethod
    def get_section_name(self) -> str:
        """Return the human-readable section name for display (e.g., 'Market Viability')"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        pass
    
    @abstractmethod
    def get_relevant_bmc_fields(self, bmc_data: Dict) -> Dict:
        """Extract relevant BMC fields for this dimension"""
        pass
    
    @abstractmethod
    def get_relevant_vpc_fields(self, vpc_data: Dict) -> Dict:
        """Extract relevant VPC fields for this dimension"""
        pass
    
    @abstractmethod
    def get_search_categories(self) -> List[str]:
        """Return relevant search result categories"""
        pass
    
    @abstractmethod
    def get_context_priority(self) -> Dict[str, int]:
        """Return context priority weights for this dimension
        
        Returns:
            Dict with keys 'bmc', 'vpc', 'vps' and integer weights (1-10)
            Higher weight = more emphasis in prompt and source collection
            
        Example:
            {'bmc': 10, 'vpc': 5, 'vps': 3}  # BMC-heavy dimension
            {'vpc': 10, 'bmc': 7, 'vps': 5}  # VPC-heavy dimension
        """
        pass
    
    async def generate_critique(
        self,
        context: Dict[str, Any],
        search_results: Dict[str, List[Dict]],
        tenant_id: str,
        user_id: str,
        project_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate critique for this dimension with citations
        
        Args:
            context: Project context (VPC, VPS, BMC, geography, etc.)
            search_results: Web search results grouped by category
            tenant_id: Tenant ID for monitoring
            user_id: User ID for monitoring
            project_id: Project ID for monitoring
            
        Returns:
            Critique object with sources and citations, or None if generation fails
        """
        try:
            logger.info(f"🔍 Generating {self.dimension} critique")
            
            # Step 1: Collect sources for citations
            sources = self._collect_sources(context, search_results)
            logger.info(f"   Collected {len(sources)} sources")
            
            # Step 2: Create monitoring context
            monitoring_context = AIUsageContext(
                tenant_id=tenant_id,
                user_id=user_id,
                feature_id="solution_critique",
                workflow_name="solution_critique_workflow",
                step_name=f"{self.dimension}_critique",
                project_id=project_id
            )
            
            # Step 3: Build prompt with sources
            system_prompt = self.get_system_prompt()
            user_prompt = self._build_user_prompt(context, sources)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Step 4: Generate critique
            logger.info(f"   Generating critique with AI...")
            response = await self.ai_service.generate_analysis_response(
                messages=messages,
                temperature=0.1,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                json_mode=True,
                monitoring_context=monitoring_context
            )
            
            # Step 5: Parse response
            critique_data = json.loads(response['content'])
            
            # Step 6: Validate structure
            if not self._validate_critique(critique_data):
                raise ValueError("Invalid critique structure")
            
            # Step 7: Add sources and validate citations
            critique_data['sources'] = sources
            citation_count = self._count_citations(critique_data.get('problem', ''))
            critique_data['citation_count'] = citation_count
            critique_data['unique_sources_used'] = len(set(self._extract_citation_numbers(critique_data.get('problem', ''))))
            
            # Step 8: Validate citations reference valid sources
            self._validate_citations(critique_data)
            
            logger.info(f"✅ {self.dimension} critique generated")
            logger.info(f"   Citations: {citation_count}, Unique sources: {critique_data['unique_sources_used']}")
            
            return critique_data
            
        except Exception as e:
            logger.error(f"❌ {self.dimension} critique failed: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None
    
    def _get_internal_source_url(self, source_type: str, project_id: str, field: str = None) -> str:
        """
        Generate URL for internal sources (BMC, VPC, VPS) that links to the project page.
        
        Args:
            source_type: 'bmc', 'vpc', or 'vps'
            project_id: The project ID to link to
            field: Optional field name for anchor linking
            
        Returns:
            URL string that can be used to navigate to the source in the frontend
        """
        if not project_id:
            return ""
        
        # Base URL patterns for internal sources
        # These match the frontend route structure: /workspace/{type}-v2/{project_id}
        url_patterns = {
            'bmc': f"/workspace/bmc-v2/{project_id}",
            'vpc': f"/workspace/vpc-v2/{project_id}",
            'vps': f"/workspace/vps-v2/{project_id}",
        }
        
        base_url = url_patterns.get(source_type, "")
        
        # Add field as anchor if provided (for deep linking)
        if base_url and field:
            # Convert field name to anchor format (e.g., "customer_segments" -> "#customer-segments")
            anchor = field.replace('_', '-').replace('.', '-').lower()
            return f"{base_url}#{anchor}"
        
        return base_url
    
    def _collect_sources(
        self,
        context: Dict[str, Any],
        search_results: Dict[str, List[Dict]]
    ) -> List[Dict[str, Any]]:
        """
        Collect sources from web search and project data with dynamic prioritization
        
        Returns numbered list of sources for citations, ordered by relevance to dimension
        """
        sources = []
        source_id = 1
        
        # Get project_id for internal source URLs
        project_id = context.get('project_id', '')
        
        # Get context priority weights for this dimension
        priority = self.get_context_priority()
        bmc_priority = priority.get('bmc', 5)
        vpc_priority = priority.get('vpc', 5)
        vps_priority = priority.get('vps', 5)
        
        logger.info(f"\n🎯 DYNAMIC CONTEXT PRIORITIZATION: {self.dimension}")
        logger.info(f"   Priority Weights (1-10 scale):")
        logger.info(f"      BMC: {bmc_priority}/10 {'🔥 HIGH' if bmc_priority >= 8 else '📊 MEDIUM' if bmc_priority >= 5 else '📉 LOW'}")
        logger.info(f"      VPC: {vpc_priority}/10 {'🔥 HIGH' if vpc_priority >= 8 else '📊 MEDIUM' if vpc_priority >= 5 else '📉 LOW'}")
        logger.info(f"      VPS: {vps_priority}/10 {'🔥 HIGH' if vps_priority >= 8 else '📊 MEDIUM' if vps_priority >= 5 else '📉 LOW'}")
        
        # Identify primary focus
        max_priority = max(bmc_priority, vpc_priority, vps_priority)
        primary_contexts = []
        if bmc_priority == max_priority:
            primary_contexts.append('BMC')
        if vpc_priority == max_priority:
            primary_contexts.append('VPC')
        if vps_priority == max_priority:
            primary_contexts.append('VPS')
        
        logger.info(f"   Primary Focus: {', '.join(primary_contexts)} (priority {max_priority}/10)")
        logger.info(f"   Content Expansion: High-priority contexts get 400+ chars vs 200 chars for low-priority")
        
        # Collect web sources from relevant categories
        relevant_categories = self.get_search_categories()
        for category in relevant_categories:
            if category in search_results:
                category_results = search_results[category]
                for query_result in category_results:
                    results = query_result.get('results', [])
                    # Take top 3 results per query
                    for result in results[:3]:
                        sources.append({
                            'id': source_id,
                            'type': 'web',
                            'title': result.get('title', 'Untitled'),
                            'url': result.get('url', '')
                        })
                        source_id += 1
                        
                        # Limit total web sources to prevent overwhelming prompt
                        if source_id > 15:
                            break
                    if source_id > 15:
                        break
        
        # Collect BMC sources (prioritized based on dimension)
        bmc_data = context.get('bmc_data', {})
        if not isinstance(bmc_data, dict):
            bmc_data = {}
        bmc_fields = self.get_relevant_bmc_fields(bmc_data) or {}
        bmc_sources = []
        for field, content in bmc_fields.items():
            if content:  # Only add if there's content
                # Expand content for high-priority dimensions
                content_length = 400 if bmc_priority >= 8 else 200
                bmc_sources.append({
                    'id': source_id,
                    'type': 'bmc',
                    'field': field,
                    'title': f"Business Model Canvas - {field.replace('_', ' ').title()}",
                    'url': self._get_internal_source_url('bmc', project_id, field),
                    'content': str(content)[:content_length] if isinstance(content, (str, list)) else 'Complex data',
                    'issue': f"Analysis of {field}",
                    'priority': bmc_priority
                })
                source_id += 1
        
        # Collect VPC sources (prioritized based on dimension)
        vpc_data = context.get('vpc_data', {})
        if not isinstance(vpc_data, dict):
            vpc_data = {}
        vpc_fields = self.get_relevant_vpc_fields(vpc_data) or {}
        vpc_sources = []
        for field, content in vpc_fields.items():
            if content:
                # Expand content for high-priority dimensions
                content_length = 400 if vpc_priority >= 8 else 200
                vpc_sources.append({
                    'id': source_id,
                    'type': 'vpc',
                    'field': field,
                    'title': f"Value Proposition Canvas - {field.replace('_', ' ').replace('.', ' - ').title()}",
                    'url': self._get_internal_source_url('vpc', project_id, field),
                    'content': str(content)[:content_length] if isinstance(content, (str, list)) else 'Complex data',
                    'context': f"Customer insight from {field}",
                    'priority': vpc_priority
                })
                source_id += 1
        
        # Add VPS as source (prioritized based on dimension)
        vps_statement = context.get('solution_description', '')
        vps_sources = []
        if vps_statement:
            # Expand content for high-priority dimensions
            content_length = 600 if vps_priority >= 8 else 300
            vps_sources.append({
                'id': source_id,
                'type': 'vps',
                'field': 'statement',
                'title': 'Value Proposition Statement',
                'url': self._get_internal_source_url('vps', project_id, 'statement'),
                'content': vps_statement[:content_length],
                'context': 'Core solution statement',
                'priority': vps_priority
            })
            source_id += 1
        
        # Order internal sources by priority (highest first)
        # This ensures high-priority context appears early in source list
        internal_sources = sorted(
            bmc_sources + vpc_sources + vps_sources,
            key=lambda x: x.get('priority', 0),
            reverse=True
        )
        
        # Combine: web sources first, then prioritized internal sources
        sources.extend(internal_sources)
        
        # Log source collection summary
        logger.info(f"\n📚 SOURCE COLLECTION SUMMARY:")
        logger.info(f"   Total sources: {len(sources)}")
        logger.info(f"   Web sources: {len([s for s in sources if s.get('type') == 'web'])}")
        logger.info(f"   BMC sources: {len(bmc_sources)} (priority {bmc_priority}/10)")
        logger.info(f"   VPC sources: {len(vpc_sources)} (priority {vpc_priority}/10)")
        logger.info(f"   VPS sources: {len(vps_sources)} (priority {vps_priority}/10)")
        logger.info(f"   Source ordering: Web first, then internal by priority (highest first)")
        
        return sources
    
    def _build_user_prompt(
        self,
        context: Dict[str, Any],
        sources: List[Dict[str, Any]]
    ) -> str:
        """Build user prompt with context and numbered sources, emphasizing priority contexts"""
        
        geography = context.get('geography', 'Not specified')
        industry = context.get('industry', 'Not specified')
        solution = context.get('solution_description', '')
        
        # Get context priority for this dimension
        priority = self.get_context_priority()
        bmc_priority = priority.get('bmc', 5)
        vpc_priority = priority.get('vpc', 5)
        vps_priority = priority.get('vps', 5)
        
        # Build priority context emphasis
        priority_contexts = []
        if bmc_priority >= 8:
            priority_contexts.append("Business Model Canvas (BMC)")
        if vpc_priority >= 8:
            priority_contexts.append("Value Proposition Canvas (VPC)")
        if vps_priority >= 8:
            priority_contexts.append("Value Proposition Statement (VPS)")
        
        priority_note = ""
        if priority_contexts:
            priority_note = f"\n\n**PRIORITY CONTEXT FOR THIS DIMENSION:**\nFocus heavily on: {', '.join(priority_contexts)}\nThese contexts are most relevant for {self.dimension} analysis.\n"
            logger.info(f"\n💡 PROMPT ENHANCEMENT:")
            logger.info(f"   Adding priority emphasis for: {', '.join(priority_contexts)}")
            logger.info(f"   This guides the AI to focus on the most relevant context for {self.dimension}")
        else:
            logger.info(f"\n💡 PROMPT ENHANCEMENT:")
            logger.info(f"   No high-priority contexts (all < 8/10), using balanced approach")
        
        # Format sources for prompt
        sources_text = self._format_sources_for_prompt(sources)
        
        prompt = f"""<task>
Analyze this solution for {self.dimension}.
</task>

<solution_context>
Solution Statement: {solution}
Geography: {geography}
Industry: {industry}
</solution_context>
{priority_note}
<sources>
{sources_text}
</sources>

<citation_requirements>
- Use numbered citations [1], [2], [3] throughout your critique
- Every factual claim, statistic, or assertion must have a citation
- Use [1][2] when multiple sources support the same claim
- Minimum 5-8 citations required in your critique
- Ensure citation numbers match the sources provided above
- Prioritize citing sources from the emphasized context areas above
</citation_requirements>

<instructions>
Generate a detailed critique focusing on {self.dimension}.
Identify specific problems with evidence [N], assess impact with citations [N][N], 
and suggest actionable improvements with supporting sources.
</instructions>

<required_output>
1. problem: Detailed analysis with embedded [N] citations (minimum 5 citations)
2. impact: Business impact with citations
3. suggestions: Actionable recommendations with supporting_sources array
4. severity: high | medium | low
5. confidence: 0.0-1.0
</required_output>

<output_rules>
Return ONLY valid JSON matching the schema. EVERY claim needs a [N] citation.
</output_rules>
"""
        return prompt
    
    def _format_sources_for_prompt(self, sources: List[Dict[str, Any]]) -> str:
        """Format sources for AI prompt"""
        formatted = []
        
        for source in sources:
            source_id = source['id']
            source_type = source['type']
            
            if source_type == 'web':
                formatted.append(
                    f"[{source_id}] {source['title']}\n"
                    f"    URL: {source['url']}"
                )
            elif source_type == 'bmc':
                formatted.append(
                    f"[{source_id}] BMC - {source['field']}\n"
                    f"    {source['content']}"
                )
            elif source_type == 'vpc':
                formatted.append(
                    f"[{source_id}] VPC - {source['field']}\n"
                    f"    {source['content']}"
                )
            elif source_type == 'vps':
                formatted.append(
                    f"[{source_id}] VPS - {source['field']}\n"
                    f"    {source['content']}"
                )
        
        return "\n\n".join(formatted)
    
    def _validate_critique(self, critique: Dict) -> bool:
        """Validate critique structure"""
        required_fields = [
            'critique_id', 'dimension', 'section_name', 'title', 'severity',
            'problem', 'summary', 'suggestions'
        ]
        
        for field in required_fields:
            if field not in critique:
                logger.error(f"Missing required field: {field}")
                return False
        
        return True
    
    def _count_citations(self, text: str) -> int:
        """Count total citations in text"""
        if not text:
            return 0
        citations = re.findall(r'\[(\d+)\]', text)
        return len(citations)
    
    def _extract_citation_numbers(self, text: str) -> List[int]:
        """Extract unique citation numbers from text"""
        if not text:
            return []
        citations = re.findall(r'\[(\d+)\]', text)
        return [int(c) for c in citations]
    
    def _validate_citations(self, critique: Dict) -> None:
        """Validate that all citations reference valid sources"""
        problem_text = critique.get('problem', '')
        impact_text = critique.get('impact', '')
        
        # Extract all citation numbers
        all_text = f"{problem_text} {impact_text}"
        citation_numbers = self._extract_citation_numbers(all_text)
        
        # Check against available sources
        max_source_id = len(critique.get('sources', []))
        
        invalid_citations = [c for c in citation_numbers if c > max_source_id or c < 1]
        
        if invalid_citations:
            logger.warning(
                f"Invalid citations found: {invalid_citations} "
                f"(max source id: {max_source_id})"
            )
        
        # Check minimum citations
        if len(citation_numbers) < 5:
            logger.warning(
                f"Low citation count: {len(citation_numbers)} "
                f"(minimum 5 required)"
            )
