from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.integrations.ogg_admin_adapter import OGGAdminAdapter


@dataclass(frozen=True)
class BackendCommand:
    table_id: str
    source_schema: str
    source_table: str
    target_schema: str
    target_table: str
    load_method: str | None
    extract_group: str | None
    replicat_group: str | None
    registration_scn: int | None
    metadata_file: str | None
    command_type: str
    command_text: str
    mode: str
    reason: str | None


@dataclass(frozen=True)
class BackendResult:
    success: bool
    load_batch_id: str | None
    rows_loaded: int | None
    started_at: str | None
    finished_at: str | None
    instantiation_candidate_scn: int | None
    raw_output: str | None
    error_code: str | None
    error_message: str | None
    resolved_flashback_scn: int | None = None
    source_rowcount: int | None = None
    source_rowcount_as_of_scn: int | None = None
    target_rowcount_before: int | None = None
    target_rowcount_after: int | None = None
    verification_passed: bool | None = None
    stdout_text: str | None = None
    stderr_text: str | None = None


class InitialLoadBackend(Protocol):
    def run(self, command: BackendCommand) -> BackendResult:
        ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_$#]*", value):
        raise ValueError(f"Unsafe Oracle identifier: {value}")
    return value


def _qualified_table(schema: str, table: str) -> str:
    return f"{_sanitize_identifier(schema)}.{_sanitize_identifier(table)}"


def _require_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required executable not found in PATH: {name}")
    return path


def _resolve_tool_path(path_or_name: str) -> str:
    value = (path_or_name or "").strip()
    if not value:
        raise RuntimeError("Executable path is empty.")
    if Path(value).exists():
        return str(Path(value))
    resolved = shutil.which(value)
    if resolved:
        return resolved
    raise RuntimeError(f"Required executable not found: {value}")


