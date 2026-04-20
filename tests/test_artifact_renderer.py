import json

from app.models.deployment import DeploymentAction, DeploymentPlan
from app.services.artifact_renderer import ArtifactRenderer


def test_artifact_renderer_writes_summary_and_actions(tmp_path):
    plan = DeploymentPlan(
        deployment_id="dep_1",
        environment_name="dev",
        git_branch=None,
        git_commit_sha=None,
        pipeline_id=None,
        actions=[
            DeploymentAction(
                action_type="REGISTER_NEW_TABLE",
                table_id="T1",
                group_name="REP_01",
                payload={
                    "desired_extract_group": "EXT_01",
                    "desired_replicat_group": "REP_01",
                    "source_schema": "SRC",
                    "source_table": "ORDERS",
                    "target_schema": "DDS",
                    "target_table": "ORDERS",
                },
            ),
            DeploymentAction(
                action_type="PLAN_INITIAL_LOAD",
                table_id="T1",
                group_name="REP_01",
                payload={
                    "source_schema": "SRC",
                    "source_table": "ORDERS",
                    "reason": "NEW_TABLE",
                },
            ),
        ],
    )

    renderer = ArtifactRenderer()
    renderer.render_plan_artifacts(plan, tmp_path)

    assert (tmp_path / "plan_summary.json").exists()
    assert (tmp_path / "deployment_actions.json").exists()
    assert (tmp_path / "source_prereq.sql").exists()

    summary = json.loads((tmp_path / "plan_summary.json").read_text(encoding="utf-8"))
    assert summary["actions_count"] == 2
    assert summary["actions_by_type"]["REGISTER_NEW_TABLE"] == 1
    assert summary["actions_by_type"]["PLAN_INITIAL_LOAD"] == 1