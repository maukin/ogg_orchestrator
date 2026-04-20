from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GroupConfig:
    group_name: str
    group_type: str
    environment_name: str
    source_system: Optional[str]
    target_system: Optional[str]
    max_tables: Optional[int]
    priority_class: Optional[str]
    active_flag: bool
    notes: Optional[str]