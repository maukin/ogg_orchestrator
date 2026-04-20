from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class StepExecutionSummary:
    step_name: str
    success: Optional[bool]
    executed_count: Optional[int]
    skipped_count: Optional[int]
    http_status: Optional[int]
    request_artifact: Optional[str]
    response_artifact: Optional[str]
    raw_output: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]


@dataclass
class DeploymentExecutionSummary:
    deployment_id: str
    environment_name: str
    step_results: list[StepExecutionSummary] = field(default_factory=list)