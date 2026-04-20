from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import json

from app.models.extract import ExtractAttachCommand
from app.models.executor import ExecutorResult


class ExtractAttachExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        commands: list[ExtractAttachCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        raise NotImplementedError


class DryRunExtractAttachExecutor(ExtractAttachExecutor):
    def execute(
        self,
        commands: list[ExtractAttachCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        sql_lines: list[str] = []
        json_rows: list[dict[str, object]] = []

        for cmd in commands:
            sql_lines.append(f"-- {cmd.table_id}")
            sql_lines.append("-- MODE: DRY_RUN")
            sql_lines.append(cmd.command_text)
            sql_lines.append("")

            json_rows.append(
                {
                    "table_id": cmd.table_id,
                    "extract_group": cmd.extract_group,
                    "source_schema": cmd.source_schema,
                    "source_table": cmd.source_table,
                    "command_type": cmd.command_type,
                    "command_text": cmd.command_text,
                    "mode": "DRY_RUN",
                    "reason": cmd.reason,
                }
            )

        (out_dir / "extract_attach_commands.sql").write_text(
            "\n".join(sql_lines).strip() + ("\n" if sql_lines else ""),
            encoding="utf-8",
        )
        (out_dir / "extract_attach_commands.json").write_text(
            json.dumps(json_rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return ExecutorResult(
            success=True,
            executed_count=len(commands),
            skipped_count=0,
            raw_output="Dry-run extract attach completed.",
            error_code=None,
            error_message=None,
            http_status=None,
            request_artifact=str(out_dir / "extract_attach_commands.sql"),
            response_artifact=str(out_dir / "extract_attach_commands.json"),
        )


class FileOnlyExtractAttachExecutor(ExtractAttachExecutor):
    def execute(
        self,
        commands: list[ExtractAttachCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        sql_lines: list[str] = []
        json_rows: list[dict[str, object]] = []

        for cmd in commands:
            sql_lines.append(f"-- {cmd.table_id}")
            sql_lines.append("-- MODE: FILE_ONLY")
            sql_lines.append(cmd.command_text)
            sql_lines.append("")

            json_rows.append(
                {
                    "table_id": cmd.table_id,
                    "extract_group": cmd.extract_group,
                    "source_schema": cmd.source_schema,
                    "source_table": cmd.source_table,
                    "command_type": cmd.command_type,
                    "command_text": cmd.command_text,
                    "mode": "FILE_ONLY",
                    "reason": cmd.reason,
                }
            )

        (out_dir / "extract_attach_commands.sql").write_text(
            "\n".join(sql_lines).strip() + ("\n" if sql_lines else ""),
            encoding="utf-8",
        )
        (out_dir / "extract_attach_commands.json").write_text(
            json.dumps(json_rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return ExecutorResult(
            success=True,
            executed_count=len(commands),
            skipped_count=0,
            raw_output="File-only extract attach completed.",
            error_code=None,
            error_message=None,
            http_status=None,
            request_artifact=str(out_dir / "extract_attach_commands.sql"),
            response_artifact=str(out_dir / "extract_attach_commands.json"),
        )