from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InitialLoadExecutionResult:
    success: bool
    executed_count: int
    skipped_count: int
    load_batch_id: Optional[str] = None
    rows_loaded: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    instantiation_candidate_scn: Optional[int] = None
    raw_output: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    request_artifact: Optional[str] = None
    response_artifact: Optional[str] = None