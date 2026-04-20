from __future__ import annotations

from datetime import datetime
import oracledb

from app.models.events import TableEvent


class EventRepository:
    def __init__(self, connection: oracledb.Connection):
        self.connection = connection

    def add_event(self, event: TableEvent) -> None:
        sql = """
            INSERT INTO etl_table_events (
                table_id,
                deployment_id,
                event_type,
                event_status,
                step_name,
                event_ts,
                payload_json,
                error_code,
                error_message,
                created_by
            ) VALUES (
                :table_id,
                :deployment_id,
                :event_type,
                :event_status,
                :step_name,
                :event_ts,
                :payload_json,
                :error_code,
                :error_message,
                :created_by
            )
        """

        event_ts = event.event_ts or datetime.now()
        created_by = event.created_by or "SYSTEM"

        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": event.table_id,
                    "deployment_id": event.deployment_id,
                    "event_type": event.event_type.value,
                    "event_status": event.event_status.value,
                    "step_name": event.step_name,
                    "event_ts": event_ts,
                    "payload_json": event.payload_json,
                    "error_code": event.error_code,
                    "error_message": event.error_message,
                    "created_by": created_by,
                },
            )