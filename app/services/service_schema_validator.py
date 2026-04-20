from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    data_type_prefix: str


@dataclass(frozen=True)
class TableValidationIssue:
    table_name: str
    column_name: str
    expected_type_prefix: str
    actual_type: str | None
    issue_type: str  # MISSING_COLUMN | TYPE_MISMATCH


@dataclass
class SchemaValidationResult:
    ok: bool
    issues: list[TableValidationIssue]


class ServiceSchemaValidator:
    REQUIRED_SCHEMA: dict[str, list[ColumnSpec]] = {
        "ETL_DEPLOYMENTS": [
            ColumnSpec("DEPLOYMENT_ID", "VARCHAR2"),
            ColumnSpec("ENVIRONMENT_NAME", "VARCHAR2"),
            ColumnSpec("STATUS", "VARCHAR2"),
            ColumnSpec("PLAN_JSON", "CLOB"),
            ColumnSpec("STARTED_AT", "TIMESTAMP"),
            ColumnSpec("FINISHED_AT", "TIMESTAMP"),
            ColumnSpec("ERROR_MESSAGE", "CLOB"),
        ],
        "ETL_TABLE_REGISTRY": [
            ColumnSpec("TABLE_ID", "VARCHAR2"),
            ColumnSpec("DESIRED_ENABLED", "CHAR"),
            ColumnSpec("DESIRED_REPLICATION_MODE", "VARCHAR2"),
            ColumnSpec("DESIRED_EXTRACT_GROUP", "VARCHAR2"),
            ColumnSpec("DESIRED_REPLICAT_GROUP", "VARCHAR2"),
            ColumnSpec("STATE", "VARCHAR2"),
            ColumnSpec("VALIDATION_STATUS", "VARCHAR2"),
            ColumnSpec("PREPARED_FOR_INSTANTIATION", "CHAR"),
            ColumnSpec("REGISTRATION_SCN", "NUMBER"),
            ColumnSpec("INSTANTIATION_CANDIDATE_SCN", "NUMBER"),
            ColumnSpec("INSTANTIATION_SCN", "NUMBER"),
            ColumnSpec("PRIMARY_KEY_JSON", "CLOB"),
            ColumnSpec("METADATA_FILE", "VARCHAR2"),
            ColumnSpec("LAST_ERROR_MESSAGE", "CLOB"),
            ColumnSpec("UPDATED_AT", "TIMESTAMP"),
        ],
        "ETL_TABLE_EVENTS": [
            ColumnSpec("EVENT_ID", "NUMBER"),
            ColumnSpec("TABLE_ID", "VARCHAR2"),
            ColumnSpec("DEPLOYMENT_ID", "VARCHAR2"),
            ColumnSpec("EVENT_TYPE", "VARCHAR2"),
            ColumnSpec("EVENT_STATUS", "VARCHAR2"),
            ColumnSpec("STEP_NAME", "VARCHAR2"),
            ColumnSpec("PAYLOAD_JSON", "CLOB"),
            ColumnSpec("ERROR_MESSAGE", "CLOB"),
            ColumnSpec("CREATED_AT", "TIMESTAMP"),
        ],
    }

    def __init__(self, connection):
        self.connection = connection

    def validate(self) -> SchemaValidationResult:
        issues: list[TableValidationIssue] = []

        for table_name, required_columns in self.REQUIRED_SCHEMA.items():
            actual_columns = self._load_columns(table_name)
            for spec in required_columns:
                actual_type = actual_columns.get(spec.name)
                if actual_type is None:
                    issues.append(
                        TableValidationIssue(
                            table_name=table_name,
                            column_name=spec.name,
                            expected_type_prefix=spec.data_type_prefix,
                            actual_type=None,
                            issue_type="MISSING_COLUMN",
                        )
                    )
                    continue

                if not actual_type.upper().startswith(spec.data_type_prefix.upper()):
                    issues.append(
                        TableValidationIssue(
                            table_name=table_name,
                            column_name=spec.name,
                            expected_type_prefix=spec.data_type_prefix,
                            actual_type=actual_type,
                            issue_type="TYPE_MISMATCH",
                        )
                    )

        return SchemaValidationResult(
            ok=len(issues) == 0,
            issues=issues,
        )

    def _load_columns(self, table_name: str) -> dict[str, str]:
        sql = """
            SELECT column_name, data_type
            FROM user_tab_columns
            WHERE table_name = :table_name
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {"table_name": table_name.upper()})
            rows = cursor.fetchall()

        return {row[0].upper(): row[1].upper() for row in rows}