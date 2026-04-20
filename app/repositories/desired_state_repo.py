from __future__ import annotations

import json
from pathlib import Path

from app.models.enums import LoadMethod, ReplicationMode
from app.models.registry import DesiredTableConfig


class DesiredStateRepositoryError(Exception):
    pass


class DesiredStateRepository:
    def load_snapshot(
        self,
        path: str | Path,
    ) -> tuple[str | None, dict[str, object], list[DesiredTableConfig]]:
        snapshot_path = Path(path)
        if not snapshot_path.exists():
            raise DesiredStateRepositoryError(f"Snapshot file not found: {snapshot_path}")

        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise DesiredStateRepositoryError("Snapshot top-level structure must be object")

        environment = raw.get("environment")
        revision = raw.get("revision", {})
        tables = raw.get("tables", [])

        if not isinstance(tables, list):
            raise DesiredStateRepositoryError("'tables' must be a list")

        result: list[DesiredTableConfig] = []

        for idx, item in enumerate(tables, start=1):
            if not isinstance(item, dict):
                raise DesiredStateRepositoryError(f"tables[{idx}] must be an object")

            result.append(
                DesiredTableConfig(
                    source_system=str(item["source_system"]),
                    source_pdb=item.get("source_pdb"),
                    source_schema=str(item["source_schema"]).upper(),
                    source_table=str(item["source_table"]).upper(),
                    target_system=str(item["target_system"]),
                    target_pdb=item.get("target_pdb"),
                    target_schema=str(item["target_schema"]).upper(),
                    target_table=str(item["target_table"]).upper(),
                    desired_enabled=bool(item["desired_enabled"]),
                    desired_replication_mode=ReplicationMode(item["desired_replication_mode"]),
                    desired_extract_group=item.get("desired_extract_group"),
                    desired_replicat_group=item.get("desired_replicat_group"),
                    desired_load_method=(
                        LoadMethod(item["desired_load_method"])
                        if item.get("desired_load_method")
                        else None
                    ),
                    desired_priority=item.get("desired_priority"),
                    desired_size_class=item.get("desired_size_class"),
                    primary_key=tuple(item.get("primary_key", [])),
                    metadata_file=item.get("metadata_file"),
                )
            )

        return environment, revision, result