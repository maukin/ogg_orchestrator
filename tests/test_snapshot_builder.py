from app.models.enums import LoadMethod, ReplicationMode
from app.models.registry import DesiredTableConfig
from app.services.desired_state_snapshot_builder import DesiredStateSnapshotBuilder


def test_build_snapshot():
    configs = [
        DesiredTableConfig(
            source_system="SRCDB",
            source_pdb="PDB1",
            source_schema="SRC",
            source_table="ORDERS",
            target_system="TGTDB",
            target_pdb="PDB2",
            target_schema="DDS",
            target_table="ORDERS",
            desired_enabled=True,
            desired_replication_mode=ReplicationMode.INITIAL_PLUS_CDC,
            desired_extract_group="EXT_01",
            desired_replicat_group="REP_01",
            desired_load_method=LoadMethod.DATAPUMP,
            desired_priority="NORMAL",
            desired_size_class="MEDIUM",
            primary_key=("ID",),
            metadata_file="metadata/orders.json",
        )
    ]

    builder = DesiredStateSnapshotBuilder()
    snapshot = builder.build_snapshot(
        environment="prod",
        configs=configs,
        git_commit_sha="abc",
        git_branch="feature/x",
        source_dir="metadata",
    )

    assert snapshot["environment"] == "prod"
    assert snapshot["tables"][0]["source_table"] == "ORDERS"
    assert snapshot["tables"][0]["primary_key"] == ["ID"]