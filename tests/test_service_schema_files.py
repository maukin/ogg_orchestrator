from pathlib import Path


def test_service_schema_sql_files_exist():
    assert Path("sql/bootstrap_service_schema.sql").exists()
    assert Path("sql/upgrade_service_schema.sql").exists()
    assert Path("docs/service_schema.md").exists()


def test_bootstrap_schema_contains_required_objects():
    ddl = Path("sql/bootstrap_service_schema.sql").read_text(encoding="utf-8").upper()

    assert "CREATE TABLE ETL_DEPLOYMENTS" in ddl
    assert "CREATE TABLE ETL_TABLE_REGISTRY" in ddl
    assert "CREATE TABLE ETL_TABLE_EVENTS" in ddl
    assert "CREATE SEQUENCE SEQ_ETL_TABLE_EVENTS" in ddl