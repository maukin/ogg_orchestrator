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

    @staticmethod
    def _debug(msg: str) -> None:
        print(f"[initial_load_executor] {msg}", flush=True)

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

        self._debug(f"execute started, commands_count={len(commands)}, artifacts_dir={out_dir}")

        for idx, c in enumerate(commands, start=1):
            self._debug(
                f"command[{idx}] "
                f"table_id={c.table_id}, "
                f"source={c.source_schema}.{c.source_table}, "
                f"target={c.target_schema}.{c.target_table}, "
                f"load_method={c.load_method}, "
                f"extract_group={c.extract_group}, "
                f"replicat_group={c.replicat_group}, "
                f"registration_scn={c.registration_scn}, "
                f"action={c.action}, "
                f"reason={c.reason}"
            )

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
        self._debug(f"request written to {request_path}")

        command = self._build_command(
            request_path=request_path,
            response_path=response_path,
        )

        self._debug(f"script_command template={self.script_command}")
        self._debug(f"rendered command={command}")
        self._debug(f"response_path={response_path}")
        self._debug(f"stdout_path={stdout_path}")
        self._debug(f"stderr_path={stderr_path}")
        self._debug(f"timeout_sec={self.timeout_sec}")

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            self._debug(f"script timeout after {self.timeout_sec} seconds")

            stdout_path.write_text(exc.stdout or "", encoding="utf-8")
            stderr_path.write_text(exc.stderr or "", encoding="utf-8")

            self._debug(f"timeout stdout saved to {stdout_path}")
            self._debug(f"timeout stderr saved to {stderr_path}")

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
            self._debug(f"script executable not found: {exc}")

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

        self._debug(f"process finished with returncode={process.returncode}")
        if process.stdout:
            self._debug(f"stdout:\n{process.stdout}")
        else:
            self._debug("stdout is empty")

        if process.stderr:
            self._debug(f"stderr:\n{process.stderr}")
        else:
            self._debug("stderr is empty")

        if process.returncode != 0:
            self._debug("script returned non-zero exit code")
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
            self._debug("response file is missing after successful script completion")
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

        self._debug(f"response file found: {response_path}")
        response_payload = json.loads(response_path.read_text(encoding="utf-8"))
        self._debug(
            "response payload summary: "
            f"success={response_payload.get('success')}, "
            f"executed_count={response_payload.get('executed_count')}, "
            f"skipped_count={response_payload.get('skipped_count')}, "
            f"load_batch_id={response_payload.get('load_batch_id')}, "
            f"rows_loaded={response_payload.get('rows_loaded')}, "
            f"instantiation_candidate_scn={response_payload.get('instantiation_candidate_scn')}, "
            f"error_code={response_payload.get('error_code')}, "
            f"error_message={response_payload.get('error_message')}"
        )

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

        self._debug(f"_build_command rendered={rendered}")

        if os.name == "nt":
            tokens = shlex.split(rendered, posix=False)
            result = [self._strip_wrapping_quotes(token) for token in tokens]
            self._debug(f"_build_command windows tokens={result}")
            return result

        result = shlex.split(rendered, posix=True)
        self._debug(f"_build_command posix tokens={result}")
        return result

    @staticmethod
    def _strip_wrapping_quotes(token: str) -> str:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}:
            return token[1:-1]
        return token