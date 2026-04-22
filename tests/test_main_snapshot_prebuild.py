import json
from pathlib import Path

from app.config import AppConfig
from app.repositories.desired_state_repo import DesiredStateRepository
from main import build_desired_state_snapshot_if_configured


def _work_dir(name: str) -> Path:
    path = Path("artifacts") / "_tests" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_build_desired_state_snapshot_if_configured_builds_snapshot_from_metadata():
    work_dir = _work_dir("main_snapshot_prebuild")
    metadata_dir = work_dir / "metadata" / "dds"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = metadata_dir / "orders.json"
    metadata_path.write_text(
        json.dumps(
            {
                "table_name": "orders",
                "schema": "rawdata",
                "meta": {
                    "table_name": "orders",
                    "src_system_schema": "source_user",
                    "tgt_system_schema": "rawdata",
                    "cdc": {
                        "enabled": True,
                        "replication_action": "INITIAL_PLUS_CDC",
                        "source_system": "SRCDB",
                        "source_pdb": "SRCPDB",
                        "target_system": "TGTDB",
                        "target_pdb": "TGPDB",
                        "extract_group": "EXT_SRC_01",
                        "replicat_group": "REP_TGT_01",
                        "load_method": "DATAPUMP",
                        "priority": "NORMAL",
                        "size_class": "SMALL",
                    },
                },
                "primary_key": ["id"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    desired_state_path = work_dir / "registry" / "desired_state.json"
    cfg = AppConfig(
        oracle_user="u",
        oracle_password="p",
        oracle_dsn="dsn",
        environment_name="dev",
        build_desired_state_from_metadata=True,
        metadata_dir=str(work_dir / "metadata"),
        desired_state_path=str(desired_state_path),
        git_branch="feature/test",
        git_commit_sha="abc123",
        pipeline_id="42",
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
        ogg_rest_username="",
        ogg_rest_password="",
        ogg_rest_deployment_name="DEPLOY1",
        ogg_rest_verify_ssl=True,
        ogg_rest_mode="OGG_REST_SKELETON",
        allow_real_prepare_source=False,
        ogg_rest_connection="OracleGoldenGate",
        trandata_scope="TABLE",
        initial_load_script_path="",
        initial_load_script_timeout_sec=3600,
        initial_load_script_command="",
        attach_extract_script_command="",
        attach_extract_script_timeout_sec=1800,
        attach_replicat_script_command="",
        attach_replicat_script_timeout_sec=1800,
    )

    build_info = build_desired_state_snapshot_if_configured(cfg)

    assert build_info is not None
    assert build_info["tables_count"] == 1
    assert desired_state_path.exists()

    environment, revision, configs = DesiredStateRepository().load_snapshot(desired_state_path)

    assert environment == "dev"
    assert revision["git_branch"] == "feature/test"
    assert len(configs) == 1
    assert configs[0].source_system == "SRCDB"
    assert configs[0].source_schema == "SOURCE_USER"
    assert configs[0].target_schema == "RAWDATA"
    assert configs[0].desired_extract_group == "EXT_SRC_01"
    assert configs[0].desired_replicat_group == "REP_TGT_01"
    assert configs[0].metadata_file.endswith("metadata\\dds\\orders.json") or configs[0].metadata_file.endswith("metadata/dds/orders.json")
