from __future__ import annotations

import json
import os
import sys

import oracledb
from pathlib import Path

from app.config import AppConfig
from app.orchestration.deployment_orchestrator import DeploymentOrchestrator
from app.repositories.deployment_repo import DeploymentRepository
from app.repositories.desired_state_repo import DesiredStateRepository
from app.repositories.event_repo import EventRepository
from app.repositories.group_repo import GroupRepository
from app.repositories.registry_repo import RegistryRepository
from app.services.artifact_renderer import ArtifactRenderer
from app.services.grouping_service import GroupingService
from app.services.planner_service import PlannerService
from app.services.state_machine_service import StateMachineService
from app.utils.ids import generate_deployment_id
from app.services.prepare_source_service import PrepareSourceService

from app.executors.prepare_source_executor import (
    DryRunPrepareExecutor,
    FileOnlyPrepareExecutor,
)
from app.services.prepare_source_service import PrepareSourceService

from app.executors.extract_attach_executor import (
    DryRunExtractAttachExecutor,
    FileOnlyExtractAttachExecutor,
)
from app.services.attach_extract_service import AttachExtractService

from app.executors.initial_load_executor import (
    DryRunInitialLoadExecutor,
    FileOnlyInitialLoadExecutor,
)
from app.services.initial_load_service import InitialLoadService

from app.executors.instantiation_executor import (
    DryRunInstantiationExecutor,
    FileOnlyInstantiationExecutor,
)
from app.services.instantiation_service import InstantiationService

from app.executors.replicat_attach_executor import (
    DryRunReplicatAttachExecutor,
    FileOnlyReplicatAttachExecutor,
)
from app.services.attach_replicat_service import AttachReplicatService

from app.executors.activation_executor import (
    DryRunActivationExecutor,
    FileOnlyActivationExecutor,
)
from app.services.activation_service import ActivationService

from app.services.rerun_analysis_service import RerunAnalysisService
from app.services.step_execution_policy_service import StepExecutionPolicyService

from app.integrations.ogg_rest_client import OGGRestClient, OGGRestConfig
from app.executors.ogg_rest_prepare_executor import OGGRestPrepareExecutor
from app.executors.ogg_rest_extract_attach_executor import OGGRestExtractAttachExecutor
from app.executors.ogg_rest_replicat_attach_executor import OGGRestReplicatAttachExecutor
from app.repositories.table_metadata_repo import TableMetadataRepository

from app.services.deployment_execution_summary_service import DeploymentExecutionSummaryService
from app.services.extract_status_probe_service import ExtractStatusProbeService
from app.services.replicat_status_probe_service import ReplicatStatusProbeService
from app.services.service_schema_validator import ServiceSchemaValidator
from app.utils.schema_validation_artifact import write_schema_validation_report
from app.services.reconciliation_service import ReconciliationService
from app.executors.script_initial_load_executor import ScriptInitialLoadExecutor
from app.services.cdc_config_render_service import CDCConfigRenderService
from app.utils.effective_config_artifact import write_effective_config_artifact

from app.executors.attach_extract_executor import (
    FileOnlyAttachExtractExecutor,
    ScriptAttachExtractExecutor,
)
from app.executors.attach_replicat_executor import (
    FileOnlyAttachReplicatExecutor,
    ScriptAttachReplicatExecutor,
)

from app.services.group_bootstrap_planner_service import GroupBootstrapPlannerService
from app.services.group_bootstrap_service import GroupBootstrapService
from app.services.ogg_base_config_factory import OGGBaseConfigFactory
from app.services.ogg_process_bootstrap_service import OGGProcessBootstrapService
from app.services.desired_state_snapshot_builder import DesiredStateSnapshotBuilder


def build_desired_state_snapshot_if_configured(cfg: AppConfig) -> dict[str, object] | None:
    if not cfg.build_desired_state_from_metadata:
        return None

    repo = TableMetadataRepository()
    builder = DesiredStateSnapshotBuilder()

    configs = repo.load_from_directory(cfg.metadata_dir)
    snapshot = builder.build_snapshot(
        environment=cfg.environment_name,
        configs=configs,
        git_commit_sha=cfg.git_commit_sha,
        git_branch=cfg.git_branch,
        source_dir=cfg.metadata_dir,
    )
    builder.write_snapshot(snapshot, cfg.desired_state_path)
    return {
        "tables_count": len(configs),
        "output_path": cfg.desired_state_path,
        "metadata_dir": cfg.metadata_dir,
    }

