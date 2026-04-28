from __future__ import annotations

import json
from pathlib import Path

from app.executors.attach_extract_executor import AttachExtractExecutor
from app.models.attach_extract import AttachExtractCommand
from app.models.attach_extract_result import AttachExtractExecutionResult
from app.models.deployment import DeploymentPlan
from app.models.enums import EventStatus, EventType, TableState
from app.models.events import TableEvent
from app.repositories.event_repo import EventRepository
from app.repositories.registry_repo import RegistryRepository
from app.services.state_machine_service import StateMachineService
from app.services.step_execution_policy_service import StepExecutionPolicyService
from app.utils.attach_extract_result_payload import attach_extract_result_to_payload
from app.utils.error_events import mark_tables_step_error
from app.utils.plan_actions import PREPARE_ATTACH_ACTIONS


def _debug(msg: str) -> None:
    print(f"[attach_extract_service] {msg}", flush=True)


class AttachExtractService:
    def __init__(
        self,
        registry_repo: RegistryRepository,
        event_repo: EventRepository,
        state_machine: StateMachineService,
        executor: AttachExtractExecutor,
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
    ) -> AttachExtractExecutionResult | None:
        _debug(f"run_attach started, deployment_id={deployment_id}, action={action}, artifacts_dir={artifacts_dir}")


        if action == "SKIP":
            _debug("action=SKIP, returning None")
            return None

        commands: list[AttachExtractCommand] = []
        target_table_ids: list[str] = []
        extract_fragment_dir = Path(artifacts_dir) / "cdc" / "extract" / "generated"
        _debug(f"extract_fragment_dir={extract_fragment_dir}")

        for plan_action in plan.actions:
            _debug(f"inspect plan_action action_type={plan_action.action_type}, table_id={plan_action.table_id}")

            if plan_action.action_type not in PREPARE_ATTACH_ACTIONS:
                _debug("skipped: action_type not in PREPARE_ATTACH_ACTIONS")
                continue
            if not plan_action.table_id:
                _debug("skipped: empty table_id")
                continue

            record = self.registry_repo.get_by_table_id(plan_action.table_id)
            if record is None:
                _debug(f"skipped: registry record not found for {plan_action.table_id}")
                continue

            _debug(
                f"record loaded: table_id={record.table_id}, "
                f"state={record.state.value}, "
                f"desired_extract_group={record.desired_extract_group}"
            )

            policy = self.step_policy.evaluate(
                table_id=record.table_id,
                current_state=record.state,
                expected_state=TableState.PREPARED,
                success_state=TableState.CDC_CAPTURE_ATTACHED,
            )
            _debug(f"policy decision={policy.decision} for table_id={record.table_id}")

            if policy.decision == "SKIP":
                _debug("skipped by policy decision=SKIP")
                continue
            if policy.decision == "INVALID_STATE":
                _debug("skipped by policy decision=INVALID_STATE")
                continue

            if not record.desired_extract_group:
                _debug("skipped: desired_extract_group is empty")
                continue

            reason = None
            if isinstance(plan_action.payload, dict):
                reason = plan_action.payload.get("reason")

            fragment_path = (
                extract_fragment_dir / f"{record.desired_extract_group}.tables.prm"
            )

            command = self._build_command(
                table_id=record.table_id,
                source_schema=record.source_schema,
                source_table=record.source_table,
                extract_group=record.desired_extract_group,
                fragment_path=str(fragment_path),
                action=action,
                reason=reason,
            )

            _debug(
                f"command built: table_id={command.table_id}, "
                f"extract_group={command.extract_group}, "
                f"fragment_path={command.fragment_path}, "
                f"command_text={command.command_text}"
            )

            commands.append(command)
            target_table_ids.append(record.table_id)

        if not commands:
            _debug("no commands built, returning None")
            return None

        _debug(f"executing commands_count={len(commands)}")
        result = self.executor.execute(commands=commands, artifacts_dir=artifacts_dir)
        _debug(
            f"executor result: success={result.success}, "
            f"executed_count={result.executed_count}, "
            f"skipped_count={result.skipped_count}, "
            f"error_code={result.error_code}, "
            f"error_message={result.error_message}"
        )

        if result.success is False:
            _debug("marking step error for tables")
            mark_tables_step_error(
                registry_repo=self.registry_repo,
                event_repo=self.event_repo,
                table_ids=target_table_ids,
                deployment_id=deployment_id,
                step_name="attach_extract",
                error_code=result.error_code,
                error_message=result.error_message or "Attach extract executor failed.",
            )
            return result

        if action == "PLAN_ONLY":
            _debug("action=PLAN_ONLY, returning executor result without state transition")
            return result

        if action != "APPLY":
            raise ValueError(f"Unsupported attach_extract action: {action}")

        for table_id in target_table_ids:
            record = self.registry_repo.get_by_table_id(table_id)
            if record is None:
                _debug(f"post-exec skip: registry record not found for {table_id}")
                continue
            if record.state != TableState.PREPARED:
                _debug(f"post-exec skip: record.state={record.state.value}, expected=PREPARED")
                continue

            _debug(f"transition PREPARED -> CDC_CAPTURE_ATTACHED for {table_id}")
            self.state_machine.ensure_transition_allowed(
                TableState.PREPARED,
                TableState.CDC_CAPTURE_ATTACHED,
            )
            self.registry_repo.mark_cdc_capture_attached(
                table_id=table_id,
                deployment_id=deployment_id,
            )

            cmd = next((c for c in commands if c.table_id == table_id), None)
            if cmd is None:
                _debug(f"post-exec skip: command not found for {table_id}")
                continue

            _debug(f"writing STARTED and DONE events for {table_id}")
            self.event_repo.add_event(
                TableEvent(
                    table_id=table_id,
                    deployment_id=deployment_id,
                    event_type=EventType.CDC_CAPTURE_ATTACH_STARTED,
                    event_status=EventStatus.STARTED,
                    step_name="attach_extract",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "extract_group": cmd.extract_group,
                            "fragment_path": cmd.fragment_path,
                            "action": cmd.action,
                            "reason": cmd.reason,
                            "attach_extract_result": attach_extract_result_to_payload(
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
                    event_type=EventType.CDC_CAPTURE_ATTACH_DONE,
                    event_status=EventStatus.SUCCESS,
                    step_name="attach_extract",
                    event_ts=None,
                    payload_json=json.dumps(
                        {
                            "extract_group": cmd.extract_group,
                            "fragment_path": cmd.fragment_path,
                            "action": cmd.action,
                            "reason": cmd.reason,
                            "new_state": TableState.CDC_CAPTURE_ATTACHED.value,
                            "attach_extract_result": attach_extract_result_to_payload(
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

        _debug("run_attach completed successfully")
        return result

    @staticmethod
    def _build_command(
        table_id: str,
        source_schema: str,
        source_table: str,
        extract_group: str,
        fragment_path: str,
        action: str,
        reason: str | None,
    ) -> AttachExtractCommand:
        return AttachExtractCommand(
            table_id=table_id,
            source_schema=source_schema,
            source_table=source_table,
            extract_group=extract_group,
            fragment_path=fragment_path,
            command_type="ATTACH_EXTRACT",
            command_text=f"attach_extract --group {extract_group} --fragment {fragment_path}",
            action=action,
            reason=reason,
        )