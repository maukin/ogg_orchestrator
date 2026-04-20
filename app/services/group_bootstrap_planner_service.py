from __future__ import annotations

from app.models.deployment import DeploymentAction
from app.models.group_bootstrap import GroupBootstrapRequest
from app.models.groups import GroupConfig
from app.models.registry import DesiredTableConfig
from app.services.ogg_base_config_factory import (
    ExtractBaseConfigParams,
    OGGBaseConfigFactory,
    ReplicatBaseConfigParams,
)


class GroupBootstrapPlannerService:
    def __init__(
        self,
        config_factory: OGGBaseConfigFactory,
        extract_credential_alias: str,
        replicat_credential_alias: str,
        extract_credential_domain: str | None = None,
        replicat_credential_domain: str | None = None,
        default_trail_name: str = "lt",
        default_extract_integrated: bool = True,
    ):
        self.config_factory = config_factory
        self.extract_credential_alias = extract_credential_alias
        self.replicat_credential_alias = replicat_credential_alias
        self.extract_credential_domain = extract_credential_domain
        self.replicat_credential_domain = replicat_credential_domain
        self.default_trail_name = default_trail_name
        self.default_extract_integrated = default_extract_integrated

    def build_bootstrap_actions(
        self,
        environment_name: str,
        desired_configs: list[DesiredTableConfig],
        available_groups: list[GroupConfig],
    ) -> list[DeploymentAction]:
        existing_extract_groups = {
            g.group_name for g in available_groups if g.group_type == "extract"
        }
        existing_replicat_groups = {
            g.group_name for g in available_groups if g.group_type == "replicat"
        }

        actions: list[DeploymentAction] = []
        planned_extracts: set[str] = set()
        planned_replicats: set[str] = set()

        for cfg in desired_configs:
            if not cfg.desired_enabled:
                continue

            requires_replicat = cfg.desired_replication_mode != "INITIAL_LOAD_ONLY"

            if cfg.desired_extract_group and cfg.desired_extract_group not in existing_extract_groups:
                if cfg.desired_extract_group not in planned_extracts:
                    req = self._build_extract_request(environment_name, cfg)
                    actions.append(
                        DeploymentAction(
                            action_type="BOOTSTRAP_EXTRACT_GROUP",
                            table_id=None,
                            group_name=req.group_name,
                            payload={
                                "group_name": req.group_name,
                                "group_type": req.group_type,
                                "environment_name": req.environment_name,
                                "source_system": req.source_system,
                                "target_system": req.target_system,
                                "credential_alias": req.credential_alias,
                                "credential_domain": req.credential_domain,
                                "trail_name": req.trail_name,
                                "mode": req.mode,
                                "base_config_lines": req.base_config_lines,
                                "notes": req.notes,
                            },
                        )
                    )
                    planned_extracts.add(cfg.desired_extract_group)

            if (
                requires_replicat
                and cfg.desired_replicat_group
                and cfg.desired_replicat_group not in existing_replicat_groups
            ):
                if cfg.desired_replicat_group not in planned_replicats:
                    req = self._build_replicat_request(environment_name, cfg)
                    actions.append(
                        DeploymentAction(
                            action_type="BOOTSTRAP_REPLICAT_GROUP",
                            table_id=None,
                            group_name=req.group_name,
                            payload={
                                "group_name": req.group_name,
                                "group_type": req.group_type,
                                "environment_name": req.environment_name,
                                "source_system": req.source_system,
                                "target_system": req.target_system,
                                "credential_alias": req.credential_alias,
                                "credential_domain": req.credential_domain,
                                "trail_name": req.trail_name,
                                "mode": req.mode,
                                "base_config_lines": req.base_config_lines,
                                "notes": req.notes,
                            },
                        )
                    )
                    planned_replicats.add(cfg.desired_replicat_group)

        return actions

    def _build_extract_request(
        self,
        environment_name: str,
        cfg: DesiredTableConfig,
    ) -> GroupBootstrapRequest:
        base_config_lines = self.config_factory.build_extract_base_config(
            ExtractBaseConfigParams(
                group_name=cfg.desired_extract_group,
                credential_alias=self.extract_credential_alias,
                trail_name=self.default_trail_name,
                integrated=self.default_extract_integrated,
            )
        )
        return GroupBootstrapRequest(
            group_name=cfg.desired_extract_group,
            group_type="extract",
            environment_name=environment_name,
            source_system=cfg.source_system,
            target_system=cfg.target_system,
            credential_alias=self.extract_credential_alias,
            credential_domain=self.extract_credential_domain,
            trail_name=self.default_trail_name,
            mode="INTEGRATED" if self.default_extract_integrated else "CLASSIC",
            base_config_lines=base_config_lines,
            notes="Auto-bootstrap extract group from desired state.",
        )

    def _build_replicat_request(
        self,
        environment_name: str,
        cfg: DesiredTableConfig,
    ) -> GroupBootstrapRequest:
        base_config_lines = self.config_factory.build_replicat_base_config(
            ReplicatBaseConfigParams(
                group_name=cfg.desired_replicat_group,
                credential_alias=self.replicat_credential_alias,
            )
        )
        return GroupBootstrapRequest(
            group_name=cfg.desired_replicat_group,
            group_type="replicat",
            environment_name=environment_name,
            source_system=cfg.source_system,
            target_system=cfg.target_system,
            credential_alias=self.replicat_credential_alias,
            credential_domain=self.replicat_credential_domain,
            trail_name=self.default_trail_name,
            mode="NONINTEGRATED",
            base_config_lines=base_config_lines,
            notes="Auto-bootstrap replicat group from desired state.",
        )
