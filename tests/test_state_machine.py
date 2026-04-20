import pytest

from app.models.enums import TableState
from app.services.state_machine_service import (
    InvalidStateTransitionError,
    StateMachineService,
)


def test_valid_transition():
    svc = StateMachineService()
    svc.ensure_transition_allowed(TableState.NEW, TableState.PLANNED)


def test_invalid_transition():
    svc = StateMachineService()
    with pytest.raises(InvalidStateTransitionError):
        svc.ensure_transition_allowed(TableState.NEW, TableState.ACTIVE)