from __future__ import annotations

from dataclasses import asdict

from app.models.deployment import DeploymentAction, DeploymentPlan
from app.models.enums import TableState
from app.models.registry import DesiredTableConfig, TableRegistryRecord
from app.utils.plan_actions import action_type_for_replication_mode


class PlannerService:
    def build_plan(
        self,
        deployment_id: str,
        environment_name: str,
        git_branch: str | None,
        git_commit_sha: str | None,
        pipeline_id: str | None,
        desired_configs: list[DesiredTableConfig],
        current_registry: list[TableRegistryRecord],
    ) -> DeploymentPlan:
        plan = DeploymentPlan(
            deployment_id=deployment_id,
            environment_name=environment_name,
            git_branch=git_branch,
            git_commit_sha=git_commit_sha,
            pipeline_id=pipeline_id,
        )

        desired_by_id = {cfg.table_id: cfg for cfg in desired_configs}
        current_by_id = {rec.table_id: rec for rec in current_registry}

        desired_ids = set(desired_by_id)
        current_ids = set(current_by_id)

        new_ids = desired_ids - current_ids
        removed_ids = current_ids - desired_ids
        common_ids = desired_ids & current_ids

        for table_id in sorted(new_ids):
            cfg = desired_by_id[table_id]

            payload = asdict(cfg)
            payload["table_id"] = cfg.table_id

            plan.actions.append(
                DeploymentAction(
                    action_type="REGISTER_NEW_TABLE",
                    table_id=cfg.table_id,
                    group_name=cfg.desired_replicat_group,
                    payload=payload,
                )
            )

            if cfg.desired_enabled:
                action_type = action_type_for_replication_mode(cfg.desired_replication_mode)
                plan.actions.append(
                    DeploymentAction(
                        action_type=action_type,
                        table_id=table_id,
                        group_name=cfg.desired_replicat_group,
                        payload={
                            "source_schema": cfg.source_schema,
                            "source_table": cfg.source_table,
                            "target_schema": cfg.target_schema,
                            "target_table": cfg.target_table,
                            "desired_extract_group": cfg.desired_extract_group,
                            "desired_replicat_group": cfg.desired_replicat_group,
                            "desired_load_method": (
                                cfg.desired_load_method.value if cfg.desired_load_method else None
                            ),
                            "desired_replication_mode": cfg.desired_replication_mode.value,
                            "reason": "NEW_TABLE",
                        },
                    )
                )

        for table_id in sorted(removed_ids):
            rec = current_by_id[table_id]
            if rec.state != TableState.REMOVED:
                plan.actions.append(
                    DeploymentAction(
                        action_type="PLAN_REMOVE_TABLE",
                        table_id=table_id,
                        group_name=rec.actual_replicat_group,
                        payload={
                            "current_state": rec.state.value,
                            "actual_extract_group": rec.actual_extract_group,
                            "actual_replicat_group": rec.actual_replicat_group,
                        },
                    )
                )

        for table_id in sorted(common_ids):
            desired = desired_by_id[table_id]
            current = current_by_id[table_id]

            changes = self._detect_changes(desired, current)
            if changes:
                plan.actions.append(
                    DeploymentAction(
                        action_type="UPDATE_TABLE_DESIRED_STATE",
                        table_id=table_id,
                        group_name=desired.desired_replicat_group,
                        payload=changes,
                    )
                )

            if desired.desired_enabled and current.state == TableState.PLANNED:
                action_type = action_type_for_replication_mode(desired.desired_replication_mode)
                plan.actions.append(
                    DeploymentAction(
                        action_type=action_type,
                        table_id=table_id,
                        group_name=desired.desired_replicat_group,
                        payload={
                            "source_schema": desired.source_schema,
                            "source_table": desired.source_table,
                            "target_schema": desired.target_schema,
                            "target_table": desired.target_table,
                            "desired_extract_group": desired.desired_extract_group,
                            "desired_replicat_group": desired.desired_replicat_group,
                            "desired_load_method": (
                                desired.desired_load_method.value if desired.desired_load_method else None
                            ),
                            "desired_replication_mode": desired.desired_replication_mode.value,
                            "reason": "PLANNED_TABLE_RECOVERY",
                        },
                    )
                )

        return plan

    @staticmethod
    def _detect_changes(
        desired: DesiredTableConfig,
        current: TableRegistryRecord,
    ) -> dict[str, object]:
        changes: dict[str, object] = {}

        if current.desired_enabled != desired.desired_enabled:
            changes["desired_enabled"] = desired.desired_enabled

        if current.desired_extract_group != desired.desired_extract_group:
            changes["desired_extract_group"] = desired.desired_extract_group

        if current.desired_replicat_group != desired.desired_replicat_group:
            changes["desired_replicat_group"] = desired.desired_replicat_group

        current_load_method = (
            current.desired_load_method.value if current.desired_load_method else None
        )
        desired_load_method = (
            desired.desired_load_method.value if desired.desired_load_method else None
        )
        if current_load_method != desired_load_method:
            changes["desired_load_method"] = desired_load_method

        if current.desired_replication_mode.value != desired.desired_replication_mode.value:
            changes["desired_replication_mode"] = desired.desired_replication_mode.value

        if current.desired_priority != desired.desired_priority:
            changes["desired_priority"] = desired.desired_priority

        if current.desired_size_class != desired.desired_size_class:
            changes["desired_size_class"] = desired.desired_size_class

        if tuple(current.primary_key) != tuple(desired.primary_key):
            changes["primary_key"] = list(desired.primary_key)

        if current.metadata_file != desired.metadata_file:
            changes["metadata_file"] = desired.metadata_file

        if current.state == TableState.ERROR:
            changes["recovery_required"] = True

        return changes
