from __future__ import annotations

from app.models.enums import TableState
from app.models.registry import DesiredTableConfig, TableRegistryRecord
from app.models.reporting import DeploymentStatusReport, TableExecutionStatus


class RerunAnalysisService:
    def build_report(
        self,
        deployment_id: str,
        environment_name: str,
        desired_configs: list[DesiredTableConfig],
        current_registry: list[TableRegistryRecord],
    ) -> DeploymentStatusReport:
        desired_by_id = {cfg.table_id: cfg for cfg in desired_configs}
        current_by_id = {rec.table_id: rec for rec in current_registry}

        table_ids = sorted(set(desired_by_id) | set(current_by_id))

        statuses: list[TableExecutionStatus] = []

        for table_id in table_ids:
            desired = desired_by_id.get(table_id)
            current = current_by_id.get(table_id)

            if desired is not None and current is None:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state="NOT_REGISTERED",
                        desired_enabled=desired.desired_enabled,
                        category="NEW",
                        message="Table is present in desired state but not registered yet.",
                        next_expected_step="REGISTER_NEW_TABLE",
                    )
                )
                continue

            if desired is None and current is not None:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=current.desired_enabled,
                        category="REMOVAL_PENDING",
                        message="Table exists in registry but is absent from desired state.",
                        next_expected_step="PLAN_REMOVE_TABLE",
                    )
                )
                continue

            if desired is None or current is None:
                continue

            if not desired.desired_enabled:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=False,
                        category="DISABLED",
                        message="Table is disabled in desired state.",
                        next_expected_step=None,
                    )
                )
                continue

            if current.state == TableState.NEW:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="PENDING_STEP",
                        message="Table is registered but not planned yet.",
                        next_expected_step="PLANNED",
                    )
                )
            elif current.state == TableState.PLANNED:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="PENDING_STEP",
                        message="Table is waiting for source prepare.",
                        next_expected_step="PREPARED",
                    )
                )
            elif current.state == TableState.PREPARED:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="PENDING_STEP",
                        message="Table is ready for extract attach.",
                        next_expected_step="CDC_CAPTURE_ATTACHED",
                    )
                )
            elif current.state == TableState.CDC_CAPTURE_ATTACHED:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="PENDING_STEP",
                        message="Table is ready for initial load.",
                        next_expected_step="INITIAL_LOAD_DONE",
                    )
                )
            elif current.state == TableState.INITIAL_LOAD_PENDING:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="PENDING_STEP",
                        message="Initial load is pending.",
                        next_expected_step="INITIAL_LOAD_RUNNING",
                    )
                )
            elif current.state == TableState.INITIAL_LOAD_RUNNING:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="PENDING_STEP",
                        message="Initial load is running.",
                        next_expected_step="INITIAL_LOAD_DONE",
                    )
                )
            elif current.state == TableState.INITIAL_LOAD_DONE:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="PENDING_STEP",
                        message="Table is ready for instantiation.",
                        next_expected_step="INSTANTIATED",
                    )
                )
            elif current.state == TableState.INSTANTIATED:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="PENDING_STEP",
                        message="Table is ready for replicat attach.",
                        next_expected_step="CDC_APPLY_ATTACHED",
                    )
                )
            elif current.state == TableState.CDC_APPLY_ATTACHED:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="PENDING_STEP",
                        message="Table is ready for activation.",
                        next_expected_step="ACTIVE",
                    )
                )
            elif current.state == TableState.ACTIVE:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="ALREADY_ACTIVE",
                        message="Table is already fully active.",
                        next_expected_step=None,
                    )
                )
            elif current.state == TableState.ERROR:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="ERROR_STATE",
                        message="Table is in ERROR state and may require recovery.",
                        next_expected_step="PLANNED",
                    )
                )
            elif current.state == TableState.REMOVAL_PLANNED:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="REMOVAL_PENDING",
                        message="Table removal is already planned.",
                        next_expected_step="REMOVED",
                    )
                )
            elif current.state == TableState.REMOVED:
                statuses.append(
                    TableExecutionStatus(
                        table_id=table_id,
                        state=current.state.value,
                        desired_enabled=True,
                        category="REMOVED",
                        message="Table is already removed.",
                        next_expected_step=None,
                    )
                )

        return DeploymentStatusReport(
            deployment_id=deployment_id,
            environment_name=environment_name,
            table_statuses=statuses,
        )