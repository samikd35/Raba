"""
Project Chat Feature

Enables users to chat with their VMP projects using:
- Project RAG: Retrieval over chunked/embedded project artifacts
- Web Search: Bounded external research when internal data is insufficient
- Thread Memory: Continuity without replaying full message history
- Structured Citations: Internal (project) and external (web) references
"""

from .models import (
    ChatState,
    ThreadMemory,
    ProjectEvidence,
    WebEvidence,
    InternalCitation,
    ExternalCitation,
    Citation,
)
from .api.endpoints import router as chat_router

__all__ = [
    "ChatState",
    "ThreadMemory",
    "ProjectEvidence",
    "WebEvidence",
    "InternalCitation",
    "ExternalCitation",
    "Citation",
    "chat_router",
]
