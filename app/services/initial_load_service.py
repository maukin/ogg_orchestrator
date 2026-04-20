from __future__ import annotations

import json
from pathlib import Path

from app.executors.initial_load_executor import InitialLoadExecutor
from app.models.deployment import DeploymentPlan
from app.models.enums import EventStatus, EventType, TableState
from app.models.events import TableEvent
from app.models.executor import ExecutorResult
from app.models.initial_load import InitialLoadCommand
from app.models.initial_load_result import InitialLoadExecutionResult
from app.repositories.event_repo import EventRepository
from app.repositories.registry_repo import RegistryRepository
from app.services.state_machine_service import StateMachineService
from app.services.step_execution_policy_service import StepExecutionPolicyService
from app.utils.error_events import mark_tables_step_error
from app.utils.initial_load_result_payload import initial_load_result_to_payload
from app.utils.plan_actions import INITIAL_LOAD_ACTIONS


class InitialLoadService:
    def __init__(
        self,
        registry_repo: RegistryRepository,
        event_repo: EventRepository,
        state_machine: StateMachineService,
        executor: InitialLoadExecutor,
        step_policy: StepExecutionPolicyService,
    ):
        self.registry_repo = registry_repo
        self.event_repo = event_repo
        self.state_machine = state_machine
        self.executor = executor
        self.step_policy = step_policy

    def run_initial_load(
        self,
        deployment_id: str,
        plan: DeploymentPlan,
        artifacts_dir: str | Path,
        mode: str = "DRY_RUN",
    ) -> InitialLoadExecutionResult | None:
        commands: list[InitialLoadCommand] = []
        target_table_ids: list[str] = []

        for action in plan.actions:
            if action.action_type not in INITIAL_LOAD_ACTIONS:
                continue
            if not action.table_id:
                continue

            record = self.registry_repo.get_by_table_id(action.table_id)
            if record is None:
                continue

            policy = self.step_policy.evaluate(
                table_id=record.table_id,
                current_state=record.state,
                expected_state=TableState.CDC_CAPTURE_ATTACHED,
                success_state=TableState.INITIAL_LOAD_DONE,
            )

            if policy.decision == "SKIP":
                continue
            if policy.decision == "INVALID_STATE":
                continue

            reason = None
            load_method = None
            if isinstance(action.payload, dict):
                reason = action.payload.get("reason")
                load_method = action.payload.get("desired_load_method")

            self.state_machine.ensure_transition_allowed(
                TableState.CDC_CAPTURE_ATTACHED,
                TableState.INITIAL_LOAD_PENDING,
            )
            self.registry_repo.update_state(
                table_id=record.table_id,
                state=TableState.INITIAL_LOAD_PENDING,
                deployment_id=deployment_id,
            )

            command = self._build_initial_load_command(
                table_id=record.table_id,
                source_schema=record.source_schema,
                source_table=record.source_table,
                target_schema=record.target_schema,
                target_table=record.target_table,
                load_method=load_method,
                extract_group=record.desired_extract_group,
                replicat_group=record.desired_replicat_group,
                registration_scn=record.registration_scn,
                metadata_file=record.metadata_file,
                mode=mode,
                reason=reason,
            )
            commands.append(command)
            target_table_ids.append(record.table_id)

        if not commands:
            return None

        result = self.executor.execute(commands=commands, artifacts_dir=artifacts_dir)

        for table_id in target_table_ids:
            self.registry_repo.set_instantiation_candidate_scn(
                table_id=table_id,
                deployment_id=deployment_id,
                instantiation_candidate_scn=result.instantiation_candidate_scn,
            )

        if result.success is False:
            mark_tables_step_error(
                registry_repo=self.registry_repo,
                event_repo=self.event_repo,
                table_ids=target_table_ids,
                deployment_id=deployment_id,
                step_name="initial_load",
                error_code=result.error_code,
                error_message=result.error_message or "Initial load executor failed.",
            )
            return result

        for table_id in target_table_ids:
            record = self.registry_repo.get_by_table_id(table_id)
            if record is None:
                continue
            if record.state != TableState.INITIAL_LOAD_PENDING:
                continue

            self.state_machine.ensure_transition_allowed(
                TableState.INITIAL_LOAD_PENDING,
                TableState.INITIAL_LOAD_RUNNING,
            )
            self.registry_repo.mark_initial_load_started(
                table_id=table_id,
                deployment_id=deployment_id,
            )

            self.event_repo.add_event(
                TableEvent(
                    table_id=table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.INITIAL_LOAD_STARTED,
                    event_status=EventStatus.STARTED,
                    step_name="initial_load",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "mode": mode,
                            "new_state": TableState.INITIAL_LOAD_RUNNING.value,
                            "initial_load_result": initial_load_result_to_payload(result),
                        },
                        ensure_ascii=False,
                    ),
                    error_code=None,
                    error_message=None,
                    created_by=None,
                )
            )

            self.state_machine.ensure_transition_allowed(
                TableState.INITIAL_LOAD_RUNNING,
                TableState.INITIAL_LOAD_DONE,
            )
            self.registry_repo.mark_initial_load_done(
                table_id=table_id,
                deployment_id=deployment_id,
                actual_load_batch_id=result.load_batch_id,
            )

            cmd = next((c for c in commands if c.table_id == table_id), None)
            if cmd is None:
                continue

            self.event_repo.add_event(
                TableEvent(
                    table_id=table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.INITIAL_LOAD_DONE,
                    event_status=EventStatus.SUCCESS,
                    step_name="initial_load",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "command_type": cmd.command_type,
                            "command_text": cmd.command_text,
                            "mode": cmd.mode,
                            "reason": cmd.reason,
                            "new_state": TableState.INITIAL_LOAD_DONE.value,
                            "initial_load_result": initial_load_result_to_payload(result),
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
    def _build_initial_load_command(
        table_id: str,
        source_schema: str,
        source_table: str,
        target_schema: str,
        target_table: str,
        load_method: str | None,
        extract_group: str | None,
        replicat_group: str | None,
        registration_scn: int | None,
        metadata_file: str | None,
        mode: str,
        reason: str | None,
    ) -> InitialLoadCommand:
        command_text = (
            f"run_initial_load --source {source_schema}.{source_table} "
            f"--target {target_schema}.{target_table}"
        )
        return InitialLoadCommand(
            table_id=table_id,
            source_schema=source_schema,
            source_table=source_table,
            target_schema=target_schema,
            target_table=target_table,
            load_method=load_method,
            extract_group=extract_group,
            replicat_group=replicat_group,
            registration_scn=registration_scn,
            metadata_file=metadata_file,
            command_type="INITIAL_LOAD",
            command_text=command_text,
            mode=mode,
            reason=reason,
        )
