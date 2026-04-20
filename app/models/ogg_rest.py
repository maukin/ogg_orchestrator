from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OGGRestRequestSpec:
    operation_name: str
    method: str
    endpoint: str
    payload: dict[str, Any]
    artifact_name: str