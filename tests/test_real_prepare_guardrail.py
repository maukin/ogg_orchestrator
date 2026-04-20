import pytest

from app.config import AppConfig


def test_real_prepare_requires_explicit_allow_flag():
    cfg = AppConfig(
        oracle_user="u",
        oracle_password="p",
        oracle_dsn="dsn",
        environment_name="dev",
        build_desired_state_from_metadata=False,
        metadata_dir="metadata",
        desired_state_path="registry/desired_state.json",
        git_branch=None,
        git_commit_sha=None,
        pipeline_id=None,
        prepare_source_mode="DRY_RUN",
        prepare_source_executor="OGG_REST_REAL",
        attach_extract_mode="DRY_RUN",
        attach_extract_executor="DRY_RUN",
        initial_load_mode="DRY_RUN",
        initial_load_executor="DRY_RUN",
        instantiation_mode="DRY_RUN",
        instantiation_executor="DRY_RUN",
        attach_replicat_mode="DRY_RUN",
        attach_replicat_executor="DRY_RUN",
        activation_mode="DRY_RUN",
        activation_executor="DRY_RUN",
        ogg_rest_base_url="http://localhost:9001",
        ogg_rest_username="",
        ogg_rest_password="",
        ogg_rest_deployment_name="DEPLOY1",
        ogg_rest_verify_ssl=False,
        ogg_rest_mode="OGG_REST_REAL",
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

    with pytest.raises(ValueError, match="ALLOW_REAL_PREPARE_SOURCE=true"):
        if cfg.prepare_source_executor == "OGG_REST_REAL" and not cfg.allow_real_prepare_source:
            raise ValueError(
                "OGG_REST_REAL for prepare_source requires ALLOW_REAL_PREPARE_SOURCE=true"
            )
