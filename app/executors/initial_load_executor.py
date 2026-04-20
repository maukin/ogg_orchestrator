from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timezone
import json

from app.models.initial_load import InitialLoadCommand
from app.models.initial_load_result import InitialLoadExecutionResult


class InitialLoadExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        commands: list[InitialLoadCommand],
        artifacts_dir: str | Path,
    ) -> InitialLoadExecutionResult:
        raise NotImplementedError


class DryRunInitialLoadExecutor(InitialLoadExecutor):
    def execute(
        self,
        commands: list[InitialLoadCommand],
        artifacts_dir: str | Path,
    ) -> InitialLoadExecutionResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        payload = [
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
                "mode": c.mode,
                "reason": c.reason,
            }
            for c in commands
        ]

        request_path = out_dir / "initial_load_commands.json"
        request_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        now = datetime.now(timezone.utc).isoformat()
        result_payload = {
            "success": True,
            "executed_count": len(commands),
            "skipped_count": 0,
            "load_batch_id": f"dryrun_{len(commands)}",
            "rows_loaded": 0,
            "started_at": now,
            "finished_at": now,
            "instantiation_candidate_scn": None,
            "raw_output": "Dry-run initial load completed.",
            "error_code": None,
            "error_message": None,
            "request_artifact": str(request_path),
            "response_artifact": str(out_dir / "initial_load_result.json"),
        }

        response_path = out_dir / "initial_load_result.json"
        response_path.write_text(
            json.dumps(result_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return InitialLoadExecutionResult(
            success=True,
            executed_count=len(commands),
            skipped_count=0,
            load_batch_id=result_payload["load_batch_id"],
            rows_loaded=0,
            started_at=now,
            finished_at=now,
            instantiation_candidate_scn=None,
            raw_output="Dry-run initial load completed.",
            error_code=None,
            error_message=None,
            request_artifact=str(request_path),
            response_artifact=str(response_path),
        )


class FileOnlyInitialLoadExecutor(InitialLoadExecutor):
    def execute(
        self,
        commands: list[InitialLoadCommand],
        artifacts_dir: str | Path,
    ) -> InitialLoadExecutionResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        payload = [
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
                "mode": c.mode,
                "reason": c.reason,
            }
            for c in commands
        ]

        request_path = out_dir / "initial_load_commands.json"
        request_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        now = datetime.now(timezone.utc).isoformat()
        response_path = out_dir / "initial_load_result.json"
        response_payload = {
            "success": True,
            "executed_count": len(commands),
            "skipped_count": 0,
            "load_batch_id": f"fileonly_{len(commands)}",
            "rows_loaded": None,
            "started_at": now,
            "finished_at": now,
            "instantiation_candidate_scn": None,
            "raw_output": "File-only initial load contract artifact created.",
            "error_code": None,
            "error_message": None,
            "request_artifact": str(request_path),
            "response_artifact": str(response_path),
        }
        response_path.write_text(
            json.dumps(response_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return InitialLoadExecutionResult(
            success=True,
            executed_count=len(commands),
            skipped_count=0,
            load_batch_id=response_payload["load_batch_id"],
            rows_loaded=None,
            started_at=now,
            finished_at=now,
            instantiation_candidate_scn=None,
            raw_output=response_payload["raw_output"],
            error_code=None,
            error_message=None,
            request_artifact=str(request_path),
            response_artifact=str(response_path),
        )