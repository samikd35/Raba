"""
Venture Builder custom exceptions.
"""


class VBBaseException(Exception):
    """Base exception for Venture Builder operations"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class VBValidationError(VBBaseException):
    """Validation error for VB operations"""
    pass


class VBInsufficientCreditsError(VBBaseException):
    """User doesn't have enough credits"""
    pass


class VBAccessDeniedError(VBBaseException):
    """User doesn't have permission"""
    pass


class VBNotFoundError(VBBaseException):
    """VB resource not found"""
    pass


class VBBookingConflictError(VBBaseException):
    """Booking time conflict"""
    pass


class VBProfileIncompleteError(VBBaseException):
    """VB profile is incomplete"""
    pass


class VBStatusError(VBBaseException):
    """VB status doesn't allow this operation"""
    pass


class VBDisputeAlreadyExistsError(VBBaseException):
    """Dispute already exists for this session"""
    pass


class VBDisputeNotEligibleError(VBBaseException):
    """Session is not eligible for dispute (e.g., not completed)"""
    pass


class VBAlreadyExistsError(VBBaseException):
    """Resource already exists (e.g., duplicate email submission)"""
    pass
