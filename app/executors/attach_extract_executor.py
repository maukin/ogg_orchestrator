from __future__ import annotations

import json
import os
import shlex
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from app.models.attach_extract import AttachExtractCommand
from app.models.attach_extract_result import AttachExtractExecutionResult


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _debug(msg: str) -> None:
    print(f"[attach_extract_executor] {msg}", flush=True)


class AttachExtractExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        commands: list[AttachExtractCommand],
        artifacts_dir: str | Path,
    ) -> AttachExtractExecutionResult:
        raise NotImplementedError


class FileOnlyAttachExtractExecutor(AttachExtractExecutor):
    def execute(
        self,
        commands: list[AttachExtractCommand],
        artifacts_dir: str | Path,
    ) -> AttachExtractExecutionResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        request_path = out_dir / "attach_extract_request.json"
        response_path = out_dir / "attach_extract_response.json"

        _debug(f"file-only execute started, commands_count={len(commands)}, artifacts_dir={out_dir}")
        for idx, c in enumerate(commands, start=1):
            _debug(
                f"command[{idx}] table_id={c.table_id}, "
                f"source={c.source_schema}.{c.source_table}, "
                f"extract_group={c.extract_group}, "
                f"fragment_path={c.fragment_path}, "
                f"action={c.action}, reason={c.reason}"
            )

        payload = {
            "commands": [
                {
                    "table_id": c.table_id,
                    "source_schema": c.source_schema,
                    "source_table": c.source_table,
                    "extract_group": c.extract_group,
                    "fragment_path": c.fragment_path,
                    "command_type": c.command_type,
                    "command_text": c.command_text,
                    "action": c.action,
                    "reason": c.reason,
                }
                for c in commands
            ]
        }

        request_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _debug(f"request written to {request_path}")

        now = _utc_now()
        group_name = commands[0].extract_group if commands else None

        result_payload = {
            "success": True,
            "executed_count": len(commands),
            "skipped_count": 0,
            "group_name": group_name,
            "applied_tables_count": len(commands),
            "started_at": now,
            "finished_at": now,
            "raw_output": "File-only attach extract contract artifact created.",
            "error_code": None,
            "error_message": None,
        }
        response_path.write_text(
            json.dumps(result_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _debug(f"response written to {response_path}")

        return AttachExtractExecutionResult(
            success=True,
            executed_count=len(commands),
            skipped_count=0,
            group_name=group_name,
            applied_tables_count=len(commands),
            started_at=now,
            finished_at=now,
            raw_output=result_payload["raw_output"],
            error_code=None,
            error_message=None,
            request_artifact=str(request_path),
            response_artifact=str(response_path),
        )


class ScriptAttachExtractExecutor(AttachExtractExecutor):
    def __init__(self, script_command: str, timeout_sec: int = 1800):
        self.script_command = script_command
        self.timeout_sec = timeout_sec

    def execute(
        self,
        commands: list[AttachExtractCommand],
        artifacts_dir: str | Path,
    ) -> AttachExtractExecutionResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        request_path = out_dir / "attach_extract_request.json"
        response_path = out_dir / "attach_extract_response.json"
        stdout_path = out_dir / "attach_extract_stdout.log"
        stderr_path = out_dir / "attach_extract_stderr.log"

        _debug(f"script execute started, commands_count={len(commands)}, artifacts_dir={out_dir}")
        for idx, c in enumerate(commands, start=1):
            _debug(
                f"command[{idx}] table_id={c.table_id}, "
                f"source={c.source_schema}.{c.source_table}, "
                f"extract_group={c.extract_group}, "
                f"fragment_path={c.fragment_path}, "
                f"command_type={c.command_type}, "
                f"action={c.action}, reason={c.reason}"
            )

        payload = {
            "commands": [
                {
                    "table_id": c.table_id,
                    "source_schema": c.source_schema,
                    "source_table": c.source_table,
                    "extract_group": c.extract_group,
                    "fragment_path": c.fragment_path,
                    "command_type": c.command_type,
                    "command_text": c.command_text,
                    "action": c.action,
                    "reason": c.reason,
                }
                for c in commands
            ]
        }
        request_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _debug(f"request written to {request_path}")

        rendered = self.script_command.format(
            request=str(request_path),
            response=str(response_path),
        )

        _debug(f"script_command template={self.script_command}")
        _debug(f"rendered command={rendered}")
        _debug(f"timeout_sec={self.timeout_sec}")
        _debug(f"response_path={response_path}")
        _debug(f"stdout_path={stdout_path}")
        _debug(f"stderr_path={stderr_path}")

        try:
            if os.name == "nt":
                _debug("running subprocess on Windows with shell=True")
                process = subprocess.run(
                    rendered,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                    check=False,
                    shell=True,
                )
            else:
                argv = shlex.split(rendered, posix=True)
                _debug(f"running subprocess on POSIX argv={argv}")
                process = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                    check=False,
                )
        except subprocess.TimeoutExpired as exc:
            _debug(f"script timeout after {self.timeout_sec} seconds")
            stdout_path.write_text(exc.stdout or "", encoding="utf-8")
            stderr_path.write_text(exc.stderr or "", encoding="utf-8")
            return AttachExtractExecutionResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                group_name=commands[0].extract_group if commands else None,
                applied_tables_count=None,
                started_at=None,
                finished_at=None,
                raw_output=exc.stdout,
                error_code="TIMEOUT",
                error_message=f"Attach extract script timed out after {self.timeout_sec} seconds.",
                request_artifact=str(request_path),
                response_artifact=str(response_path) if response_path.exists() else None,
            )
        except FileNotFoundError as exc:
            _debug(f"script executable not found: {exc}")
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text(str(exc), encoding="utf-8")
            return AttachExtractExecutionResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                group_name=commands[0].extract_group if commands else None,
                applied_tables_count=None,
                started_at=None,
                finished_at=None,
                raw_output=None,
                error_code="FILE_NOT_FOUND",
                error_message=str(exc),
                request_artifact=str(request_path),
                response_artifact=str(response_path) if response_path.exists() else None,
            )

        stdout_path.write_text(process.stdout or "", encoding="utf-8")
        stderr_path.write_text(process.stderr or "", encoding="utf-8")

        _debug(f"process finished with returncode={process.returncode}")
        if process.stdout:
            _debug(f"stdout:\n{process.stdout}")
        else:
            _debug("stdout is empty")
        if process.stderr:
            _debug(f"stderr:\n{process.stderr}")
        else:
            _debug("stderr is empty")

        if process.returncode != 0:
            _debug("script returned non-zero exit code")
            return AttachExtractExecutionResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                group_name=commands[0].extract_group if commands else None,
                applied_tables_count=None,
                started_at=None,
                finished_at=None,
                raw_output=process.stdout,
                error_code=f"EXIT_{process.returncode}",
                error_message=process.stderr or "Attach extract script failed.",
                request_artifact=str(request_path),
                response_artifact=str(response_path) if response_path.exists() else None,
            )

        if not response_path.exists():
            _debug("response file is missing after successful script completion")
            return AttachExtractExecutionResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                group_name=commands[0].extract_group if commands else None,
                applied_tables_count=None,
                started_at=None,
                finished_at=None,
                raw_output=process.stdout,
                error_code="MISSING_RESPONSE",
                error_message="Attach extract script completed but did not create response file.",
                request_artifact=str(request_path),
                response_artifact=None,
            )

        _debug(f"response file found: {response_path}")
        response_payload = json.loads(response_path.read_text(encoding="utf-8"))
        _debug(
            "response payload summary: "
            f"success={response_payload.get('success')}, "
            f"executed_count={response_payload.get('executed_count')}, "
            f"skipped_count={response_payload.get('skipped_count')}, "
            f"group_name={response_payload.get('group_name')}, "
            f"applied_tables_count={response_payload.get('applied_tables_count')}, "
            f"error_code={response_payload.get('error_code')}, "
            f"error_message={response_payload.get('error_message')}, "
            f"restart_performed={response_payload.get('restart_performed')}, "
            f"rollback_performed={response_payload.get('rollback_performed')}"
        )

        return AttachExtractExecutionResult(
            success=bool(response_payload.get("success")),
            executed_count=int(response_payload.get("executed_count", 0)),
            skipped_count=int(response_payload.get("skipped_count", 0)),
            group_name=response_payload.get("group_name"),
            applied_tables_count=response_payload.get("applied_tables_count"),
            started_at=response_payload.get("started_at"),
            finished_at=response_payload.get("finished_at"),
            raw_output=response_payload.get("raw_output"),
            error_code=response_payload.get("error_code"),
            error_message=response_payload.get("error_message"),
            request_artifact=str(request_path),
            response_artifact=str(response_path),
            restart_performed=response_payload.get("restart_performed"),
            rollback_performed=response_payload.get("rollback_performed"),
        )