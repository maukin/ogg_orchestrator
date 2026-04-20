from app.models.enums import LoadMethod, ReplicationMode
from app.models.registry import DesiredTableConfig
from app.services.cdc_config_render_service import CDCConfigRenderService


def test_cdc_config_render_service_builds_extract_and_replicat_fragments():
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
        ),
        DesiredTableConfig(
            source_system="SRCDB",
            source_pdb="PDB1",
            source_schema="SRC",
            source_table="CUSTOMERS",
            target_system="TGTDB",
            target_pdb="PDB2",
            target_schema="DDS",
            target_table="CUSTOMERS",
            desired_enabled=True,
            desired_replication_mode=ReplicationMode.INITIAL_PLUS_CDC,
            desired_extract_group="EXT_01",
            desired_replicat_group="REP_01",
            desired_load_method=LoadMethod.DATAPUMP,
            desired_priority="NORMAL",
            desired_size_class="SMALL",
            primary_key=("CUSTOMER_ID",),
            metadata_file="metadata/customers.json",
        ),
    ]

    svc = CDCConfigRenderService()
    bundle = svc.build_bundle(configs)

    assert len(bundle.extract_groups) == 1
    assert len(bundle.replicat_groups) == 1
    assert "TABLE SRC.ORDERS;" in bundle.extract_groups[0].lines
    assert "TABLE SRC.CUSTOMERS;" in bundle.extract_groups[0].lines
    assert "MAP SRC.ORDERS, TARGET DDS.ORDERS;" in bundle.replicat_groups[0].lines
    assert "MAP SRC.CUSTOMERS, TARGET DDS.CUSTOMERS;" in bundle.replicat_groups[0].lines


def test_cdc_config_render_service_skips_replicat_for_initial_load_only():
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
            desired_replication_mode=ReplicationMode.INITIAL_LOAD_ONLY,
            desired_extract_group="EXT_01",
            desired_replicat_group="REP_01",
            desired_load_method=LoadMethod.DATAPUMP,
            desired_priority="NORMAL",
            desired_size_class="MEDIUM",
            primary_key=("ID",),
            metadata_file="metadata/orders.json",
        )
    ]

    svc = CDCConfigRenderService()
    bundle = svc.build_bundle(configs)

    assert len(bundle.extract_groups) == 1
    assert bundle.extract_groups[0].lines == ["TABLE SRC.ORDERS;"]
    assert bundle.replicat_groups == []
