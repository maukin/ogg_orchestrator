from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ReplicatAttachCommand:
    table_id: str
    replicat_group: str
    source_schema: str
    source_table: str
    target_schema: str
    target_table: str
    command_type: str
    command_text: str
    mode: str
    reason: Optional[str]