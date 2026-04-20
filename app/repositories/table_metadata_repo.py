from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.enums import LoadMethod, ReplicationMode
from app.models.registry import DesiredTableConfig


class TableMetadataRepositoryError(Exception):
    pass


class TableMetadataRepository:
    def load_from_directory(self, root_dir: str | Path) -> list[DesiredTableConfig]:
        root = Path(root_dir)
        if not root.exists():
            raise TableMetadataRepositoryError(f"Metadata directory not found: {root}")

        json_files = sorted(root.rglob("*.json"))
        if not json_files:
            raise TableMetadataRepositoryError(f"No JSON files found in: {root}")

        result: list[DesiredTableConfig] = []
        for path in json_files:
            raw = self._load_json(path)
            cfg = self._parse_table_metadata(raw=raw, path=path, root=root)
            if cfg is not None:
                result.append(cfg)

        self._validate_duplicates(result)
        return result

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TableMetadataRepositoryError(f"Invalid JSON in {path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise TableMetadataRepositoryError(f"Top-level JSON must be object in {path}")

        return raw

    def _parse_table_metadata(
        self,
        raw: dict[str, Any],
        path: Path,
        root: Path,
    ) -> DesiredTableConfig | None:
        meta = raw.get("meta")
        if not isinstance(meta, dict):
            raise TableMetadataRepositoryError(f"'meta' block is missing or invalid in {path}")

        cdc_cfg = self._extract_cdc_config(
            meta=meta,
            load_params=raw.get("load_params"),
            path=path,
        )
        if cdc_cfg is None:
            return None

        table_name = self._required_str(raw.get("table_name") or meta.get("table_name"), "table_name", path)
        schema_name = self._required_str(raw.get("schema") or meta.get("tgt_system_schema"), "schema", path)

        source_schema = str(meta.get("src_system_schema") or schema_name).strip().upper()
        target_schema = str(meta.get("tgt_system_schema") or schema_name).strip().upper()

        primary_key = tuple(
            str(col).strip().upper()
            for col in raw.get("primary_key", [])
            if str(col).strip()
        )

        relative_path = str(path.relative_to(root.parent)) if root.parent in path.parents else str(path)

        return DesiredTableConfig(
            source_system=cdc_cfg["source_system"],
            source_pdb=cdc_cfg["source_pdb"],
            source_schema=source_schema,
            source_table=table_name.upper(),
            target_system=cdc_cfg["target_system"],
            target_pdb=cdc_cfg["target_pdb"],
            target_schema=target_schema,
            target_table=table_name.upper(),
            desired_enabled=cdc_cfg["enabled"],
            desired_replication_mode=ReplicationMode(cdc_cfg["replication_mode"]),
            desired_extract_group=cdc_cfg["extract_group"],
            desired_replicat_group=cdc_cfg["replicat_group"],
            desired_load_method=(
                LoadMethod(cdc_cfg["load_method"]) if cdc_cfg["load_method"] else None
            ),
            desired_priority=cdc_cfg["priority"],
            desired_size_class=cdc_cfg["size_class"],
            primary_key=primary_key,
            metadata_file=relative_path,
        )

    def _extract_cdc_config(
        self,
        meta: dict[str, Any],
        load_params: Any,
        path: Path,
    ) -> dict[str, Any] | None:
        cdc = meta.get("cdc")

        if isinstance(cdc, dict):
            return {
                "enabled": bool(cdc.get("enabled", False)),
                "replication_mode": str(cdc.get("replication_mode", "INITIAL_PLUS_CDC")).strip().upper(),
                "source_system": self._defaulted_str(cdc.get("source_system"), "UNKNOWN_SRC"),
                "source_pdb": self._nullable_str(cdc.get("source_pdb")),
                "target_system": self._defaulted_str(cdc.get("target_system"), "UNKNOWN_TGT"),
                "target_pdb": self._nullable_str(cdc.get("target_pdb")),
                "extract_group": self._nullable_str(cdc.get("extract_group")),
                "replicat_group": self._nullable_str(cdc.get("replicat_group")),
                "load_method": self._nullable_upper(cdc.get("load_method")),
                "priority": self._nullable_upper(cdc.get("priority")),
                "size_class": self._nullable_upper(cdc.get("size_class")),
            }

        legacy_cdc_flag = meta.get("cdc_flag")
        legacy_enabled = bool(legacy_cdc_flag) if legacy_cdc_flag is not None else False

        extract_group = None
        replicat_group = None

        if isinstance(load_params, list):
            for item in load_params:
                if not isinstance(item, dict):
                    continue
                if str(item.get("comment", "")).strip().lower() != "goldengate":
                    continue

                param = str(item.get("param", "")).strip().upper()
                value = self._nullable_str(item.get("value"))

                if param == "EXTRACT_GROUP":
                    extract_group = value
                elif param == "REPLICAT_GROUP":
                    replicat_group = value

        if legacy_cdc_flag is None and extract_group is None and replicat_group is None:
            return None

        if legacy_enabled and (extract_group is None or replicat_group is None):
            raise TableMetadataRepositoryError(
                f"Legacy CDC config is incomplete in {path}: extract/replicat group is missing"
            )

        return {
            "enabled": legacy_enabled,
            "replication_mode": "INITIAL_PLUS_CDC",
            "source_system": "UNKNOWN_SRC",
            "source_pdb": None,
            "target_system": "UNKNOWN_TGT",
            "target_pdb": None,
            "extract_group": extract_group,
            "replicat_group": replicat_group,
            "load_method": "DATAPUMP" if legacy_enabled else None,
            "priority": None,
            "size_class": None,
        }

    @staticmethod
    def _required_str(value: Any, field_name: str, path: Path) -> str:
        if value is None or str(value).strip() == "":
            raise TableMetadataRepositoryError(f"{field_name} is missing in {path}")
        return str(value).strip()

    @staticmethod
    def _nullable_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _nullable_upper(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip().upper()
        return text or None

    @staticmethod
    def _defaulted_str(value: Any, default: str) -> str:
        if value is None or str(value).strip() == "":
            return default
        return str(value).strip()

    @staticmethod
    def _validate_duplicates(configs: list[DesiredTableConfig]) -> None:
        seen: set[str] = set()
        duplicates: list[str] = []

        for cfg in configs:
            if cfg.table_id in seen:
                duplicates.append(cfg.table_id)
            seen.add(cfg.table_id)

        if duplicates:
            raise TableMetadataRepositoryError(
                f"Duplicate table_id values found: {duplicates}"
            )