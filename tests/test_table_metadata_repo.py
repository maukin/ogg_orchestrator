from __future__ import annotations

import json
import os
import sys

import oracledb

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


def main() -> int:
    cfg = AppConfig.from_env()
    cfg.validate()

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

        orchestrator = DeploymentOrchestrator(
            registry_repo=registry_repo,
            event_repo=event_repo,
            deployment_repo=deployment_repo,
            group_repo=group_repo,
            planner_service=planner_service,
            state_machine=state_machine,
            grouping_service=grouping_service,
            artifact_renderer=artifact_renderer,
        )

        plan = orchestrator.build_and_apply_registry_changes(
            deployment_id=deployment_id,
            environment_name=environment_name,
            git_branch=cfg.git_branch,
            git_commit_sha=cfg.git_commit_sha,
            pipeline_id=cfg.pipeline_id,
            desired_configs=desired_configs,
            artifacts_dir=artifacts_dir,
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
        connection.rollback()
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
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())