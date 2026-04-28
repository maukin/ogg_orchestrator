from __future__ import annotations

import json
from pathlib import Path

from app.models.deployment import DeploymentPlan
from app.models.enums import EventStatus, EventType, TableState
from app.models.events import TableEvent
from app.models.registry import DesiredTableConfig
from app.repositories.deployment_repo import DeploymentRepository
from app.repositories.event_repo import EventRepository
from app.repositories.group_repo import GroupRepository
from app.repositories.registry_repo import RegistryRepository
from app.services.activation_service import ActivationService
from app.services.artifact_renderer import ArtifactRenderer
from app.services.attach_extract_service import AttachExtractService
from app.services.attach_replicat_service import AttachReplicatService
from app.services.deployment_execution_summary_service import (
    DeploymentExecutionSummaryService,
)
from app.services.extract_status_probe_service import ExtractStatusProbeService
from app.services.grouping_service import GroupingService
from app.services.initial_load_service import InitialLoadService
from app.services.instantiation_service import InstantiationService
from app.services.planner_service import PlannerService
from app.services.prepare_source_service import PrepareSourceService
from app.services.replicat_status_probe_service import ReplicatStatusProbeService
from app.services.rerun_analysis_service import RerunAnalysisService
from app.services.state_machine_service import StateMachineService
from app.utils.error_events import mark_tables_step_error

from app.services.reconciliation_service import ReconciliationService
from app.services.cdc_config_render_service import CDCConfigRenderService

from app.services.group_bootstrap_planner_service import GroupBootstrapPlannerService
from app.services.group_bootstrap_service import GroupBootstrapService

from app.models.group_bootstrap import GroupBootstrapRequest


