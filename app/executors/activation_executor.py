from __future__ import annotations

import json
from pathlib import Path

from app.models.activation import ActivationCommand
from app.models.deployment import DeploymentPlan
from app.models.enums import EventStatus, EventType, TableState, ValidationStatus
from app.models.events import TableEvent
from app.models.executor import ExecutorResult
from app.repositories.event_repo import EventRepository
from app.repositories.registry_repo import RegistryRepository
from app.services.state_machine_service import StateMachineService
from app.services.step_execution_policy_service import StepExecutionPolicyService
from app.utils.error_events import mark_tables_step_error
from app.utils.plan_actions import CDC_APPLY_ACTIONS


class ActivationService:
    def __init__(
        self,
        registry_repo: RegistryRepository,
        event_repo: EventRepository,
        state_machine: StateMachineService,
        step_policy: StepExecutionPolicyService,
    ):
        self.registry_repo = registry_repo
        self.event_repo = event_repo
        self.state_machine = state_machine
        self.step_policy = step_policy

    def run_activation(
        self,
        deployment_id: str,
        plan: DeploymentPlan,
        artifacts_dir: str | Path,
        action: str = "PLAN_ONLY",
    ) -> ExecutorResult | None:
        if action == "SKIP":
            return None

        commands: list[ActivationCommand] = []
        target_table_ids: list[str] = []

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
                expected_state=TableState.CDC_APPLY_ATTACHED,
                success_state=TableState.ACTIVE,
            )
            if policy.decision == "SKIP":
                continue
            if policy.decision == "INVALID_STATE":
                continue

            reason = None
            if isinstance(plan_action.payload, dict):
                reason = plan_action.payload.get("reason")

            self.registry_repo.update_validation_status(
                table_id=record.table_id,
                validation_status=ValidationStatus.PENDING,
                deployment_id=deployment_id,
            )

            self.event_repo.add_event(
                TableEvent(
                    table_id=record.table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.VALIDATION_STARTED,
                    event_status=EventStatus.STARTED,
                    step_name="activation_validation",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "action": action,
                            "reason": reason,
                            "current_state": record.state.value,
                            "validation_status": ValidationStatus.PENDING.value,
                        },
                        ensure_ascii=False,
                    ),
                    error_code=None,
                    error_message=None,
                    created_by=None,
                )
            )

            command = self._build_activation_command(
                table_id=record.table_id,
                source_schema=record.source_schema,
                source_table=record.source_table,
                target_schema=record.target_schema,
                target_table=record.target_table,
                action=action,
                reason=reason,
            )
            commands.append(command)
            target_table_ids.append(record.table_id)

        if not commands:
            return None

        if action == "PLAN_ONLY":
            return ExecutorResult(
                success=True,
                executed_count=0,
                skipped_count=len(commands),
                raw_output="Activation plan built successfully.",
            )

        if action != "APPLY":
            return ExecutorResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                raw_output=None,
                error_code="UNSUPPORTED_ACTION",
                error_message=f"Unsupported activation action: {action}",
            )

        try:
            for table_id in target_table_ids:
                record = self.registry_repo.get_by_table_id(table_id)
                if record is None:
                    continue
                if record.state != TableState.CDC_APPLY_ATTACHED:
                    continue

                self.registry_repo.update_validation_status(
                    table_id=table_id,
                    validation_status=ValidationStatus.PASSED,
                    deployment_id=deployment_id,
                )

                self.event_repo.add_event(
                    TableEvent(
                        table_id=table_id,
                        deployment_id=deployment_id,
                        event_type=EventType.VALIDATION_PASSED,
                        event_status=EventStatus.SUCCESS,
                        step_name="activation_validation",
                        event_ts=None,
                        payload_json=json.dumps(
                            {
                                "action": action,
                                "validation_result": "PASSED",
                                "validation_status": ValidationStatus.PASSED.value,
                            },
                            ensure_ascii=False,
                        ),
                        error_code=None,
                        error_message=None,
                        created_by=None,
                    )
                )

                self.state_machine.ensure_transition_allowed(
                    TableState.CDC_APPLY_ATTACHED,
                    TableState.ACTIVE,
                )
                self.registry_repo.mark_activated(
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
                        event_type=EventType.TABLE_ACTIVATED,
                        event_status=EventStatus.SUCCESS,
                        step_name="activation",
                        event_ts=None,
                        payload_json=json.dumps(
                            {
                                "command_type": cmd.command_type,
                                "command_text": cmd.command_text,
                                "action": cmd.action,
                                "reason": cmd.reason,
                                "new_state": TableState.ACTIVE.value,
                                "validation_status": ValidationStatus.PASSED.value,
                            },
                            ensure_ascii=False,
                        ),
                        error_code=None,
                        error_message=None,
                        created_by=None,
                    )
                )

            return ExecutorResult(
                success=True,
                executed_count=len(commands),
                skipped_count=0,
                raw_output="Activation completed successfully.",
            )

        except Exception as exc:
            self._mark_validation_failed(
                deployment_id=deployment_id,
                table_ids=target_table_ids,
                action=action,
                error_code="ACTIVATION_EXCEPTION",
                error_message=str(exc),
            )
            mark_tables_step_error(
                registry_repo=self.registry_repo,
                event_repo=self.event_repo,
                table_ids=target_table_ids,
                deployment_id=deployment_id,
                step_name="activation",
                error_code="ACTIVATION_EXCEPTION",
                error_message=str(exc),
            )
            return ExecutorResult(
                success=False,
                executed_count=0,
                skipped_count=0,
                raw_output=None,
                error_code="ACTIVATION_EXCEPTION",
                error_message=str(exc),
            )

    def _mark_validation_failed(
        self,
        deployment_id: str,
        table_ids: list[str],
        action: str,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        for table_id in table_ids:
            record = self.registry_repo.get_by_table_id(table_id)
            if record is None:
                continue

            self.registry_repo.update_validation_status(
                table_id=table_id,
                validation_status=ValidationStatus.FAILED,
                deployment_id=deployment_id,
            )

            self.event_repo.add_event(
                TableEvent(
                    table_id=table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.VALIDATION_FAILED,
                    event_status=EventStatus.FAILED,
                    step_name="activation_validation",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "action": action,
                            "validation_result": "FAILED",
                            "validation_status": ValidationStatus.FAILED.value,
                            "error_code": error_code,
                            "error_message": error_message,
                        },
                        ensure_ascii=False,
                    ),
                    error_code=error_code,
                    error_message=error_message,
                    created_by=None,
                )
            )

    @staticmethod
    def _build_activation_command(
        table_id: str,
        source_schema: str,
        source_table: str,
        target_schema: str,
        target_table: str,
        action: str,
        reason: str | None,
    ) -> ActivationCommand:
        command_text = (
            f"VALIDATE AND ACTIVATE {source_schema}.{source_table} "
            f"-> {target_schema}.{target_table}"
        )
        return ActivationCommand(
            table_id=table_id,
            source_schema=source_schema,
            source_table=source_table,
            target_schema=target_schema,
            target_table=target_table,
            command_type="VALIDATE_AND_ACTIVATE",
            command_text=command_text,
            action=action,
            reason=reason,
        )