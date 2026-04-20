from __future__ import annotations

import json
from typing import Any

from app.models.deployment import DeploymentPlan
from app.utils.oracle_types import read_lob


class DeploymentRepository:
    def __init__(self, connection):
        self.connection = connection

    def start(
        self,
        deployment_id: str,
        environment_name: str,
        git_branch: str | None,
        git_commit_sha: str | None,
        pipeline_id: str | None,
        plan: DeploymentPlan,
    ) -> None:
        sql = """
            INSERT INTO etl_deployments (
                deployment_id,
                environment_name,
                git_branch,
                git_commit_sha,
                pipeline_id,
                trigger_source,
                status,
                plan_json,
                rollback_plan_json,
                started_at,
                initiated_by,
                created_at,
                error_message
            )
            VALUES (
                :deployment_id,
                :environment_name,
                :git_branch,
                :git_commit_sha,
                :pipeline_id,
                :trigger_source,
                :status,
                :plan_json,
                :rollback_plan_json,
                SYSTIMESTAMP,
                :initiated_by,
                SYSTIMESTAMP,
                :error_message
            )
        """

        plan_payload = {
            "deployment_id": plan.deployment_id,
            "environment_name": plan.environment_name,
            "git_branch": plan.git_branch,
            "git_commit_sha": plan.git_commit_sha,
            "pipeline_id": plan.pipeline_id,
            "actions_count": len(plan.actions),
            "actions": [
                {
                    "action_type": action.action_type,
                    "table_id": action.table_id,
                    "group_name": action.group_name,
                    "payload": action.payload,
                }
                for action in plan.actions
            ],
        }

        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "deployment_id": deployment_id,
                    "environment_name": environment_name,
                    "git_branch": git_branch,
                    "git_commit_sha": git_commit_sha,
                    "pipeline_id": pipeline_id,
                    "trigger_source": "ORCHESTRATOR",
                    "status": "STARTED",
                    "plan_json": json.dumps(plan_payload, ensure_ascii=False),
                    "rollback_plan_json": None,
                    "initiated_by": "SYSTEM",
                    "error_message": None,
                },
            )

    def finish(
        self,
        deployment_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        sql = """
            UPDATE etl_deployments
               SET status = :status,
                   finished_at = SYSTIMESTAMP,
                   error_message = :error_message
             WHERE deployment_id = :deployment_id
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                {
                    "deployment_id": deployment_id,
                    "status": status,
                    "error_message": error_message,
                },
            )

    def record_failure(
        self,
        deployment_id: str,
        environment_name: str,
        git_branch: str | None,
        git_commit_sha: str | None,
        pipeline_id: str | None,
        error_message: str | None,
        plan: DeploymentPlan | None = None,
    ) -> None:
        update_sql = """
            UPDATE etl_deployments
               SET status = :status,
                   finished_at = SYSTIMESTAMP,
                   error_message = :error_message
             WHERE deployment_id = :deployment_id
        """
        insert_sql = """
            INSERT INTO etl_deployments (
                deployment_id,
                environment_name,
                git_branch,
                git_commit_sha,
                pipeline_id,
                trigger_source,
                status,
                plan_json,
                rollback_plan_json,
                started_at,
                finished_at,
                initiated_by,
                created_at,
                error_message
            )
            VALUES (
                :deployment_id,
                :environment_name,
                :git_branch,
                :git_commit_sha,
                :pipeline_id,
                :trigger_source,
                :status,
                :plan_json,
                :rollback_plan_json,
                SYSTIMESTAMP,
                SYSTIMESTAMP,
                :initiated_by,
                SYSTIMESTAMP,
                :error_message
            )
        """
        params = {
            "deployment_id": deployment_id,
            "status": "FAILED",
            "error_message": error_message,
        }
        with self.connection.cursor() as cursor:
            cursor.execute(update_sql, params)
            if cursor.rowcount:
                return

            cursor.execute(
                insert_sql,
                {
                    "deployment_id": deployment_id,
                    "environment_name": environment_name,
                    "git_branch": git_branch,
                    "git_commit_sha": git_commit_sha,
                    "pipeline_id": pipeline_id,
                    "trigger_source": "ORCHESTRATOR",
                    "status": "FAILED",
                    "plan_json": self._build_plan_json(plan),
                    "rollback_plan_json": None,
                    "initiated_by": "SYSTEM",
                    "error_message": error_message,
                },
            )

    @staticmethod
    def _build_plan_json(plan: DeploymentPlan | None) -> str | None:
        if plan is None:
            return None

        plan_payload = {
            "deployment_id": plan.deployment_id,
            "environment_name": plan.environment_name,
            "git_branch": plan.git_branch,
            "git_commit_sha": plan.git_commit_sha,
            "pipeline_id": plan.pipeline_id,
            "actions_count": len(plan.actions),
            "actions": [
                {
                    "action_type": action.action_type,
                    "table_id": action.table_id,
                    "group_name": action.group_name,
                    "payload": action.payload,
                }
                for action in plan.actions
            ],
        }
        return json.dumps(plan_payload, ensure_ascii=False)

    def get(self, deployment_id: str) -> dict[str, Any] | None:
        sql = """
            SELECT
                deployment_id,
                environment_name,
                git_branch,
                git_commit_sha,
                pipeline_id,
                trigger_source,
                status,
                plan_json,
                rollback_plan_json,
                started_at,
                finished_at,
                initiated_by,
                created_at,
                error_message
            FROM etl_deployments
            WHERE deployment_id = :deployment_id
        """

        with self.connection.cursor() as cursor:
            cursor.execute(sql, {"deployment_id": deployment_id})
            row = cursor.fetchone()

        if row is None:
            return None

        return {
            "deployment_id": row[0],
            "environment_name": row[1],
            "git_branch": row[2],
            "git_commit_sha": row[3],
            "pipeline_id": row[4],
            "trigger_source": row[5],
            "status": row[6],
            "plan_json": read_lob(row[7]),
            "rollback_plan_json": read_lob(row[8]),
            "started_at": row[9],
            "finished_at": row[10],
            "initiated_by": row[11],
            "created_at": row[12],
            "error_message": read_lob(row[13]),
        }
