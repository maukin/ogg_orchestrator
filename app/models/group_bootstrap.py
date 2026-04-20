from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


GroupBootstrapType = Literal["extract", "replicat"]


@dataclass(frozen=True)
class GroupBootstrapRequest:
    group_name: str
    group_type: GroupBootstrapType
    environment_name: str
    source_system: str | None
    target_system: str | None
    credential_alias: str
    credential_domain: str | None
    trail_name: str | None
    mode: str
    base_config_lines: list[str]
    notes: str | None = None


@dataclass(frozen=True)
class GroupBootstrapResult:
    success: bool
    group_name: str
    group_type: GroupBootstrapType
    started_at: str | None
    finished_at: str | None
    request_artifact: str | None
    response_artifact: str | None
    raw_output: str | None
    error_code: str | None
    error_message: str | None