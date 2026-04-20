from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OGGProcessStatusRequest:
    process_type: str  # EXTRACT | REPLICAT
    process_name: str
    endpoint: str
    artifact_prefix: str


@dataclass(frozen=True)
class OGGProcessStatusResult:
    process_type: str
    process_name: str
    success: bool
    http_status: Optional[int]
    request_artifact: Optional[str]
    response_artifact: Optional[str]
    raw_output: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]