"""
Base Agent for MVP Requirements Generator

Provides common functionality for all AMRG agents.
"""

import logging
import json
import re
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.market_research.utils.ai_service_wrapper import get_ai_service_wrapper
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)

# Prompt templates directory
PROMPTS_DIR = Path(__file__).parent.parent / "templates" / "prompts"


class BaseAMRGAgent(ABC):
    """
    Base class for AMRG agents.
    
    Provides:
    - AI service integration (Azure OpenAI via AIServiceWrapper)
    - Jinja2 template rendering
    - Monitoring context setup
    - JSON response parsing
    """
    
    def __init__(self):
        """Initialize base agent."""
        self.ai_service = get_ai_service_wrapper()
        self.jinja_env = Environment(
            loader=FileSystemLoader(PROMPTS_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )
        logger.info(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def get_agent_name(self) -> str:
        """Return the agent name for logging/monitoring."""
        pass
    
    def render_prompt(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Render a Jinja2 prompt template.
        
        Args:
            template_name: Name of template file (e.g., "routing_coarse.j2")
            context: Template context variables
            
        Returns:
            Rendered prompt string
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise
    
    def create_monitoring_context(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        step_name: str
    ) -> AIUsageContext:
        """Create monitoring context for AI calls."""
        return AIUsageContext(
            tenant_id=tenant_id,
            user_id=user_id,
            feature_id="mvp_requirements",
            workflow_name="amrg_workflow",
            step_name=step_name,
            project_id=project_id
        )
    
    async def call_llm(
        self,
        prompt: str,
        monitoring_context: AIUsageContext,
        temperature: float = 0.2,
        max_tokens: int = 16000,  # gpt-5-mini needs large token budget
        json_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Call LLM with standard configuration.
        
        Args:
            prompt: The prompt text
            monitoring_context: Monitoring context
            temperature: LLM temperature (default 0.2 for consistency)
            max_tokens: Maximum tokens
            json_mode: Whether to request JSON output
            
        Returns:
            Parsed JSON response
        """
        try:
            messages = [
                {"role": "system", "content": "You are an expert product strategist. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.ai_service.generate_analysis_response(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                monitoring_context=monitoring_context
            )
            
            content = response.get('content', '{}')
            return self.parse_json_response(content)
            
        except Exception as e:
            logger.error(f"LLM call failed in {self.get_agent_name()}: {e}")
            raise
    
    def parse_json_response(self, content: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response.
        
        Handles common issues like markdown code blocks and truncated responses.
        """
        try:
            # Clean up response
            cleaned = content.strip()
            
            # Remove markdown code blocks if present
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            
            # Try to repair truncated JSON
            repaired = self._repair_truncated_json(cleaned)
            if repaired:
                try:
                    result = json.loads(repaired)
                    logger.info("Successfully repaired truncated JSON response")
                    return result
                except json.JSONDecodeError:
                    pass
            
            logger.debug(f"Response content (first 1000 chars): {content[:1000]}")
            raise ValueError(f"Invalid JSON response: {e}")
    
    def _repair_truncated_json(self, content: str) -> Optional[str]:
        """
        Robust JSON repair for truncated LLM responses.
        
        Uses state-machine parsing to find valid truncation points.
        """
        if not content or len(content) < 10:
            return None
        
        try:
            # Strategy 1: Find the last complete JSON object/array ending
            repaired = self._find_last_valid_json_end(content)
            if repaired:
                return repaired
            
            # Strategy 2: State-machine based repair
            repaired = self._state_machine_repair(content)
            if repaired:
                return repaired
            
            # Strategy 3: Aggressive truncation - find last complete key-value pair
            repaired = self._aggressive_truncate_repair(content)
            if repaired:
                return repaired
            
            return None
            
        except Exception as e:
            logger.debug(f"JSON repair failed: {e}")
            return None
    
    def _find_last_valid_json_end(self, content: str) -> Optional[str]:
        """Find the last position where JSON is still valid and close it."""
        # Try progressively shorter substrings
        for end_pos in range(len(content), max(len(content) - 500, 100), -1):
            substr = content[:end_pos]
            # Check if this ends at a good boundary (}, ], or ")
            last_char = substr.rstrip()[-1] if substr.rstrip() else ''
            if last_char in ['}', ']', '"', ',']:
                try:
                    # Calculate what needs to be closed
                    stack = []
                    in_string = False
                    i = 0
                    while i < len(substr):
                        char = substr[i]
                        if in_string:
                            if char == '\\' and i + 1 < len(substr):
                                i += 2
                                continue
                            if char == '"':
                                in_string = False
                        else:
                            if char == '"':
                                in_string = True
                            elif char == '{':
                                stack.append('}')
                            elif char == '[':
                                stack.append(']')
                            elif char in ['}', ']']:
                                if stack and stack[-1] == char:
                                    stack.pop()
                        i += 1
                    
                    # If we're not in a string and have a reasonable stack, close it
                    if not in_string and len(stack) <= 10:
                        result = substr.rstrip().rstrip(',')
                        result += ''.join(reversed(stack))
                        json.loads(result)  # Validate
                        return result
                except:
                    continue
        return None
    
    def _state_machine_repair(self, content: str) -> Optional[str]:
        """Parse JSON with state machine and close properly."""
        stack = []  # Track open brackets/braces
        in_string = False
        last_good_pos = 0
        i = 0
        
        while i < len(content):
            char = content[i]
            
            if in_string:
                if char == '\\' and i + 1 < len(content):
                    i += 2
                    continue
                if char == '"':
                    in_string = False
                    last_good_pos = i + 1
            else:
                if char == '"':
                    in_string = True
                elif char == '{':
                    stack.append('}')
                elif char == '[':
                    stack.append(']')
                elif char == '}':
                    if stack and stack[-1] == '}':
                        stack.pop()
                        last_good_pos = i + 1
                elif char == ']':
                    if stack and stack[-1] == ']':
                        stack.pop()
                        last_good_pos = i + 1
                elif char == ',':
                    if not in_string:
                        last_good_pos = i + 1
            i += 1
        
        # If truncated inside string, find last complete field
        if in_string:
            # Go back to last good position before incomplete string
            last_comma = content.rfind(',', 0, last_good_pos)
            if last_comma > 0:
                content = content[:last_comma]
                # Recalculate stack
                stack = []
                in_string = False
                for i, char in enumerate(content):
                    if in_string:
                        if char == '\\' and i + 1 < len(content) and content[i+1] in ['"', '\\', 'n', 'r', 't']:
                            continue
                        if char == '"':
                            in_string = False
                    else:
                        if char == '"':
                            in_string = True
                        elif char == '{':
                            stack.append('}')
                        elif char == '[':
                            stack.append(']')
                        elif char == '}' and stack and stack[-1] == '}':
                            stack.pop()
                        elif char == ']' and stack and stack[-1] == ']':
                            stack.pop()
        
        # Build repaired JSON
        repaired = content.rstrip().rstrip(',')
        if in_string:
            repaired += '"'
        repaired += ''.join(reversed(stack))
        
        try:
            json.loads(repaired)
            return repaired
        except:
            return None
    
    def _aggressive_truncate_repair(self, content: str) -> Optional[str]:
        """Aggressively truncate to find valid JSON."""
        # Find positions of complete-looking structures
        good_endings = []
        
        # Look for patterns like "}, " or "], " or '": "value",'
        for match in re.finditer(r'"\s*[,}}\]]', content):
            good_endings.append(match.end())
        
        # Try each position from latest to earliest
        for pos in reversed(good_endings[-20:]):  # Check last 20 good positions
            substr = content[:pos]
            
            # Calculate closures needed
            stack = []
            in_string = False
            i = 0
            while i < len(substr):
                char = substr[i]
                if in_string:
                    if char == '\\' and i + 1 < len(substr):
                        i += 2
                        continue
                    if char == '"':
                        in_string = False
                else:
                    if char == '"':
                        in_string = True
                    elif char == '{':
                        stack.append('}')
                    elif char == '[':
                        stack.append(']')
                    elif char in ['}', ']'] and stack and stack[-1] == char:
                        stack.pop()
                i += 1
            
            if not in_string:
                repaired = substr.rstrip().rstrip(',') + ''.join(reversed(stack))
                try:
                    json.loads(repaired)
                    return repaired
                except:
                    continue
        
        return None
    
    async def call_llm_with_retry(
        self,
        prompt: str,
        monitoring_context: AIUsageContext,
        max_retries: int = 2,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call LLM with retry on JSON parse errors.
        
        Args:
            prompt: The prompt text
            monitoring_context: Monitoring context
            max_retries: Maximum retry attempts
            **kwargs: Additional arguments for call_llm
            
        Returns:
            Parsed JSON response
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self.call_llm(prompt, monitoring_context, **kwargs)
            except ValueError as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(f"Retry {attempt + 1}/{max_retries} due to: {e}")
                    # Add instruction to fix JSON
                    prompt = prompt + "\n\nIMPORTANT: Your previous response was not valid JSON. Please return ONLY valid JSON, no markdown or explanations."
        
        raise last_error
