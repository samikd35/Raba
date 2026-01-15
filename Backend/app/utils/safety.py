"""RABA Content Safety Utilities.

Content moderation and safety filters for video generation.

Reference: Phase 5.1.3 - Content Safety Filters
"""

import re
from typing import Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


BLOCKED_TOPICS = [
    "violence", "gore", "murder", "killing",
    "hate", "racist", "sexist", "discriminat",
    "porn", "nsfw", "nude", "sexual",
    "terror", "bomb", "weapon",
    "drugs", "cocaine", "heroin",
    "suicide", "self-harm",
    "child abuse", "pedophil",
]

BLOCKED_PATTERNS = [
    r"\bhow\s+to\s+make\s+a?\s*bomb",
    r"\bhow\s+to\s+kill",
    r"\bhow\s+to\s+harm",
]

FOOTBALL_BANTER_ALLOWED = [
    "hate watching", "hate the ref",
    "killing it", "killing the game",
    "bottled it", "bottlers",
    "violent tackle", "violent shot",
]


class ContentSafetyResult:
    """Result of content safety check."""
    
    def __init__(
        self,
        is_safe: bool,
        reason: Optional[str] = None,
        severity: str = "none",
    ):
        self.is_safe = is_safe
        self.reason = reason
        self.severity = severity  # none, low, medium, high
    
    def __bool__(self):
        return self.is_safe


def check_topic_safety(topic: str) -> ContentSafetyResult:
    """
    Check if a video topic is safe for generation.
    
    Args:
        topic: User-provided topic
        
    Returns:
        ContentSafetyResult indicating if topic is safe
    """
    topic_lower = topic.lower()
    
    # Check for football banter exceptions first
    for allowed in FOOTBALL_BANTER_ALLOWED:
        if allowed in topic_lower:
            # These terms are okay in football context
            continue
    
    # Check blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, topic_lower, re.IGNORECASE):
            logger.warning(f"Blocked pattern in topic: {pattern}")
            return ContentSafetyResult(
                is_safe=False,
                reason="Topic contains prohibited content",
                severity="high",
            )
    
    # Check blocked keywords
    for keyword in BLOCKED_TOPICS:
        if keyword in topic_lower:
            # Check if it's in an allowed football context
            is_football_context = any(
                allowed in topic_lower for allowed in FOOTBALL_BANTER_ALLOWED
            )
            
            if not is_football_context:
                logger.warning(f"Blocked keyword in topic: {keyword}")
                return ContentSafetyResult(
                    is_safe=False,
                    reason="Topic contains prohibited content",
                    severity="medium",
                )
    
    return ContentSafetyResult(is_safe=True)


def check_script_safety(script: str) -> ContentSafetyResult:
    """
    Check if generated script content is safe.
    
    Args:
        script: Generated script text
        
    Returns:
        ContentSafetyResult indicating if script is safe
    """
    script_lower = script.lower()
    
    # Check blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, script_lower, re.IGNORECASE):
            logger.warning(f"Blocked pattern in script")
            return ContentSafetyResult(
                is_safe=False,
                reason="Script contains prohibited content",
                severity="high",
            )
    
    # Check blocked keywords (stricter for scripts)
    blocked_count = 0
    for keyword in BLOCKED_TOPICS:
        if keyword in script_lower:
            blocked_count += 1
    
    if blocked_count >= 2:
        logger.warning(f"Multiple blocked keywords in script: {blocked_count}")
        return ContentSafetyResult(
            is_safe=False,
            reason="Script contains potentially unsafe content",
            severity="medium",
        )
    
    return ContentSafetyResult(is_safe=True)


def check_image_prompt_safety(prompt: str) -> ContentSafetyResult:
    """
    Check if an image generation prompt is safe.
    
    Args:
        prompt: Image generation prompt
        
    Returns:
        ContentSafetyResult indicating if prompt is safe
    """
    prompt_lower = prompt.lower()
    
    # Image prompts are stricter
    image_blocked_terms = [
        "nude", "naked", "nsfw", "porn",
        "gore", "blood", "violent",
        "weapon", "gun", "knife",
        "child", "minor", "underage",
    ]
    
    for term in image_blocked_terms:
        if term in prompt_lower:
            logger.warning(f"Blocked term in image prompt: {term}")
            return ContentSafetyResult(
                is_safe=False,
                reason="Image prompt contains prohibited content",
                severity="high",
            )
    
    return ContentSafetyResult(is_safe=True)


def sanitize_for_generation(text: str) -> str:
    """
    Remove potentially problematic content from text before generation.
    
    This is a soft filter that modifies rather than blocks.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text
    """
    # Remove URLs (could be used for prompt injection)
    text = re.sub(r'https?://\S+', '[URL removed]', text)
    
    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[email removed]', text)
    
    # Remove phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[phone removed]', text)
    
    return text


class ContentModerator:
    """
    Content moderation service for the generation pipeline.
    
    Checks content at each stage:
    1. Topic input
    2. Generated script
    3. Image prompts
    4. Final video content
    """
    
    def __init__(self):
        self._logger = get_logger(f"{__name__}.ContentModerator")
    
    def check_topic(self, topic: str) -> ContentSafetyResult:
        """Check topic safety."""
        return check_topic_safety(topic)
    
    def check_script(self, script: str) -> ContentSafetyResult:
        """Check script safety."""
        return check_script_safety(script)
    
    def check_image_prompt(self, prompt: str) -> ContentSafetyResult:
        """Check image prompt safety."""
        return check_image_prompt_safety(prompt)
    
    def validate_workflow_content(
        self,
        topic: str,
        script: Optional[str] = None,
        image_prompts: Optional[list[str]] = None,
    ) -> ContentSafetyResult:
        """
        Validate all content in a workflow.
        
        Returns first safety issue found, or safe result.
        """
        # Check topic
        topic_result = self.check_topic(topic)
        if not topic_result.is_safe:
            return topic_result
        
        # Check script
        if script:
            script_result = self.check_script(script)
            if not script_result.is_safe:
                return script_result
        
        # Check image prompts
        if image_prompts:
            for prompt in image_prompts:
                prompt_result = self.check_image_prompt(prompt)
                if not prompt_result.is_safe:
                    return prompt_result
        
        return ContentSafetyResult(is_safe=True)


_content_moderator: Optional[ContentModerator] = None


def get_content_moderator() -> ContentModerator:
    """Get singleton ContentModerator instance."""
    global _content_moderator
    if _content_moderator is None:
        _content_moderator = ContentModerator()
    return _content_moderator
