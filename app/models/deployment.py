from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class DeploymentAction:
    action_type: str
    table_id: Optional[str]
    group_name: Optional[str]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentPlan:
    deployment_id: str
    environment_name: str
    git_branch: Optional[str]
    git_commit_sha: Optional[str]
    pipeline_id: Optional[str]
    actions: list[DeploymentAction] = field(default_factory=list)


@dataclass
class DeploymentRecord:
    deployment_id: str
    environment_name: str
    git_branch: Optional[str]
    git_commit_sha: Optional[str]
    pipeline_id: Optional[str]
    trigger_source: Optional[str]
    status: str
    plan_json: Optional[str]
    rollback_plan_json: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    initiated_by: Optional[str]