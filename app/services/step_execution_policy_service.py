from __future__ import annotations

from app.models.enums import TableState
from app.models.policy import StepPolicyDecision


class StepExecutionPolicyService:
    _ORDER = {
        TableState.NEW: 1,
        TableState.PLANNED: 2,
        TableState.PREPARED: 3,
        TableState.CDC_CAPTURE_ATTACHED: 4,
        TableState.INITIAL_LOAD_PENDING: 5,
        TableState.INITIAL_LOAD_RUNNING: 6,
        TableState.INITIAL_LOAD_DONE: 7,
        TableState.INSTANTIATED: 8,
        TableState.CDC_APPLY_ATTACHED: 9,
        TableState.ACTIVE: 10,
        TableState.ERROR: 99,
        TableState.REMOVAL_PLANNED: 100,
        TableState.REMOVED: 101,
    }

    def evaluate(
        self,
        table_id: str,
        current_state: TableState,
        expected_state: TableState,
        success_state: TableState,
    ) -> StepPolicyDecision:
        if current_state == expected_state:
            return StepPolicyDecision(
                decision="EXECUTE",
                reason="State matches expected step state.",
                current_state=current_state.value,
                expected_state=expected_state.value,
                success_state=success_state.value,
                table_id=table_id,
            )

        if current_state in {TableState.ERROR, TableState.REMOVAL_PLANNED, TableState.REMOVED}:
            return StepPolicyDecision(
                decision="INVALID_STATE",
                reason="Table is in terminal or recovery-required state.",
                current_state=current_state.value,
                expected_state=expected_state.value,
                success_state=success_state.value,
                table_id=table_id,
            )

        current_order = self._ORDER[current_state]
        expected_order = self._ORDER[expected_state]

        if current_order > expected_order:
            return StepPolicyDecision(
                decision="SKIP",
                reason="Step is already completed or table has progressed further.",
                current_state=current_state.value,
                expected_state=expected_state.value,
                success_state=success_state.value,
                table_id=table_id,
            )

        return StepPolicyDecision(
            decision="INVALID_STATE",
            reason="Table has not reached the required lifecycle state yet.",
            current_state=current_state.value,
            expected_state=expected_state.value,
            success_state=success_state.value,
            table_id=table_id,
        )