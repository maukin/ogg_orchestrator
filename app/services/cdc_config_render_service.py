from __future__ import annotations

from collections import defaultdict

from app.models.cdc_config import CDCConfigBundle, ExtractGroupConfig, ReplicatGroupConfig
from app.models.registry import DesiredTableConfig


class CDCConfigRenderService:
    def build_bundle(
        self,
        desired_configs: list[DesiredTableConfig],
    ) -> CDCConfigBundle:
        extract_groups: dict[str, list[str]] = defaultdict(list)
        replicat_groups: dict[str, list[str]] = defaultdict(list)

        enabled_configs = [cfg for cfg in desired_configs if cfg.desired_enabled]

        for cfg in sorted(enabled_configs, key=lambda x: x.table_id):
            if cfg.desired_extract_group:
                extract_groups[cfg.desired_extract_group].append(
                    f"TABLE {cfg.source_schema}.{cfg.source_table};"
                )

            if (
                cfg.desired_replicat_group
                and cfg.desired_replication_mode.value != "INITIAL_LOAD_ONLY"
            ):
                replicat_groups[cfg.desired_replicat_group].append(
                    f"MAP {cfg.source_schema}.{cfg.source_table}, TARGET {cfg.target_schema}.{cfg.target_table};"
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
