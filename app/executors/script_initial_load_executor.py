from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

from app.models.initial_load import InitialLoadCommand
from app.models.initial_load_result import InitialLoadExecutionResult


class ScriptInitialLoadExecutor:
    def __init__(
        self,
        script_command: str,
        timeout_sec: int = 3600,
    ):
        self.script_command = script_command
        self.timeout_sec = timeout_sec

    def execute(
        self,
        commands: list[InitialLoadCommand],
        artifacts_dir: str | Path,
    ) -> InitialLoadExecutionResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        request_path = out_dir / "initial_load_request.json"
        response_path = out_dir / "initial_load_response.json"
        stdout_path = out_dir / "initial_load_stdout.log"
        stderr_path = out_dir / "initial_load_stderr.log"

        request_payload = {
            "commands": [
                {
                    "table_id": c.table_id,
                    "source_schema": c.source_schema,
                    "source_table": c.source_table,
                    "target_schema": c.target_schema,
                    "target_table": c.target_table,
                    "load_method": c.load_method,
                    "extract_group": c.extract_group,
                    "replicat_group": c.replicat_group,
                    "registration_scn": c.registration_scn,
                    "metadata_file": c.metadata_file,
                    "command_type": c.command_type,
                    "command_text": c.command_text,
                    "action": c.action,
                    "reason": c.reason,
                }
                for c in commands
            ]
        }

        request_path.write_text(
            json.dumps(request_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        command = self._build_command(
            request_path=request_path,
            response_path=response_path,
        )

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout_path.write_text(exc.stdout or "", encoding="utf-8")
            stderr_path.write_text(exc.stderr or "", encoding="utf-8")

            return InitialLoadExecutionResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                load_batch_id=None,
                rows_loaded=None,
                started_at=None,
                finished_at=None,
                instantiation_candidate_scn=None,
                raw_output=exc.stdout,
                error_code="TIMEOUT",
                error_message=f"Initial load script timed out after {self.timeout_sec} seconds.",
                request_artifact=str(request_path),
                response_artifact=str(response_path) if response_path.exists() else None,
            )
        except FileNotFoundError as exc:
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text(str(exc), encoding="utf-8")

            return InitialLoadExecutionResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                load_batch_id=None,
                rows_loaded=None,
                started_at=None,
                finished_at=None,
                instantiation_candidate_scn=None,
                raw_output=None,
                error_code="FILE_NOT_FOUND",
                error_message=str(exc),
                request_artifact=str(request_path),
                response_artifact=str(response_path) if response_path.exists() else None,
            )

        stdout_path.write_text(process.stdout or "", encoding="utf-8")
        stderr_path.write_text(process.stderr or "", encoding="utf-8")

        if process.returncode != 0:
            return InitialLoadExecutionResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                load_batch_id=None,
                rows_loaded=None,
                started_at=None,
                finished_at=None,
                instantiation_candidate_scn=None,
                raw_output=process.stdout,
                error_code=f"EXIT_{process.returncode}",
                error_message=process.stderr or "Initial load script failed.",
                request_artifact=str(request_path),
                response_artifact=str(response_path) if response_path.exists() else None,
            )

        if not response_path.exists():
            return InitialLoadExecutionResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                load_batch_id=None,
                rows_loaded=None,
                started_at=None,
                finished_at=None,
                instantiation_candidate_scn=None,
                raw_output=process.stdout,
                error_code="MISSING_RESPONSE",
                error_message="Initial load script completed but did not create response file.",
                request_artifact=str(request_path),
                response_artifact=None,
            )

        response_payload = json.loads(response_path.read_text(encoding="utf-8"))

        return InitialLoadExecutionResult(
            success=bool(response_payload.get("success")),
            executed_count=int(response_payload.get("executed_count", 0)),
            skipped_count=int(response_payload.get("skipped_count", 0)),
            load_batch_id=response_payload.get("load_batch_id"),
            rows_loaded=response_payload.get("rows_loaded"),
            started_at=response_payload.get("started_at"),
            finished_at=response_payload.get("finished_at"),
            instantiation_candidate_scn=response_payload.get("instantiation_candidate_scn"),
            raw_output=response_payload.get("raw_output"),
            error_code=response_payload.get("error_code"),
            error_message=response_payload.get("error_message"),
            request_artifact=str(request_path),
            response_artifact=str(response_path),
        )

    def _build_command(
        self,
        request_path: Path,
        response_path: Path,
    ) -> list[str]:
        rendered = self.script_command.format(
            request=str(request_path),
            response=str(response_path),
        )

        if os.name == "nt":
            tokens = shlex.split(rendered, posix=False)
            return [self._strip_wrapping_quotes(token) for token in tokens]

        return shlex.split(rendered, posix=True)

    @staticmethod
    def _strip_wrapping_quotes(token: str) -> str:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}:
            return token[1:-1]
        return token