from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SourcePrepareCommand:
    table_id: str
    source_schema: str
    source_table: str
    command_type: str
    command_text: str
    action: str
    reason: Optional[str]