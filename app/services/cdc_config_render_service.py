from __future__ import annotations

from collections import defaultdict

from app.models.cdc_config import CDCConfigBundle, ExtractGroupConfig, ReplicatGroupConfig
from app.models.registry import DesiredTableConfig, TableRegistryRecord
from app.models.enums import ReplicationMode


class CDCConfigRenderService:
    def build_bundle(
        self,
        desired_configs: list[DesiredTableConfig],
        registry_records: list[TableRegistryRecord] | None = None,
    ) -> CDCConfigBundle:
        extract_groups: dict[str, list[str]] = defaultdict(list)
        replicat_groups: dict[str, list[str]] = defaultdict(list)

        enabled_configs = [cfg for cfg in desired_configs if cfg.desired_enabled]
        registry_by_table_id = {
            record.table_id: record
            for record in (registry_records or [])
        }

        for cfg in sorted(enabled_configs, key=lambda x: x.table_id):
            if cfg.desired_extract_group:
                extract_groups[cfg.desired_extract_group].append(
                    f"TABLE {cfg.source_schema}.{cfg.source_table};"
                )

            if (
                cfg.desired_replicat_group
                and cfg.desired_replication_mode != ReplicationMode.INITIAL_LOAD_ONLY
            ):
                record = registry_by_table_id.get(cfg.table_id)
                filter_scn = self._resolve_replicat_filter_scn(cfg, record)

                replicat_groups[cfg.desired_replicat_group].append(
                    self._build_replicat_map_line(
                        source_schema=cfg.source_schema,
                        source_table=cfg.source_table,
                        target_schema=cfg.target_schema,
                        target_table=cfg.target_table,
                        filter_scn=filter_scn,
                    )
                )

        bundle = CDCConfigBundle(
            extract_groups=[
                ExtractGroupConfig(group_name=group_name, lines=lines)
                for group_name, lines in sorted(extract_groups.items())
            ],
            replicat_groups=[
                ReplicatGroupConfig(group_name=group_name, lines=lines)
                for group_name, lines in sorted(replicat_groups.items())
            ],
        )
        return bundle

    @staticmethod
    def _build_replicat_map_line(
        *,
        source_schema: str,
        source_table: str,
        target_schema: str,
        target_table: str,
        filter_scn: int | None,
    ) -> str:
        if filter_scn is not None:
            return (
                f"MAP {source_schema}.{source_table}, "
                f"TARGET {target_schema}.{target_table}, "
                f"FILTER ( @GETENV('TRANSACTION', 'CSN') > {filter_scn} );"
            )

        return (
            f"MAP {source_schema}.{source_table}, "
            f"TARGET {target_schema}.{target_table};"
        )

    @staticmethod
    def _resolve_replicat_filter_scn(
        cfg: DesiredTableConfig,
        record: TableRegistryRecord | None,
    ) -> int | None:
        if record is None:
            return None

        if cfg.desired_replication_mode == ReplicationMode.CDC_ONLY:
            return record.registration_scn

        if cfg.desired_replication_mode == ReplicationMode.INITIAL_PLUS_CDC:
            return record.instantiation_scn or record.instantiation_candidate_scn

        return None