def main() -> int:
    cfg = AppConfig.from_env()
    cfg.validate()
    connection = None
    plan = None

    Path("artifacts").mkdir(parents=True, exist_ok=True)
    write_effective_config_artifact(cfg, "artifacts")

    snapshot_build_info = build_desired_state_snapshot_if_configured(cfg)
    if snapshot_build_info is not None:
        print(
            json.dumps(
                {
                    "message": "desired_state_snapshot_built",
                    **snapshot_build_info,
                },
                ensure_ascii=False,
            )
        )

    def build_ogg_rest_client(cfg: AppConfig) -> OGGRestClient:
        if not cfg.ogg_rest_base_url:
            raise ValueError("OGG_REST_BASE_URL is required for OGG_REST executors")
        if not cfg.ogg_rest_deployment_name:
            raise ValueError("OGG_REST_DEPLOYMENT_NAME is required for OGG_REST executors")

        return OGGRestClient(
            OGGRestConfig(
                base_url=cfg.ogg_rest_base_url,
                username=cfg.ogg_rest_username,
                password=cfg.ogg_rest_password,
                deployment_name=cfg.ogg_rest_deployment_name,
                verify_ssl=cfg.ogg_rest_verify_ssl,
                mode=cfg.ogg_rest_mode,
            )
        )





    desired_state_repo = DesiredStateRepository()
    environment_from_snapshot, revision, desired_configs = desired_state_repo.load_snapshot(
        cfg.desired_state_path
    )

    environment_name = environment_from_snapshot or cfg.environment_name
    artifacts_dir = os.getenv("ARTIFACTS_DIR", "artifacts")

    deployment_id = generate_deployment_id()

    print(
        json.dumps(
            {
                "message": "starting_deployment",
                "deployment_id": deployment_id,
                "environment_name": environment_name,
                "desired_tables": len(desired_configs),
                "snapshot_revision": revision,
            },
            ensure_ascii=False,
        )
    )

    connection = oracledb.connect(
        user=cfg.oracle_user,
        password=cfg.oracle_password,
        dsn=cfg.oracle_dsn,
    )

    try:
        registry_repo = RegistryRepository(connection)
        event_repo = EventRepository(connection)
        deployment_repo = DeploymentRepository(connection)
        group_repo = GroupRepository(connection)

        planner_service = PlannerService()
        state_machine = StateMachineService()
        grouping_service = GroupingService()
        artifact_renderer = ArtifactRenderer()

        deployment_execution_summary_service = DeploymentExecutionSummaryService()

        if cfg.prepare_source_executor == "DRY_RUN":
            prepare_executor = DryRunPrepareExecutor()
        elif cfg.prepare_source_executor == "FILE_ONLY":
            prepare_executor = FileOnlyPrepareExecutor()
        elif cfg.prepare_source_executor in {"OGG_REST_SKELETON", "OGG_REST_REAL"}:
            if cfg.prepare_source_executor == "OGG_REST_REAL" and not cfg.allow_real_prepare_source:
                raise ValueError(
                    "OGG_REST_REAL for prepare_source requires ALLOW_REAL_PREPARE_SOURCE=true"
                )
            prepare_executor = OGGRestPrepareExecutor(
                build_ogg_rest_client(cfg),
                connection_name=cfg.ogg_rest_connection,
                trandata_scope=cfg.trandata_scope,
            )
        else:
            raise ValueError(f"Unsupported prepare executor: {cfg.prepare_source_executor}")

        step_policy_service = StepExecutionPolicyService()
        
        prepare_source_service = PrepareSourceService(
            registry_repo=registry_repo,
            event_repo=event_repo,
            state_machine=state_machine,
            executor=prepare_executor,
            step_policy=step_policy_service,
        )        

        if cfg.attach_extract_executor == "DRY_RUN":
            attach_extract_executor = FileOnlyAttachExtractExecutor()
        elif cfg.attach_extract_executor == "FILE_ONLY":
            attach_extract_executor = FileOnlyAttachExtractExecutor()
        elif cfg.attach_extract_executor == "SCRIPT":
            attach_extract_executor = ScriptAttachExtractExecutor(
                script_command=cfg.attach_extract_script_command,
                timeout_sec=cfg.attach_extract_script_timeout_sec,
            )
        else:
            # временно оставляем skeleton/rest режимы совместимыми через file-only,
            # пока не сделаем отдельный real apply backend
            attach_extract_executor = FileOnlyAttachExtractExecutor()

        attach_extract_service = AttachExtractService(
            registry_repo=registry_repo,
            event_repo=event_repo,
            state_machine=state_machine,
            executor=attach_extract_executor,
            step_policy=step_policy_service,
        )

        if cfg.initial_load_executor == "DRY_RUN":
            initial_load_executor = DryRunInitialLoadExecutor()
        elif cfg.initial_load_executor == "FILE_ONLY":
            initial_load_executor = FileOnlyInitialLoadExecutor()
        elif cfg.initial_load_executor == "SCRIPT":
            initial_load_executor = ScriptInitialLoadExecutor(
                script_command=cfg.initial_load_script_command,
                timeout_sec=cfg.initial_load_script_timeout_sec,
            )
        else:
            raise ValueError(f"Unsupported initial load executor: {cfg.initial_load_executor}")

        initial_load_service = InitialLoadService(
            registry_repo=registry_repo,
            event_repo=event_repo,
            state_machine=state_machine,
            executor=initial_load_executor,
            step_policy=step_policy_service,
        )

        if cfg.instantiation_executor == "DRY_RUN":
            instantiation_executor = DryRunInstantiationExecutor()
        elif cfg.instantiation_executor == "FILE_ONLY":
            instantiation_executor = FileOnlyInstantiationExecutor()
        else:
            raise ValueError(f"Unsupported instantiation executor: {cfg.instantiation_executor}")

        instantiation_service = InstantiationService(
            registry_repo=registry_repo,
            event_repo=event_repo,
            state_machine=state_machine,
            executor=instantiation_executor,
            step_policy=step_policy_service,
        )

        if cfg.attach_replicat_executor == "DRY_RUN":
            attach_replicat_executor = FileOnlyAttachReplicatExecutor()
        elif cfg.attach_replicat_executor == "FILE_ONLY":
            attach_replicat_executor = FileOnlyAttachReplicatExecutor()
        elif cfg.attach_replicat_executor == "SCRIPT":
            attach_replicat_executor = ScriptAttachReplicatExecutor(
                script_command=cfg.attach_replicat_script_command,
                timeout_sec=cfg.attach_replicat_script_timeout_sec,
            )
        else:
            # временно оставляем skeleton/rest режимы совместимыми через file-only,
            # пока не сделаем отдельный real apply backend
            attach_replicat_executor = FileOnlyAttachReplicatExecutor()

        attach_replicat_service = AttachReplicatService(
            registry_repo=registry_repo,
            event_repo=event_repo,
            state_machine=state_machine,
            executor=attach_replicat_executor,
            step_policy=step_policy_service,
        )

        if cfg.activation_executor == "DRY_RUN":
            activation_executor = DryRunActivationExecutor()
        elif cfg.activation_executor == "FILE_ONLY":
            activation_executor = FileOnlyActivationExecutor()
        else:
            raise ValueError(f"Unsupported activation executor: {cfg.activation_executor}")

        activation_service = ActivationService(
            registry_repo=registry_repo,
            event_repo=event_repo,
            state_machine=state_machine,
            executor=activation_executor,
            step_policy=step_policy_service,
        )

        schema_validator = ServiceSchemaValidator(connection)
        schema_validation_result = schema_validator.validate()
        write_schema_validation_report(schema_validation_result, "artifacts")
        cdc_config_render_service = CDCConfigRenderService()



        if not schema_validation_result.ok:
            issue_lines = [
                f"{x.table_name}.{x.column_name}: {x.issue_type} "
                f"(expected {x.expected_type_prefix}, actual {x.actual_type})"
                for x in schema_validation_result.issues
            ]
            raise ValueError(
                "Service schema validation failed: " + "; ".join(issue_lines)
            )

        reconciliation_service = ReconciliationService()


        rerun_analysis_service = RerunAnalysisService()


        extract_status_probe_service = None
        replicat_status_probe_service = None

        if cfg.prepare_source_executor in {"OGG_REST_SKELETON", "OGG_REST_REAL"} \
           or cfg.attach_extract_executor == "OGG_REST_SKELETON" \
           or cfg.attach_replicat_executor == "OGG_REST_SKELETON":
            ogg_rest_client = build_ogg_rest_client(cfg)
            extract_status_probe_service = ExtractStatusProbeService(ogg_rest_client)
            replicat_status_probe_service = ReplicatStatusProbeService(ogg_rest_client)


        group_bootstrap_planner_service = GroupBootstrapPlannerService(
            config_factory=OGGBaseConfigFactory(),
            extract_credential_alias="GGADMIN",
            replicat_credential_alias="TARGET_DB_CONN",
            extract_credential_domain="OracleGoldenGate",
            replicat_credential_domain=None,
            default_trail_name="lt",
            default_extract_integrated=True,
        )

        ogg_process_bootstrap_service = None
        if cfg.ogg_rest_base_url and cfg.ogg_rest_deployment_name:
            ogg_process_bootstrap_service = OGGProcessBootstrapService(
                client=build_ogg_rest_client(cfg),
            )

        group_bootstrap_service = GroupBootstrapService(
            group_repo=group_repo,
            ogg_process_bootstrap_service=ogg_process_bootstrap_service,
        )


        orchestrator = DeploymentOrchestrator(
            registry_repo=registry_repo,
            event_repo=event_repo,
            deployment_repo=deployment_repo,
            group_repo=group_repo,
            planner_service=planner_service,
            state_machine=state_machine,
            grouping_service=grouping_service,
            artifact_renderer=artifact_renderer,
            prepare_source_service=prepare_source_service,
            attach_extract_service=attach_extract_service,
            initial_load_service=initial_load_service,
            instantiation_service=instantiation_service,
            attach_replicat_service=attach_replicat_service,
            activation_service=activation_service,
            rerun_analysis_service = rerun_analysis_service,
            deployment_execution_summary_service=deployment_execution_summary_service,
            extract_status_probe_service=extract_status_probe_service,
            replicat_status_probe_service=replicat_status_probe_service,
            reconciliation_service=reconciliation_service,
            cdc_config_render_service=cdc_config_render_service,
            group_bootstrap_planner_service=group_bootstrap_planner_service,
            group_bootstrap_service=group_bootstrap_service,
        )

        plan = orchestrator.build_and_apply_registry_changes(
            deployment_id=deployment_id,
            environment_name=environment_name,
            git_branch=cfg.git_branch,
            git_commit_sha=cfg.git_commit_sha,
            pipeline_id=cfg.pipeline_id,
            desired_configs=desired_configs,
            artifacts_dir=artifacts_dir,
            prepare_source_action=cfg.prepare_source_action,
            attach_extract_action=cfg.attach_extract_action,
            initial_load_action=cfg.initial_load_action,
            instantiation_action=cfg.instantiation_action,
            attach_replicat_action=cfg.attach_replicat_action,
            activation_action=cfg.activation_action,
        )

        deployment_repo.finish(
            deployment_id=deployment_id,
            status="COMPLETED",
        )
        connection.commit()

        print(
            json.dumps(
                {
                    "message": "deployment_completed",
                    "deployment_id": deployment_id,
                    "actions_count": len(plan.actions),
                    "artifacts_dir": artifacts_dir,
                },
                ensure_ascii=False,
            )
        )
        return 0

    except Exception as exc:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass

            try:
                DeploymentRepository(connection).record_failure(
                    deployment_id=deployment_id,
                    environment_name=environment_name,
                    git_branch=cfg.git_branch,
                    git_commit_sha=cfg.git_commit_sha,
                    pipeline_id=cfg.pipeline_id,
                    error_message=str(exc),
                    plan=plan,
                )
                connection.commit()
            except Exception as audit_exc:
                print(
                    json.dumps(
                        {
                            "message": "deployment_failure_audit_failed",
                            "deployment_id": deployment_id,
                            "error": str(audit_exc),
                        },
                        ensure_ascii=False,
                    ),
                    file=sys.stderr,
                )
        print(
            json.dumps(
                {
                    "message": "deployment_failed",
                    "error": str(exc),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
