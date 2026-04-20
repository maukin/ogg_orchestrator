from __future__ import annotations

import json

from app.models.enums import EventStatus, EventType, TableState
from app.models.events import TableEvent
from app.repositories.event_repo import EventRepository
from app.repositories.registry_repo import RegistryRepository


def mark_tables_step_error(
    registry_repo: RegistryRepository,
    event_repo: EventRepository,
    table_ids: list[str],
    deployment_id: str,
    step_name: str,
    error_code: str | None,
    error_message: str | None,
) -> None:
    for table_id in table_ids:
        registry_repo.mark_error(
            table_id=table_id,
            deployment_id=deployment_id,
            error_code=error_code,
            error_message=error_message,
        )

        event_repo.add_event(
            TableEvent(
                table_id=table_id,
                deployment_id=deployment_id,
                event_type=EventType.ERROR_OCCURRED,
                event_status=EventStatus.FAILED,
                step_name=step_name,
                event_ts=None,
                payload_json=json.dumps(
                    {
                        "step_name": step_name,
                        "error_code": error_code,
                        "error_message": error_message,
                        "new_state": TableState.ERROR.value,
                    },
                    ensure_ascii=False,
                ),
                error_code=error_code,
                error_message=error_message,
                created_by=None,
            )
        )