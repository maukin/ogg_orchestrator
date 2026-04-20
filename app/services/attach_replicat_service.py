from __future__ import annotations

import json
from pathlib import Path

from app.executors.attach_replicat_executor import AttachReplicatExecutor
from app.models.attach_replicat import AttachReplicatCommand
from app.models.attach_replicat_result import AttachReplicatExecutionResult
from app.models.deployment import DeploymentPlan
from app.models.enums import EventStatus, EventType, TableState
from app.models.events import TableEvent
from app.repositories.event_repo import EventRepository
from app.repositories.registry_repo import RegistryRepository
from app.services.state_machine_service import StateMachineService
from app.services.step_execution_policy_service import StepExecutionPolicyService
from app.utils.attach_replicat_result_payload import attach_replicat_result_to_payload
from app.utils.error_events import mark_tables_step_error
from app.utils.plan_actions import CDC_APPLY_ACTIONS


class AttachReplicatService:
    def __init__(
        self,
        registry_repo: RegistryRepository,
        event_repo: EventRepository,
        state_machine: StateMachineService,
        executor: AttachReplicatExecutor,
        step_policy: StepExecutionPolicyService,
    ):
        self.registry_repo = registry_repo
        self.event_repo = event_repo
        self.state_machine = state_machine
        self.executor = executor
        self.step_policy = step_policy

    def run_attach(
        self,
        deployment_id: str,
        plan: DeploymentPlan,
        artifacts_dir: str | Path,
        action: str = "PLAN_ONLY",
    ) -> AttachReplicatExecutionResult | None:
        if action == "SKIP":
            return None

        commands: list[AttachReplicatCommand] = []
        target_table_ids: list[str] = []
        replicat_fragment_dir = Path(artifacts_dir) / "cdc" / "replicat"

        for plan_action in plan.actions:
            if plan_action.action_type not in CDC_APPLY_ACTIONS:
                continue
            if not plan_action.table_id:
                continue

            record = self.registry_repo.get_by_table_id(plan_action.table_id)
            if record is None:
                continue

            policy = self.step_policy.evaluate(
                table_id=record.table_id,
                current_state=record.state,
                expected_state=TableState.INSTANTIATED,
                success_state=TableState.CDC_APPLY_ATTACHED,
            )
            if policy.decision == "SKIP":
                continue
            if policy.decision == "INVALID_STATE":
                continue

            if not record.desired_replicat_group:
                continue

            reason = None
            if isinstance(plan_action.payload, dict):
                reason = plan_action.payload.get("reason")

            fragment_path = (
                replicat_fragment_dir / f"{record.desired_replicat_group}.maps.prm"
            )

            command = self._build_command(
                table_id=record.table_id,
                source_schema=record.source_schema,
                source_table=record.source_table,
                target_schema=record.target_schema,
                target_table=record.target_table,
                replicat_group=record.desired_replicat_group,
                fragment_path=str(fragment_path),
                action=action,
                reason=reason,
            )
            commands.append(command)
            target_table_ids.append(record.table_id)

        if not commands:
            return None

        result = self.executor.execute(commands=commands, artifacts_dir=artifacts_dir)

        if result.success is False:
            mark_tables_step_error(
                registry_repo=self.registry_repo,
                event_repo=self.event_repo,
                table_ids=target_table_ids,
                deployment_id=deployment_id,
                step_name="attach_replicat",
                error_code=result.error_code,
                error_message=result.error_message or "Attach replicat executor failed.",
            )
            return result

        if action == "PLAN_ONLY":
            return result

        if action != "APPLY":
            raise ValueError(f"Unsupported attach_replicat action: {action}")

        for table_id in target_table_ids:
            record = self.registry_repo.get_by_table_id(table_id)
            if record is None:
                continue
            if record.state != TableState.INSTANTIATED:
                continue

            self.state_machine.ensure_transition_allowed(
                TableState.INSTANTIATED,
                TableState.CDC_APPLY_ATTACHED,
            )
            self.registry_repo.mark_cdc_apply_attached(
                table_id=table_id,
                deployment_id=deployment_id,
            )

            cmd = next((c for c in commands if c.table_id == table_id), None)
            if cmd is None:
                continue

            self.event_repo.add_event(
                TableEvent(
                    table_id=table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.CDC_APPLY_ATTACH_STARTED,
                    event_status=EventStatus.STARTED,
                    step_name="attach_replicat",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "replicat_group": cmd.replicat_group,
                            "fragment_path": cmd.fragment_path,
                            "action": cmd.action,
                            "reason": cmd.reason,
                            "attach_replicat_result": attach_replicat_result_to_payload(
                                result
                            ),
                        },
                        ensure_ascii=False,
                    ),
                    error_code=None,
                    error_message=None,
                    created_by=None,
                )
            )

            self.event_repo.add_event(
                TableEvent(
                    table_id=table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.CDC_APPLY_ATTACH_DONE,
                    event_status=EventStatus.SUCCESS,
                    step_name="attach_replicat",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "replicat_group": cmd.replicat_group,
                            "fragment_path": cmd.fragment_path,
                            "action": cmd.action,
                            "reason": cmd.reason,
                            "new_state": TableState.CDC_APPLY_ATTACHED.value,
                            "attach_replicat_result": attach_replicat_result_to_payload(
                                result
                            ),
                        },
                        ensure_ascii=False,
                    ),
                    error_code=None,
                    error_message=None,
                    created_by=None,
                )
            )

        return result

    @staticmethod
    def _build_command(
        table_id: str,
        source_schema: str,
        source_table: str,
        target_schema: str,
        target_table: str,
        replicat_group: str,
        fragment_path: str,
        action: str,
        reason: str | None,
    ) -> AttachReplicatCommand:
        return AttachReplicatCommand(
            table_id=table_id,
            source_schema=source_schema,
            source_table=source_table,
            target_schema=target_schema,
            target_table=target_table,
            replicat_group=replicat_group,
            fragment_path=fragment_path,
            command_type="ATTACH_REPLICAT",
            command_text=f"attach_replicat --group {replicat_group} --fragment {fragment_path}",
            action=action,
            reason=reason,
        )