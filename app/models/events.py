from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.models.enums import EventStatus, EventType


@dataclass
class TableEvent:
    table_id: str
    deployment_id: Optional[str]
    event_type: EventType
    event_status: EventStatus
    step_name: Optional[str]
    event_ts: Optional[datetime]
    payload_json: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    created_by: Optional[str]