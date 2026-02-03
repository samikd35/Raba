"""
LangGraph Workflow for Project Chat

Contains the orchestration flow with 10 nodes:
1. LoadThreadContext
2. IntentRouter
3. QueryRewrite
4. ProjectRetrieve
5. EvidenceGrade
6. WebPlan
7. WebSearch + ExtractEvidence
8. AnswerCompose
9. MemoryUpdate
10. Persist
"""

from .chat_workflow import ProjectChatWorkflow, run_chat_workflow

__all__ = ["ProjectChatWorkflow", "run_chat_workflow"]
