"""
Relevance Ranker Node

Node 10 in the Problem Generator agent graph.
Ranks filtered statements by relevance to user parameters using weighted scoring.
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config

from ..graph_state import ProblemGraphState

logger = logging.getLogger(__name__)


@traceable(name="relevance_ranker_node")
def relevance_ranker_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 10: Relevance Ranker
    
    Ranks filtered statements by relevance to user parameters using weighted scoring.
    
    Args:
        state: Current workflow state with filtered statements
        
    Returns:
        Updated workflow state with relevance-ranked statements
    """
    logger.info("Starting relevance ranking")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "relevance_ranker"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        ranking_config = agent_config.get("relevance_ranking", {})
        
        # Get filtered statements and user parameters
        filtered_statements = state.get("filtered_statements", [])
        user_params = state.get("params", {})
        
        if not filtered_statements:
            logger.warning("No filtered statements found for relevance ranking")
            state["ranked_statements"] = []
            return state
        
        if not user_params:
            logger.warning("No user parameters found for relevance ranking")
            # Return statements with default ranking
            state["ranked_statements"] = filtered_statements
            return state
        
        logger.info(f"Ranking {len(filtered_statements)} statements by relevance to user parameters")
        
        # =============================================
        # CALCULATE RELEVANCE SCORES
        # =============================================
        
        ranked_statements = []
        ranking_stats = {
            "statements_ranked": 0,
            "avg_relevance_score": 0,
            "max_relevance_score": 0,
            "min_relevance_score": float('inf'),
            "parameter_matches": {}
        }
        
        for statement in filtered_statements:
            # Calculate comprehensive relevance score
            relevance_score, match_details = calculate_relevance_score(statement, user_params, ranking_config)
            
            # Add relevance metadata
            statement["relevance_score"] = relevance_score
            statement["parameter_matches"] = match_details
            statement["ranked_at"] = datetime.now().isoformat()
            
            ranked_statements.append(statement)
            
            # Update stats
            ranking_stats["statements_ranked"] += 1
            ranking_stats["max_relevance_score"] = max(ranking_stats["max_relevance_score"], relevance_score)
            ranking_stats["min_relevance_score"] = min(ranking_stats["min_relevance_score"], relevance_score)
            
            # Track parameter matches
            for param, score in match_details.items():
                if param not in ranking_stats["parameter_matches"]:
                    ranking_stats["parameter_matches"][param] = []
                ranking_stats["parameter_matches"][param].append(score)
        
        # Calculate average relevance score
        if ranked_statements:
            total_relevance = sum(s["relevance_score"] for s in ranked_statements)
            ranking_stats["avg_relevance_score"] = total_relevance / len(ranked_statements)
        
        # =============================================
        # STRICT FILTERING: Remove non-matching statements
        # =============================================
        
        # CRITICAL: Filter out statements that don't match user's industry or geography
        # This ensures we only return relevant problems, even if it means fewer results
        strictly_filtered = []
        filtered_out_count = 0
        
        for statement in ranked_statements:
            match_details = statement.get("parameter_matches", {})
            industry_score = match_details.get("industry", 0.5)
            geography_score = match_details.get("geography", 0.5)
            
            # STRICT: Both industry AND geography must have non-zero scores
            # A score of 0.0 means complete mismatch - these should be excluded
            if industry_score > 0.0 and geography_score > 0.0:
                strictly_filtered.append(statement)
            else:
                filtered_out_count += 1
                logger.info(f"Filtered out statement due to strict matching: industry={industry_score}, geography={geography_score}, category={statement.get('category', 'N/A')}")
        
        logger.info(f"Strict filtering: kept {len(strictly_filtered)}/{len(ranked_statements)} statements (filtered out {filtered_out_count} non-matching)")
        
        # If strict filtering removed all statements, log a warning but keep top 3 by score
        if len(strictly_filtered) == 0 and len(ranked_statements) > 0:
            logger.warning("Strict filtering removed ALL statements - keeping top 3 by relevance score as fallback")
            ranked_statements.sort(key=lambda x: x["relevance_score"], reverse=True)
            strictly_filtered = ranked_statements[:3]
        
        # =============================================
        # SORT BY RELEVANCE SCORE
        # =============================================
        
        # Sort by relevance score (descending)
        strictly_filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Add ranking positions
        for i, statement in enumerate(strictly_filtered):
            statement["relevance_rank"] = i + 1
        
        # =============================================
        # APPLY DIVERSITY CONSTRAINTS (within matching statements only)
        # =============================================
        
        # Note: We no longer diversify across industries - we stay within user's specified industry
        diversified_statements = apply_diversity_constraints(
            strictly_filtered, 
            user_params, 
            ranking_config
        )
        
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["ranked_statements"] = diversified_statements
        state["ranking_stats"] = ranking_stats
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        ranking_metrics = {
            "statements_ranked": len(filtered_statements),
            "final_ranked_count": len(diversified_statements),
            "avg_relevance_score": ranking_stats["avg_relevance_score"],
            "score_range": ranking_stats["max_relevance_score"] - ranking_stats["min_relevance_score"],
            "processing_time_ms": total_time
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["relevance_ranker"] = ranking_metrics
        
        logger.info(f"Relevance ranking completed successfully")
        logger.info(f"Ranked {len(diversified_statements)} statements")
        logger.info(f"Average relevance score: {ranking_stats['avg_relevance_score']:.2f}")
        logger.info(f"Top statement score: {ranking_stats['max_relevance_score']:.2f}")
        
        return state
        
    except Exception as e:
        error_msg = f"Relevance ranking failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state


def calculate_relevance_score(
    statement: Dict[str, Any], 
    user_params: Dict[str, Any], 
    config: Dict[str, Any]
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate relevance score for a statement based on user parameters.
    
    Args:
        statement: Statement to score
        user_params: User parameters
        config: Ranking configuration
        
    Returns:
        Tuple of (relevance_score, match_details)
    """
    total_score = 0.0
    match_details = {}
    
    # Parameter relevance weights (all parameters now mandatory with balanced importance)
    PARAMETER_WEIGHTS = {
        "industry": 0.25,           # Core business context
        "geography": 0.20,          # Regional specificity
        "target_customer": 0.20,    # Market segment focus (now mandatory)
        "impact_focus": 0.15,       # Impact focus dimension (now mandatory)
        "product_type": 0.15,       # Solution category
        "background": 0.05          # User context
    }
    
    # =============================================
    # INDUSTRY MATCHING
    # =============================================
    
    industry_score = calculate_industry_match(
        statement.get("category", ""), 
        user_params.get("industry", [])
    )
    match_details["industry"] = industry_score
    total_score += industry_score * PARAMETER_WEIGHTS.get("industry", 0.25)
    
    # =============================================
    # GEOGRAPHY MATCHING
    # =============================================
    
    geography_score = calculate_geography_match(
        statement.get("geography", ""), 
        user_params.get("geography", [])
    )
    match_details["geography"] = geography_score
    total_score += geography_score * PARAMETER_WEIGHTS.get("geography", 0.20)
    
    # =============================================
    # IMPACT FOCUS MATCHING
    # =============================================
    
    impact_focus_score = calculate_impact_focus_match(
        statement.get("impact_focus", ""), 
        user_params.get("impact_focus", [])
    )
    match_details["impact_focus"] = impact_focus_score
    total_score += impact_focus_score * PARAMETER_WEIGHTS.get("impact_focus", 0.15)
    
    # =============================================
    # PRODUCT TYPE MATCHING
    # =============================================
    
    product_score = calculate_product_type_match(
        statement, 
        user_params.get("product_type", [])
    )
    match_details["product_type"] = product_score
    total_score += product_score * PARAMETER_WEIGHTS.get("product_type", 0.15)
    
    # =============================================
    # TARGET CUSTOMER MATCHING
    # =============================================
    
    customer_score = calculate_target_customer_match(
        statement, 
        user_params.get("target_customer", [])
    )
    match_details["target_customer"] = customer_score
    total_score += customer_score * PARAMETER_WEIGHTS.get("target_customer", 0.20)
    
    # =============================================
    # BACKGROUND MATCHING
    # =============================================
    
    background_score = calculate_background_match(
        statement,
        user_params.get("background", [])
    )
    match_details["background"] = background_score
    total_score += background_score * PARAMETER_WEIGHTS.get("background", 0.05)
    
    return total_score, match_details


def calculate_industry_match(statement_category: str, user_industries: List[str]) -> float:
    """
    Calculate industry matching score with STRICT enforcement.
    
    CRITICAL: When user specifies an industry, we MUST return problems in that industry.
    Non-matching industries should be heavily penalized (score = 0.0) to ensure
    they are filtered out during ranking.
    """
    if not user_industries or not statement_category:
        return 0.5  # Neutral score only when no preference specified
    
    statement_category_lower = statement_category.lower().strip()
    
    # Direct match - highest priority
    for user_industry in user_industries:
        if user_industry.lower().strip() == statement_category_lower:
            return 1.0
        # Check if user industry is contained in statement category or vice versa
        if user_industry.lower() in statement_category_lower or statement_category_lower in user_industry.lower():
            return 1.0
    
    # Related industry matching - STRICT mapping (only very closely related)
    industry_relations = {
        "Agriculture": ["Food Security", "Rural Development", "Agriculture / Food", "Agribusiness", "Farming"],
        "Healthcare": ["Health", "Medical", "Healthcare / Life Sciences", "Public Health"],
        "FinTech": ["Finance", "Banking", "Financial Inclusion", "Financial Services & FinTech", "Financial Services"],
        "Education": ["Learning", "Training", "Skills", "Education & EdTech", "EdTech"],
        "Energy": ["Power", "Renewable Energy", "Electricity", "Energy & Utilities", "Clean Energy"],
        "Transportation": ["Logistics", "Mobility", "Transport", "Transportation & Mobility"],
        "ICT": ["Technology", "Digital", "Mobile", "ICT / Telecom", "Telecom", "Tech"],
        "Manufacturing": ["Production", "Industrial", "Manufacturing"],
        "Construction": ["Building", "Infrastructure", "Construction & Real Estate", "Real Estate"],
        "Tourism": ["Travel", "Hospitality", "Tourism & Hospitality"],
        "Water": ["Sanitation", "Clean Water", "Water & Sanitation", "WASH"],
        "Climate": ["Environment", "Sustainability", "Climate / Environmental Services", "Environmental"],
        "Government": ["Public", "Policy", "Public Services / GovTech", "GovTech"],
        "Mining": ["Natural Resources", "Extraction", "Mining & Natural Resources"],
        "Media": ["Entertainment", "Content", "Media & Entertainment"],
        "Retail": ["Commerce", "Shopping", "Retail & e-Commerce", "E-Commerce", "eCommerce"],
        "Sports": ["Recreation", "Fitness", "Sports & Recreation", "Sports", "Athletics", "Gym", "Wellness"]
    }
    
    # Check for related matches - only allow closely related industries
    for user_industry in user_industries:
        user_industry_lower = user_industry.lower().strip()
        
        # Check if statement category is in user's related industries
        related_to_user = industry_relations.get(user_industry, [])
        for related in related_to_user:
            if related.lower() == statement_category_lower or statement_category_lower in related.lower():
                return 0.9  # High score for closely related
        
        # Check if user industry is in statement category's related industries
        related_to_statement = industry_relations.get(statement_category, [])
        for related in related_to_statement:
            if related.lower() == user_industry_lower or user_industry_lower in related.lower():
                return 0.9  # High score for closely related
    
    # STRICT: Non-matching industries get ZERO score - they should be filtered out
    logger.warning(f"Industry mismatch: statement='{statement_category}' vs user='{user_industries}' - assigning 0.0 score")
    return 0.0  # ZERO score for unrelated industries - this ensures they are filtered out


def calculate_background_match(statement: Dict[str, Any], user_backgrounds: List[str]) -> float:
    """Calculate background matching score."""
    if not user_backgrounds:
        return 0.5  # Neutral score
    
    # Extract relevant fields from statement for background matching
    statement_text = f"{statement.get('title', '')} {statement.get('description', '')}".lower()
    
    # Background-related keywords mapping
    background_keywords = {
        "Software Developer": ["software", "app", "digital", "platform", "tech", "development"],
        "Business Analyst": ["business", "analysis", "strategy", "operations", "process"],
        "Product Manager": ["product", "management", "user", "customer", "market"],
        "Consultant": ["consulting", "advisory", "strategy", "implementation"],
        "Entrepreneur": ["startup", "business", "venture", "innovation", "founder"],
        "Researcher": ["research", "study", "analysis", "data", "insights"],
        "Student": ["education", "learning", "academic", "university", "study"]
    }
    
    # Check for background-related matches
    for user_background in user_backgrounds:
        keywords = background_keywords.get(user_background, [user_background.lower()])
        for keyword in keywords:
            if keyword in statement_text:
                return 0.8
    
    return 0.3  # Lower relevance for unrelated backgrounds


def calculate_geography_match(statement_geography: str, user_geographies: List[str]) -> float:
    """
    Calculate geography matching score with STRICT enforcement.
    
    CRITICAL: When user specifies a country (e.g., Ethiopia), we MUST return problems
    specifically for that country. Problems from other countries should be heavily
    penalized (score = 0.0) to ensure they are filtered out.
    """
    if not user_geographies or not statement_geography:
        return 0.5  # Neutral score only when no preference specified
    
    statement_geo_lower = statement_geography.lower().strip()
    
    # Direct country match - highest priority
    for user_geo in user_geographies:
        user_geo_lower = user_geo.lower().strip()
        # Exact match or contained within
        if user_geo_lower in statement_geo_lower or statement_geo_lower in user_geo_lower:
            return 1.0
        # Check for country name variations
        if user_geo_lower == statement_geo_lower:
            return 1.0
    
    # Check if statement mentions "Africa" generally when user specified a specific country
    # This is NOT a match - we want specific country problems
    if "africa" in statement_geo_lower and not any(user_geo.lower() in statement_geo_lower for user_geo in user_geographies):
        logger.warning(f"Geography mismatch: statement mentions 'Africa' generally but user wants specific country: {user_geographies}")
        return 0.0  # Reject generic "Africa" when user wants specific country
    
    # Regional matching - only if user specified a region, not a specific country
    african_regions = {
        "west africa": ["nigeria", "ghana", "senegal", "mali", "burkina faso", "côte d'ivoire", "liberia", "sierra leone", "guinea", "togo", "benin", "niger", "gambia", "mauritania", "cape verde", "guinea-bissau"],
        "east africa": ["kenya", "ethiopia", "uganda", "tanzania", "rwanda", "burundi", "south sudan", "somalia", "djibouti", "eritrea"],
        "southern africa": ["south africa", "botswana", "namibia", "zambia", "zimbabwe", "mozambique", "malawi", "lesotho", "eswatini", "angola"],
        "north africa": ["egypt", "morocco", "tunisia", "algeria", "libya", "sudan"],
        "central africa": ["cameroon", "democratic republic of congo", "drc", "congo", "chad", "central african republic", "gabon", "equatorial guinea"]
    }
    
    # Only allow regional matching if user specified a region (not a specific country)
    for user_geo in user_geographies:
        user_geo_lower = user_geo.lower().strip()
        
        # Check if user specified a region
        if user_geo_lower in african_regions:
            # User specified a region - allow countries within that region
            region_countries = african_regions[user_geo_lower]
            if any(country in statement_geo_lower for country in region_countries):
                return 0.9
    
    # STRICT: Non-matching geographies get ZERO score - they should be filtered out
    logger.warning(f"Geography mismatch: statement='{statement_geography}' vs user='{user_geographies}' - assigning 0.0 score")
    return 0.0  # ZERO score for different countries - this ensures they are filtered out


def calculate_impact_focus_match(statement_impact: str, user_impact_focus: List[str]) -> float:
    """Calculate impact focus matching score."""
    if not user_impact_focus or not statement_impact:
        return 0.5
    
    statement_impact_lower = statement_impact.lower()
    
    # Direct match
    for user_focus in user_impact_focus:
        if user_focus.lower() in statement_impact_lower:
            return 1.0
    
    # Related impact focus matching
    impact_relations = {
        "commercial": ["Fully Commercial", "Business", "Profit"],
        "social": ["Social Venture", "Social Impact", "Community"],
        "non-profit": ["Non-Profit / Foundations", "NGO", "Foundation"],
        "venture": ["Social Venture", "Startup", "Enterprise"]
    }
    
    for user_focus in user_impact_focus:
        user_focus_lower = user_focus.lower()
        for key, related in impact_relations.items():
            if user_focus in related and key in statement_impact_lower:
                return 0.8
    
    return 0.3


def calculate_demographic_match(statement_demographic: str, user_demographics: List[str]) -> float:
    """Calculate demographic matching score."""
    if not user_demographics or not statement_demographic:
        return 0.5
    
    statement_demo_lower = statement_demographic.lower()
    
    # Direct match
    for user_demo in user_demographics:
        if user_demo.lower() in statement_demo_lower:
            return 1.0
    
    # Related demographic matching
    demo_relations = {
        "smallholder farmers": ["Rural Populations", "Smallholder Farmers", "Agriculture"],
        "women": ["Women & Girls", "Gender Equality"],
        "youth": ["Youth", "Students"],
        "small businesses": ["Micro Businesses", "SMEs", "Entrepreneurs"],
        "urban poor": ["Urban Poor", "Informal Workers"]
    }
    
    for user_demo in user_demographics:
        user_demo_lower = user_demo.lower()
        for key, related in demo_relations.items():
            if user_demo in related and key in statement_demo_lower:
                return 0.8
            if user_demo_lower in key and any(r.lower() in statement_demo_lower for r in related):
                return 0.8
    
    return 0.3


def calculate_product_type_match(statement: Dict[str, Any], user_product_types: List[str]) -> float:
    """Calculate product type matching score."""
    if not user_product_types:
        return 0.5
    
    statement_text = statement.get("statement", "").lower()
    
    # Product type indicators in statement
    digital_indicators = ["mobile", "app", "digital", "online", "platform", "software", "tech"]
    physical_indicators = ["food", "beverage", "hygiene", "fertilizer", "goods", "product"]
    manufacturing_indicators = ["equipment", "device", "tool", "machine", "manufacturing", "engineering", "industrial"]
    creative_indicators = ["fashion", "design", "entertainment", "sports", "writing", "creative", "art", "music", "film", "media", "content", "brand", "marketing", "advertising"]
    service_indicators = ["service", "training", "education", "consultation", "support"]
    
    statement_product_types = []
    
    if any(indicator in statement_text for indicator in digital_indicators):
        statement_product_types.append("Digital")
    if any(indicator in statement_text for indicator in physical_indicators):
        statement_product_types.append("Physical")
    if any(indicator in statement_text for indicator in manufacturing_indicators):
        statement_product_types.append("Manufacturing")
    if any(indicator in statement_text for indicator in creative_indicators):
        statement_product_types.append("Creative Products / Services")
    if any(indicator in statement_text for indicator in service_indicators):
        statement_product_types.append("Services")
    
    # Check for matches
    for user_type in user_product_types:
        if user_type in statement_product_types:
            return 1.0
        if user_type == "Hybrid" and len(statement_product_types) > 1:
            return 0.9
    
    return 0.4


def calculate_target_customer_match(statement: Dict[str, Any], user_customers: List[str]) -> float:
    """Calculate target customer matching score."""
    if not user_customers:
        return 0.5
    
    statement_text = statement.get("statement", "").lower()
    impact_focus = statement.get("impact_focus", "").lower()
    
    # Customer indicators
    customer_indicators = {
        "Mass Consumers": ["consumers", "households", "families", "individuals"],
        "Rural Consumers": ["rural", "farmers", "villages", "countryside"],
        "Urban Consumers": ["urban", "city", "metropolitan", "towns"],
        "Micro Businesses": ["micro", "small business", "entrepreneurs", "startups"],
        "SMEs": ["sme", "small medium", "businesses", "companies"],
        "Government": ["government", "public sector", "ministry", "agency"]
    }
    
    for user_customer in user_customers:
        indicators = customer_indicators.get(user_customer, [])
        if any(indicator in statement_text or indicator in impact_focus for indicator in indicators):
            return 1.0
    
    return 0.3



def apply_diversity_constraints(
    ranked_statements: List[Dict[str, Any]], 
    user_params: Dict[str, Any], 
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Apply diversity constraints to ensure variety in final results.
    
    Args:
        ranked_statements: Statements ranked by relevance
        user_params: User parameters
        config: Configuration
        
    Returns:
        Diversified list of statements
    """
    max_per_category = config.get("max_per_category", 3)
    max_per_geography = config.get("max_per_geography", 4)
    
    diversified = []
    category_counts = {}
    geography_counts = {}
    
    for statement in ranked_statements:
        category = statement.get("category", "Other")
        geography = statement.get("geography", "Unknown")
        
        # Check category diversity
        if category_counts.get(category, 0) >= max_per_category:
            continue
        
        # Check geography diversity
        if geography_counts.get(geography, 0) >= max_per_geography:
            continue
        
        # Add to diversified list
        diversified.append(statement)
        category_counts[category] = category_counts.get(category, 0) + 1
        geography_counts[geography] = geography_counts.get(geography, 0) + 1
    
    return diversified
