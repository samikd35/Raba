"""
Quality Filter Node

Node 9 in the Problem Generator agent graph.
Filters problem statements based on quality criteria and removes duplicates.
"""

import logging
from typing import Dict, Any, List, Set
from datetime import datetime
import re

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config

from ..graph_state import ProblemGraphState

logger = logging.getLogger(__name__)


@traceable(name="quality_filter_node")
def quality_filter_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 9: Quality Filter
    
    Filters problem statements based on quality criteria and removes duplicates.
    
    Args:
        state: Current workflow state with refined statements
        
    Returns:
        Updated workflow state with filtered quality statements
    """
    logger.info("Starting quality filtering")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "quality_filter"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        filter_config = agent_config.get("quality_filter", {})
        
        # Get refined statements
        refined_statements = state.get("refined_statements", [])
        if not refined_statements:
            logger.warning("No refined statements found for quality filtering")
            state["filtered_statements"] = []
            return state
        
        logger.info(f"Quality filtering {len(refined_statements)} refined statements")
        
        # =============================================
        # APPLY QUALITY FILTERS
        # =============================================
        
        # Initialize filtering stats
        filter_stats = {
            "input_statements": len(refined_statements),
            "passed_length_filter": 0,
            "passed_structure_filter": 0,
            "passed_content_filter": 0,
            "passed_entrepreneur_filter": 0,
            "passed_specificity_filter": 0,
            "passed_duplication_filter": 0,
            "final_statements": 0
        }
        
        # Step 1: Length Filter
        length_filtered = apply_length_filter(refined_statements, filter_config)
        filter_stats["passed_length_filter"] = len(length_filtered)
        logger.info(f"Length filter: {len(length_filtered)}/{len(refined_statements)} passed")
        
        # Step 2: Structure Filter (Cause → Effect format)
        structure_filtered = apply_structure_filter(length_filtered, filter_config)
        filter_stats["passed_structure_filter"] = len(structure_filtered)
        logger.info(f"Structure filter: {len(structure_filtered)}/{len(length_filtered)} passed")
        
        # Step 3: Content Quality Filter
        content_filtered = apply_content_filter(structure_filtered, filter_config)
        filter_stats["passed_content_filter"] = len(content_filtered)
        logger.info(f"Content filter: {len(content_filtered)}/{len(structure_filtered)} passed")
        
        # Step 4: STRICT Entrepreneur-Actionable Filter (reject government/policy problems)
        entrepreneur_filtered = apply_entrepreneur_actionable_filter(content_filtered, filter_config)
        filter_stats["passed_entrepreneur_filter"] = len(entrepreneur_filtered)
        logger.info(f"Entrepreneur filter: {len(entrepreneur_filtered)}/{len(content_filtered)} passed")
        
        # Step 5: Specificity Filter
        specificity_filtered = apply_specificity_filter(entrepreneur_filtered, filter_config)
        filter_stats["passed_specificity_filter"] = len(specificity_filtered)
        logger.info(f"Specificity filter: {len(specificity_filtered)}/{len(content_filtered)} passed")
        
        # Step 6: Deduplication Filter
        deduplicated = apply_deduplication_filter(specificity_filtered, filter_config)
        filter_stats["passed_duplication_filter"] = len(deduplicated)
        logger.info(f"Deduplication filter: {len(deduplicated)}/{len(specificity_filtered)} passed")
        
        # =============================================
        # FINAL RANKING AND SELECTION
        # =============================================
        
        # Calculate final quality scores
        for statement in deduplicated:
            statement["quality_score"] = calculate_comprehensive_quality_score(statement)
        
        # Sort by quality score
        deduplicated.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        
        # Apply final count limit
        max_statements = filter_config.get("max_final_statements", 15)
        final_statements = deduplicated[:max_statements]
        
        filter_stats["final_statements"] = len(final_statements)
        
        # =============================================
        # ADD QUALITY METADATA
        # =============================================
        
        for i, statement in enumerate(final_statements):
            statement["quality_rank"] = i + 1
            statement["filtered_at"] = datetime.now().isoformat()
            statement["filter_passed"] = [
                "length", "structure", "content", "entrepreneur_actionable", "specificity", "deduplication"
            ]
        
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["filtered_statements"] = final_statements
        state["filter_stats"] = filter_stats
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        filter_metrics = {
            "input_statements": len(refined_statements),
            "output_statements": len(final_statements),
            "filter_efficiency": len(final_statements) / max(len(refined_statements), 1),
            "avg_quality_score": sum(s.get("quality_score", 0) for s in final_statements) / max(len(final_statements), 1),
            "processing_time_ms": total_time
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["quality_filter"] = filter_metrics
        
        logger.info(f"Quality filtering completed successfully")
        logger.info(f"Filtered to {len(final_statements)} high-quality statements from {len(refined_statements)} input")
        logger.info(f"Average quality score: {filter_metrics['avg_quality_score']:.2f}")
        
        return state
        
    except Exception as e:
        error_msg = f"Quality filtering failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state


def apply_length_filter(statements: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter statements based on length requirements.
    
    Args:
        statements: List of statements to filter
        config: Filter configuration
        
    Returns:
        Filtered statements
    """
    min_length = config.get("min_statement_length", 50)
    max_length = config.get("max_statement_length", 3000)  # Updated for enhanced citation system
    
    filtered = []
    for statement in statements:
        text = statement.get("statement", "").strip()
        if min_length <= len(text) <= max_length:
            filtered.append(statement)
            logger.info(f"Length filter passed: {len(text)} chars")
        else:
            logger.warning(f"Length filter rejected: {len(text)} chars (range: {min_length}-{max_length}) - {text[:100]}...")
    
    return filtered


