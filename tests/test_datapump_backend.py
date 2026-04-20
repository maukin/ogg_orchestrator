from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations.initial_load_backends import BackendCommand, DataPumpBackend


def _cmd() -> BackendCommand:
    return BackendCommand(
        table_id="T1",
        source_schema="SRC",
        source_table="ORDERS",
        target_schema="DDS",
        target_table="ORDERS",
        load_method="DATAPUMP",
        extract_group="EXT_01",
        replicat_group="REP_01",
        registration_scn=123456,
        metadata_file="metadata/orders.json",
        command_type="INITIAL_LOAD",
        command_text="run_initial_load",
        mode="SCRIPT",
        reason="TEST",
    )


@pytest.fixture
def datapump_env(monkeypatch):
    monkeypatch.setenv("SOURCE_DB_CONNECT_STRING", "src_conn")
    monkeypatch.setenv("TARGET_DB_CONNECT_STRING", "tgt_conn")
    monkeypatch.setenv("DATAPUMP_NETWORK_LINK", "SOURCE_LINK")
    monkeypatch.setenv("DATAPUMP_DIRECTORY", "DATA_PUMP_DIR")
    monkeypatch.setenv("INITIAL_LOAD_REQUIRE_EMPTY_TARGET", "true")
    monkeypatch.setenv("DATAPUMP_DEFAULT_PARALLEL", "1")

    monkeypatch.setattr(
        "app.integrations.initial_load_backends._require_executable",
        lambda name: name,
    )


def test_datapump_backend_empty_source(datapump_env, monkeypatch):
    backend = DataPumpBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "0"
        raise AssertionError(sql)

    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "EMPTY_SOURCE"
    assert result.rows_loaded == 0


def test_datapump_backend_target_not_empty(datapump_env, monkeypatch):
    backend = DataPumpBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS" in sql:
            return "3"
        raise AssertionError(sql)

    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "BACKEND_EXCEPTION"
    assert "TARGET_NOT_EMPTY" in (result.error_message or "")


def test_datapump_backend_impdp_failure(datapump_env, monkeypatch):
    backend = DataPumpBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS" in sql:
            return "0"
        if "SELECT CURRENT_SCN FROM V$DATABASE" in sql:
            return "999999"
        raise AssertionError(sql)

    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=5,
            stdout="impdp stdout",
            stderr="impdp stderr",
        )

    monkeypatch.setattr("app.integrations.initial_load_backends.subprocess.run", fake_run)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "IMPDP_EXIT_5"
    assert result.load_batch_id is not None
    assert result.instantiation_candidate_scn == 999999
    assert "impdp stdout" in (result.raw_output or "")


def test_datapump_backend_rowcount_mismatch(datapump_env, monkeypatch):
    backend = DataPumpBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS;" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS;" in sql:
            # first call = before, second call = after
            fake_sql.target_calls += 1
            return "0" if fake_sql.target_calls == 1 else "8"
        if "SELECT CURRENT_SCN FROM V$DATABASE" in sql:
            return "111111"
        if "AS OF SCN 111111" in sql:
            return "10"
        raise AssertionError(sql)

    fake_sql.target_calls = 0
    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="impdp ok",
            stderr="",
        )

    monkeypatch.setattr("app.integrations.initial_load_backends.subprocess.run", fake_run)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "ROWCOUNT_MISMATCH"
    assert result.rows_loaded == 8
    assert "111111" in (result.error_message or "")


def test_datapump_backend_success(datapump_env, monkeypatch):
    backend = DataPumpBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS;" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS;" in sql:
            fake_sql.target_calls += 1
            return "0" if fake_sql.target_calls == 1 else "10"
        if "SELECT CURRENT_SCN FROM V$DATABASE" in sql:
            return "222222"
        if "AS OF SCN 222222" in sql:
            return "10"
        raise AssertionError(sql)

    fake_sql.target_calls = 0
    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="impdp ok",
            stderr="",
        )

    monkeypatch.setattr("app.integrations.initial_load_backends.subprocess.run", fake_run)

    result = backend.run(_cmd())

    assert result.success is True
    assert result.error_code is None
    assert result.rows_loaded == 10
    assert result.instantiation_candidate_scn == 222222
    assert result.load_batch_id is not None