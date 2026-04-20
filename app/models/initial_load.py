from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InitialLoadCommand:
    table_id: str
    source_schema: str
    source_table: str
    target_schema: str
    target_table: str
    load_method: Optional[str]
    extract_group: Optional[str]
    replicat_group: Optional[str]
    registration_scn: Optional[int]
    metadata_file: Optional[str]
    command_type: str
    command_text: str
    action: str
    reason: Optional[str]