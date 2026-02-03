"""
Context Summarization Service for MVP Requirements Generator

Provides intelligent summarization of context artifacts to fit within LLM token limits.
Extracts key signals for template routing without dumping full JSON payloads.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _to_plain_dict(obj: Any) -> Any:
    """
    Convert any object to plain Python dict/list recursively.
    Handles Pydantic models, dataclasses, and other custom objects.
    """
    if obj is None:
        return None
    
    # Handle Pydantic models
    if hasattr(obj, 'model_dump'):
        return _to_plain_dict(obj.model_dump())
    if hasattr(obj, 'dict'):
        return _to_plain_dict(obj.dict())
    
    # Handle dataclasses
    if hasattr(obj, '__dataclass_fields__'):
        from dataclasses import asdict
        return _to_plain_dict(asdict(obj))
    
    # Handle dict
    if isinstance(obj, dict):
        return {k: _to_plain_dict(v) for k, v in obj.items()}
    
    # Handle list/tuple
    if isinstance(obj, (list, tuple)):
        return [_to_plain_dict(item) for item in obj]
    
    # Handle primitives
    if isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Fallback: convert to string
    try:
        return str(obj)
    except:
        return ""


def _safe_list(obj: Any) -> List[Any]:
    """Safely convert object to a list for iteration."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, (tuple, set)):
        return list(obj)
    if isinstance(obj, dict):
        return list(obj.values())
    # Try to iterate
    try:
        return list(obj)
    except (TypeError, ValueError):
        return [obj] if obj else []


