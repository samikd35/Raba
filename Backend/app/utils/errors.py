from __future__ import annotations

from typing import Optional

from app.utils.helpers import utc_now_iso


def build_error_details(
    *,
    node: str,
    phase: str,
    exception: Exception | str,
    run_id: Optional[str] = None,
) -> dict[str, str]:
    message = exception if isinstance(exception, str) else str(exception)
    return {
        "node": node,
        "phase": phase,
        "exception": message,
        "error_type": type(exception).__name__ if not isinstance(exception, str) else "Error",
        "timestamp": utc_now_iso(),
        "run_id": run_id or "",
    }
