from __future__ import annotations

import json
from pathlib import Path

from app.executors.instantiation_executor import InstantiationExecutor
from app.models.deployment import DeploymentPlan
from app.models.enums import EventStatus, EventType, TableState
from app.models.events import TableEvent
from app.models.executor import ExecutorResult
from app.models.instantiation import InstantiationCommand
from app.repositories.event_repo import EventRepository
from app.repositories.registry_repo import RegistryRepository
from app.services.state_machine_service import StateMachineService
from app.services.step_execution_policy_service import StepExecutionPolicyService
from app.utils.error_events import mark_tables_step_error
from app.utils.instantiation_scn import resolve_instantiation_scn
from app.utils.plan_actions import PLAN_CDC_ONLY, PREPARE_ATTACH_ACTIONS


class InstantiationService:
    def __init__(
        self,
        registry_repo: RegistryRepository,
        event_repo: EventRepository,
        state_machine: StateMachineService,
        executor: InstantiationExecutor,
        step_policy: StepExecutionPolicyService,
    ):
        self.registry_repo = registry_repo
        self.event_repo = event_repo
        self.state_machine = state_machine
        self.executor = executor
        self.step_policy = step_policy

    def run_instantiation(
        self,
        deployment_id: str,
        plan: DeploymentPlan,
        artifacts_dir: str | Path,
        action: str = "PLAN_ONLY",
    ) -> ExecutorResult | None:
        if action == "SKIP":
            return None

        commands: list[InstantiationCommand] = []
        instantiated_table_ids: list[str] = []
        command_by_table_id: dict[str, InstantiationCommand] = {}
        action_type_by_table_id: dict[str, str] = {}

        for plan_action in plan.actions:
            if plan_action.action_type not in PREPARE_ATTACH_ACTIONS:
                continue
            if not plan_action.table_id:
                continue

            record = self.registry_repo.get_by_table_id(plan_action.table_id)
            if record is None:
                continue

            expected_state = (
                TableState.CDC_CAPTURE_ATTACHED
                if plan_action.action_type == PLAN_CDC_ONLY
                else TableState.INITIAL_LOAD_DONE
            )

            policy = self.step_policy.evaluate(
                table_id=record.table_id,
                current_state=record.state,
                expected_state=expected_state,
                success_state=TableState.INSTANTIATED,
            )
            if policy.decision == "SKIP":
                continue
            if policy.decision == "INVALID_STATE":
                continue

            reason = None
            if isinstance(plan_action.payload, dict):
                reason = plan_action.payload.get("reason")

            instantiation_scn = resolve_instantiation_scn(
                registration_scn=record.registration_scn,
                instantiation_candidate_scn=record.instantiation_candidate_scn,
            )

            command = self._build_instantiation_command(
                table_id=record.table_id,
                source_schema=record.source_schema,
                source_table=record.source_table,
                target_schema=record.target_schema,
                target_table=record.target_table,
                instantiation_scn=instantiation_scn,
                action=action,
                reason=reason,
            )
            commands.append(command)
            instantiated_table_ids.append(record.table_id)
            command_by_table_id[record.table_id] = command
            action_type_by_table_id[record.table_id] = plan_action.action_type

        if not commands:
            return None

        result = self._execute(commands=commands, artifacts_dir=artifacts_dir)

        if result.success is False:
            mark_tables_step_error(
                registry_repo=self.registry_repo,
                event_repo=self.event_repo,
                table_ids=instantiated_table_ids,
                deployment_id=deployment_id,
                step_name="instantiation",
                error_code=result.error_code,
                error_message=result.error_message or "Instantiation executor failed.",
            )
            return result

        if action == "PLAN_ONLY":
            return result

        if action != "APPLY":
            raise ValueError(f"Unsupported instantiation action: {action}")

        for table_id in instantiated_table_ids:
            record = self.registry_repo.get_by_table_id(table_id)
            if record is None:
                continue

            cmd = command_by_table_id.get(table_id)
            if cmd is None:
                continue

            action_type = action_type_by_table_id.get(table_id)
            if action_type == PLAN_CDC_ONLY and record.state != TableState.CDC_CAPTURE_ATTACHED:
                continue
            if action_type != PLAN_CDC_ONLY and record.state != TableState.INITIAL_LOAD_DONE:
                continue

            self.registry_repo.record_instantiation(
                table_id=table_id,
                deployment_id=deployment_id,
                instantiation_scn=cmd.instantiation_scn,
            )

            self.state_machine.ensure_transition_allowed(
                record.state,
                TableState.INSTANTIATED,
            )
            self.registry_repo.update_state(
                table_id=table_id,
                state=TableState.INSTANTIATED,
                deployment_id=deployment_id,
            )

            self.event_repo.add_event(
                TableEvent(
                    table_id=table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.INSTANTIATION_RECORDED,
                    event_status=EventStatus.SUCCESS,
                    step_name="instantiation",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "command_type": cmd.command_type,
                            "command_text": cmd.command_text,
                            "action": cmd.action,
                            "reason": cmd.reason,
                            "new_state": TableState.INSTANTIATED.value,
                            "instantiation_scn": cmd.instantiation_scn,
                        },
                        ensure_ascii=False,
                    ),
                    error_code=None,
                    error_message=None,
                    created_by=None,
                )
            )

        return result

    def _execute(
        self,
        commands: list[InstantiationCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        try:
            result = self.executor.execute(commands=commands, artifacts_dir=artifacts_dir)
        except Exception as exc:
            return ExecutorResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                raw_output=None,
                error_code="EXECUTOR_EXCEPTION",
                error_message=str(exc),
            )

        if isinstance(result, ExecutorResult):
            return result

        return ExecutorResult(
            success=False,
            executed_count=0,
            skipped_count=0,
            raw_output=None,
            error_code="EXECUTOR_NO_RESULT",
            error_message="Instantiation executor returned no structured result.",
        )

    @staticmethod
    def _build_instantiation_command(
        *,
        table_id: str,
        source_schema: str,
        source_table: str,
        target_schema: str,
        target_table: str,
        instantiation_scn: int,
        action: str,
        reason: str | None,
    ) -> InstantiationCommand:
        command_text = (
            f"SET INSTANTIATION SCN {instantiation_scn} "
            f"FOR {source_schema}.{source_table} -> {target_schema}.{target_table}"
        )
        return InstantiationCommand(
            table_id=table_id,
            source_schema=source_schema,
            source_table=source_table,
            target_schema=target_schema,
            target_table=target_table,
            instantiation_scn=instantiation_scn,
            command_type="RECORD_INSTANTIATION",
            command_text=command_text,
            action=action,
            reason=reason,
        )