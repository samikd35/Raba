"""
Utility functions for Venture Builder API.

Shared helpers used across multiple router modules.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from .exceptions import (
    VBAccessDeniedError,
    VBBaseException,
    VBBookingConflictError,
    VBDisputeAlreadyExistsError,
    VBDisputeNotEligibleError,
    VBInsufficientCreditsError,
    VBNotFoundError,
    VBProfileIncompleteError,
    VBStatusError,
    VBValidationError,
)


def handle_vb_exception(e: VBBaseException):
    """Convert VB exceptions to HTTP exceptions (legacy - use vb_exception_handler instead)"""
    status_map = {
        VBValidationError: status.HTTP_400_BAD_REQUEST,
        VBNotFoundError: status.HTTP_404_NOT_FOUND,
        VBAccessDeniedError: status.HTTP_403_FORBIDDEN,
        VBInsufficientCreditsError: status.HTTP_402_PAYMENT_REQUIRED,
        VBBookingConflictError: status.HTTP_409_CONFLICT,
        VBProfileIncompleteError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        VBStatusError: status.HTTP_400_BAD_REQUEST,
        VBDisputeAlreadyExistsError: status.HTTP_409_CONFLICT,
        VBDisputeNotEligibleError: status.HTTP_400_BAD_REQUEST,
    }

    status_code = status_map.get(type(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise HTTPException(status_code=status_code, detail=str(e))


async def vb_exception_handler(request: Request, exc: VBBaseException) -> JSONResponse:
    """
    Custom exception handler for VB exceptions.
    Returns standardized error response format.
    """
    status_map = {
        VBValidationError: status.HTTP_400_BAD_REQUEST,
        VBNotFoundError: status.HTTP_404_NOT_FOUND,
        VBAccessDeniedError: status.HTTP_403_FORBIDDEN,
        VBInsufficientCreditsError: status.HTTP_402_PAYMENT_REQUIRED,
        VBBookingConflictError: status.HTTP_409_CONFLICT,
        VBProfileIncompleteError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        VBStatusError: status.HTTP_400_BAD_REQUEST,
        VBDisputeAlreadyExistsError: status.HTTP_409_CONFLICT,
        VBDisputeNotEligibleError: status.HTTP_400_BAD_REQUEST,
    }

    status_code = status_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": str(exc)
        }
    )
