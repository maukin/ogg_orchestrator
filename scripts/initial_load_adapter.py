from __future__ import annotations

import json
import sys
from pathlib import Path

from app.integrations.initial_load_backends import (
    BackendCommand,
    InitialLoadBackendDispatcher,
)
from app.utils.initial_load_backend_artifacts import (
    write_initial_load_backend_context,
    write_initial_load_backend_result,
)


def _to_command(payload: dict) -> BackendCommand:
    return BackendCommand(
        table_id=payload["table_id"],
        source_schema=payload["source_schema"],
        source_table=payload["source_table"],
        target_schema=payload["target_schema"],
        target_table=payload["target_table"],
        load_method=payload.get("load_method"),
        extract_group=payload.get("extract_group"),
        replicat_group=payload.get("replicat_group"),
        registration_scn=payload.get("registration_scn"),
        metadata_file=payload.get("metadata_file"),
        command_type=payload["command_type"],
        command_text=payload["command_text"],
        action=payload["action"],
        reason=payload.get("reason"),
    )


def _write_response(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/initial_load_adapter.py <request.json> <response.json>")
        return 2

    request_path = Path(sys.argv[1])
    response_path = Path(sys.argv[2])
    artifacts_dir = response_path.parent

    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    commands_payload = request_payload.get("commands", [])
    commands = [_to_command(item) for item in commands_payload]

    if not commands:
        _write_response(
            response_path,
            {
                "success": True,
                "executed_count": 0,
                "skipped_count": 0,
                "load_batch_id": None,
                "rows_loaded": None,
                "started_at": None,
                "finished_at": None,
                "instantiation_candidate_scn": None,
                "raw_output": None,
                "error_code": None,
                "error_message": None,
                "backend_names": [],
            },
        )
        return 0

    dispatcher = InitialLoadBackendDispatcher()

    executed_count = 0
    total_rows_loaded = 0
    any_rows_loaded = False
    raw_outputs: list[str] = []
    backend_names: list[str] = []

    last_load_batch_id: str | None = None
    last_instantiation_candidate_scn: int | None = None
    started_at: str | None = None
    finished_at: str | None = None

    last_backend_context: dict | None = None
    last_backend_result_payload: dict | None = None

    for command in commands:
        backend = dispatcher.get_backend(command.load_method)
        backend_name = backend.__class__.__name__
        backend_names.append(backend_name)

        backend_context = {
            "selected_backend": backend_name,
            "load_method": command.load_method,
            "table_id": command.table_id,
            "source_schema": command.source_schema,
            "source_table": command.source_table,
            "target_schema": command.target_schema,
            "target_table": command.target_table,
            "extract_group": command.extract_group,
            "replicat_group": command.replicat_group,
            "registration_scn": command.registration_scn,
            "metadata_file": command.metadata_file,
            "command_type": command.command_type,
            "command_text": command.command_text,
            "action": command.action,
            "reason": command.reason,
        }
        last_backend_context = backend_context
        write_initial_load_backend_context(
            backend_context,
            artifacts_dir=artifacts_dir,
        )

        result = backend.run(command)

        backend_result_payload = {
            "selected_backend": backend_name,
            "success": result.success,
            "load_batch_id": result.load_batch_id,
            "rows_loaded": result.rows_loaded,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "instantiation_candidate_scn": result.instantiation_candidate_scn,
            "raw_output": result.raw_output,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "resolved_flashback_scn": result.resolved_flashback_scn,
            "source_rowcount": result.source_rowcount,
            "source_rowcount_as_of_scn": result.source_rowcount_as_of_scn,
            "target_rowcount_before": result.target_rowcount_before,
            "target_rowcount_after": result.target_rowcount_after,
            "verification_passed": result.verification_passed,
            "stdout_text": result.stdout_text,
            "stderr_text": result.stderr_text,
        }
        last_backend_result_payload = backend_result_payload
        write_initial_load_backend_result(
            backend_result_payload,
            artifacts_dir=artifacts_dir,
        )

        if result.stdout_text is not None:
            (artifacts_dir / "initial_load_stdout.log").write_text(
                result.stdout_text,
                encoding="utf-8",
            )

        if result.stderr_text is not None:
            (artifacts_dir / "initial_load_stderr.log").write_text(
                result.stderr_text,
                encoding="utf-8",
            )

        if started_at is None:
            started_at = result.started_at
        finished_at = result.finished_at

        if result.raw_output:
            raw_outputs.append(result.raw_output)

        if result.rows_loaded is not None:
            total_rows_loaded += result.rows_loaded
            any_rows_loaded = True

        if result.load_batch_id is not None:
            last_load_batch_id = result.load_batch_id

        if result.instantiation_candidate_scn is not None:
            last_instantiation_candidate_scn = result.instantiation_candidate_scn

        if not result.success:
            _write_response(
                response_path,
                {
                    "success": False,
                    "executed_count": executed_count,
                    "skipped_count": 0,
                    "load_batch_id": last_load_batch_id,
                    "rows_loaded": total_rows_loaded if any_rows_loaded else None,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "instantiation_candidate_scn": last_instantiation_candidate_scn,
                    "raw_output": "\n".join(raw_outputs) if raw_outputs else result.raw_output,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                    "backend_names": backend_names,
                    "last_backend_context": last_backend_context,
                    "last_backend_result": last_backend_result_payload,
                },
            )
            return 1

        executed_count += 1

    _write_response(
        response_path,
        {
            "success": True,
            "executed_count": executed_count,
            "skipped_count": 0,
            "load_batch_id": last_load_batch_id,
            "rows_loaded": total_rows_loaded if any_rows_loaded else None,
            "started_at": started_at,
            "finished_at": finished_at,
            "instantiation_candidate_scn": last_instantiation_candidate_scn,
            "raw_output": "\n".join(raw_outputs) if raw_outputs else None,
            "error_code": None,
            "error_message": None,
            "backend_names": backend_names,
            "last_backend_context": last_backend_context,
            "last_backend_result": last_backend_result_payload,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())