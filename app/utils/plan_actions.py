from __future__ import annotations

from app.models.enums import ReplicationMode


PLAN_INITIAL_LOAD = "PLAN_INITIAL_LOAD"
PLAN_CDC_ONLY = "PLAN_CDC_ONLY"
PLAN_INITIAL_LOAD_ONLY = "PLAN_INITIAL_LOAD_ONLY"

PREPARE_ATTACH_ACTIONS = {
    PLAN_INITIAL_LOAD,
    PLAN_CDC_ONLY,
    PLAN_INITIAL_LOAD_ONLY,
}

INITIAL_LOAD_ACTIONS = {
    PLAN_INITIAL_LOAD,
    PLAN_INITIAL_LOAD_ONLY,
}

CDC_APPLY_ACTIONS = {
    PLAN_INITIAL_LOAD,
    PLAN_CDC_ONLY,
}


def action_type_for_replication_mode(mode: ReplicationMode) -> str:
    if mode == ReplicationMode.CDC_ONLY:
        return PLAN_CDC_ONLY
    if mode == ReplicationMode.INITIAL_LOAD_ONLY:
        return PLAN_INITIAL_LOAD_ONLY
    return PLAN_INITIAL_LOAD