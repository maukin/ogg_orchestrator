from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InstantiationCommand:
    table_id: str
    source_schema: str
    source_table: str
    target_schema: str
    target_table: str
    instantiation_scn: int
    command_type: str
    command_text: str
    action: str
    reason: Optional[str]