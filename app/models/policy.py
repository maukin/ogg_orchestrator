from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StepPolicyDecision:
    decision: str  # EXECUTE | SKIP | INVALID_STATE
    reason: str
    current_state: str
    expected_state: str
    success_state: str
    table_id: Optional[str] = None