class DeploymentOrchestrator:
    def __init__(
        self,
        registry_repo: RegistryRepository,
        event_repo: EventRepository,
        deployment_repo: DeploymentRepository,
        group_repo: GroupRepository,
        planner_service: PlannerService,
        state_machine: StateMachineService,
        grouping_service: GroupingService,
        artifact_renderer: ArtifactRenderer,
        prepare_source_service: PrepareSourceService | None,
        attach_extract_service: AttachExtractService | None,
        initial_load_service: InitialLoadService | None,
        instantiation_service: InstantiationService | None,
        attach_replicat_service: AttachReplicatService | None,
        activation_service: ActivationService | None,
        rerun_analysis_service: RerunAnalysisService,
        deployment_execution_summary_service: DeploymentExecutionSummaryService,
        extract_status_probe_service: ExtractStatusProbeService | None,
        replicat_status_probe_service: ReplicatStatusProbeService | None,
        reconciliation_service: ReconciliationService,
        cdc_config_render_service: CDCConfigRenderService,
        group_bootstrap_planner_service: GroupBootstrapPlannerService | None = None,
        group_bootstrap_service: GroupBootstrapService | None = None,
    ):
        self.registry_repo = registry_repo
        self.event_repo = event_repo
        self.deployment_repo = deployment_repo
        self.group_repo = group_repo
        self.planner_service = planner_service
        self.state_machine = state_machine
        self.grouping_service = grouping_service
        self.artifact_renderer = artifact_renderer
        self.prepare_source_service = prepare_source_service
        self.attach_extract_service = attach_extract_service
        self.initial_load_service = initial_load_service
        self.instantiation_service = instantiation_service
        self.attach_replicat_service = attach_replicat_service
        self.activation_service = activation_service
        self.rerun_analysis_service = rerun_analysis_service
        self.deployment_execution_summary_service = deployment_execution_summary_service
        self.extract_status_probe_service = extract_status_probe_service
        self.replicat_status_probe_service = replicat_status_probe_service
        self.reconciliation_service = reconciliation_service
        self.cdc_config_render_service = cdc_config_render_service
        self.group_bootstrap_planner_service = group_bootstrap_planner_service
        self.group_bootstrap_service = group_bootstrap_service

    def _raise_if_step_failed(self, step_name: str, result: object | None) -> None:
        if result is None:
            return

        if getattr(result, "success", None) is False:
            error_code = getattr(result, "error_code", None)
            error_message = getattr(result, "error_message", None)
            print(
                f"[orchestrator] step failed: {step_name}, "
                f"error_code={error_code}, error_message={error_message}",
                flush=True,
            )
            raise RuntimeError(
                f"{step_name} failed: "
                f"error_code={error_code}, error_message={error_message}"
            )

    def _run_group_bootstrap_actions(
        self,
        bootstrap_actions: list,
        artifacts_dir: str | Path,
        step_results: list[tuple[str, object | None]],
    ) -> None:
        if self.group_bootstrap_service is None:
            raise ValueError("Group bootstrap service is not configured.")

        for action in bootstrap_actions:
            payload = dict(action.payload or {})
            request = GroupBootstrapRequest(
                group_name=payload["group_name"],
                group_type=payload["group_type"],
                environment_name=payload["environment_name"],
                source_system=payload.get("source_system"),
                target_system=payload.get("target_system"),
                credential_alias=payload["credential_alias"],
                credential_domain=payload.get("credential_domain"),
                trail_name=payload.get("trail_name"),
                mode=payload["mode"],
                base_config_lines=list(payload.get("base_config_lines") or []),
                notes=payload.get("notes"),
            )
            result = self.group_bootstrap_service.bootstrap(
                request=request,
                artifacts_dir=artifacts_dir,
            )
            step_results.append(
                (f"bootstrap_group:{request.group_type}:{request.group_name}", result)
            )

            if not result.success:
                raise ValueError(
                    f"Failed to bootstrap {request.group_type} group {request.group_name}: "
                    f"{result.error_message or result.error_code}"
                )

    def build_and_apply_registry_changes(
        self,
        deployment_id: str,
        environment_name: str,
        git_branch: str | None,
        git_commit_sha: str | None,
        pipeline_id: str | None,
        desired_configs: list[DesiredTableConfig],
        artifacts_dir: str | Path | None = None,
        prepare_source_action: str = "PLAN_ONLY",
        attach_extract_action: str = "PLAN_ONLY",
        initial_load_action: str = "PLAN_ONLY",
        instantiation_action: str = "PLAN_ONLY",
        attach_replicat_action: str = "PLAN_ONLY",
        activation_action: str = "PLAN_ONLY",
    ) -> DeploymentPlan:
        current_registry = self.registry_repo.list_all()
        available_groups = self.group_repo.list_active_groups(environment_name)

        step_results: list[tuple[str, object | None]] = []
        extract_probe_results: dict[str, object] = {}
        replicat_probe_results: dict[str, object] = {}

        self.grouping_service.validate_desired_groups(
            desired_configs=desired_configs,
            current_registry=current_registry,
            available_groups=available_groups,
            strict_existing_groups=False,
        )

        bootstrap_actions = []
        if self.group_bootstrap_planner_service is not None:
            bootstrap_actions = self.group_bootstrap_planner_service.build_bootstrap_actions(
                environment_name=environment_name,
                desired_configs=desired_configs,
                available_groups=available_groups,
            )

        if bootstrap_actions:
            if artifacts_dir is None:
                raise ValueError(
                    "artifacts_dir is required when bootstrap of groups is needed."
                )
            self._run_group_bootstrap_actions(
                bootstrap_actions=bootstrap_actions,
                artifacts_dir=artifacts_dir,
                step_results=step_results,
            )
            available_groups = self.group_repo.list_active_groups(environment_name)

        self.grouping_service.validate_desired_groups(
            desired_configs=desired_configs,
            current_registry=current_registry,
            available_groups=available_groups,
            strict_existing_groups=True,
        )

        plan = self.planner_service.build_plan(
            deployment_id=deployment_id,
            environment_name=environment_name,
            git_branch=git_branch,
            git_commit_sha=git_commit_sha,
            pipeline_id=pipeline_id,
            desired_configs=desired_configs,
            current_registry=current_registry,
        )

        self.deployment_repo.start(
            deployment_id=deployment_id,
            environment_name=environment_name,
            git_branch=git_branch,
            git_commit_sha=git_commit_sha,
            pipeline_id=pipeline_id,
            plan=plan,
        )

        if artifacts_dir is not None:
            self.artifact_renderer.render_plan_artifacts(
                plan=plan,
                output_dir=artifacts_dir,
            )

            registry_records = [
                self.registry_repo.get_by_table_id(cfg.table_id)
                for cfg in desired_configs
            ]
            registry_records = [r for r in registry_records if r is not None]

            cdc_bundle = self.cdc_config_render_service.build_bundle(
                desired_configs=desired_configs,
                registry_records=registry_records,
            )

            self.artifact_renderer.render_cdc_config_bundle(
                bundle=cdc_bundle,
                output_dir=artifacts_dir,
            )

        for action in plan.actions:
            if action.action_type == "REGISTER_NEW_TABLE":
                self._register_new_table(
                    deployment_id=deployment_id,
                    action=action,
                )
            elif action.action_type == "UPDATE_TABLE_DESIRED_STATE":
                self._update_existing_table(
                    deployment_id=deployment_id,
                    action=action,
                )
            elif action.action_type == "PLAN_REMOVE_TABLE":
                self._plan_remove_table(
                    deployment_id=deployment_id,
                    action=action,
                )

        if artifacts_dir is not None and self.prepare_source_service is not None:
            prepare_result = self.prepare_source_service.run_prepare(
                deployment_id=deployment_id,
                plan=plan,
                artifacts_dir=artifacts_dir,
                action=prepare_source_action,
            )
            step_results.append(("prepare_source", prepare_result))
            self._raise_if_step_failed("prepare_source", prepare_result)

        if artifacts_dir is not None and self.extract_status_probe_service is not None:
            extract_groups = sorted(
                {
                    cfg.desired_extract_group
                    for cfg in desired_configs
                    if cfg.desired_enabled and cfg.desired_extract_group
                }
            )
            for extract_group in extract_groups:
                probe_result = self.extract_status_probe_service.probe(
                    extract_name=extract_group,
                    artifacts_dir=artifacts_dir,
                )
                extract_probe_results[extract_group] = probe_result
                step_results.append((f"probe_extract_status:{extract_group}", probe_result))

        failed_extract_groups = {
            group_name
            for group_name, probe_result in extract_probe_results.items()
            if getattr(probe_result, "success", None) is False
        }

        if failed_extract_groups:
            for group_name in sorted(failed_extract_groups):
                affected_table_ids = [
                    cfg.table_id
                    for cfg in desired_configs
                    if cfg.desired_enabled and cfg.desired_extract_group == group_name
                ]
                mark_tables_step_error(
                    registry_repo=self.registry_repo,
                    event_repo=self.event_repo,
                    table_ids=affected_table_ids,
                    deployment_id=deployment_id,
                    step_name=f"attach_extract_probe:{group_name}",
                    error_code=getattr(
                        extract_probe_results[group_name],
                        "error_code",
                        None,
                    ),
                    error_message=getattr(
                        extract_probe_results[group_name],
                        "error_message",
                        f"Extract probe failed for group {group_name}",
                    ),
                )

        if artifacts_dir is not None and self.attach_extract_service is not None:
            filtered_plan = plan
            if failed_extract_groups:
                filtered_actions = []
                for action in plan.actions:
                    if not action.table_id:
                        filtered_actions.append(action)
                        continue

                    cfg = next(
                        (x for x in desired_configs if x.table_id == action.table_id),
                        None,
                    )
                    if cfg is None:
                        filtered_actions.append(action)
                        continue

                    if cfg.desired_extract_group in failed_extract_groups:
                        continue

                    filtered_actions.append(action)

                filtered_plan = DeploymentPlan(
                    deployment_id=plan.deployment_id,
                    environment_name=plan.environment_name,
                    git_branch=plan.git_branch,
                    git_commit_sha=plan.git_commit_sha,
                    pipeline_id=plan.pipeline_id,
                    actions=filtered_actions,
                )

            extract_result = self.attach_extract_service.run_attach(
                deployment_id=deployment_id,
                plan=filtered_plan,
                artifacts_dir=artifacts_dir,
                action=attach_extract_action,
            )
            step_results.append(("attach_extract", extract_result))
            self._raise_if_step_failed("attach_extract", extract_result)

        if artifacts_dir is not None and self.initial_load_service is not None:
            initial_load_result = self.initial_load_service.run_initial_load(
                deployment_id=deployment_id,
                plan=plan,
                artifacts_dir=artifacts_dir,
                action=initial_load_action,
            )
            step_results.append(("initial_load", initial_load_result))
            self._raise_if_step_failed("initial_load", initial_load_result)

        if artifacts_dir is not None and self.instantiation_service is not None:
            instantiation_result = self.instantiation_service.run_instantiation(
                deployment_id=deployment_id,
                plan=plan,
                artifacts_dir=artifacts_dir,
                action=instantiation_action,
            )
            step_results.append(("instantiation", instantiation_result))
            self._raise_if_step_failed("instantiation", instantiation_result)

        if artifacts_dir is not None and self.replicat_status_probe_service is not None:
            replicat_groups = sorted(
                {
                    cfg.desired_replicat_group
                    for cfg in desired_configs
                    if cfg.desired_enabled and cfg.desired_replicat_group
                }
            )
            for replicat_group in replicat_groups:
                probe_result = self.replicat_status_probe_service.probe(
                    replicat_name=replicat_group,
                    artifacts_dir=artifacts_dir,
                )
                replicat_probe_results[replicat_group] = probe_result
                step_results.append(
                    (f"probe_replicat_status:{replicat_group}", probe_result)
                )

        failed_replicat_groups = {
            group_name
            for group_name, probe_result in replicat_probe_results.items()
            if getattr(probe_result, "success", None) is False
        }

        if failed_replicat_groups:
            for group_name in sorted(failed_replicat_groups):
                affected_table_ids = [
                    cfg.table_id
                    for cfg in desired_configs
                    if cfg.desired_enabled and cfg.desired_replicat_group == group_name
                ]
                mark_tables_step_error(
                    registry_repo=self.registry_repo,
                    event_repo=self.event_repo,
                    table_ids=affected_table_ids,
                    deployment_id=deployment_id,
                    step_name=f"attach_replicat_probe:{group_name}",
                    error_code=getattr(
                        replicat_probe_results[group_name],
                        "error_code",
                        None,
                    ),
                    error_message=getattr(
                        replicat_probe_results[group_name],
                        "error_message",
                        f"Replicat probe failed for group {group_name}",
                    ),
                )

        if artifacts_dir is not None and self.attach_replicat_service is not None:
            filtered_plan = plan
            if failed_replicat_groups:
                filtered_actions = []
                for action in plan.actions:
                    if not action.table_id:
                        filtered_actions.append(action)
                        continue

                    cfg = next(
                        (x for x in desired_configs if x.table_id == action.table_id),
                        None,
                    )
                    if cfg is None:
                        filtered_actions.append(action)
                        continue

                    if cfg.desired_replicat_group in failed_replicat_groups:
                        continue

                    filtered_actions.append(action)

                filtered_plan = DeploymentPlan(
                    deployment_id=plan.deployment_id,
                    environment_name=plan.environment_name,
                    git_branch=plan.git_branch,
                    git_commit_sha=plan.git_commit_sha,
                    pipeline_id=plan.pipeline_id,
                    actions=filtered_actions,
                )

            replicat_result = self.attach_replicat_service.run_attach(
                deployment_id=deployment_id,
                plan=filtered_plan,
                artifacts_dir=artifacts_dir,
                action=attach_replicat_action,
            )
            step_results.append(("attach_replicat", replicat_result))
            self._raise_if_step_failed("attach_replicat", replicat_result)

        if artifacts_dir is not None and self.activation_service is not None:
            activation_result = self.activation_service.run_activation(
                deployment_id=deployment_id,
                plan=plan,
                artifacts_dir=artifacts_dir,
                action=activation_action,
            )
            step_results.append(("activation", activation_result))
            self._raise_if_step_failed("activation", activation_result)

        if artifacts_dir is not None:
            status_report = self.rerun_analysis_service.build_report(
                deployment_id=deployment_id,
                environment_name=environment_name,
                desired_configs=desired_configs,
                current_registry=self.registry_repo.list_all(),
            )
            self.artifact_renderer.render_status_report(
                report=status_report,
                output_dir=artifacts_dir,
            )

            execution_summary = self.deployment_execution_summary_service.build_summary(
                deployment_id=deployment_id,
                environment_name=environment_name,
                step_results=step_results,
            )
            self.artifact_renderer.render_execution_summary(
                summary=execution_summary,
                output_dir=artifacts_dir,
            )

            reconciliation_report = self.reconciliation_service.build_report(
                deployment_id=deployment_id,
                environment_name=environment_name,
                desired_configs=desired_configs,
                current_registry=self.registry_repo.list_all(),
                extract_probe_results=extract_probe_results,
                replicat_probe_results=replicat_probe_results,
            )
            self.artifact_renderer.render_reconciliation_report(
                report=reconciliation_report,
                output_dir=artifacts_dir,
            )

        return plan

    def _register_new_table(self, deployment_id: str, action) -> None:
        payload = dict(action.payload or {})
        self.registry_repo.register_new_table(
            payload=payload,
            deployment_id=deployment_id,
        )
        self.event_repo.add_event(
            TableEvent(
                table_id=action.table_id,
                deployment_id=deployment_id,
                event_type=EventType.TABLE_REGISTERED,
                event_status=EventStatus.SUCCESS,
                step_name="register_table",
                event_ts=None,
                payload_json=json.dumps(payload, ensure_ascii=False),
                error_code=None,
                error_message=None,
                created_by=None,
            )
        )

    def _update_existing_table(self, deployment_id: str, action) -> None:
        if not action.table_id:
            return

        current = self.registry_repo.get_by_table_id(action.table_id)
        if current is None:
            return

        self.registry_repo.update_desired_state(
            table_id=action.table_id,
            changes=dict(action.payload or {}),
            deployment_id=deployment_id,
        )

        self.event_repo.add_event(
            TableEvent(
                table_id=action.table_id,
                deployment_id=deployment_id,
                event_type=EventType.DESIRED_STATE_UPDATED,
                event_status=EventStatus.SUCCESS,
                step_name="update_desired_state",
                event_ts=None,
                payload_json=json.dumps(action.payload or {}, ensure_ascii=False),
                error_code=None,
                error_message=None,
                created_by=None,
            )
        )

        if current.state == TableState.ERROR:
            self.replan_error_table(
                table_id=action.table_id,
                deployment_id=deployment_id,
            )

    def _plan_remove_table(self, deployment_id: str, action) -> None:
        if not action.table_id:
            return

        current = self.registry_repo.get_by_table_id(action.table_id)
        if current is None:
            return

        self.state_machine.ensure_transition_allowed(
            current.state,
            TableState.REMOVAL_PLANNED,
        )
        self.registry_repo.update_state(
            table_id=action.table_id,
            state=TableState.REMOVAL_PLANNED,
            deployment_id=deployment_id,
        )
        self.event_repo.add_event(
            TableEvent(
                table_id=action.table_id,
                deployment_id=deployment_id,
                event_type=EventType.REMOVAL_PLANNED,
                event_status=EventStatus.SUCCESS,
                step_name="plan_remove_table",
                event_ts=None,
                payload_json=json.dumps(action.payload or {}, ensure_ascii=False),
                error_code=None,
                error_message=None,
                created_by=None,
            )
        )

    def _mark_table_error(
        self,
        table_id: str,
        deployment_id: str,
        step_name: str,
        error_message: str,
        error_code: str | None = None,
    ) -> None:
        self.registry_repo.mark_error(
            table_id=table_id,
            deployment_id=deployment_id,
            error_code=error_code,
            error_message=error_message,
        )

        self.event_repo.add_event(
            TableEvent(
                table_id=table_id,
                deployment_id=deployment_id,
                event_type=EventType.ERROR_OCCURRED,
                event_status=EventStatus.FAILED,
                step_name=step_name,
                event_ts=None,
                payload_json=json.dumps(
                    {
                        "step_name": step_name,
                        "error_code": error_code,
                        "error_message": error_message,
                        "new_state": TableState.ERROR.value,
                    },
                    ensure_ascii=False,
                ),
                error_code=error_code,
                error_message=error_message,
                created_by=None,
            )
        )

    def replan_error_table(
        self,
        table_id: str,
        deployment_id: str,
    ) -> None:
        current = self.registry_repo.get_by_table_id(table_id)
        if current is None:
            raise ValueError(f"Table not found in registry: {table_id}")

        if current.state != TableState.ERROR:
            return

        self.state_machine.ensure_transition_allowed(
            TableState.ERROR,
            TableState.PLANNED,
        )
        self.registry_repo.update_state(
            table_id=table_id,
            state=TableState.PLANNED,
            deployment_id=deployment_id,
        )

        self.event_repo.add_event(
            TableEvent(
                table_id=table_id,
                deployment_id=deployment_id,
                event_type=EventType.ROLLBACK_DONE,
                event_status=EventStatus.SUCCESS,
                step_name="error_replanned",
                event_ts=None,
                payload_json=json.dumps(
                    {
                        "from_state": TableState.ERROR.value,
                        "to_state": TableState.PLANNED.value,
                    },
                    ensure_ascii=False,
                ),
                error_code=None,
                error_message=None,
                created_by=None,
            )
        )