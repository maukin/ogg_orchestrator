from __future__ import annotations

import json
from pathlib import Path

from app.executors.prepare_source_executor import PrepareSourceExecutor
from app.models.deployment import DeploymentPlan
from app.models.enums import EventStatus, EventType, TableState
from app.models.events import TableEvent
from app.models.executor import ExecutorResult
from app.models.prepare import SourcePrepareCommand
from app.repositories.event_repo import EventRepository
from app.repositories.registry_repo import RegistryRepository
from app.services.state_machine_service import StateMachineService
from app.services.step_execution_policy_service import StepExecutionPolicyService
from app.utils.executor_result_payload import executor_result_to_payload
from app.utils.scn import generate_simulated_scn
from app.utils.error_events import mark_tables_step_error
from app.utils.plan_actions import PREPARE_ATTACH_ACTIONS


class PrepareSourceService:
    def __init__(
        self,
        registry_repo: RegistryRepository,
        event_repo: EventRepository,
        state_machine: StateMachineService,
        executor: PrepareSourceExecutor,
        step_policy: StepExecutionPolicyService,
    ):
        self.registry_repo = registry_repo
        self.event_repo = event_repo
        self.state_machine = state_machine
        self.executor = executor
        self.step_policy = step_policy

    def run_prepare(
        self,
        deployment_id: str,
        plan: DeploymentPlan,
        artifacts_dir: str | Path,
        mode: str = "DRY_RUN",
    ) -> ExecutorResult | None:
        commands: list[SourcePrepareCommand] = []
        prepared_table_ids: list[str] = []

        for action in plan.actions:
            if action.action_type not in PREPARE_ATTACH_ACTIONS:
                continue
            if not action.table_id:
                continue

            record = self.registry_repo.get_by_table_id(action.table_id)
            if record is None:
                continue

            policy = self.step_policy.evaluate(
                table_id=record.table_id,
                current_state=record.state,
                expected_state=TableState.PLANNED,
                success_state=TableState.PREPARED,
            )

            if policy.decision == "SKIP":
                continue
            if policy.decision == "INVALID_STATE":
                continue

            reason = None
            if isinstance(action.payload, dict):
                reason = action.payload.get("reason")

            self.event_repo.add_event(
                TableEvent(
                    table_id=record.table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.SOURCE_PREPARE_STARTED,
                    event_status=EventStatus.STARTED,
                    step_name="prepare_source",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "source_schema": record.source_schema,
                            "source_table": record.source_table,
                            "mode": mode,
                            "reason": reason,
                        },
                        ensure_ascii=False,
                    ),
                    error_code=None,
                    error_message=None,
                    created_by=None,
                )
            )

            command = self._build_prepare_command(
                table_id=record.table_id,
                source_schema=record.source_schema,
                source_table=record.source_table,
                mode=mode,
                reason=reason,
            )
            commands.append(command)
            prepared_table_ids.append(record.table_id)

        if not commands:
            return None

        result = self.executor.execute(
            commands=commands,
            artifacts_dir=artifacts_dir,
        )

        if result.success is False:
            mark_tables_step_error(
                registry_repo=self.registry_repo,
                event_repo=self.event_repo,
                table_ids=prepared_table_ids,
                deployment_id=deployment_id,
                step_name="prepare_source",
                error_code=result.error_code,
                error_message=result.error_message or "Prepare source executor failed.",
            )
            return result

        for table_id in prepared_table_ids:
            record = self.registry_repo.get_by_table_id(table_id)
            if record is None:
                continue
            if record.state != TableState.PLANNED:
                continue

            registration_scn = generate_simulated_scn(table_id, "registration")

            self.registry_repo.mark_prepared_for_instantiation(
                table_id=table_id,
                deployment_id=deployment_id,
                registration_scn=registration_scn,
            )

            self.state_machine.ensure_transition_allowed(
                TableState.PLANNED,
                TableState.PREPARED,
            )
            self.registry_repo.update_state(
                table_id=table_id,
                state=TableState.PREPARED,
                deployment_id=deployment_id,
            )

            cmd = next((c for c in commands if c.table_id == table_id), None)
            if cmd is None:
                continue

            self.event_repo.add_event(
                TableEvent(
                    table_id=table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.SOURCE_PREPARE_DONE,
                    event_status=EventStatus.SUCCESS,
                    step_name="prepare_source",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "command_type": cmd.command_type,
                            "command_text": cmd.command_text,
                            "mode": cmd.mode,
                            "reason": cmd.reason,
                            "new_state": TableState.PREPARED.value,
                            "prepared_for_instantiation": True,
                            "registration_scn": registration_scn,
                            "executor_result": executor_result_to_payload(result),
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
    def _build_prepare_command(
        table_id: str,
        source_schema: str,
        source_table: str,
        mode: str,
        reason: str | None,
    ) -> SourcePrepareCommand:
        command_text = f"ADD TRANDATA {source_schema}.{source_table};"
        return SourcePrepareCommand(
            table_id=table_id,
            source_schema=source_schema,
            source_table=source_table,
            command_type="ADD_TRANDATA",
            command_text=command_text,
            mode=mode,
            reason=reason,
        )
