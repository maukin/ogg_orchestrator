import pytest

from app.config import AppConfig


def test_attach_extract_script_requires_command():
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
        prepare_source_executor="DRY_RUN",
        attach_extract_mode="DRY_RUN",
        attach_extract_executor="SCRIPT",
        attach_extract_script_command="",
        attach_extract_script_timeout_sec=1800,
        initial_load_mode="DRY_RUN",
        initial_load_executor="DRY_RUN",
        initial_load_script_path="",
        initial_load_script_timeout_sec=3600,
        initial_load_script_command="",
        instantiation_mode="DRY_RUN",
        instantiation_executor="DRY_RUN",
        attach_replicat_mode="DRY_RUN",
        attach_replicat_executor="DRY_RUN",
        attach_replicat_script_command="",
        attach_replicat_script_timeout_sec=1800,
        activation_mode="DRY_RUN",
        activation_executor="DRY_RUN",
        ogg_rest_base_url="http://localhost:9001",
        ogg_rest_username="",
        ogg_rest_password="",
        ogg_rest_deployment_name="DEPLOY1",
        ogg_rest_verify_ssl=False,
        ogg_rest_mode="OGG_REST_SKELETON",
        ogg_rest_connection="OracleGoldenGate",
        trandata_scope="TABLE",
        allow_real_prepare_source=False,
    )

    with pytest.raises(ValueError, match="ATTACH_EXTRACT_SCRIPT_COMMAND"):
        cfg.validate()


def test_attach_replicat_script_requires_command():
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
        prepare_source_executor="DRY_RUN",
        attach_extract_mode="DRY_RUN",
        attach_extract_executor="DRY_RUN",
        attach_extract_script_command="",
        attach_extract_script_timeout_sec=1800,
        initial_load_mode="DRY_RUN",
        initial_load_executor="DRY_RUN",
        initial_load_script_path="",
        initial_load_script_timeout_sec=3600,
        initial_load_script_command="",
        instantiation_mode="DRY_RUN",
        instantiation_executor="DRY_RUN",
        attach_replicat_mode="DRY_RUN",
        attach_replicat_executor="SCRIPT",
        attach_replicat_script_command="",
        attach_replicat_script_timeout_sec=1800,
        activation_mode="DRY_RUN",
        activation_executor="DRY_RUN",
        ogg_rest_base_url="http://localhost:9001",
        ogg_rest_username="",
        ogg_rest_password="",
        ogg_rest_deployment_name="DEPLOY1",
        ogg_rest_verify_ssl=False,
        ogg_rest_mode="OGG_REST_SKELETON",
        ogg_rest_connection="OracleGoldenGate",
        trandata_scope="TABLE",
        allow_real_prepare_source=False,
    )

    with pytest.raises(ValueError, match="ATTACH_REPLICAT_SCRIPT_COMMAND"):
        cfg.validate()


def test_ogg_rest_verify_ssl_defaults_to_true(monkeypatch):
    monkeypatch.setenv("ORACLE_USER", "u")
    monkeypatch.setenv("ORACLE_PASSWORD", "p")
    monkeypatch.setenv("ORACLE_DSN", "dsn")
    monkeypatch.delenv("OGG_REST_VERIFY_SSL", raising=False)
    monkeypatch.delenv("BUILD_DESIRED_STATE_FROM_METADATA", raising=False)
    monkeypatch.delenv("METADATA_DIR", raising=False)

    cfg = AppConfig.from_env()

    assert cfg.ogg_rest_verify_ssl is True
    assert cfg.build_desired_state_from_metadata is False
    assert cfg.metadata_dir == "metadata"
