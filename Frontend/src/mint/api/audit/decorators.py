#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audit Decorators.

This module provides decorators for automatic audit logging of administrative actions.
"""

import logging
from typing import Optional, Callable, Any
from fastapi import Request

from .models import AuditLogAction, AuditLogTargetType
from .service import AuditService

# Configure logging
logger = logging.getLogger(__name__)


def audit_action(
    action: AuditLogAction,
    target_type: AuditLogTargetType,
    get_target_id: Optional[callable] = None,
    get_details: Optional[callable] = None
):
    """
    Decorator to automatically log admin actions.
    
    Args:
        action: Type of action being performed
        target_type: Type of target being affected
        get_target_id: Function to extract target ID from function args
        get_details: Function to extract additional details from function args
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            audit_service = AuditService()
            
            # Extract admin user ID from request context
            admin_user_id = None
            ip_address = None
            user_agent = None
            
            # Look for request object in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                # Extract user ID from JWT token or session
                admin_user_id = getattr(request.state, 'user_id', None)
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get('user-agent')
            
            # Extract target ID and details if functions provided
            target_id = None
            details = {}
            
            if get_target_id:
                try:
                    target_id = get_target_id(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Failed to extract target ID: {str(e)}")
            
            if get_details:
                try:
                    details = get_details(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Failed to extract details: {str(e)}")
            
            # Execute the function
            success = True
            error_message = None
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful action
                if admin_user_id:
                    await audit_service.log_action(
                        admin_user_id=admin_user_id,
                        action=action,
                        target_type=target_type,
                        target_id=target_id,
                        details=details,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=True
                    )
                
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                
                # Log failed action
                if admin_user_id:
                    await audit_service.log_action(
                        admin_user_id=admin_user_id,
                        action=action,
                        target_type=target_type,
                        target_id=target_id,
                        details=details,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=False,
                        error_message=error_message
                    )
                
                raise
        
        return wrapper
    return decorator


def audit_user_action(action: AuditLogAction):
    """
    Decorator specifically for user-related actions.
    
    Args:
        action: Type of user action being performed
    """
    def get_user_id(*args, **kwargs):
        # Extract user ID from function arguments
        for arg in args:
            if isinstance(arg, str) and len(arg) > 10:  # Likely a user ID
                return arg
        return None
    
    def get_user_details(*args, **kwargs):
        # Extract user-related details
        details = {}
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                details.update(arg)
        return details
    
    return audit_action(
        action=action,
        target_type=AuditLogTargetType.USER,
        get_target_id=get_user_id,
        get_details=get_user_details
    )


def audit_system_action(action: AuditLogAction):
    """
    Decorator specifically for system-related actions.
    
    Args:
        action: Type of system action being performed
    """
    def get_system_details(*args, **kwargs):
        # Extract system-related details
        details = {}
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                details.update(arg)
        return details
    
    return audit_action(
        action=action,
        target_type=AuditLogTargetType.SYSTEM,
        get_details=get_system_details
    )


def audit_config_action(action: AuditLogAction):
    """
    Decorator specifically for configuration-related actions.
    
    Args:
        action: Type of config action being performed
    """
    def get_config_details(*args, **kwargs):
        # Extract configuration-related details
        details = {}
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                details.update(arg)
        return details
    
    return audit_action(
        action=action,
        target_type=AuditLogTargetType.CONFIG,
        get_details=get_config_details
    )


def audit_session_action(action: AuditLogAction):
    """
    Decorator specifically for session-related actions.
    
    Args:
        action: Type of session action being performed
    """
    def get_session_id(*args, **kwargs):
        # Extract session ID from function arguments
        for arg in args:
            if isinstance(arg, str) and len(arg) > 10:  # Likely a session ID
                return arg
        return None
    
    def get_session_details(*args, **kwargs):
        # Extract session-related details
        details = {}
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                details.update(arg)
        return details
    
    return audit_action(
        action=action,
        target_type=AuditLogTargetType.SESSION,
        get_target_id=get_session_id,
        get_details=get_session_details
    )


def audit_data_action(action: AuditLogAction):
    """
    Decorator specifically for data-related actions.
    
    Args:
        action: Type of data action being performed
    """
    def get_data_details(*args, **kwargs):
        # Extract data-related details
        details = {}
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                details.update(arg)
        return details
    
    return audit_action(
        action=action,
        target_type=AuditLogTargetType.DATA,
        get_details=get_data_details
    )


def audit_feature_flag_action(action: AuditLogAction):
    """
    Decorator specifically for feature flag-related actions.
    
    Args:
        action: Type of feature flag action being performed
    """
    def get_feature_flag_id(*args, **kwargs):
        # Extract feature flag ID from function arguments
        for arg in args:
            if isinstance(arg, str) and len(arg) > 5:  # Likely a feature flag ID
                return arg
        return None
    
    def get_feature_flag_details(*args, **kwargs):
        # Extract feature flag-related details
        details = {}
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                details.update(arg)
        return details
    
    return audit_action(
        action=action,
        target_type=AuditLogTargetType.FEATURE_FLAG,
        get_target_id=get_feature_flag_id,
        get_details=get_feature_flag_details
    )


def audit_cache_action(action: AuditLogAction):
    """
    Decorator specifically for cache-related actions.
    
    Args:
        action: Type of cache action being performed
    """
    def get_cache_details(*args, **kwargs):
        # Extract cache-related details
        details = {}
        for i, arg in enumerate(args):
            if isinstance(arg, dict):
                details.update(arg)
        return details
    
    return audit_action(
        action=action,
        target_type=AuditLogTargetType.CACHE,
        get_details=get_cache_details
    )

