from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus


@dataclass(frozen=True)
class DesiredTableConfig:
    source_system: str
    source_pdb: Optional[str]
    source_schema: str
    source_table: str
    target_system: str
    target_pdb: Optional[str]
    target_schema: str
    target_table: str
    desired_enabled: bool
    desired_replication_mode: ReplicationMode
    desired_extract_group: Optional[str]
    desired_replicat_group: Optional[str]
    desired_load_method: Optional[LoadMethod]
    desired_priority: Optional[str]
    desired_size_class: Optional[str]
    primary_key: tuple[str, ...]
    metadata_file: Optional[str]

    @property
    def table_id(self) -> str:
        src_pdb = self.source_pdb or "-"
        tgt_pdb = self.target_pdb or "-"
        return (
            f"{self.source_system}:{src_pdb}:{self.source_schema}.{self.source_table}"
            f"->{self.target_system}:{tgt_pdb}:{self.target_schema}.{self.target_table}"
        )


@dataclass
class TableRegistryRecord:
    table_id: str
    source_system: str
    source_pdb: Optional[str]
    source_schema: str
    source_table: str
    target_system: str
    target_pdb: Optional[str]
    target_schema: str
    target_table: str
    desired_enabled: bool
    desired_replication_mode: ReplicationMode
    desired_extract_group: Optional[str]
    desired_replicat_group: Optional[str]
    desired_load_method: Optional[LoadMethod]
    desired_priority: Optional[str]
    desired_size_class: Optional[str]
    primary_key: tuple[str, ...]
    metadata_file: Optional[str]
    actual_extract_group: Optional[str]
    actual_replicat_group: Optional[str]
    actual_load_batch_id: Optional[str]
    state: TableState
    validation_status: ValidationStatus
    prepared_for_instantiation: bool
    registration_scn: Optional[int]
    instantiation_candidate_scn: Optional[int] = None
    instantiation_scn: Optional[int] = None
    initial_load_started_at: Optional[object] = None
    initial_load_finished_at: Optional[object] = None
    cdc_capture_attached_at: Optional[object] = None
    cdc_apply_attached_at: Optional[object] = None
    activated_at: Optional[object] = None
    last_deployment_id: Optional[str] = None
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    created_at: Optional[object] = None
    updated_at: Optional[object] = None