def apply_structure_filter(statements: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter statements based on cause-effect structure.
    
    Args:
        statements: List of statements to filter
        config: Filter configuration
        
    Returns:
        Filtered statements
    """
    # Structure indicators for cause-effect relationships
    structure_patterns = [
        r'\b(prevents?|preventing)\b',
        r'\b(causes?|causing)\b',
        r'\b(results? in|resulting in)\b',
        r'\b(leads? to|leading to)\b',
        r'\b(due to)\b',
        r'\b(because of?)\b',
        r'\b(forc(es?|ing))\b',
        r'\b(mak(es?|ing))\b',
        r'\b(affect(s?|ing))\b',
        r'\b(hinder(s?|ing))\b',
        r'\b(limit(s?|ing))\b'
    ]
    
    filtered = []
    for statement in statements:
        text = statement.get("statement", "").lower()
        
        # Check for structure indicators
        structure_matches = sum(
            1 for pattern in structure_patterns 
            if re.search(pattern, text)
        )
        
        if structure_matches >= 1:  # At least one structure indicator
            filtered.append(statement)
        else:
            logger.debug(f"Structure filter rejected: {text[:50]}...")
    
    return filtered


def apply_content_filter(statements: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter statements based on content quality.
    
    Args:
        statements: List of statements to filter
        config: Filter configuration
        
    Returns:
        Filtered statements
    """
    # Solution keywords to avoid
    solution_keywords = [
        "solution", "solve", "fix", "address", "implement", "develop",
        "create", "build", "establish", "launch", "start", "design",
        "introduce", "deploy", "install", "setup"
    ]
    
    # Problem indicators that should be present - expanded with word boundary patterns
    problem_keywords = [
        "lack", "shortage", "unable", "cannot", "prevents", "hinders",
        "barrier", "obstacle", "insufficient", "absence", "difficulty",
        "challenge", "problem", "issue", "gap", "need", "limited",
        "scarcity", "deficit", "constraint", "restriction", "underserved"
    ]
    
    # Negation patterns that might invalidate problem detection
    negation_patterns = [
        r'\bno\s+lack\b',
        r'\bwithout\s+(?:any\s+)?(?:problem|issue|challenge|difficulty)\b',
        r'\bovercome\s+the\s+(?:problem|issue|challenge|barrier)\b',
        r'\bsolved\s+the\s+(?:problem|issue|challenge)\b',
        r'\beliminated?\s+the\s+(?:problem|issue|shortage)\b',
        r'\bno\s+longer\s+(?:a\s+)?(?:problem|issue|challenge)\b'
    ]
    
    filtered = []
    for statement in statements:
        text = statement.get("statement", "").lower()
        
        # Check for excessive solution mentions (use word boundaries to avoid partial matches)
        solution_count = sum(1 for keyword in solution_keywords 
                           if re.search(r'\b' + re.escape(keyword) + r'\b', text))
        if solution_count > 1:  # Allow maximum 1 solution mention
            logger.debug(f"Content filter rejected (solutions): {text[:50]}...")
            continue
        
        # Check for problem indicators WITH WORD BOUNDARIES to avoid partial matches
        # e.g., "lacking" should match "lack", but "blacksmith" should not
        problem_count = sum(1 for keyword in problem_keywords 
                           if re.search(r'\b' + re.escape(keyword) + r'(?:s|ing|ed)?\b', text))
        
        # Check for negation patterns that invalidate problem detection
        negation_count = sum(1 for pattern in negation_patterns if re.search(pattern, text))
        
        # Effective problem count = detected problems - negations
        effective_problem_count = max(0, problem_count - negation_count)
        
        if effective_problem_count < 1:  # Must have at least 1 valid problem indicator
            logger.debug(f"Content filter rejected (no problems, detected={problem_count}, negated={negation_count}): {text[:50]}...")
            continue
        
        # Check for vague language
        vague_phrases = [
            "many people", "some individuals", "certain groups", "various",
            "several", "numerous", "lots of", "plenty of"
        ]
        
        vague_count = sum(1 for phrase in vague_phrases if phrase in text)
        if vague_count > 2:  # Too much vague language
            logger.debug(f"Content filter rejected (vague): {text[:50]}...")
            continue
        
        filtered.append(statement)
    
    return filtered


def apply_entrepreneur_actionable_filter(statements: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    STRICT filter to reject problems that are NOT solvable by entrepreneurs.
    Rejects government problems, policy issues, infrastructure requiring state intervention.
    
    Args:
        statements: List of statements to filter
        config: Filter configuration
        
    Returns:
        Filtered statements (only entrepreneur-actionable problems)
    """
    # ===========================================
    # GOVERNMENT/POLICY KEYWORDS - STRICT REJECT
    # ===========================================
    government_keywords = [
        # Government entities
        r'\b(government|ministry|ministries|parliament|congress|senate)\b',
        r'\b(federal|national|state|provincial|municipal)\s+(government|authority|agency)\b',
        r'\b(public sector|civil service|bureaucracy)\b',
        
        # Policy and regulation
        r'\b(policy|policies|regulation|regulations|regulatory)\b',
        r'\b(legislation|legislative|law|laws|legal reform)\b',
        r'\b(reform|reforms|reforming)\b',
        r'\b(subsidy|subsidies|subsidize|subsidizing)\b',
        r'\b(tax|taxes|taxation|tariff|tariffs)\b',
        r'\b(mandate|mandates|mandating|mandated)\b',
        
        # Government actions
        r'\b(nationalize|privatize|deregulate)\b',
        r'\b(central bank|monetary policy|fiscal policy)\b',
        r'\b(government spending|public spending|budget allocation)\b',
        r'\b(public investment|state investment)\b',
        
        # Large infrastructure (government-scale)
        r'\b(national grid|power grid|electricity grid)\b',
        r'\b(highway|highways|motorway|national road)\b',
        r'\b(public infrastructure|major infrastructure)\b',
        r'\b(dam|dams|hydropower plant|power station)\b',
        r'\b(port|ports|airport|airports|railway|railways)\b',
        
        # International/Aid
        r'\b(international aid|foreign aid|development aid)\b',
        r'\b(world bank|imf|african development bank)\b',
        r'\b(united nations|un agencies|donor|donors)\b',
        r'\b(bilateral|multilateral)\s+(agreement|aid|funding)\b',
        
        # Systemic issues requiring state action
        r'\b(corruption|corrupt|bribery)\b',
        r'\b(political instability|political will|governance)\b',
        r'\b(land reform|land rights|land tenure)\b',
        r'\b(border|borders|customs)\s+(control|policy|enforcement)\b',
        
        # Healthcare/Education systems (government-run)
        r'\b(public health system|national health|universal healthcare)\b',
        r'\b(public education|national curriculum|education policy)\b',
        r'\b(public hospital|government hospital)\b'
    ]
    
    # ===========================================
    # ENTREPRENEUR-ACTIONABLE INDICATORS - KEEP
    # ===========================================
    entrepreneur_positive = [
        # Products and services
        r'\b(app|apps|platform|platforms|software|saas)\b',
        r'\b(marketplace|market place|e-commerce)\b',
        r'\b(product|products|service|services)\b',
        r'\b(startup|startups|business|businesses|company|companies)\b',
        
        # Technology solutions
        r'\b(digital|mobile|online|internet|web)\b',
        r'\b(fintech|agtech|healthtech|edtech|insurtech)\b',
        r'\b(ai|artificial intelligence|machine learning)\b',
        r'\b(iot|sensors|automation)\b',
        
        # Business models
        r'\b(subscription|pay-per-use|freemium)\b',
        r'\b(b2b|b2c|marketplace|aggregator)\b',
        r'\b(franchise|licensing|distribution)\b',
        
        # Entrepreneurial actions
        r'\b(connect|connecting|connects)\b',
        r'\b(provide|providing|provides|offer|offering)\b',
        r'\b(enable|enabling|enables|empower|empowering)\b',
        r'\b(train|training|educate|educating|teach|teaching)\b',
        r'\b(finance|financing|lend|lending|credit)\b',
        
        # Target customers
        r'\b(farmers|merchants|traders|vendors|retailers)\b',
        r'\b(smes|msmes|small business|entrepreneurs)\b',
        r'\b(consumers|customers|users|households)\b'
    ]
    
    filtered = []
    for statement in statements:
        text = statement.get("statement", "").lower()
        
        # Count government/policy matches (REJECT indicators)
        govt_matches = sum(1 for pattern in government_keywords if re.search(pattern, text))
        
        # Count entrepreneur-actionable matches (KEEP indicators)
        entrepreneur_matches = sum(1 for pattern in entrepreneur_positive if re.search(pattern, text))
        
        # STRICT REJECTION LOGIC:
        # 1. If ANY strong government keyword found AND no entrepreneur indicators → REJECT
        # 2. If government matches > entrepreneur matches → REJECT
        # 3. Otherwise → KEEP
        
        if govt_matches > 0 and entrepreneur_matches == 0:
            logger.info(f"🚫 ENTREPRENEUR FILTER REJECTED (govt={govt_matches}, entrepreneur=0): {text[:80]}...")
            continue
        
        if govt_matches > entrepreneur_matches:
            logger.info(f"🚫 ENTREPRENEUR FILTER REJECTED (govt={govt_matches} > entrepreneur={entrepreneur_matches}): {text[:80]}...")
            continue
        
        # Additional check: specific phrases that are ALWAYS government problems
        absolute_reject_phrases = [
            r'government\s+(must|should|needs? to)',
            r'policy\s+(change|reform|intervention)',
            r'regulatory\s+(change|reform|framework)',
            r'requires?\s+(government|policy|regulation)',
            r'(national|federal|state)\s+level\s+(intervention|action)',
            r'public\s+sector\s+(reform|investment)',
            r'international\s+(cooperation|coordination|aid)',
            r'(world bank|imf|donor)\s+(funding|support|intervention)'
        ]
        
        absolute_reject = any(re.search(pattern, text) for pattern in absolute_reject_phrases)
        if absolute_reject:
            logger.info(f"🚫 ENTREPRENEUR FILTER REJECTED (absolute phrase match): {text[:80]}...")
            continue
        
        logger.debug(f"✅ ENTREPRENEUR FILTER PASSED (govt={govt_matches}, entrepreneur={entrepreneur_matches}): {text[:60]}...")
        filtered.append(statement)
    
    return filtered


def apply_specificity_filter(statements: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter statements based on specificity requirements.
    
    Args:
        statements: List of statements to filter
        config: Filter configuration
        
    Returns:
        Filtered statements
    """
    # Specificity indicators (broadened to be more inclusive)
    specificity_indicators = [
        # Numbers and statistics
        r'\b\d+%\b', r'\b\d+\s*percent\b', r'\b\d+\s*million\b', r'\b\d+\s*thousand\b',
        r'\b\d+\s*billion\b', r'\bestimated?\s+\d+\b', r'\bover\s+\d+\b', r'\bunder\s+\d+\b',
        r'\b(few|many|most|majority|minority)\b', r'\b(significant|substantial|considerable)\b',
        
        # Geographic specificity (broader)
        r'\b(africa|african|nigeria|kenya|ghana|south africa|ethiopia|uganda|tanzania|rwanda|senegal|morocco|egypt)\b',
        r'\b(lagos|nairobi|accra|cape town|addis ababa|kampala|dar es salaam|kigali|dakar|casablanca|cairo)\b',
        r'\b(northern|southern|eastern|western|central)\s+(nigeria|kenya|ghana|africa|region)\b',
        r'\b(developing|emerging)\s+(countries?|nations?|markets?)\b',
        r'\b(sub-saharan|north africa|west africa|east africa)\b',
        
        # Demographic specificity (broader)
        r'\b(smallholder|small-scale)\s+(farmers?|producers?)\b',
        r'\b(rural|urban)\s+(communities?|populations?|residents?|areas?)\b',
        r'\b(women|youth|students?|entrepreneurs?|businesses?|smes?|msmes?)\b',
        r'\b(low-income|middle-income|vulnerable)\s+(groups?|populations?|households?)\b',
        
        # Industry/sector specificity (broader)
        r'\b(agricultural?|healthcare|educational?|financial?|energy|transport|technology|manufacturing)\s+(sector|industry|market|services?)\b',
        r'\b(fintech|agtech|healthtech|edtech)\b',
        r'\b(microfinance|mobile money|digital payments?)\b',
        
        # Problem context indicators
        r'\b(access to|lack of|shortage of|limited)\s+(credit|financing|capital|resources?|infrastructure)\b',
        r'\b(market access|supply chain|value chain)\b',
        r'\b(digital divide|connectivity|internet access)\b'
    ]
    
    filtered = []
    for statement in statements:
        text = statement.get("statement", "").lower()
        
        # Count specificity matches
        specificity_score = sum(
            1 for pattern in specificity_indicators 
            if re.search(pattern, text)
        )
        
        # Require minimum specificity
        min_specificity = config.get("min_specificity_score", 2)
        if specificity_score >= min_specificity:
            statement["specificity_score"] = specificity_score
            filtered.append(statement)
        else:
            logger.debug(f"Specificity filter rejected (score {specificity_score}): {text[:50]}...")
    
    return filtered


def apply_deduplication_filter(statements: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Remove duplicate or very similar statements.
    
    Args:
        statements: List of statements to filter
        config: Filter configuration
        
    Returns:
        Deduplicated statements
    """
    similarity_threshold = config.get("similarity_threshold", 0.7)
    
    filtered = []
    seen_statements = []
    
    for statement in statements:
        text = statement.get("statement", "").lower().strip()
        
        # Check similarity with existing statements
        is_duplicate = False
        
        for seen_text in seen_statements:
            similarity = calculate_text_similarity(text, seen_text)
            if similarity >= similarity_threshold:
                is_duplicate = True
                logger.debug(f"Deduplication filter rejected (similarity {similarity:.2f}): {text[:50]}...")
                break
        
        if not is_duplicate:
            filtered.append(statement)
            seen_statements.append(text)
    
    return filtered


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts using simple word overlap.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score (0-1)
    """
    try:
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
        
    except Exception:
        return 0.0


def calculate_comprehensive_quality_score(statement: Dict[str, Any]) -> float:
    """
    Calculate comprehensive quality score for a statement.
    
    Args:
        statement: Statement data
        
    Returns:
        Quality score (higher = better)
    """
    score = 0.0
    
    text = statement.get("statement", "").lower()
    
    # Base specificity score
    specificity_score = statement.get("specificity_score", 0)
    score += specificity_score * 2.0
    
    # Length optimization (favor concise statements)
    length = len(text)
    if 80 <= length <= 150:
        score += 5.0  # Ideal length
    elif 50 <= length <= 200:
        score += 3.0
    elif length <= 250:
        score += 1.0
    
    # Problem clarity indicators with WORD BOUNDARIES
    clarity_keywords = [
        "prevents", "unable", "lack", "shortage", "cannot", "insufficient",
        "hinders", "blocks", "limits", "restricts", "barrier", "obstacle"
    ]
    
    clarity_count = sum(1 for keyword in clarity_keywords 
                       if re.search(r'\b' + re.escape(keyword) + r'\b', text))
    score += min(clarity_count * 1.5, 4.0)
    
    # ENTREPRENEUR-ACTIONABLE BONUS: Problems that entrepreneurs can solve
    actionable_patterns = [
        r'\b(app|platform|marketplace|service|product)\b',
        r'\b(digital|mobile|online|software)\b',
        r'\b(training|education|skills)\b',
        r'\b(financing|credit|lending|payment)\b',
        r'\b(supply chain|distribution|logistics)\b',
        r'\b(market access|connecting|linking)\b'
    ]
    
    actionable_count = sum(1 for pattern in actionable_patterns if re.search(pattern, text))
    score += min(actionable_count * 1.0, 3.0)  # Up to 3 points for actionability
    
    # Quantitative evidence
    quantitative_patterns = [
        r'\b\d+%', r'\b\d+\s*percent', r'\b\d+\s*million', r'\bestimated\s+\d+',
        r'\bover\s+\d+', r'\bunder\s+\d+', r'\bbetween\s+\d+', r'\bapproximately\s+\d+'
    ]
    
    quant_matches = sum(1 for pattern in quantitative_patterns if re.search(pattern, text))
    score += min(quant_matches * 2.0, 4.0)
    
    # African context specificity
    african_indicators = [
        "africa", "nigeria", "kenya", "ghana", "south africa", "ethiopia",
        "smallholder", "rural", "subsistence", "informal sector"
    ]
    
    african_count = sum(1 for indicator in african_indicators if indicator in text)
    score += min(african_count * 1.0, 3.0)
    
    # Severity and market size bonuses
    severity = statement.get("severity", "")
    if severity == "High":
        score += 3.0
    elif severity == "Medium":
        score += 2.0
    elif severity == "Low":
        score += 1.0
    
    market_size = statement.get("market_size", "")
    if market_size == "National":
        score += 2.5
    elif market_size == "Multi-country":
        score += 3.0
    elif market_size == "Regional":
        score += 2.0
    elif market_size == "Local":
        score += 1.0
    
    return score
