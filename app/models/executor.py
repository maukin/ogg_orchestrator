from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExecutorResult:
    success: bool
    executed_count: int
    skipped_count: int
    raw_output: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    http_status: Optional[int] = None
    request_artifact: Optional[str] = None
    response_artifact: Optional[str] = None