from __future__ import annotations

import json
from typing import Any

from app.models.enums import LoadMethod, ReplicationMode, TableState, ValidationStatus
from app.models.registry import TableRegistryRecord

from app.utils.oracle_types import (
    bool_to_char_flag,
    char_flag_to_bool,
    load_json_lob,
    read_lob,
)




def _parse_enum(enum_cls, value):
    if value is None:
        return None
    return enum_cls(value)



class RegistryRepository:
    def __init__(self, connection):
        self.connection = connection

    def list_all(self) -> list[TableRegistryRecord]:
        sql = """
            SELECT
                table_id,
                source_system,
                source_pdb,
                source_schema,
                source_table,
                target_system,
                target_pdb,
                target_schema,
                target_table,
                desired_enabled,
                desired_replication_mode,
                desired_extract_group,
                desired_replicat_group,
                desired_load_method,
                desired_priority,
                desired_size_class,
                actual_extract_group,
                actual_replicat_group,
                actual_load_batch_id,
                state,
                validation_status,
                prepared_for_instantiation,
                registration_scn,
                instantiation_candidate_scn,
                instantiation_scn,
                initial_load_started_at,
                initial_load_finished_at,
                cdc_capture_attached_at,
                cdc_apply_attached_at,
                activated_at,
                last_deployment_id,
                last_error_code,
                last_error_message,
                created_at,
                updated_at,
                primary_key_json,
                metadata_file
            FROM etl_table_registry
            ORDER BY table_id
        """

        with self.connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [self._map_row(row) for row in rows]

    def get_by_table_id(self, table_id: str) -> TableRegistryRecord | None:
        sql = """
            SELECT
                table_id,
                source_system,
                source_pdb,
                source_schema,
                source_table,
                target_system,
                target_pdb,
                target_schema,
                target_table,
                desired_enabled,
                desired_replication_mode,
                desired_extract_group,
                desired_replicat_group,
                desired_load_method,
                desired_priority,
                desired_size_class,
                actual_extract_group,
                actual_replicat_group,
                actual_load_batch_id,
                state,
                validation_status,
                prepared_for_instantiation,
                registration_scn,
                instantiation_candidate_scn,
                instantiation_scn,
                initial_load_started_at,
                initial_load_finished_at,
                cdc_capture_attached_at,
                cdc_apply_attached_at,
                activated_at,
                last_deployment_id,
                last_error_code,
                last_error_message,
                created_at,
                updated_at,
                primary_key_json,
                metadata_file
            FROM etl_table_registry
            WHERE table_id = :table_id
        """

        with self.connection.cursor() as cursor:
            cursor.execute(sql, {"table_id": table_id})
            row = cursor.fetchone()

        if row is None:
            return None

        return self._map_row(row)

    def register_new_table(
        self,
        payload: dict[str, Any],
        deployment_id: str,
    ) -> None:
        sql = """
            INSERT INTO etl_table_registry (
                table_id,
                source_system,
                source_pdb,
                source_schema,
                source_table,
                target_system,
                target_pdb,
                target_schema,
                target_table,
                desired_enabled,
                desired_replication_mode,
                desired_extract_group,
                desired_replicat_group,
                desired_load_method,
                desired_priority,
                desired_size_class,
                actual_extract_group,
                actual_replicat_group,
                actual_load_batch_id,
                state,
                validation_status,
                prepared_for_instantiation,
                registration_scn,
                instantiation_candidate_scn,
                instantiation_scn,
                initial_load_started_at,
                initial_load_finished_at,
                cdc_capture_attached_at,
                cdc_apply_attached_at,
                activated_at,
                last_deployment_id,
                last_error_code,
                last_error_message,
                created_at,
                updated_at,
                primary_key_json,
                metadata_file
            )
            VALUES (
                :table_id,
                :source_system,
                :source_pdb,
                :source_schema,
                :source_table,
                :target_system,
                :target_pdb,
                :target_schema,
                :target_table,
                :desired_enabled,
                :desired_replication_mode,
                :desired_extract_group,
                :desired_replicat_group,
                :desired_load_method,
                :desired_priority,
                :desired_size_class,
                :actual_extract_group,
                :actual_replicat_group,
                :actual_load_batch_id,
                :state,
                :validation_status,
                :prepared_for_instantiation,
                :registration_scn,
                :instantiation_candidate_scn,
                :instantiation_scn,
                :initial_load_started_at,
                :initial_load_finished_at,
                :cdc_capture_attached_at,
                :cdc_apply_attached_at,
                :activated_at,
                :last_deployment_id,
                :last_error_code,
                :last_error_message,
                SYSTIMESTAMP,
                SYSTIMESTAMP,
                :primary_key_json,
                :metadata_file
            )
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": payload["table_id"],
                    "source_system": payload["source_system"],
                    "source_pdb": payload.get("source_pdb"),
                    "source_schema": payload["source_schema"],
                    "source_table": payload["source_table"],
                    "target_system": payload["target_system"],
                    "target_pdb": payload.get("target_pdb"),
                    "target_schema": payload["target_schema"],
                    "target_table": payload["target_table"],
                    "desired_enabled": bool_to_char_flag(bool(payload["desired_enabled"])),
                    "desired_replication_mode": payload["desired_replication_mode"],
                    "desired_extract_group": payload.get("desired_extract_group"),
                    "desired_replicat_group": payload.get("desired_replicat_group"),
                    "desired_load_method": payload.get("desired_load_method"),
                    "desired_priority": payload.get("desired_priority"),
                    "desired_size_class": payload.get("desired_size_class"),
                    "actual_extract_group": None,
                    "actual_replicat_group": None,
                    "actual_load_batch_id": None,
                    "state": TableState.PLANNED.value if payload["desired_enabled"] else TableState.NEW.value,
                    "validation_status": ValidationStatus.UNKNOWN.value,
                    "prepared_for_instantiation": "N",
                    "registration_scn": None,
                    "instantiation_candidate_scn": None,
                    "instantiation_scn": None,
                    "initial_load_started_at": None,
                    "initial_load_finished_at": None,
                    "cdc_capture_attached_at": None,
                    "cdc_apply_attached_at": None,
                    "activated_at": None,
                    "last_deployment_id": deployment_id,
                    "last_error_code": None,
                    "last_error_message": None,
                    "primary_key_json": json.dumps(payload.get("primary_key", []), ensure_ascii=False),
                    "metadata_file": payload.get("metadata_file"),
                },
            )

    def update_desired_state(
        self,
        table_id: str,
        changes: dict[str, object],
        deployment_id: str,
    ) -> None:
        if not changes:
            return

        allowed_fields = {
            "desired_enabled": "desired_enabled",
            "desired_extract_group": "desired_extract_group",
            "desired_replicat_group": "desired_replicat_group",
            "desired_load_method": "desired_load_method",
            "desired_replication_mode": "desired_replication_mode",
            "desired_priority": "desired_priority",
            "desired_size_class": "desired_size_class",
            "primary_key": "primary_key_json",
            "metadata_file": "metadata_file",
        }

        set_clauses: list[str] = []
        params: dict[str, object] = {
            "table_id": table_id,
            "last_deployment_id": deployment_id,
        }

        for key, value in changes.items():
            if key not in allowed_fields:
                continue

            column_name = allowed_fields[key]
            bind_name = key

            if key == "desired_enabled":
                params[bind_name] = bool_to_char_flag(bool(value))
            elif key == "primary_key":
                params[bind_name] = json.dumps(value, ensure_ascii=False)
            else:
                params[bind_name] = value

            set_clauses.append(f"{column_name} = :{bind_name}")

        if not set_clauses:
            return

        set_clauses.append("last_deployment_id = :last_deployment_id")
        set_clauses.append("updated_at = SYSTIMESTAMP")

        sql = f"""
            UPDATE etl_table_registry
               SET {", ".join(set_clauses)}
             WHERE table_id = :table_id
        """

        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)

    def update_state(
        self,
        table_id: str,
        state: TableState,
        deployment_id: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET state = :state,
                   last_deployment_id = :last_deployment_id,
                   last_error_code = :last_error_code,
                   last_error_message = :last_error_message,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "state": state.value,
                    "last_deployment_id": deployment_id,
                    "last_error_code": error_code,
                    "last_error_message": error_message,
                },
            )

    def update_validation_status(
        self,
        table_id: str,
        validation_status: ValidationStatus,
        deployment_id: str,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET validation_status = :validation_status,
                   last_deployment_id = :last_deployment_id,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "validation_status": validation_status.value,
                    "last_deployment_id": deployment_id,
                },
            )

    def mark_prepared_for_instantiation(
        self,
        table_id: str,
        deployment_id: str,
        registration_scn: int,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET prepared_for_instantiation = 'Y',
                   registration_scn = :registration_scn,
                   last_deployment_id = :last_deployment_id,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "registration_scn": registration_scn,
                    "last_deployment_id": deployment_id,
                },
            )

    def record_instantiation(
        self,
        table_id: str,
        deployment_id: str,
        instantiation_scn: int,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET instantiation_scn = :instantiation_scn,
                   last_deployment_id = :last_deployment_id,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "instantiation_scn": instantiation_scn,
                    "last_deployment_id": deployment_id,
                },
            )

    def mark_cdc_capture_attached(
        self,
        table_id: str,
        deployment_id: str,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET state = :state,
                   cdc_capture_attached_at = SYSTIMESTAMP,
                   last_deployment_id = :last_deployment_id,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "state": TableState.CDC_CAPTURE_ATTACHED.value,
                    "last_deployment_id": deployment_id,
                },
            )

    def mark_initial_load_started(
        self,
        table_id: str,
        deployment_id: str,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET state = :state,
                   initial_load_started_at = COALESCE(initial_load_started_at, SYSTIMESTAMP),
                   last_deployment_id = :last_deployment_id,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "state": TableState.INITIAL_LOAD_RUNNING.value,
                    "last_deployment_id": deployment_id,
                },
            )

    def mark_initial_load_done(
        self,
        table_id: str,
        deployment_id: str,
        actual_load_batch_id: str | None = None,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET state = :state,
                   actual_load_batch_id = :actual_load_batch_id,
                   initial_load_finished_at = SYSTIMESTAMP,
                   last_deployment_id = :last_deployment_id,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "state": TableState.INITIAL_LOAD_DONE.value,
                    "actual_load_batch_id": actual_load_batch_id,
                    "last_deployment_id": deployment_id,
                },
            )

    def mark_cdc_apply_attached(
        self,
        table_id: str,
        deployment_id: str,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET state = :state,
                   cdc_apply_attached_at = SYSTIMESTAMP,
                   last_deployment_id = :last_deployment_id,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "state": TableState.CDC_APPLY_ATTACHED.value,
                    "last_deployment_id": deployment_id,
                },
            )

    def mark_activated(
        self,
        table_id: str,
        deployment_id: str,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET state = :state,
                   activated_at = SYSTIMESTAMP,
                   last_deployment_id = :last_deployment_id,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "state": TableState.ACTIVE.value,
                    "last_deployment_id": deployment_id,
                },
            )

    def mark_error(
        self,
        table_id: str,
        deployment_id: str,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET state = :state,
                   last_deployment_id = :last_deployment_id,
                   last_error_code = :last_error_code,
                   last_error_message = :last_error_message,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "state": TableState.ERROR.value,
                    "last_deployment_id": deployment_id,
                    "last_error_code": error_code,
                    "last_error_message": error_message,
                },
            )

    @staticmethod
    def _map_row(row) -> TableRegistryRecord:
        primary_key_raw = row[34]
        primary_key = tuple(json.loads(primary_key_raw)) if primary_key_raw else tuple()

    @staticmethod
    def _map_row(row) -> TableRegistryRecord:
        primary_key = tuple(load_json_lob(row[35], default=[]))
        last_error_message = read_lob(row[32])

        return TableRegistryRecord(
            table_id=row[0],
            source_system=row[1],
            source_pdb=row[2],
            source_schema=row[3],
            source_table=row[4],
            target_system=row[5],
            target_pdb=row[6],
            target_schema=row[7],
            target_table=row[8],
            desired_enabled=char_flag_to_bool(row[9]),
            desired_replication_mode=_parse_enum(ReplicationMode, row[10]),
            desired_extract_group=row[11],
            desired_replicat_group=row[12],
            desired_load_method=_parse_enum(LoadMethod, row[13]),
            desired_priority=row[14],
            desired_size_class=row[15],
            actual_extract_group=row[16],
            actual_replicat_group=row[17],
            actual_load_batch_id=row[18],
            state=_parse_enum(TableState, row[19]),
            validation_status=_parse_enum(ValidationStatus, row[20]),
            prepared_for_instantiation=char_flag_to_bool(row[21]),
            registration_scn=row[22],
            instantiation_candidate_scn=row[23],
            instantiation_scn=row[24],
            initial_load_started_at=row[25],
            initial_load_finished_at=row[26],
            cdc_capture_attached_at=row[27],
            cdc_apply_attached_at=row[28],
            activated_at=row[29],
            last_deployment_id=row[30],
            last_error_code=row[31],
            last_error_message=last_error_message,
            created_at=row[33],
            updated_at=row[34],
            primary_key=primary_key,
            metadata_file=row[36],
        )

    def set_instantiation_candidate_scn(
        self,
        table_id: str,
        deployment_id: str,
        instantiation_candidate_scn: int | None,
    ) -> None:
        sql = """
            UPDATE etl_table_registry
               SET instantiation_candidate_scn = :instantiation_candidate_scn,
                   last_deployment_id = :last_deployment_id,
                   updated_at = SYSTIMESTAMP
             WHERE table_id = :table_id
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "table_id": table_id,
                    "instantiation_candidate_scn": instantiation_candidate_scn,
                    "last_deployment_id": deployment_id,
                },
            )