from app.services.service_schema_validator import ServiceSchemaValidator


class DummyCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql, params):
        self.params = params

    def fetchall(self):
        table_name = self.params["table_name"]
        return self.rows.get(table_name, [])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyConnection:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        return DummyCursor(self.rows)


def test_schema_validator_ok():
    rows = {
        "ETL_DEPLOYMENTS": [
            ("DEPLOYMENT_ID", "VARCHAR2"),
            ("ENVIRONMENT_NAME", "VARCHAR2"),
            ("STATUS", "VARCHAR2"),
            ("PLAN_JSON", "CLOB"),
            ("STARTED_AT", "TIMESTAMP"),
            ("FINISHED_AT", "TIMESTAMP"),
            ("ERROR_MESSAGE", "CLOB"),
        ],
        "ETL_TABLE_REGISTRY": [
            ("TABLE_ID", "VARCHAR2"),
            ("DESIRED_ENABLED", "CHAR"),
            ("DESIRED_REPLICATION_MODE", "VARCHAR2"),
            ("DESIRED_EXTRACT_GROUP", "VARCHAR2"),
            ("DESIRED_REPLICAT_GROUP", "VARCHAR2"),
            ("STATE", "VARCHAR2"),
            ("VALIDATION_STATUS", "VARCHAR2"),
            ("PREPARED_FOR_INSTANTIATION", "CHAR"),
            ("REGISTRATION_SCN", "NUMBER"),
            ("INSTANTIATION_CANDIDATE_SCN", "NUMBER"),
            ("INSTANTIATION_SCN", "NUMBER"),
            ("PRIMARY_KEY_JSON", "CLOB"),
            ("METADATA_FILE", "VARCHAR2"),
            ("LAST_ERROR_MESSAGE", "CLOB"),
            ("UPDATED_AT", "TIMESTAMP"),
        ],
        "ETL_TABLE_EVENTS": [
            ("EVENT_ID", "NUMBER"),
            ("TABLE_ID", "VARCHAR2"),
            ("DEPLOYMENT_ID", "VARCHAR2"),
            ("EVENT_TYPE", "VARCHAR2"),
            ("EVENT_STATUS", "VARCHAR2"),
            ("STEP_NAME", "VARCHAR2"),
            ("PAYLOAD_JSON", "CLOB"),
            ("ERROR_MESSAGE", "CLOB"),
            ("CREATED_AT", "TIMESTAMP"),
        ],
    }

    svc = ServiceSchemaValidator(DummyConnection(rows))
    result = svc.validate()

    assert result.ok is True
    assert result.issues == []


def test_schema_validator_detects_missing_column():
    rows = {
        "ETL_DEPLOYMENTS": [
            ("DEPLOYMENT_ID", "VARCHAR2"),
        ],
        "ETL_TABLE_REGISTRY": [],
        "ETL_TABLE_EVENTS": [],
    }

    svc = ServiceSchemaValidator(DummyConnection(rows))
    result = svc.validate()

    assert result.ok is False
    assert len(result.issues) > 0