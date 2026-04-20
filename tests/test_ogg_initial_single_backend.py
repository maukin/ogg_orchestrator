from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.integrations.initial_load_backends import BackendCommand, OGGInitialSingleBackend


def _cmd() -> BackendCommand:
    return BackendCommand(
        table_id="T1",
        source_schema="SRC",
        source_table="ORDERS",
        target_schema="DDS",
        target_table="ORDERS",
        load_method="OGG_INITIAL_SINGLE",
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
def ogg_single_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SOURCE_DB_CONNECT_STRING", "src_conn")
    monkeypatch.setenv("TARGET_DB_CONNECT_STRING", "tgt_conn")
    monkeypatch.setenv("OGG_ADMIN_URL", "http://ogg-host:9010")
    monkeypatch.setenv("OGG_ADMIN_DEPLOYMENT", "GG-01")
    monkeypatch.setenv("OGG_ADMIN_USER", "ggadmin")
    monkeypatch.setenv("OGG_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("OGG_PARAM_DIR", str(tmp_path))
    monkeypatch.setenv("OGG_TEMP_DIR", str(tmp_path))
    monkeypatch.setenv("OGG_SOURCE_USERID", "src_user")
    monkeypatch.setenv("OGG_SOURCE_PASSWORD", "src_pwd")
    monkeypatch.setenv("OGG_TARGET_USERID", "tgt_user")
    monkeypatch.setenv("OGG_TARGET_PASSWORD", "tgt_pwd")
    monkeypatch.setenv("OGG_ADMINCLIENT_PATH", "adminclient")
    monkeypatch.setenv("INITIAL_LOAD_REQUIRE_EMPTY_TARGET", "true")
    monkeypatch.setenv("OGG_INITIAL_SINGLE_EXTRACT_WAIT_SEC", "10")
    monkeypatch.setenv("OGG_INITIAL_SINGLE_REPLICAT_WAIT_SEC", "10")
    monkeypatch.setenv("OGG_INITIAL_SINGLE_POLL_INTERVAL_SEC", "1")

    monkeypatch.setattr(
        "app.integrations.initial_load_backends._resolve_tool_path",
        lambda value: value,
    )
    monkeypatch.setattr(
        "app.integrations.initial_load_backends._require_executable",
        lambda value: value,
    )


def test_ogg_initial_single_empty_source(ogg_single_env, monkeypatch):
    backend = OGGInitialSingleBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "0"
        raise AssertionError(sql)

    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "EMPTY_SOURCE"
    assert result.rows_loaded == 0


def test_ogg_initial_single_target_not_empty(ogg_single_env, monkeypatch):
    backend = OGGInitialSingleBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS" in sql:
            return "5"
        raise AssertionError(sql)

    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "TARGET_NOT_EMPTY"
    assert result.rows_loaded == 5


def test_ogg_initial_single_add_extract_failed(ogg_single_env, monkeypatch):
    backend = OGGInitialSingleBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS" in sql:
            return "0"
        raise AssertionError(sql)

    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)
    monkeypatch.setattr(backend, "_safe_delete_process", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_safe_stop_delete_process", lambda *args, **kwargs: "")
    monkeypatch.setattr(backend, "_write_extract_prm", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_write_replicat_prm", lambda *args, **kwargs: None)

    def fake_admin(body: str):
        if body.startswith("ADD EXTRACT"):
            return SimpleNamespace(success=False, stdout="bad", stderr="cannot add", exit_code=1)
        return SimpleNamespace(success=True, stdout="ok", stderr="", exit_code=0)

    monkeypatch.setattr(backend, "_admin_commands", fake_admin)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "ADD_EXTRACT_FAILED"
    assert result.load_batch_id is not None


def test_ogg_initial_single_empty_dump_file(ogg_single_env, monkeypatch, tmp_path: Path):
    backend = OGGInitialSingleBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS" in sql:
            return "0"
        raise AssertionError(sql)

    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)
    monkeypatch.setattr(backend, "_safe_delete_process", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_safe_stop_delete_process", lambda *args, **kwargs: "")
    monkeypatch.setattr(backend, "_admin_commands", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="ok", stderr="", exit_code=0))
    monkeypatch.setattr(backend, "_wait_for_extract_stop", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="stopped", stderr="", exit_code=0))
    monkeypatch.setattr(backend, "_write_extract_prm", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_write_replicat_prm", lambda *args, **kwargs: None)

    monkeypatch.setattr(Path, "exists", lambda self: False if self.suffix == ".dat" else Path.__dict__["exists"](self))
    # avoid finally unlink issues
    monkeypatch.setattr(Path, "unlink", lambda self, missing_ok=True: None)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "EMPTY_DUMP_FILE"


def test_ogg_initial_single_wait_replicat_failed(ogg_single_env, monkeypatch, tmp_path: Path):
    backend = OGGInitialSingleBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS" in sql:
            return "0"
        raise AssertionError(sql)

    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)
    monkeypatch.setattr(backend, "_safe_delete_process", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_safe_stop_delete_process", lambda *args, **kwargs: "")
    monkeypatch.setattr(backend, "_write_extract_prm", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_write_replicat_prm", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_admin_commands", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="ok", stderr="", exit_code=0))
    monkeypatch.setattr(backend, "_wait_for_extract_stop", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="stopped", stderr="", exit_code=0))
    monkeypatch.setattr(backend, "_wait_for_replicat_catchup", lambda *args, **kwargs: SimpleNamespace(success=False, stdout="lag", stderr="timeout", exit_code=1))

    original_exists = Path.exists
    original_stat = Path.stat
    original_unlink = Path.unlink

    def fake_exists(self):
        if self.suffix == ".dat":
            return True
        return original_exists(self)

    def fake_stat(self):
        if self.suffix == ".dat":
            return SimpleNamespace(st_size=100)
        return original_stat(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "stat", fake_stat)
    monkeypatch.setattr(Path, "unlink", lambda self, missing_ok=True: None)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "WAIT_REPLICAT_FAILED"


