from pathlib import Path

from app.models.cdc_config import CDCConfigBundle, ExtractGroupConfig, ReplicatGroupConfig
from app.services.artifact_renderer import ArtifactRenderer


def test_artifact_renderer_writes_cdc_config_bundle(tmp_path: Path):
    renderer = ArtifactRenderer()

    bundle = CDCConfigBundle(
        extract_groups=[
            ExtractGroupConfig(
                group_name="EXT_01",
                lines=["TABLE SRC.ORDERS;", "TABLE SRC.CUSTOMERS;"],
            )
        ],
        replicat_groups=[
            ReplicatGroupConfig(
                group_name="REP_01",
                lines=["MAP SRC.ORDERS, TARGET DDS.ORDERS;"],
            )
        ],
    )

    renderer.render_cdc_config_bundle(bundle=bundle, output_dir=tmp_path)

    assert (tmp_path / "cdc" / "extract" / "EXT_01.tables.prm").exists()
    assert (tmp_path / "cdc" / "replicat" / "REP_01.maps.prm").exists()