def _safe_dict(obj: Any) -> Dict[str, Any]:
    """Safely convert object to a dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    # Handle Pydantic models
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    if hasattr(obj, 'dict'):
        return obj.dict()
    # Handle dataclasses
    if hasattr(obj, '__dataclass_fields__'):
        from dataclasses import asdict
        return asdict(obj)
    return {}

# Token budget configuration (approximate - 1 token ≈ 4 chars)
TOKEN_LIMITS = {
    "routing_coarse": {
        "total": 8000,  # Conservative limit for routing
        "vps_v2": 1500,
        "bmc_v2": 2500,
        "solution_critique": 1500,
        "vpc_v2": 1500,
        "metadata": 500
    },
    "routing_final": {
        "total": 6000,
        "vps_v2": 1000,
        "bmc_v2": 1500,
        "solution_critique": 1000,
        "vpc_v2": 1000,
        "metadata": 500
    },
    "questions_base": {
        "total": 6000,
        "vps_v2": 1000,
        "bmc_v2": 1500,
        "solution_critique": 1000,
        "vpc_v2": 1000,
        "metadata": 500
    },
    "prd_generation": {
        "total": 12000,  # Larger budget for PRD generation
        "vps_v2": 2500,
        "bmc_v2": 4000,
        "solution_critique": 2500,
        "vpc_v2": 2000,
        "metadata": 1000
    }
}

DEFAULT_CHAR_LIMIT = 6000  # ~1500 tokens per artifact


@dataclass
class SummarizedContext:
    """Container for summarized context ready for prompt templates."""
    vps_v2_summary: str
    bmc_v2_summary: str
    solution_critique_summary: str
    vpc_v2_summary: Optional[str]
    metadata: Dict[str, Any]
    token_estimate: int


class ContextSummarizer:
    """
    Summarizes context artifacts for efficient LLM processing.
    
    Instead of dumping full JSON, extracts key signals relevant to:
    - Template routing (what type of product/service is this?)
    - PRD generation (what are the key requirements?)
    """
    
    def __init__(self, use_case: str = "routing_coarse"):
        """
        Initialize summarizer with token limits for specific use case.
        
        Args:
            use_case: One of 'routing_coarse', 'routing_final', 'questions_base', 'prd_generation'
        """
        self.use_case = use_case
        self.limits = TOKEN_LIMITS.get(use_case, TOKEN_LIMITS["routing_coarse"])
    
    def summarize_context_pack(self, context_pack: Dict[str, Any]) -> SummarizedContext:
        """
        Summarize entire context pack for prompt injection.
        
        Args:
            context_pack: Full context pack from ContextLoaderService
            
        Returns:
            SummarizedContext with token-budgeted summaries
        """
        # Convert to plain dicts to avoid Pydantic/dataclass issues
        context_pack = _to_plain_dict(context_pack) or {}
        
        artifacts = _safe_dict(context_pack.get("artifacts", {}))
        optional_artifacts = _safe_dict(context_pack.get("optional_artifacts", {}))
        metadata = _safe_dict(context_pack.get("metadata", {}))
        
        # Summarize each artifact
        vps_v2_summary = self._summarize_vps_v2(
            artifacts.get("vps_v2", {}).get("data", {}),
            char_limit=self.limits["vps_v2"] * 4
        )
        
        bmc_v2_summary = self._summarize_bmc_v2(
            artifacts.get("bmc_v2", {}).get("data", {}),
            char_limit=self.limits["bmc_v2"] * 4
        )
        
        critique_summary = self._summarize_solution_critique(
            artifacts.get("solution_critique", {}).get("data", {}),
            char_limit=self.limits["solution_critique"] * 4
        )
        
        vpc_v2_summary = None
        if "vpc_v2" in optional_artifacts:
            vpc_v2_summary = self._summarize_vpc_v2(
                optional_artifacts["vpc_v2"].get("data", {}),
                char_limit=self.limits["vpc_v2"] * 4
            )
        
        # Calculate token estimate
        total_chars = (
            len(vps_v2_summary) + 
            len(bmc_v2_summary) + 
            len(critique_summary) + 
            (len(vpc_v2_summary) if vpc_v2_summary else 0)
        )
        token_estimate = total_chars // 4
        
        logger.info(f"📊 Context summarized for {self.use_case}: ~{token_estimate} tokens")
        
        return SummarizedContext(
            vps_v2_summary=vps_v2_summary,
            bmc_v2_summary=bmc_v2_summary,
            solution_critique_summary=critique_summary,
            vpc_v2_summary=vpc_v2_summary,
            metadata=metadata,
            token_estimate=token_estimate
        )
    
    def _summarize_vps_v2(self, vps_data: Dict[str, Any], char_limit: int = DEFAULT_CHAR_LIMIT) -> str:
        """
        Extract key signals from VPS v2 for template routing.
        
        Key signals:
        - Target customer description
        - Core problem being solved
        - Solution approach
        - Key differentiators
        - Value proposition statement
        """
        if not vps_data:
            return "VPS v2: No data available"
        
        lines = ["## Value Proposition Statement v2"]
        
        # Core statement (most important)
        if vps_data.get("statement"):
            lines.append(f"**Statement**: {self._truncate(vps_data['statement'], 500)}")
        
        # Target customer
        if vps_data.get("target_customer"):
            lines.append(f"**Target Customer**: {self._truncate(vps_data['target_customer'], 300)}")
        
        # Problem
        if vps_data.get("problem"):
            lines.append(f"**Problem**: {self._truncate(vps_data['problem'], 300)}")
        
        # Solution
        if vps_data.get("solution"):
            lines.append(f"**Solution**: {self._truncate(vps_data['solution'], 300)}")
        
        # Key benefits
        if vps_data.get("key_benefits"):
            benefits = _safe_list(vps_data["key_benefits"])
            if benefits:
                benefits_text = ", ".join(str(b) for b in benefits[:5])
                lines.append(f"**Key Benefits**: {self._truncate(benefits_text, 200)}")
        
        # Differentiators
        if vps_data.get("differentiators"):
            diff = _safe_list(vps_data["differentiators"])
            if diff:
                diff_text = ", ".join(str(d) for d in diff[:5])
                lines.append(f"**Differentiators**: {self._truncate(diff_text, 200)}")
        
        # Check nested structure (some VPS formats have 'vps' key)
        if vps_data.get("vps") and isinstance(vps_data["vps"], dict):
            nested = vps_data["vps"]
            if nested.get("for_statement"):
                lines.append(f"**For**: {self._truncate(nested['for_statement'], 200)}")
            if nested.get("who_statement"):
                lines.append(f"**Who**: {self._truncate(nested['who_statement'], 200)}")
            if nested.get("our_product_is"):
                lines.append(f"**Our Product**: {self._truncate(nested['our_product_is'], 200)}")
            if nested.get("unlike"):
                lines.append(f"**Unlike**: {self._truncate(nested['unlike'], 200)}")
        
        result = "\n".join(lines)
        return self._truncate(result, char_limit)
    
    def _summarize_bmc_v2(self, bmc_data: Dict[str, Any], char_limit: int = DEFAULT_CHAR_LIMIT) -> str:
        """
        Extract key signals from BMC v2 for template routing.
        
        Key signals for routing:
        - Key Activities (digital vs physical vs service)
        - Revenue Streams (subscription, transaction, licensing)
        - Channels (online, offline, hybrid)
        - Key Resources (tech, human, physical)
        - Customer Segments (B2B, B2C, marketplace)
        """
        if not bmc_data:
            return "BMC v2: No data available"
        
        lines = ["## Business Model Canvas v2"]
        
        # Customer Segments (critical for routing)
        segments = bmc_data.get("customer_segments", [])
        if segments:
            seg_summary = self._extract_bmc_block_summary(segments, "segments")
            lines.append(f"**Customer Segments**: {self._truncate(seg_summary, 400)}")
        
        # Value Propositions
        value_props = bmc_data.get("value_propositions", [])
        if value_props:
            vp_summary = self._extract_bmc_block_summary(value_props, "value")
            lines.append(f"**Value Propositions**: {self._truncate(vp_summary, 400)}")
        
        # Channels (important for digital vs offline)
        channels = bmc_data.get("channels", [])
        if channels:
            ch_summary = self._extract_bmc_block_summary(channels, "channels")
            lines.append(f"**Channels**: {self._truncate(ch_summary, 300)}")
        
        # Revenue Streams (critical for business model type)
        revenue = bmc_data.get("revenue_streams", [])
        if revenue:
            rev_summary = self._extract_bmc_block_summary(revenue, "revenue")
            lines.append(f"**Revenue Streams**: {self._truncate(rev_summary, 400)}")
        
        # Key Activities (critical for product type)
        activities = bmc_data.get("key_activities", [])
        if activities:
            act_summary = self._extract_bmc_block_summary(activities, "activities")
            lines.append(f"**Key Activities**: {self._truncate(act_summary, 400)}")
        
        # Key Resources (tech vs physical vs human)
        resources = bmc_data.get("key_resources", [])
        if resources:
            res_summary = self._extract_bmc_block_summary(resources, "resources")
            lines.append(f"**Key Resources**: {self._truncate(res_summary, 300)}")
        
        # Key Partnerships
        partners = bmc_data.get("key_partnerships", [])
        if partners:
            part_summary = self._extract_bmc_block_summary(partners, "partners")
            lines.append(f"**Key Partnerships**: {self._truncate(part_summary, 300)}")
        
        # Cost Structure
        costs = bmc_data.get("cost_structure", [])
        if costs:
            cost_summary = self._extract_bmc_block_summary(costs, "costs")
            lines.append(f"**Cost Structure**: {self._truncate(cost_summary, 300)}")
        
        result = "\n".join(lines)
        return self._truncate(result, char_limit)
    
    def _extract_bmc_block_summary(self, block_items: Any, block_type: str) -> str:
        """Extract summary from BMC block items."""
        if not block_items:
            return "Not specified"
        
        # Convert to safe list before slicing
        items_list = _safe_list(block_items)
        if not items_list:
            return "Not specified"
        
        summaries = []
        for item in items_list[:5]:  # Max 5 items
            if isinstance(item, dict):
                # Extract name/title and brief description
                name = item.get("name") or item.get("title") or item.get("type", "")
                desc = item.get("description", "")
                if name:
                    if desc:
                        summaries.append(f"{name}: {self._truncate(desc, 100)}")
                    else:
                        summaries.append(name)
                elif desc:
                    summaries.append(self._truncate(desc, 150))
            elif isinstance(item, str):
                summaries.append(self._truncate(item, 150))
        
        return "; ".join(summaries) if summaries else "Not specified"
    
    def _summarize_solution_critique(self, critique_data: Dict[str, Any], char_limit: int = DEFAULT_CHAR_LIMIT) -> str:
        """
        Extract key signals from Solution Critique.
        
        Key signals:
        - Overall assessment
        - Critical gaps identified
        - Recommendations
        - Competitive insights
        """
        if not critique_data:
            return "Solution Critique: No data available"
        
        lines = ["## Solution Critique Summary"]
        
        # Check for results structure
        results = critique_data.get("results", critique_data)
        if isinstance(results, dict):
            # Overall assessment
            if results.get("overall_assessment"):
                lines.append(f"**Assessment**: {self._truncate(results['overall_assessment'], 400)}")
            
            # Executive summary
            if results.get("executive_summary"):
                lines.append(f"**Executive Summary**: {self._truncate(results['executive_summary'], 400)}")
            
            # Key strengths
            strengths = _safe_list(results.get("strengths", []))
            if strengths:
                strength_text = "; ".join(str(s.get("point", s) if isinstance(s, dict) else s) for s in strengths[:3])
                lines.append(f"**Strengths**: {self._truncate(strength_text, 300)}")
            
            # Key weaknesses/gaps
            weaknesses = _safe_list(results.get("weaknesses", results.get("gaps", [])))
            if weaknesses:
                weak_text = "; ".join(str(w.get("point", w) if isinstance(w, dict) else w) for w in weaknesses[:3])
                lines.append(f"**Gaps/Weaknesses**: {self._truncate(weak_text, 300)}")
            
            # Recommendations
            recs = _safe_list(results.get("recommendations", []))
            if recs:
                rec_text = "; ".join(str(r.get("recommendation", r) if isinstance(r, dict) else r) for r in recs[:3])
                lines.append(f"**Recommendations**: {self._truncate(rec_text, 300)}")
            
            # Competitive landscape
            competitors = _safe_list(results.get("competitive_analysis", results.get("competitors", [])))
            if competitors:
                comp_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in competitors[:5]]
                lines.append(f"**Competitors Analyzed**: {', '.join(comp_names)}")
        
        result = "\n".join(lines)
        return self._truncate(result, char_limit)
    
    def _summarize_vpc_v2(self, vpc_data: Dict[str, Any], char_limit: int = DEFAULT_CHAR_LIMIT) -> str:
        """
        Extract key signals from VPC v2.
        
        Key signals:
        - Jobs to be done
        - Key pains
        - Desired gains
        - Solution fit
        """
        if not vpc_data:
            return None
        
        lines = ["## Value Proposition Canvas v2"]
        
        # Customer Profile side
        customer_profile = vpc_data.get("customer_profile", {})
        if customer_profile:
            # Jobs to be done
            jobs = customer_profile.get("jobs_to_be_done", customer_profile.get("jobs", []))
            if jobs:
                job_texts = self._extract_vpc_items(jobs, 3)
                if job_texts:
                    lines.append(f"**Jobs to be Done**: {self._truncate('; '.join(job_texts), 300)}")
            
            # Pains
            pains = customer_profile.get("pains", [])
            if pains:
                pain_texts = self._extract_vpc_items(pains, 3)
                if pain_texts:
                    lines.append(f"**Key Pains**: {self._truncate('; '.join(pain_texts), 300)}")
            
            # Gains
            gains = customer_profile.get("gains", [])
            if gains:
                gain_texts = self._extract_vpc_items(gains, 3)
                if gain_texts:
                    lines.append(f"**Desired Gains**: {self._truncate('; '.join(gain_texts), 300)}")
        
        # Value Map side
        value_map = vpc_data.get("value_map_selections", vpc_data.get("value_map", {}))
        if value_map:
            # Products & Services
            products = value_map.get("products_services", value_map.get("products", []))
            if products:
                prod_texts = self._extract_vpc_items(products, 3)
                if prod_texts:
                    lines.append(f"**Products/Services**: {self._truncate('; '.join(prod_texts), 300)}")
            
            # Pain Relievers
            relievers = value_map.get("pain_relievers", [])
            if relievers:
                rel_texts = self._extract_vpc_items(relievers, 3)
                if rel_texts:
                    lines.append(f"**Pain Relievers**: {self._truncate('; '.join(rel_texts), 300)}")
            
            # Gain Creators
            creators = value_map.get("gain_creators", [])
            if creators:
                creat_texts = self._extract_vpc_items(creators, 3)
                if creat_texts:
                    lines.append(f"**Gain Creators**: {self._truncate('; '.join(creat_texts), 300)}")
        
        if len(lines) <= 1:
            return None
        
        result = "\n".join(lines)
        return self._truncate(result, char_limit)
    
    def _extract_vpc_items(self, items: Any, max_items: int = 3) -> List[str]:
        """Extract text summaries from VPC items."""
        # Convert to safe list before slicing
        items_list = _safe_list(items)
        if not items_list:
            return []
        
        texts = []
        for item in items_list[:max_items]:
            if isinstance(item, dict):
                text = item.get("description") or item.get("text") or item.get("name") or str(item)
                texts.append(self._truncate(text, 150))
            elif isinstance(item, str):
                texts.append(self._truncate(item, 150))
        return texts
    
    def _truncate(self, text: str, max_chars: int) -> str:
        """Truncate text to max characters, preserving word boundaries."""
        if not text:
            return ""
        
        text = str(text).strip()
        
        if len(text) <= max_chars:
            return text
        
        # Find last space before limit
        truncated = text[:max_chars]
        last_space = truncated.rfind(' ')
        
        if last_space > max_chars * 0.7:  # Only use space if it's not too far back
            truncated = truncated[:last_space]
        
        return truncated.rstrip('.,;:') + "..."


def get_summarized_context(
    context_pack: Dict[str, Any],
    use_case: str = "routing_coarse"
) -> SummarizedContext:
    """
    Convenience function to get summarized context.
    
    Args:
        context_pack: Full context pack
        use_case: One of 'routing_coarse', 'routing_final', 'questions_base', 'prd_generation'
        
    Returns:
        SummarizedContext ready for prompt templates
    """
    summarizer = ContextSummarizer(use_case=use_case)
    return summarizer.summarize_context_pack(context_pack)
