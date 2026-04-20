from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TableExecutionStatus:
    table_id: str
    state: str
    desired_enabled: bool
    category: str
    message: str
    next_expected_step: Optional[str] = None


@dataclass
class DeploymentStatusReport:
    deployment_id: str
    environment_name: str
    table_statuses: list[TableExecutionStatus] = field(default_factory=list)