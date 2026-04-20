from __future__ import annotations

from app.models.enums import TableState
from app.models.reconciliation import (
    DeploymentReconciliationReport,
    TableReconciliationRow,
)
from app.models.registry import DesiredTableConfig, TableRegistryRecord


class ReconciliationService:
    def build_report(
        self,
        deployment_id: str,
        environment_name: str,
        desired_configs: list[DesiredTableConfig],
        current_registry: list[TableRegistryRecord],
        extract_probe_results: dict[str, object] | None = None,
        replicat_probe_results: dict[str, object] | None = None,
    ) -> DeploymentReconciliationReport:
        extract_probe_results = extract_probe_results or {}
        replicat_probe_results = replicat_probe_results or {}

        desired_by_id = {cfg.table_id: cfg for cfg in desired_configs}
        registry_by_id = {rec.table_id: rec for rec in current_registry}

        rows: list[TableReconciliationRow] = []

        for table_id in sorted(desired_by_id):
            desired = desired_by_id[table_id]
            registry = registry_by_id.get(table_id)

            notes: list[str] = []
            has_error = False
            is_blocked = False
            block_reason = None
            next_step = None

            if registry is None:
                notes.append("Table is present in desired state but missing in registry.")
                is_blocked = True
                block_reason = "NOT_REGISTERED"
                next_step = "REGISTER_NEW_TABLE"
                rows.append(
                    TableReconciliationRow(
                        table_id=table_id,
                        desired_enabled=desired.desired_enabled,
                        registry_state=None,
                        validation_status=None,
                        has_error=False,
                        is_blocked=is_blocked,
                        block_reason=block_reason,
                        next_recommended_step=next_step,
                        notes=notes,
                    )
                )
                continue

            registry_state = registry.state.value
            validation_status = registry.validation_status.value

            if registry.state == TableState.ERROR:
                has_error = True
                is_blocked = True
                block_reason = "TABLE_IN_ERROR"
                next_step = "REPLAN_ERROR_TABLE"
                notes.append("Registry state is ERROR.")

            extract_group = desired.desired_extract_group
            if extract_group and extract_group in extract_probe_results:
                probe_result = extract_probe_results[extract_group]
                if getattr(probe_result, "success", None) is False:
                    is_blocked = True
                    block_reason = f"EXTRACT_PROBE_FAILED:{extract_group}"
                    notes.append(
                        f"Extract probe failed for group {extract_group}: "
                        f"{getattr(probe_result, 'error_message', None)}"
                    )

            replicat_group = desired.desired_replicat_group
            if replicat_group and replicat_group in replicat_probe_results:
                probe_result = replicat_probe_results[replicat_group]
                if getattr(probe_result, "success", None) is False:
                    is_blocked = True
                    block_reason = f"REPLICAT_PROBE_FAILED:{replicat_group}"
                    notes.append(
                        f"Replicat probe failed for group {replicat_group}: "
                        f"{getattr(probe_result, 'error_message', None)}"
                    )

            if not desired.desired_enabled:
                next_step = None
                notes.append("Table is disabled in desired state.")
            elif not is_blocked:
                next_step = self._recommend_next_step(registry.state)
                if (
                    desired.desired_replication_mode.value == "INITIAL_LOAD_ONLY"
                    and registry.state == TableState.INSTANTIATED
                ):
                    next_step = None
                notes.append(
                    f"Replication mode is {desired.desired_replication_mode.value}."
                )

            if registry.desired_extract_group != desired.desired_extract_group:
                notes.append("Desired extract group differs from registry.")
            if registry.desired_replicat_group != desired.desired_replicat_group:
                notes.append("Desired replicat group differs from registry.")
            if tuple(registry.primary_key) != tuple(desired.primary_key):
                notes.append("Primary key differs between desired state and registry.")

            rows.append(
                TableReconciliationRow(
                    table_id=table_id,
                    desired_enabled=desired.desired_enabled,
                    registry_state=registry_state,
                    validation_status=validation_status,
                    has_error=has_error,
                    is_blocked=is_blocked,
                    block_reason=block_reason,
                    next_recommended_step=next_step,
                    notes=notes,
                )
            )

        return DeploymentReconciliationReport(
            deployment_id=deployment_id,
            environment_name=environment_name,
            rows=rows,
        )

    @staticmethod
    def _recommend_next_step(state: TableState) -> str | None:
        mapping = {
            TableState.NEW: "PLAN_TABLE",
            TableState.PLANNED: "PREPARE_SOURCE",
            TableState.PREPARED: "ATTACH_EXTRACT",
            TableState.CDC_CAPTURE_ATTACHED: "RUN_INITIAL_LOAD",
            TableState.INITIAL_LOAD_PENDING: "WAIT_OR_RUN_INITIAL_LOAD",
            TableState.INITIAL_LOAD_RUNNING: "WAIT_FOR_INITIAL_LOAD",
            TableState.INITIAL_LOAD_DONE: "RECORD_INSTANTIATION",
            TableState.INSTANTIATED: "ATTACH_REPLICAT",
            TableState.CDC_APPLY_ATTACHED: "ACTIVATE_TABLE",
            TableState.ACTIVE: None,
            TableState.ERROR: "REPLAN_ERROR_TABLE",
            TableState.REMOVAL_PLANNED: "REMOVE_TABLE",
            TableState.REMOVED: None,
        }
        return mapping.get(state)
