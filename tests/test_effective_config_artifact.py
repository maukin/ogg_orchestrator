import json
from pathlib import Path

from app.config import AppConfig
from app.utils.effective_config_artifact import write_effective_config_artifact


def _artifacts_dir(name: str) -> Path:
    path = Path("artifacts") / "_tests" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_write_effective_config_artifact_masks_passwords():
    cfg = AppConfig(
        oracle_user="user",
        oracle_password="secret",
        oracle_dsn="dsn",
        environment_name="dev",
        build_desired_state_from_metadata=False,
        metadata_dir="metadata",
        desired_state_path="registry/desired_state.json",
        git_branch=None,
        git_commit_sha=None,
        pipeline_id=None,
        prepare_source_action="PLAN_ONLY",
        prepare_source_executor="PLAN_ONLY",
        attach_extract_action="PLAN_ONLY",
        attach_extract_executor="PLAN_ONLY",
        initial_load_action="PLAN_ONLY",
        initial_load_executor="PLAN_ONLY",
        instantiation_action="PLAN_ONLY",
        instantiation_executor="PLAN_ONLY",
        attach_replicat_action="PLAN_ONLY",
        attach_replicat_executor="PLAN_ONLY",
        activation_action="PLAN_ONLY",
        activation_executor="PLAN_ONLY",
        ogg_rest_base_url="http://localhost:9001",
        ogg_rest_username="ogg_user",
        ogg_rest_password="ogg_secret",
        ogg_rest_deployment_name="DEPLOY1",
        ogg_rest_verify_ssl=False,
        ogg_rest_mode="OGG_REST_SKELETON",
        ogg_rest_connection="OracleGoldenGate",
        trandata_scope="TABLE",
        allow_real_prepare_source=False,
        initial_load_script_path="",
        initial_load_script_timeout_sec=3600,
        initial_load_script_command="",
        attach_extract_script_command="",
        attach_extract_script_timeout_sec=1800,
        attach_replicat_script_command="",
        attach_replicat_script_timeout_sec=1800,
    )

    path = write_effective_config_artifact(cfg, _artifacts_dir("effective_config_artifact"))
    payload = json.loads(Path(path).read_text(encoding="utf-8"))

    assert payload["oracle_password"] == "***"
    assert payload["ogg_rest_password"] == "***"