def test_ogg_initial_single_rowcount_mismatch(ogg_single_env, monkeypatch):
    backend = OGGInitialSingleBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS" in sql:
            fake_sql.target_calls += 1
            return "0" if fake_sql.target_calls == 1 else "8"
        raise AssertionError(sql)

    fake_sql.target_calls = 0
    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)
    monkeypatch.setattr(backend, "_safe_delete_process", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_safe_stop_delete_process", lambda *args, **kwargs: "")
    monkeypatch.setattr(backend, "_write_extract_prm", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_write_replicat_prm", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_admin_commands", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="ok", stderr="", exit_code=0))
    monkeypatch.setattr(backend, "_wait_for_extract_stop", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="stopped", stderr="", exit_code=0))
    monkeypatch.setattr(backend, "_wait_for_replicat_catchup", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="caught up", stderr="", exit_code=0))

    original_exists = Path.exists
    original_stat = Path.stat
    monkeypatch.setattr(Path, "unlink", lambda self, missing_ok=True: None)

    def fake_exists(self):
        if self.suffix == ".dat":
            return True
        return original_exists(self)

    def fake_stat(self):
        if self.suffix == ".dat":
            return SimpleNamespace(st_size=100)
        return original_stat(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "stat", fake_stat)

    result = backend.run(_cmd())

    assert result.success is False
    assert result.error_code == "ROWCOUNT_MISMATCH"
    assert result.rows_loaded == 8


def test_ogg_initial_single_success(ogg_single_env, monkeypatch):
    backend = OGGInitialSingleBackend()

    def fake_sql(connect_string: str, sql: str) -> str:
        if "SELECT COUNT(*) FROM SRC.ORDERS" in sql:
            return "10"
        if "SELECT COUNT(*) FROM DDS.ORDERS" in sql:
            fake_sql.target_calls += 1
            return "0" if fake_sql.target_calls == 1 else "10"
        raise AssertionError(sql)

    fake_sql.target_calls = 0
    monkeypatch.setattr(backend, "_sqlplus_scalar", fake_sql)
    monkeypatch.setattr(backend, "_safe_delete_process", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_safe_stop_delete_process", lambda *args, **kwargs: "")
    monkeypatch.setattr(backend, "_write_extract_prm", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_write_replicat_prm", lambda *args, **kwargs: None)
    monkeypatch.setattr(backend, "_admin_commands", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="ok", stderr="", exit_code=0))
    monkeypatch.setattr(backend, "_wait_for_extract_stop", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="stopped", stderr="", exit_code=0))
    monkeypatch.setattr(backend, "_wait_for_replicat_catchup", lambda *args, **kwargs: SimpleNamespace(success=True, stdout="caught up", stderr="", exit_code=0))

    original_exists = Path.exists
    original_stat = Path.stat
    monkeypatch.setattr(Path, "unlink", lambda self, missing_ok=True: None)

    def fake_exists(self):
        if self.suffix == ".dat":
            return True
        return original_exists(self)

    def fake_stat(self):
        if self.suffix == ".dat":
            return SimpleNamespace(st_size=100)
        return original_stat(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "stat", fake_stat)

    result = backend.run(_cmd())

    assert result.success is True
    assert result.error_code is None
    assert result.rows_loaded == 10
    assert result.load_batch_id is not None
    assert result.verification_passed is True