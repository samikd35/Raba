#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ID Consistency Middleware.

This module provides middleware functions to ensure ID consistency
across all MINT services and operations.
"""

import logging
import uuid
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class IDConsistencyError(Exception):
    """Raised when ID consistency validation fails."""
    pass


def validate_uuid_format(id_value: Union[str, None], id_name: str = "ID") -> bool:
    """Validate that an ID is a proper UUID format.
    
    Args:
        id_value: The ID value to validate
        id_name: Name of the ID for logging purposes
        
    Returns:
        bool: True if valid UUID format, False otherwise
        
    Raises:
        IDConsistencyError: If ID is required but invalid
    """
    if id_value is None:
        return True  # Allow None values
    
    try:
        uuid.UUID(str(id_value))
        logger.debug(f"ID VALIDATION: {id_name} {id_value} is valid UUID")
        return True
    except (ValueError, TypeError):
        logger.error(f"ID VALIDATION: {id_name} {id_value} is NOT a valid UUID")
        return False


def ensure_report_id_consistency(report_id: str, operation: str = "operation") -> str:
    """Ensure report ID is consistent and valid.
    
    Args:
        report_id: The report ID to validate
        operation: Description of the operation for logging
        
    Returns:
        str: The validated report ID
        
    Raises:
        IDConsistencyError: If report ID is invalid
    """
    if not report_id:
        raise IDConsistencyError(f"Report ID is required for {operation}")
    
    if not validate_uuid_format(report_id, "Report ID"):
        raise IDConsistencyError(f"Invalid report ID format for {operation}: {report_id}")
    
    logger.info(f"ID CONSISTENCY: Report ID {report_id} validated for {operation}")
    return report_id


def ensure_user_id_consistency(user_id: Optional[str], operation: str = "operation") -> Optional[str]:
    """Ensure user ID is consistent and valid.
    
    Args:
        user_id: The user ID to validate (can be None)
        operation: Description of the operation for logging
        
    Returns:
        Optional[str]: The validated user ID
        
    Raises:
        IDConsistencyError: If user ID is provided but invalid
    """
    if user_id is None:
        logger.warning(f"ID CONSISTENCY: No user ID provided for {operation}")
        return None
    
    if not validate_uuid_format(user_id, "User ID"):
        raise IDConsistencyError(f"Invalid user ID format for {operation}: {user_id}")
    
    logger.info(f"ID CONSISTENCY: User ID {user_id} validated for {operation}")
    return user_id


def log_id_flow(stage: str, **ids) -> None:
    """Log ID flow through different stages of processing.
    
    Args:
        stage: The current processing stage
        **ids: Keyword arguments containing ID values to log
    """
    # Import the enhanced logging service
    try:
        from .id_logging_service import id_logger
        use_enhanced_logging = True
    except ImportError:
        use_enhanced_logging = False
    
    id_info = []
    for id_name, id_value in ids.items():
        id_type = type(id_value).__name__
        id_info.append(f"{id_name}={id_value} ({id_type})")
    
    log_message = f"ID FLOW [{stage}]: {', '.join(id_info)}"
    
    if use_enhanced_logging:
        id_logger.info(log_message)
    else:
        logger.info(log_message)


def validate_id_relationships(report_id: str, user_id: Optional[str] = None, 
                            session_id: Optional[str] = None) -> Dict[str, Any]:
    """Validate relationships between different IDs.
    
    Args:
        report_id: The report ID
        user_id: The user ID (optional)
        session_id: The session ID (optional)
        
    Returns:
        Dict[str, Any]: Validation results
        
    Raises:
        IDConsistencyError: If validation fails
    """
    results = {
        "report_id_valid": False,
        "user_id_valid": False,
        "session_id_valid": False,
        "all_valid": False
    }
    
    try:
        # Validate report ID (required)
        ensure_report_id_consistency(report_id, "relationship validation")
        results["report_id_valid"] = True
        
        # Validate user ID (optional)
        if user_id:
            ensure_user_id_consistency(user_id, "relationship validation")
            results["user_id_valid"] = True
        else:
            results["user_id_valid"] = True  # None is acceptable
        
        # Validate session ID (optional)
        if session_id:
            if not validate_uuid_format(session_id, "Session ID"):
                raise IDConsistencyError(f"Invalid session ID format: {session_id}")
            results["session_id_valid"] = True
        else:
            results["session_id_valid"] = True  # None is acceptable
        
        results["all_valid"] = all([
            results["report_id_valid"],
            results["user_id_valid"], 
            results["session_id_valid"]
        ])
        
        if results["all_valid"]:
            logger.info("ID RELATIONSHIPS: All ID relationships are valid")
        
        return results
        
    except IDConsistencyError as e:
        logger.error(f"ID RELATIONSHIPS: Validation failed - {e}")
        raise
    except Exception as e:
        logger.error(f"ID RELATIONSHIPS: Unexpected error - {e}")
        raise IDConsistencyError(f"ID relationship validation failed: {e}")


def log_report_id_mismatch(expected_id: str, actual_id: str, context: str) -> None:
    """Log when report IDs don't match expectations.
    
    Args:
        expected_id: The expected report ID
        actual_id: The actual report ID found
        context: Context where the mismatch occurred
    """
    try:
        from .id_logging_service import id_logger
        id_logger.error(f"REPORT_ID_MISMATCH [{context}]: expected={expected_id}, actual={actual_id}")
    except ImportError:
        logger.error(f"REPORT_ID_MISMATCH [{context}]: expected={expected_id}, actual={actual_id}")


def log_database_id_lookup(table: str, lookup_field: str, lookup_value: str, 
                          found_id: Optional[str] = None, success: bool = True) -> None:
    """Log database ID lookup operations.
    
    Args:
        table: Database table being queried
        lookup_field: Field used for lookup
        lookup_value: Value being looked up
        found_id: ID that was found (if any)
        success: Whether the lookup was successful
    """
    try:
        from .id_logging_service import id_logger
        status = "SUCCESS" if success else "FAILED"
        found_info = f", found_id={found_id}" if found_id else ""
        id_logger.info(f"DB_ID_LOOKUP [{status}]: {table}.{lookup_field}={lookup_value}{found_info}")
    except ImportError:
        status = "SUCCESS" if success else "FAILED"
        found_info = f", found_id={found_id}" if found_id else ""
        logger.info(f"DB_ID_LOOKUP [{status}]: {table}.{lookup_field}={lookup_value}{found_info}")


def track_id_transformation(operation: str, input_id: str, output_id: str, 
                           transformation_type: str) -> None:
    """Track ID transformations through the system.
    
    Args:
        operation: The operation performing the transformation
        input_id: The input ID
        output_id: The output ID
        transformation_type: Type of transformation (e.g., "session_to_report", "resolve_identifier")
    """
    try:
        from .id_logging_service import id_logger
        id_logger.info(f"ID_TRANSFORM [{operation}]: {transformation_type} - {input_id} -> {output_id}")
    except ImportError:
        logger.info(f"ID_TRANSFORM [{operation}]: {transformation_type} - {input_id} -> {output_id}")
