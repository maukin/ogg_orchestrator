from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AttachExtractCommand:
    table_id: str
    source_schema: str
    source_table: str
    extract_group: str
    fragment_path: str
    command_type: str
    command_text: str
    action: str
    reason: Optional[str]