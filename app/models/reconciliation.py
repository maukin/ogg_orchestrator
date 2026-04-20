from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TableReconciliationRow:
    table_id: str
    desired_enabled: bool
    registry_state: Optional[str]
    validation_status: Optional[str]
    has_error: bool
    is_blocked: bool
    block_reason: Optional[str]
    next_recommended_step: Optional[str]
    notes: list[str]


@dataclass
class DeploymentReconciliationReport:
    deployment_id: str
    environment_name: str
    rows: list[TableReconciliationRow] = field(default_factory=list)