class DataPumpBackend:
    def __init__(self):
        self.source_db = self._require_env("SOURCE_DB_CONNECT_STRING")
        self.target_db = self._require_env("TARGET_DB_CONNECT_STRING")
        self.network_link = self._require_env("DATAPUMP_NETWORK_LINK")
        self.directory = os.getenv("DATAPUMP_DIRECTORY", "DATA_PUMP_DIR").strip() or "DATA_PUMP_DIR"
        self.require_empty_target = os.getenv("INITIAL_LOAD_REQUIRE_EMPTY_TARGET", "true").lower() == "true"
        self.default_parallel = int(os.getenv("DATAPUMP_DEFAULT_PARALLEL", "1"))
        self.sqlplus_bin = _require_executable("sqlplus")
        self.impdp_bin = _require_executable("impdp")

    @staticmethod
    def _require_env(name: str) -> str:
        value = os.getenv(name, "").strip()
        if not value:
            raise RuntimeError(f"Missing required environment variable for DataPump backend: {name}")
        return value

    def _sqlplus_scalar(self, connect_string: str, sql: str) -> str:
        process = subprocess.run(
            [self.sqlplus_bin, "-s", connect_string],
            input=(
                "set pagesize 0 feedback off verify off heading off echo off termout off\n"
                f"{sql}\n"
                "exit;\n"
            ),
            text=True,
            capture_output=True,
            check=False,
        )

        stdout = (process.stdout or "").strip()
        stderr = (process.stderr or "").strip()

        if process.returncode != 0:
            raise RuntimeError(
                f"sqlplus failed; sql={sql!r}; returncode={process.returncode}; "
                f"stdout={stdout!r}; stderr={stderr!r}"
            )

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError(f"sqlplus returned empty output for sql={sql!r}")

        last = lines[-1]
        if last.startswith("ORA-"):
            raise RuntimeError(f"Oracle error for sql={sql!r}: {last}")

        return last

    def _get_current_source_scn(self) -> int:
        return int(
            self._sqlplus_scalar(
                self.source_db,
                "SELECT CURRENT_SCN FROM V$DATABASE;",
            )
        )

    def _resolve_flashback_scn(self, command: BackendCommand) -> int:
        return self._get_current_source_scn()

    def _get_source_rowcount(self, source_schema: str, source_table: str) -> int:
        sql = f"SELECT COUNT(*) FROM {_qualified_table(source_schema, source_table)};"
        return int(self._sqlplus_scalar(self.source_db, sql))

    def _get_target_rowcount(self, target_schema: str, target_table: str) -> int:
        sql = f"SELECT COUNT(*) FROM {_qualified_table(target_schema, target_table)};"
        return int(self._sqlplus_scalar(self.target_db, sql))

    def _get_source_rowcount_via_link_as_of_scn(
        self,
        source_schema: str,
        source_table: str,
        flashback_scn: int,
    ) -> int:
        source_full = _qualified_table(source_schema, source_table)
        sql = (
            f"SELECT COUNT(*) "
            f"FROM {source_full}@{self.network_link} "
            f"AS OF SCN {flashback_scn};"
        )
        return int(self._sqlplus_scalar(self.target_db, sql))

    def _ensure_target_is_empty(self, target_schema: str, target_table: str) -> int:
        target_before = self._get_target_rowcount(target_schema, target_table)
        if self.require_empty_target and target_before != 0:
            raise RuntimeError(
                f"TARGET_NOT_EMPTY: {_qualified_table(target_schema, target_table)} "
                f"contains {target_before} rows before initial load."
            )
        return target_before

    def _make_load_batch_id(self, command: BackendCommand) -> str:
        return (
            f"datapump_{command.source_schema}_{command.source_table}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

    def _build_impdp_command(
        self,
        command: BackendCommand,
        load_batch_id: str,
        flashback_scn: int,
    ) -> list[str]:
        source_full = _qualified_table(command.source_schema, command.source_table)
        logfile = f"impdp_{load_batch_id}.log"

        return [
            self.impdp_bin,
            self.target_db,
            f"network_link={self.network_link}",
            f"directory={self.directory}",
            f"tables={source_full}",
            f"remap_schema={command.source_schema}:{command.target_schema}",
            f"parallel={self.default_parallel}",
            "content=data_only",
            f"logfile={logfile}",
            f"flashback_scn={flashback_scn}",
        ]

    def run(self, command: BackendCommand) -> BackendResult:
        started_at = _utc_now()
        source_full = _qualified_table(command.source_schema, command.source_table)
        target_full = _qualified_table(command.target_schema, command.target_table)
        load_batch_id = self._make_load_batch_id(command)

        try:
            source_rows = self._get_source_rowcount(command.source_schema, command.source_table)
            if source_rows <= 0:
                return BackendResult(
                    success=False,
                    load_batch_id=load_batch_id,
                    rows_loaded=0,
                    started_at=started_at,
                    finished_at=_utc_now(),
                    instantiation_candidate_scn=None,
                    raw_output=None,
                    error_code="EMPTY_SOURCE",
                    error_message=f"Source table {source_full} is empty.",
                    resolved_flashback_scn=None,
                    source_rowcount=source_rows,
                    source_rowcount_as_of_scn=None,
                    target_rowcount_before=None,
                    target_rowcount_after=None,
                    verification_passed=False,
                    stdout_text=None,
                    stderr_text=None,
                )

            target_rows_before = self._ensure_target_is_empty(command.target_schema, command.target_table)
            flashback_scn = self._resolve_flashback_scn(command)

            impdp_args = self._build_impdp_command(
                command=command,
                load_batch_id=load_batch_id,
                flashback_scn=flashback_scn,
            )

            process = subprocess.run(
                impdp_args,
                capture_output=True,
                text=True,
                check=False,
            )

            stdout_text = (process.stdout or "").strip() or None
            stderr_text = (process.stderr or "").strip() or None
            raw_output = "\n".join(part for part in [stdout_text, stderr_text] if part) or None

            target_rows_after = self._get_target_rowcount(command.target_schema, command.target_table)

            if process.returncode != 0:
                return BackendResult(
                    success=False,
                    load_batch_id=load_batch_id,
                    rows_loaded=target_rows_after,
                    started_at=started_at,
                    finished_at=_utc_now(),
                    instantiation_candidate_scn=flashback_scn,
                    raw_output=raw_output,
                    error_code=f"IMPDP_EXIT_{process.returncode}",
                    error_message=raw_output or "impdp failed",
                    resolved_flashback_scn=flashback_scn,
                    source_rowcount=source_rows,
                    source_rowcount_as_of_scn=None,
                    target_rowcount_before=target_rows_before,
                    target_rowcount_after=target_rows_after,
                    verification_passed=False,
                    stdout_text=stdout_text,
                    stderr_text=stderr_text,
                )

            source_rows_at_scn = self._get_source_rowcount_via_link_as_of_scn(
                command.source_schema,
                command.source_table,
                flashback_scn,
            )

            if target_rows_after != source_rows_at_scn:
                return BackendResult(
                    success=False,
                    load_batch_id=load_batch_id,
                    rows_loaded=target_rows_after,
                    started_at=started_at,
                    finished_at=_utc_now(),
                    instantiation_candidate_scn=flashback_scn,
                    raw_output=raw_output,
                    error_code="ROWCOUNT_MISMATCH",
                    error_message=(
                        f"Target rows {target_rows_after} do not match source rows at SCN "
                        f"{flashback_scn}: {source_rows_at_scn}. "
                        f"Target before load: {target_rows_before}."
                    ),
                    resolved_flashback_scn=flashback_scn,
                    source_rowcount=source_rows,
                    source_rowcount_as_of_scn=source_rows_at_scn,
                    target_rowcount_before=target_rows_before,
                    target_rowcount_after=target_rows_after,
                    verification_passed=False,
                    stdout_text=stdout_text,
                    stderr_text=stderr_text,
                )

            return BackendResult(
                success=True,
                load_batch_id=load_batch_id,
                rows_loaded=target_rows_after,
                started_at=started_at,
                finished_at=_utc_now(),
                instantiation_candidate_scn=flashback_scn,
                raw_output=raw_output,
                error_code=None,
                error_message=None,
                resolved_flashback_scn=flashback_scn,
                source_rowcount=source_rows,
                source_rowcount_as_of_scn=source_rows_at_scn,
                target_rowcount_before=target_rows_before,
                target_rowcount_after=target_rows_after,
                verification_passed=True,
                stdout_text=stdout_text,
                stderr_text=stderr_text,
            )

        except Exception as exc:
            return BackendResult(
                success=False,
                load_batch_id=load_batch_id,
                rows_loaded=None,
                started_at=started_at,
                finished_at=_utc_now(),
                instantiation_candidate_scn=None,
                raw_output=None,
                error_code="BACKEND_EXCEPTION",
                error_message=str(exc),
                resolved_flashback_scn=None,
                source_rowcount=None,
                source_rowcount_as_of_scn=None,
                target_rowcount_before=None,
                target_rowcount_after=None,
                verification_passed=False,
                stdout_text=None,
                stderr_text=None,
            )


class OGGInitialSingleBackend:
    def __init__(self):
        self.source_db = self._require_env("SOURCE_DB_CONNECT_STRING")
        self.target_db = self._require_env("TARGET_DB_CONNECT_STRING")
        self.ogg_url = self._require_env("OGG_ADMIN_URL")
        self.ogg_deployment = self._require_env("OGG_ADMIN_DEPLOYMENT")
        self.ogg_user = self._require_env("OGG_ADMIN_USER")
        self.ogg_password = self._require_env("OGG_ADMIN_PASSWORD")
        self.ogg_param_dir = Path(self._require_env("OGG_PARAM_DIR"))
        self.ogg_temp_dir = Path(self._require_env("OGG_TEMP_DIR"))
        self.source_userid = self._require_env("OGG_SOURCE_USERID")
        self.source_password = self._require_env("OGG_SOURCE_PASSWORD")
        self.target_userid = self._require_env("OGG_TARGET_USERID")
        self.target_password = self._require_env("OGG_TARGET_PASSWORD")
        self.require_empty_target = os.getenv("INITIAL_LOAD_REQUIRE_EMPTY_TARGET", "true").lower() == "true"
        self.extract_wait_sec = int(os.getenv("OGG_INITIAL_SINGLE_EXTRACT_WAIT_SEC", "360"))
        self.replicat_wait_sec = int(os.getenv("OGG_INITIAL_SINGLE_REPLICAT_WAIT_SEC", "360"))
        self.poll_interval_sec = int(os.getenv("OGG_INITIAL_SINGLE_POLL_INTERVAL_SEC", "2"))
        self.sqlplus_bin = _require_executable("sqlplus")
        self.adminclient_path = _resolve_tool_path(os.getenv("OGG_ADMINCLIENT_PATH", "adminclient"))
        self.admin = OGGAdminAdapter(self.adminclient_path)

        if not self.ogg_param_dir.exists():
            raise RuntimeError(f"OGG_PARAM_DIR does not exist: {self.ogg_param_dir}")
        if not self.ogg_temp_dir.exists():
            raise RuntimeError(f"OGG_TEMP_DIR does not exist: {self.ogg_temp_dir}")

    @staticmethod
    def _require_env(name: str) -> str:
        value = os.getenv(name, "").strip()
        if not value:
            raise RuntimeError(f"Missing required environment variable for OGG initial single backend: {name}")
        return value

    def run(self, command: BackendCommand) -> BackendResult:
        started_at = _utc_now()
        source_full = _qualified_table(command.source_schema, command.source_table)
        target_full = _qualified_table(command.target_schema, command.target_table)
        load_batch_id = (
            f"ogg_single_{command.source_schema}_{command.source_table}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        extract_name = self._make_process_name("ILX", command)
        replicat_name = self._make_process_name("ILR", command)
        dump_file = self.ogg_temp_dir / f"{extract_name}.dat"
        discard_file = self.ogg_temp_dir / f"{replicat_name}.dsc"
        extract_prm = self.ogg_param_dir / f"{extract_name}.prm"
        replicat_prm = self.ogg_param_dir / f"{replicat_name}.prm"

        source_rows: int | None = None
        target_rows_before: int | None = None
        target_rows_after: int | None = None
        scn: int | None = None

        cleanup_outputs: list[str] = []

        try:
            source_rows = int(self._sqlplus_scalar(self.source_db, f"SELECT COUNT(*) FROM {source_full};") or "0")
            if source_rows <= 0:
                return BackendResult(
                    success=False,
                    load_batch_id=load_batch_id,
                    rows_loaded=0,
                    started_at=started_at,
                    finished_at=_utc_now(),
                    instantiation_candidate_scn=None,
                    raw_output=None,
                    error_code="EMPTY_SOURCE",
                    error_message=f"Source table {source_full} is empty.",
                    source_rowcount=source_rows,
                    verification_passed=False,
                )

            target_rows_before = int(self._sqlplus_scalar(self.target_db, f"SELECT COUNT(*) FROM {target_full};") or "0")
            if self.require_empty_target and target_rows_before != 0:
                return BackendResult(
                    success=False,
                    load_batch_id=load_batch_id,
                    rows_loaded=target_rows_before,
                    started_at=started_at,
                    finished_at=_utc_now(),
                    instantiation_candidate_scn=None,
                    raw_output=None,
                    error_code="TARGET_NOT_EMPTY",
                    error_message=f"Target table {target_full} is not empty: {target_rows_before} rows.",
                    source_rowcount=source_rows,
                    target_rowcount_before=target_rows_before,
                    verification_passed=False,
                )

            scn = command.registration_scn
            if scn is None:
                scn = int(self._sqlplus_scalar(self.source_db, "SELECT CURRENT_SCN FROM V$DATABASE;"))

            self._safe_delete_process("REPLICAT", replicat_name)
            self._safe_delete_process("EXTRACT", extract_name)

            self._write_extract_prm(extract_prm, extract_name, str(dump_file), source_full)
            self._write_replicat_prm(replicat_prm, replicat_name, str(discard_file), source_full, target_full)

            try:
                dump_file.unlink(missing_ok=True)
            except Exception:
                pass

            add_extract = self._admin_commands(f"ADD EXTRACT {extract_name}, SOURCEISTABLE")
            if not add_extract.success:
                return self._fail(
                    started_at=started_at,
                    scn=scn,
                    load_batch_id=load_batch_id,
                    admin_result=add_extract,
                    code="ADD_EXTRACT_FAILED",
                    source_rows=source_rows,
                    target_rows_before=target_rows_before,
                )

            start_extract = self._admin_commands(f"START EXTRACT {extract_name}")
            if not start_extract.success:
                return self._fail(
                    started_at=started_at,
                    scn=scn,
                    load_batch_id=load_batch_id,
                    admin_result=start_extract,
                    code="START_EXTRACT_FAILED",
                    source_rows=source_rows,
                    target_rows_before=target_rows_before,
                )

            wait_extract = self._wait_for_extract_stop(extract_name)
            if not wait_extract.success:
                return self._fail(
                    started_at=started_at,
                    scn=scn,
                    load_batch_id=load_batch_id,
                    admin_result=wait_extract,
                    code="WAIT_EXTRACT_FAILED",
                    source_rows=source_rows,
                    target_rows_before=target_rows_before,
                )

            if not dump_file.exists() or dump_file.stat().st_size == 0:
                return BackendResult(
                    success=False,
                    load_batch_id=load_batch_id,
                    rows_loaded=None,
                    started_at=started_at,
                    finished_at=_utc_now(),
                    instantiation_candidate_scn=scn,
                    raw_output=wait_extract.stdout,
                    error_code="EMPTY_DUMP_FILE",
                    error_message=f"Dump file {dump_file} was not created or is empty.",
                    source_rowcount=source_rows,
                    target_rowcount_before=target_rows_before,
                    verification_passed=False,
                )

            add_replicat = self._admin_commands(
                f"ADD REPLICAT {replicat_name}, EXTFILE {dump_file}, NODBCHECKPOINT"
            )
            if not add_replicat.success:
                return self._fail(
                    started_at=started_at,
                    scn=scn,
                    load_batch_id=load_batch_id,
                    admin_result=add_replicat,
                    code="ADD_REPLICAT_FAILED",
                    source_rows=source_rows,
                    target_rows_before=target_rows_before,
                )

            start_replicat = self._admin_commands(f"START REPLICAT {replicat_name}")
            if not start_replicat.success:
                return self._fail(
                    started_at=started_at,
                    scn=scn,
                    load_batch_id=load_batch_id,
                    admin_result=start_replicat,
                    code="START_REPLICAT_FAILED",
                    source_rows=source_rows,
                    target_rows_before=target_rows_before,
                )

            wait_replicat = self._wait_for_replicat_catchup(replicat_name, dump_file)
            if not wait_replicat.success:
                return self._fail(
                    started_at=started_at,
                    scn=scn,
                    load_batch_id=load_batch_id,
                    admin_result=wait_replicat,
                    code="WAIT_REPLICAT_FAILED",
                    source_rows=source_rows,
                    target_rows_before=target_rows_before,
                )

            target_rows_after = int(self._sqlplus_scalar(self.target_db, f"SELECT COUNT(*) FROM {target_full};") or "0")

            if target_rows_after != source_rows:
                return BackendResult(
                    success=False,
                    load_batch_id=load_batch_id,
                    rows_loaded=target_rows_after,
                    started_at=started_at,
                    finished_at=_utc_now(),
                    instantiation_candidate_scn=scn,
                    raw_output="\n".join(filter(None, [wait_extract.stdout, wait_replicat.stdout])),
                    error_code="ROWCOUNT_MISMATCH",
                    error_message=f"Target rows {target_rows_after} do not match source rows {source_rows}.",
                    resolved_flashback_scn=scn,
                    source_rowcount=source_rows,
                    target_rowcount_before=target_rows_before,
                    target_rowcount_after=target_rows_after,
                    verification_passed=False,
                    stdout_text="\n".join(filter(None, [wait_extract.stdout, wait_replicat.stdout])),
                )

            return BackendResult(
                success=True,
                load_batch_id=load_batch_id,
                rows_loaded=target_rows_after,
                started_at=started_at,
                finished_at=_utc_now(),
                instantiation_candidate_scn=scn,
                raw_output="\n".join(filter(None, [wait_extract.stdout, wait_replicat.stdout])),
                error_code=None,
                error_message=None,
                resolved_flashback_scn=scn,
                source_rowcount=source_rows,
                target_rowcount_before=target_rows_before,
                target_rowcount_after=target_rows_after,
                verification_passed=True,
                stdout_text="\n".join(filter(None, [wait_extract.stdout, wait_replicat.stdout])),
            )

        except Exception as exc:
            return BackendResult(
                success=False,
                load_batch_id=load_batch_id,
                rows_loaded=None,
                started_at=started_at,
                finished_at=_utc_now(),
                instantiation_candidate_scn=scn,
                raw_output=None,
                error_code="BACKEND_EXCEPTION",
                error_message=str(exc),
                resolved_flashback_scn=scn,
                source_rowcount=source_rows,
                target_rowcount_before=target_rows_before,
                target_rowcount_after=target_rows_after,
                verification_passed=False,
            )
        finally:
            cleanup_outputs.append(self._safe_stop_delete_process("REPLICAT", replicat_name))
            cleanup_outputs.append(self._safe_stop_delete_process("EXTRACT", extract_name))

            try:
                extract_prm.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                replicat_prm.unlink(missing_ok=True)
            except Exception:
                pass

    def _sqlplus_scalar(self, connect_string: str, sql: str) -> str:
        process = subprocess.run(
            [self.sqlplus_bin, "-s", connect_string],
            input=(
                "set pagesize 0 feedback off verify off heading off echo off termout off\n"
                f"{sql}\n"
                "exit;\n"
            ),
            text=True,
            capture_output=True,
            check=False,
        )
        stdout = (process.stdout or "").strip()
        stderr = (process.stderr or "").strip()
        if process.returncode != 0:
            raise RuntimeError(
                f"sqlplus failed; sql={sql!r}; returncode={process.returncode}; "
                f"stdout={stdout!r}; stderr={stderr!r}"
            )
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError(f"sqlplus returned empty output for sql={sql!r}")
        last = lines[-1]
        if last.startswith("ORA-"):
            raise RuntimeError(f"Oracle error for sql={sql!r}: {last}")
        return last

    def _make_process_name(self, prefix: str, command: BackendCommand) -> str:
        suffix = datetime.now(timezone.utc).strftime("%m%d%H%M%S")
        schema_part = re.sub(r"[^A-Za-z0-9]", "", command.source_schema.upper())[:3] or "SRC"
        table_part = re.sub(r"[^A-Za-z0-9]", "", command.source_table.upper())[:4] or "TAB"
        return f"{prefix}{schema_part}{table_part}{suffix}"[:8]

    def _admin_commands(self, body: str):
        commands = (
            f"CONNECT {self.ogg_url} DEPLOYMENT {self.ogg_deployment} "
            f"AS {self.ogg_user} PASSWORD {self.ogg_password}\n"
            f"{body}\n"
            f"EXIT\n"
        )
        return self.admin.run_commands(commands)

    def _safe_delete_process(self, process_type: str, process_name: str) -> None:
        try:
            self._admin_commands(f"DELETE {process_type} {process_name}")
        except Exception:
            pass

    def _safe_stop_delete_process(self, process_type: str, process_name: str) -> str:
        outputs: list[str] = []
        try:
            stop_result = self._admin_commands(f"STOP {process_type} {process_name}")
            if stop_result.stdout:
                outputs.append(stop_result.stdout)
            if stop_result.stderr:
                outputs.append(stop_result.stderr)
        except Exception as exc:
            outputs.append(f"STOP {process_type} {process_name} cleanup failed: {exc}")

        try:
            delete_result = self._admin_commands(f"DELETE {process_type} {process_name}")
            if delete_result.stdout:
                outputs.append(delete_result.stdout)
            if delete_result.stderr:
                outputs.append(delete_result.stderr)
        except Exception as exc:
            outputs.append(f"DELETE {process_type} {process_name} cleanup failed: {exc}")

        return "\n".join(filter(None, outputs))

    def _write_extract_prm(self, path: Path, extract_name: str, dump_file: str, source_full: str) -> None:
        path.write_text(
            "\n".join(
                [
                    f"EXTRACT {extract_name}",
                    f"USERID {self.source_userid}, PASSWORD {self.source_password}",
                    f"EXTFILE {dump_file}",
                    f"TABLE {source_full};",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _write_replicat_prm(
        self,
        path: Path,
        replicat_name: str,
        discard_file: str,
        source_full: str,
        target_full: str,
    ) -> None:
        path.write_text(
            "\n".join(
                [
                    f"REPLICAT {replicat_name}",
                    f"USERID {self.target_userid}, PASSWORD {self.target_password}",
                    "ASSUMETARGETDEFS",
                    f"DISCARDFILE {discard_file}, PURGE",
                    f"MAP {source_full}, TARGET {target_full};",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _wait_for_extract_stop(self, extract_name: str):
        max_polls = max(1, self.extract_wait_sec // self.poll_interval_sec)
        last_stdout = ""
        result = None
        for _ in range(max_polls):
            result = self._admin_commands(f"INFO EXTRACT {extract_name}")
            last_stdout = result.stdout
            if "ABENDED" in result.stdout:
                return result
            if "STOPPED" in result.stdout:
                return result
            time.sleep(self.poll_interval_sec)

        return type(result)(
            success=False,
            stdout=last_stdout,
            stderr=f"Timed out waiting for extract to stop after {self.extract_wait_sec} seconds.",
            exit_code=1,
        )

    def _wait_for_replicat_catchup(self, replicat_name: str, dump_file: Path):
        max_polls = max(1, self.replicat_wait_sec // self.poll_interval_sec)
        max_rba = dump_file.stat().st_size
        prev_rba = None
        last_result = None

        for _ in range(max_polls):
            result = self._admin_commands(f"INFO REPLICAT {replicat_name}")
            last_result = result
            if "ABENDED" in result.stdout:
                return result

            match = re.search(r"RBA\s+(\d+)", result.stdout)
            rba = int(match.group(1)) if match else None
            if rba is not None and rba >= max_rba:
                return result
            if rba is not None and prev_rba is not None and rba == prev_rba and rba > 0:
                return result

            prev_rba = rba
            time.sleep(self.poll_interval_sec)

        return type(last_result)(
            success=False,
            stdout=last_result.stdout if last_result else "",
            stderr=f"Timed out waiting for replicat catch-up after {self.replicat_wait_sec} seconds.",
            exit_code=1,
        )

    def _fail(
        self,
        started_at: str,
        scn: int | None,
        load_batch_id: str,
        admin_result,
        code: str,
        source_rows: int | None = None,
        target_rows_before: int | None = None,
    ) -> BackendResult:
        raw_output = "\n".join(
            part for part in [(admin_result.stdout or "").strip(), (admin_result.stderr or "").strip()] if part
        ) or None
        return BackendResult(
            success=False,
            load_batch_id=load_batch_id,
            rows_loaded=None,
            started_at=started_at,
            finished_at=_utc_now(),
            instantiation_candidate_scn=scn,
            raw_output=raw_output,
            error_code=code,
            error_message=admin_result.stderr or admin_result.stdout or code,
            resolved_flashback_scn=scn,
            source_rowcount=source_rows,
            target_rowcount_before=target_rows_before,
            verification_passed=False,
            stdout_text=(admin_result.stdout or "").strip() or None,
            stderr_text=(admin_result.stderr or "").strip() or None,
        )


class UnsupportedBackend:
    def __init__(self, backend_name: str):
        self.backend_name = backend_name

    def run(self, command: BackendCommand) -> BackendResult:
        now = _utc_now()
        return BackendResult(
            success=False,
            load_batch_id=None,
            rows_loaded=None,
            started_at=now,
            finished_at=now,
            instantiation_candidate_scn=command.registration_scn,
            raw_output=None,
            error_code="NOT_IMPLEMENTED",
            error_message=f"Initial load backend '{self.backend_name}' is not implemented yet.",
        )


class InitialLoadBackendDispatcher:
    def __init__(self):
        self._datapump = None
        self._ogg_single = None
        self._ogg_parallel = None

    def get_backend(self, load_method: str | None) -> InitialLoadBackend:
        normalized = (load_method or "").upper().strip()

        if normalized in {"DATAPUMP", "DATA_PUMP"}:
            if self._datapump is None:
                self._datapump = DataPumpBackend()
            return self._datapump

        if normalized in {"OGG_INITIAL_SINGLE", "OGG_INITIAL", "OGG"}:
            if self._ogg_single is None:
                self._ogg_single = OGGInitialSingleBackend()
            return self._ogg_single

        if normalized in {"OGG_INITIAL_PARALLEL", "OGG_PARALLEL"}:
            if self._ogg_parallel is None:
                self._ogg_parallel = UnsupportedBackend("OGG_INITIAL_PARALLEL")
            return self._ogg_parallel

        return UnsupportedBackend(normalized or "UNKNOWN")