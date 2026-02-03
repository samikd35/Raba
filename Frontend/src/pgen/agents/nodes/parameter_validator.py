"""
Parameter Validator Node

Node 0 in the Problem Generator agent graph.
Validates and normalizes user input parameters, expands regions to country lists.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config

from ..graph_state import ProblemGraphState

logger = logging.getLogger(__name__)

# African countries mapping for geography expansion
AFRICAN_COUNTRIES = {
    "north_africa": ["Algeria", "Egypt", "Libya", "Morocco", "Sudan", "Tunisia"],
    "west_africa": ["Benin", "Burkina Faso", "Cape Verde", "Côte d'Ivoire", "Gambia", "Ghana", 
                   "Guinea", "Guinea-Bissau", "Liberia", "Mali", "Mauritania", "Niger", 
                   "Nigeria", "Senegal", "Sierra Leone", "Togo"],
    "central_africa": ["Cameroon", "Central African Republic", "Chad", "Democratic Republic of Congo", 
                      "Equatorial Guinea", "Gabon", "Republic of Congo", "São Tomé and Príncipe"],
    "east_africa": ["Burundi", "Comoros", "Djibouti", "Eritrea", "Ethiopia", "Kenya", "Madagascar", 
                   "Malawi", "Mauritius", "Mozambique", "Rwanda", "Seychelles", "Somalia", 
                   "South Sudan", "Tanzania", "Uganda", "Zambia", "Zimbabwe"],
    "southern_africa": ["Angola", "Botswana", "Eswatini", "Lesotho", "Namibia", "South Africa"]
}

# Valid parameter enums
VALID_INDUSTRIES = [
    "Agriculture", "Healthcare", "Education", "FinTech", "Energy", "Transportation", 
    "Manufacturing", "Retail", "Media", "Tourism", "ICT", "Mining", "Other"
]

VALID_BACKGROUNDS = [
    "Student", "Software Developer", "Data Professional", "Engineer", "Business", 
    "Finance", "Marketing", "Healthcare Professional", "Agriculture", "Education", 
    "Design", "Legal", "Research", "Other"
]

VALID_PRODUCT_TYPES = [
    "Digital",  # Digital and/or tech enabled products such as apps, platforms
    "Physical",  # Physical products such as foods & beverages, hygiene products, organic fertilizer, etc.
    "Manufacturing",  # Manufacturing products that require engineering skills
    "Creative Products / Services",  # Fashion Designs, Entertainment, Sports, Writing - anything that requires creative thinking
    "Hybrid",  # Combination of digital and physical
    "Other"  # Other product types
]

VALID_TARGET_CUSTOMERS = [
    "Mass Consumers", "Urban Consumers", "Rural Consumers", "Micro Businesses", 
    "SMEs", "Large Enterprises", "Government", "NGOs", "Diaspora", "Other"
]

VALID_DEMOGRAPHICS = [
    "Women & Girls", "Youth", "Children", "Elderly", "People with Disabilities", 
    "Rural Populations", "Urban Poor", "Refugees", "Smallholder Farmers", 
    "Informal Workers", "Students", "Healthcare Workers", "Other"
]


@traceable(name="parameter_validator_node")
def parameter_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 0: Parameter Validator
    
    Validates and normalizes user input parameters, expands regions to country lists.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated workflow state with validated parameters
    """
    logger.info("Starting parameter validation")
    start_time = datetime.now()
    
    try:
        # Update status
        state["status"] = "processing"
        state["current_node"] = "parameter_validator"
        
        # Get agent configuration
        agent_config = get_agent_config(state, "problem_generator")
        validation_config = agent_config.get("parameter_validation", {})
        
        # Extract parameters from state
        params = state.get("params", {})
        if not params:
            raise ValueError("No parameters provided for validation")
        
        logger.info(f"Validating parameters: {list(params.keys())}")
        
        # Initialize validated parameters
        validated_params = {}
        validation_errors = []
        
        # =============================================
        # VALIDATE REQUIRED PARAMETERS
        # =============================================
        
        # Industry validation with case-insensitive matching
        industry = params.get("industry", [])
        if not industry or industry == ["All"]:
            validated_params["industry"] = VALID_INDUSTRIES  # All industries
        else:
            validated_industry = []
            for ind in industry:
                # Try exact match first
                if ind in VALID_INDUSTRIES:
                    validated_industry.append(ind)
                else:
                    # Try case-insensitive match
                    matched = False
                    for valid_ind in VALID_INDUSTRIES:
                        if ind.lower() == valid_ind.lower():
                            validated_industry.append(valid_ind)
                            matched = True
                            break
                    if not matched:
                        # Allow custom values (treat as "Other" category)
                        validated_industry.append(ind)
                        logger.info(f"Using custom industry value: {ind}")
            
            validated_params["industry"] = validated_industry
        
        # Geography validation - now handles single country selection only
        geography = params.get("geography", [])
        if isinstance(geography, str):
            # Handle single string input
            geography = [geography]
        
        if not geography or not geography[0]:
            validation_errors.append("Geography is required - please select a specific country")
        else:
            selected_geo = geography[0]  # Take only the first (and should be only) selection
            
            # Check if it's a valid African country
            all_african_countries = [country for countries in AFRICAN_COUNTRIES.values() for country in countries]
            if selected_geo in all_african_countries:
                # Store as single country in a list for backward compatibility
                validated_params["geography"] = [selected_geo]
            else:
                validation_errors.append(f"Invalid geography: {selected_geo}. Please select a valid African country.")
                logger.warning(f"Invalid geography provided: {selected_geo}")
        
        # Background validation with flexible matching
        background = params.get("background", [])
        if not background or background == ["All"]:
            validated_params["background"] = VALID_BACKGROUNDS
        else:
            validated_background = []
            for bg in background:
                # Try exact match first
                if bg in VALID_BACKGROUNDS:
                    validated_background.append(bg)
                else:
                    # Try case-insensitive match
                    matched = False
                    for valid_bg in VALID_BACKGROUNDS:
                        if bg.lower() == valid_bg.lower():
                            validated_background.append(valid_bg)
                            matched = True
                            break
                    
                    # Try partial matching for common variations
                    if not matched:
                        if "sme" in bg.lower() or "small" in bg.lower() or "medium" in bg.lower():
                            validated_background.append("Business")
                            matched = True
                        elif "startup" in bg.lower() or "entrepreneur" in bg.lower():
                            validated_background.append("Business")
                            matched = True
                    
                    if not matched:
                        # Allow custom values
                        validated_background.append(bg)
                        logger.info(f"Using custom background value: {bg}")
            
            validated_params["background"] = validated_background
        
        # Product type validation with flexible matching
        product_type = params.get("product_type", [])
        if not product_type or product_type == ["All"]:
            validated_params["product_type"] = VALID_PRODUCT_TYPES
        else:
            validated_product_type = []
            for pt in product_type:
                # Try exact match first
                if pt in VALID_PRODUCT_TYPES:
                    validated_product_type.append(pt)
                else:
                    # Try case-insensitive match
                    matched = False
                    for valid_pt in VALID_PRODUCT_TYPES:
                        if pt.lower() == valid_pt.lower():
                            validated_product_type.append(valid_pt)
                            matched = True
                            break
                    
                    # Try partial matching for common variations
                    if not matched:
                        if "digital" in pt.lower() or "app" in pt.lower() or "software" in pt.lower() or "platform" in pt.lower():
                            validated_product_type.append("Digital")
                            matched = True
                        elif "physical" in pt.lower() or "goods" in pt.lower() or "food" in pt.lower() or "beverage" in pt.lower() or "hygiene" in pt.lower() or "fertilizer" in pt.lower():
                            validated_product_type.append("Physical")
                            matched = True
                        elif "manufacturing" in pt.lower() or "engineering" in pt.lower() or "industrial" in pt.lower():
                            validated_product_type.append("Manufacturing")
                            matched = True
                        elif "service" in pt.lower() or "access" in pt.lower():
                            validated_product_type.append("Digital")
                            matched = True
                    
                    if not matched:
                        # Allow custom values
                        validated_product_type.append(pt)
                        logger.info(f"Using custom product_type value: {pt}")
            
            validated_params["product_type"] = validated_product_type
        
        # Target customer validation with flexible matching (NOW REQUIRED)
        target_customer = params.get("target_customer", [])
        if not target_customer or target_customer == ["All"]:
            validation_errors.append("Target customer is required - please select at least one customer segment")
        else:
            validated_target_customer = []
            for tc in target_customer:
                # Try exact match first
                if tc in VALID_TARGET_CUSTOMERS:
                    validated_target_customer.append(tc)
                else:
                    # Try case-insensitive match
                    matched = False
                    for valid_tc in VALID_TARGET_CUSTOMERS:
                        if tc.lower() == valid_tc.lower():
                            validated_target_customer.append(valid_tc)
                            matched = True
                            break
                    
                    # Try partial matching for common variations
                    if not matched:
                        if "consumer" in tc.lower() or "b2c" in tc.lower():
                            validated_target_customer.append("Mass Consumers")
                            matched = True
                        elif "sme" in tc.lower() or "small" in tc.lower() or "medium" in tc.lower():
                            validated_target_customer.append("SMEs")
                            matched = True
                        elif "enterprise" in tc.lower() or "large" in tc.lower() or "corporate" in tc.lower():
                            validated_target_customer.append("Large Enterprises")
                            matched = True
                        elif "government" in tc.lower() or "public" in tc.lower():
                            validated_target_customer.append("Government")
                            matched = True
                    
                    if not matched:
                        # Allow custom values
                        validated_target_customer.append(tc)
                        logger.info(f"Using custom target_customer value: {tc}")
            
            validated_params["target_customer"] = validated_target_customer
        
        # Impact Focus validation (NOW REQUIRED - replaces demographics)
        impact_focus = params.get("impact_focus", [])
        if not impact_focus:
            validation_errors.append("Impact Focus is required - please select at least one impact focus")
        else:
            validated_impact_focus = []
            valid_impact_focus_options = [
                'Fully Commercial', 'Social Venture', 'Non-Profit / Foundations', 'Other'
            ]
            
            for focus in impact_focus:
                # Try exact match first
                if focus in valid_impact_focus_options:
                    validated_impact_focus.append(focus)
                else:
                    # Try case-insensitive match
                    matched = False
                    for valid_focus in valid_impact_focus_options:
                        if focus.lower() == valid_focus.lower():
                            validated_impact_focus.append(valid_focus)
                            matched = True
                            break
                    
                    # Try partial matching for common variations
                    if not matched:
                        if "commercial" in focus.lower() or "profit" in focus.lower():
                            validated_impact_focus.append("Fully Commercial")
                            matched = True
                        elif "social" in focus.lower() or "venture" in focus.lower():
                            validated_impact_focus.append("Social Venture")
                            matched = True
                        elif "non-profit" in focus.lower() or "foundation" in focus.lower() or "ngo" in focus.lower():
                            validated_impact_focus.append("Non-Profit / Foundations")
                            matched = True
                        elif "other" in focus.lower():
                            validated_impact_focus.append("Other")
                            matched = True
                    
                    if not matched:
                        # Allow custom values but log them
                        validated_impact_focus.append(focus)
                        logger.info(f"Using custom impact_focus value: {focus}")
            
            validated_params["impact_focus"] = validated_impact_focus
        
        # =============================================
        # CHECK FOR VALIDATION ERRORS
        # =============================================
        
        if validation_errors:
            error_msg = f"Parameter validation failed: {'; '.join(validation_errors)}"
            logger.error(error_msg)
            state["error"] = error_msg
            state["status"] = "failed"
            return state
        
        # =============================================
        # STORE VALIDATED PARAMETERS
        # =============================================
        
        state["params"] = validated_params
        
        # Add validation metadata
        validation_metadata = {
            "original_param_count": len(params),
            "validated_param_count": len(validated_params),
            "geography_expanded": len(validated_params["geography"]),
            "validation_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
        }
        
        state["processing_metrics"] = state.get("processing_metrics", {})
        state["processing_metrics"]["parameter_validator"] = validation_metadata
        
        logger.info(f"Parameter validation completed successfully")
        logger.info(f"Validated {len(validated_params)} parameter groups")
        logger.info(f"Geography expanded to {len(validated_params['geography'])} countries")
        
        return state
        
    except Exception as e:
        error_msg = f"Parameter validation failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state
