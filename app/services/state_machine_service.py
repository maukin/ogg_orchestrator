from __future__ import annotations

from app.models.enums import TableState


class InvalidStateTransitionError(Exception):
    pass


class StateMachineService:
    _ALLOWED_TRANSITIONS: dict[TableState, set[TableState]] = {
        TableState.NEW: {
            TableState.PLANNED,
            TableState.ERROR,
            TableState.REMOVAL_PLANNED,
        },
        TableState.PLANNED: {
            TableState.PREPARED,
            TableState.ERROR,
            TableState.REMOVAL_PLANNED,
        },
        TableState.PREPARED: {
            TableState.CDC_CAPTURE_ATTACHED,
            TableState.INITIAL_LOAD_PENDING,
            TableState.ERROR,
        },
        TableState.CDC_CAPTURE_ATTACHED: {
            TableState.INITIAL_LOAD_PENDING,
            TableState.INSTANTIATED,
            TableState.ERROR,
        },
        TableState.INITIAL_LOAD_PENDING: {
            TableState.INITIAL_LOAD_RUNNING,
            TableState.ERROR,
        },
        TableState.INITIAL_LOAD_RUNNING: {
            TableState.INITIAL_LOAD_DONE,
            TableState.ERROR,
        },
        TableState.INITIAL_LOAD_DONE: {
            TableState.INSTANTIATED,
            TableState.ERROR,
        },
        TableState.INSTANTIATED: {
            TableState.CDC_APPLY_ATTACHED,
            TableState.ERROR,
        },
        TableState.CDC_APPLY_ATTACHED: {
            TableState.ACTIVE,
            TableState.ERROR,
        },
        TableState.ACTIVE: {
            TableState.ERROR,
            TableState.REMOVAL_PLANNED,
        },
        TableState.ERROR: {
            TableState.PLANNED,
            TableState.REMOVAL_PLANNED,
        },
        TableState.REMOVAL_PLANNED: {
            TableState.REMOVED,
            TableState.ERROR,
        },
        TableState.REMOVED: set(),
    }

    def ensure_transition_allowed(
        self,
        current_state: TableState,
        new_state: TableState,
    ) -> None:
        if current_state == new_state:
            return

        allowed = self._ALLOWED_TRANSITIONS.get(current_state, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid transition: {current_state.value} -> {new_state.value}"
            )
