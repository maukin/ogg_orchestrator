from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json

from app.models.registry import DesiredTableConfig


class DesiredStateSnapshotBuilder:
    def build_snapshot(
        self,
        environment: str,
        configs: list[DesiredTableConfig],
        git_commit_sha: str | None,
        git_branch: str | None,
        source_dir: str,
    ) -> dict[str, object]:
        sorted_configs = sorted(
            configs,
            key=lambda x: (
                x.source_system,
                x.source_pdb or "",
                x.source_schema,
                x.source_table,
                x.target_system,
                x.target_pdb or "",
                x.target_schema,
                x.target_table,
            ),
        )

        tables = []
        for cfg in sorted_configs:
            row = asdict(cfg)
            row["table_id"] = cfg.table_id
            row["primary_key"] = list(cfg.primary_key)
            if cfg.desired_load_method is not None:
                row["desired_load_method"] = cfg.desired_load_method.value
            if cfg.desired_replication_mode is not None:
                row["desired_replication_mode"] = cfg.desired_replication_mode.value
            tables.append(row)

        return {
            "environment": environment,
            "revision": {
                "git_commit_sha": git_commit_sha,
                "git_branch": git_branch,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_dir": source_dir,
            },
            "tables": tables,
        }

    def write_snapshot(self, snapshot: dict[str, object], output_path: str | Path) -> None:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )