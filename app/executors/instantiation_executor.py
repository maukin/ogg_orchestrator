from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import json
import subprocess

from app.models.instantiation import InstantiationCommand
from app.models.executor import ExecutorResult


def _debug(msg: str) -> None:
    print(f"[instantiation_executor] {msg}", flush=True)


class InstantiationExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        commands: list[InstantiationCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        raise NotImplementedError


class DryRunInstantiationExecutor(InstantiationExecutor):
    def execute(
        self,
        commands: list[InstantiationCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        _debug(f"dry-run execute started, commands_count={len(commands)}, artifacts_dir={out_dir}")
        for idx, cmd in enumerate(commands, start=1):
            _debug(
                f"command[{idx}] table_id={cmd.table_id}, "
                f"source={cmd.source_schema}.{cmd.source_table}, "
                f"target={cmd.target_schema}.{cmd.target_table}, "
                f"instantiation_scn={cmd.instantiation_scn}, "
                f"action={cmd.action}, reason={cmd.reason}"
            )

        sql_lines: list[str] = []
        json_rows: list[dict[str, object]] = []

        for cmd in commands:
            sql_lines.append(f"-- {cmd.table_id}")
            sql_lines.append("-- ACTION: PLAN_ONLY / DRY_RUN")
            sql_lines.append(cmd.command_text)
            sql_lines.append("")

            json_rows.append(
                {
                    "table_id": cmd.table_id,
                    "source_schema": cmd.source_schema,
                    "source_table": cmd.source_table,
                    "target_schema": cmd.target_schema,
                    "target_table": cmd.target_table,
                    "instantiation_scn": cmd.instantiation_scn,
                    "command_type": cmd.command_type,
                    "command_text": cmd.command_text,
                    "action": cmd.action,
                    "reason": cmd.reason,
                }
            )

        sql_path = out_dir / "instantiation_commands.sql"
        json_path = out_dir / "instantiation_commands.json"

        sql_path.write_text(
            "\n".join(sql_lines).strip() + ("\n" if sql_lines else ""),
            encoding="utf-8",
        )
        json_path.write_text(
            json.dumps(json_rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        _debug(f"sql artifact written to {sql_path}")
        _debug(f"json artifact written to {json_path}")

        return ExecutorResult(
            success=True,
            executed_count=len(commands),
            skipped_count=0,
            raw_output="Instantiation dry-run artifacts generated.",
            request_artifact=str(sql_path),
            response_artifact=str(json_path),
        )


class FileOnlyInstantiationExecutor(InstantiationExecutor):
    def execute(
        self,
        commands: list[InstantiationCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        _debug(f"file-only execute started, commands_count={len(commands)}, artifacts_dir={out_dir}")
        for idx, cmd in enumerate(commands, start=1):
            _debug(
                f"command[{idx}] table_id={cmd.table_id}, "
                f"source={cmd.source_schema}.{cmd.source_table}, "
                f"target={cmd.target_schema}.{cmd.target_table}, "
                f"instantiation_scn={cmd.instantiation_scn}, "
                f"action={cmd.action}, reason={cmd.reason}"
            )

        sql_lines: list[str] = []
        json_rows: list[dict[str, object]] = []

        for cmd in commands:
            sql_lines.append(f"-- {cmd.table_id}")
            sql_lines.append("-- ACTION: APPLY / FILE_ONLY")
            sql_lines.append(cmd.command_text)
            sql_lines.append("")

            json_rows.append(
                {
                    "table_id": cmd.table_id,
                    "source_schema": cmd.source_schema,
                    "source_table": cmd.source_table,
                    "target_schema": cmd.target_schema,
                    "target_table": cmd.target_table,
                    "instantiation_scn": cmd.instantiation_scn,
                    "command_type": cmd.command_type,
                    "command_text": cmd.command_text,
                    "action": cmd.action,
                    "reason": cmd.reason,
                }
            )

        sql_path = out_dir / "instantiation_commands.sql"
        json_path = out_dir / "instantiation_commands.json"

        sql_path.write_text(
            "\n".join(sql_lines).strip() + ("\n" if sql_lines else ""),
            encoding="utf-8",
        )
        json_path.write_text(
            json.dumps(json_rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        _debug(f"sql artifact written to {sql_path}")
        _debug(f"json artifact written to {json_path}")

        return ExecutorResult(
            success=True,
            executed_count=len(commands),
            skipped_count=0,
            raw_output="Instantiation file-only artifacts generated.",
            request_artifact=str(sql_path),
            response_artifact=str(json_path),
        )


class ScriptInstantiationExecutor(InstantiationExecutor):
    def __init__(
        self,
        script_command: str,
        timeout_sec: int = 1800,
    ):
        self.script_command = script_command
        self.timeout_sec = timeout_sec

    def execute(
        self,
        commands: list[InstantiationCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        request_path = out_dir / "instantiation_request.json"
        response_path = out_dir / "instantiation_response.json"

        _debug(f"script execute started, commands_count={len(commands)}, artifacts_dir={out_dir}")
        for idx, cmd in enumerate(commands, start=1):
            _debug(
                f"command[{idx}] table_id={cmd.table_id}, "
                f"source={cmd.source_schema}.{cmd.source_table}, "
                f"target={cmd.target_schema}.{cmd.target_table}, "
                f"instantiation_scn={cmd.instantiation_scn}, "
                f"command_type={cmd.command_type}, "
                f"action={cmd.action}, reason={cmd.reason}"
            )

        request_payload = {
            "commands": [
                {
                    "table_id": cmd.table_id,
                    "source_schema": cmd.source_schema,
                    "source_table": cmd.source_table,
                    "target_schema": cmd.target_schema,
                    "target_table": cmd.target_table,
                    "instantiation_scn": cmd.instantiation_scn,
                    "command_type": cmd.command_type,
                    "command_text": cmd.command_text,
                    "action": cmd.action,
                    "reason": cmd.reason,
                }
                for cmd in commands
            ]
        }
        request_path.write_text(
            json.dumps(request_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _debug(f"request written to {request_path}")

        command = (
            self.script_command
            .replace("{request}", str(request_path))
            .replace("{response}", str(response_path))
        )

        _debug(f"script_command template={self.script_command}")
        _debug(f"rendered command={command}")
        _debug(f"timeout_sec={self.timeout_sec}")
        _debug(f"response_path={response_path}")

        try:
            completed = subprocess.run(
                command,
                shell=True,
                check=False,
                timeout=self.timeout_sec,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired:
            _debug(f"script timeout after {self.timeout_sec} seconds")
            return ExecutorResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                raw_output=None,
                error_code="SCRIPT_TIMEOUT",
                error_message=f"Instantiation script timed out after {self.timeout_sec} seconds.",
                request_artifact=str(request_path),
                response_artifact=str(response_path) if response_path.exists() else None,
            )
        except Exception as exc:
            _debug(f"script exception: {exc}")
            return ExecutorResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                raw_output=None,
                error_code="SCRIPT_EXCEPTION",
                error_message=str(exc),
                request_artifact=str(request_path),
                response_artifact=str(response_path) if response_path.exists() else None,
            )

        _debug(f"process finished with returncode={completed.returncode}")
        if completed.stdout:
            _debug(f"stdout:\n{completed.stdout}")
        else:
            _debug("stdout is empty")
        if completed.stderr:
            _debug(f"stderr:\n{completed.stderr}")
        else:
            _debug("stderr is empty")

        response_payload: dict[str, object] | None = None
        if response_path.exists():
            try:
                response_payload = json.loads(response_path.read_text(encoding="utf-8"))
                _debug(f"response file found: {response_path}")
                _debug(
                    "response payload summary: "
                    f"success={response_payload.get('success')}, "
                    f"executed_count={response_payload.get('executed_count')}, "
                    f"skipped_count={response_payload.get('skipped_count')}, "
                    f"error_code={response_payload.get('error_code')}, "
                    f"error_message={response_payload.get('error_message')}"
                )
            except Exception as exc:
                _debug(f"failed to parse response file: {exc}")
                response_payload = None
        else:
            _debug("response file not found")

        if completed.returncode != 0:
            _debug("script returned non-zero exit code")
            return ExecutorResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                raw_output=(completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else ""),
                error_code=response_payload.get("error_code") if response_payload else f"EXIT_{completed.returncode}",
                error_message=response_payload.get("error_message") if response_payload else "Instantiation script failed.",
                request_artifact=str(request_path),
                response_artifact=str(response_path) if response_path.exists() else None,
            )

        if response_payload is not None:
            return ExecutorResult(
                success=bool(response_payload.get("success", True)),
                executed_count=int(response_payload.get("executed_count", len(commands))),
                skipped_count=int(response_payload.get("skipped_count", 0)),
                raw_output=response_payload.get("raw_output"),
                error_code=response_payload.get("error_code"),
                error_message=response_payload.get("error_message"),
                request_artifact=str(request_path),
                response_artifact=str(response_path),
            )

        return ExecutorResult(
            success=True,
            executed_count=len(commands),
            skipped_count=0,
            raw_output=(completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else ""),
            request_artifact=str(request_path),
            response_artifact=str(response_path) if response_path.exists() else None,
        )