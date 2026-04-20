from __future__ import annotations

import pytest

from app.models.enums import TableState, ValidationStatus
from app.models.groups import GroupConfig
from app.models.registry import DesiredTableConfig, TableRegistryRecord
from app.services.grouping_service import GroupValidationError, GroupingService


def _cfg(
    table_id_suffix: str,
    extract_group: str | None,
    replicat_group: str | None,
    enabled: bool = True,
) -> DesiredTableConfig:
    return DesiredTableConfig(
        source_system="SRCDB",
        source_pdb="SRCPDB",
        source_schema="SRC",
        source_table=f"T_{table_id_suffix}",
        target_system="TGTDB",
        target_pdb="TGPDB",
        target_schema="DDS",
        target_table=f"T_{table_id_suffix}",
        desired_enabled=enabled,
        desired_replication_mode="INITIAL_PLUS_CDC",
        desired_extract_group=extract_group,
        desired_replicat_group=replicat_group,
        desired_load_method="DATAPUMP",
        desired_priority="NORMAL",
        desired_size_class="SMALL",
        primary_key=["ID"],
        metadata_file=f"metadata/{table_id_suffix}.json",
    )


def _group(name: str, group_type: str, max_tables=None) -> GroupConfig:
    return GroupConfig(
        group_name=name,
        group_type=group_type,
        environment_name="dev",
        source_system="SRCDB",
        target_system="TGTDB",
        max_tables=max_tables,
        priority_class=None,
        active_flag=True,
        notes=None,
    )


def _registry_record(
    table_id_suffix: str,
    actual_extract_group: str | None = None,
    actual_replicat_group: str | None = None,
) -> TableRegistryRecord:
    return TableRegistryRecord(
        table_id=f"SRCDB:SRCPDB:SRC.T_{table_id_suffix}->TGTDB:TGPDB:DDS.T_{table_id_suffix}",
        source_system="SRCDB",
        source_pdb="SRCPDB",
        source_schema="SRC",
        source_table=f"T_{table_id_suffix}",
        target_system="TGTDB",
        target_pdb="TGPDB",
        target_schema="DDS",
        target_table=f"T_{table_id_suffix}",
        desired_enabled=True,
        desired_replication_mode="INITIAL_PLUS_CDC",
        desired_extract_group=actual_extract_group,
        desired_replicat_group=actual_replicat_group,
        desired_load_method="DATAPUMP",
        desired_priority="NORMAL",
        desired_size_class="SMALL",
        primary_key=("ID",),
        metadata_file=f"metadata/{table_id_suffix}.json",
        actual_extract_group=actual_extract_group,
        actual_replicat_group=actual_replicat_group,
        actual_load_batch_id=None,
        state=TableState.ACTIVE,
        validation_status=next(iter(ValidationStatus)),
        prepared_for_instantiation=False,
        registration_scn=None,
        instantiation_candidate_scn=None,
        instantiation_scn=None,
        initial_load_started_at=None,
        initial_load_finished_at=None,
        cdc_capture_attached_at=None,
        cdc_apply_attached_at=None,
        activated_at=None,
        last_deployment_id=None,
        last_error_code=None,
        last_error_message=None,
        created_at=None,
        updated_at=None,
    )


def test_find_missing_groups():
    service = GroupingService()

    desired_configs = [
        _cfg("1", "EXT_EXISTS", "REP_NEW"),
        _cfg("2", "EXT_NEW", "REP_EXISTS"),
        _cfg("3", "EXT_NEW", "REP_NEW"),
    ]
    available_groups = [
        _group("EXT_EXISTS", "extract"),
        _group("REP_EXISTS", "replicat"),
    ]

    missing = service.find_missing_groups(
        desired_configs=desired_configs,
        available_groups=available_groups,
    )

    assert missing["extract"] == {"EXT_NEW"}
    assert missing["replicat"] == {"REP_NEW"}


def test_validate_desired_groups_non_strict_does_not_fail_on_missing_groups():
    service = GroupingService()

    desired_configs = [
        _cfg("1", "EXT_NEW", "REP_NEW"),
    ]
    current_registry: list[TableRegistryRecord] = []
    available_groups: list[GroupConfig] = []

    service.validate_desired_groups(
        desired_configs=desired_configs,
        current_registry=current_registry,
        available_groups=available_groups,
        strict_existing_groups=False,
    )


def test_validate_desired_groups_strict_fails_on_missing_groups():
    service = GroupingService()

    desired_configs = [
        _cfg("1", "EXT_NEW", "REP_NEW"),
    ]
    current_registry: list[TableRegistryRecord] = []
    available_groups: list[GroupConfig] = []

    with pytest.raises(GroupValidationError) as exc:
        service.validate_desired_groups(
            desired_configs=desired_configs,
            current_registry=current_registry,
            available_groups=available_groups,
            strict_existing_groups=True,
        )

    text = str(exc.value)
    assert "extract group not found: EXT_NEW" in text
    assert "replicat group not found: REP_NEW" in text


def test_validate_desired_groups_requires_group_names_for_enabled_table():
    service = GroupingService()

    desired_configs = [
        _cfg("1", None, None),
    ]
    current_registry: list[TableRegistryRecord] = []
    available_groups: list[GroupConfig] = []

    with pytest.raises(GroupValidationError) as exc:
        service.validate_desired_groups(
            desired_configs=desired_configs,
            current_registry=current_registry,
            available_groups=available_groups,
            strict_existing_groups=False,
        )

    text = str(exc.value)
    assert "desired_extract_group is required" in text
    assert "desired_replicat_group is required" in text


def test_validate_desired_groups_ignores_disabled_table_missing_groups():
    service = GroupingService()

    desired_configs = [
        _cfg("1", "EXT_NEW", "REP_NEW", enabled=False),
    ]
    current_registry: list[TableRegistryRecord] = []
    available_groups: list[GroupConfig] = []

    service.validate_desired_groups(
        desired_configs=desired_configs,
        current_registry=current_registry,
        available_groups=available_groups,
        strict_existing_groups=True,
    )


def test_validate_desired_groups_checks_capacity():
    service = GroupingService()

    desired_configs = [
        _cfg("1", "EXT_01", "REP_01"),
    ]
    current_registry = [
        _registry_record("A", actual_extract_group="EXT_01", actual_replicat_group="REP_01"),
        _registry_record("B", actual_extract_group="EXT_01", actual_replicat_group="REP_01"),
    ]
    available_groups = [
        _group("EXT_01", "extract", max_tables=1),
        _group("REP_01", "replicat", max_tables=5),
    ]

    with pytest.raises(GroupValidationError) as exc:
        service.validate_desired_groups(
            desired_configs=desired_configs,
            current_registry=current_registry,
            available_groups=available_groups,
            strict_existing_groups=True,
        )

    assert "group EXT_01 exceeds capacity" in str(exc.value)