from app.integrations.ogg_rest_payload_builders import (
    OGGRestPreparePayloadBuilder,
    OGGRestExtractAttachPayloadBuilder,
    OGGRestReplicatAttachPayloadBuilder,
)
from app.models.prepare import SourcePrepareCommand
from app.models.extract import ExtractAttachCommand
from app.models.replicat import ReplicatAttachCommand


def test_prepare_payload_builder_table_scope():
    builder = OGGRestPreparePayloadBuilder(
        connection_name="OracleGoldenGate",
        trandata_scope="TABLE",
    )
    spec = builder.build(
        [
            SourcePrepareCommand(
                table_id="T1",
                source_schema="SRC",
                source_table="ORDERS",
                command_type="ADD_TRANDATA",
                command_text="ADD TRANDATA SRC.ORDERS;",
                mode="DRY_RUN",
                reason="TEST",
            )
        ]
    )
    assert spec.method == "POST"
    assert spec.endpoint == "/services/v2/connections/OracleGoldenGate/trandata/table"
    assert spec.payload["items"][0]["schemaName"] == "SRC"
    assert spec.payload["items"][0]["tableName"] == "ORDERS"


def test_prepare_payload_builder_schema_scope():
    builder = OGGRestPreparePayloadBuilder(
        connection_name="OracleGoldenGate",
        trandata_scope="SCHEMA",
    )
    spec = builder.build(
        [
            SourcePrepareCommand(
                table_id="T1",
                source_schema="SRC",
                source_table="ORDERS",
                command_type="ADD_TRANDATA",
                command_text="ADD TRANDATA SRC.ORDERS;",
                mode="DRY_RUN",
                reason="TEST",
            )
        ]
    )
    assert spec.endpoint == "/services/v2/connections/OracleGoldenGate/trandata/schema"
    assert spec.payload["items"][0]["schemaName"] == "SRC"


def test_extract_attach_payload_builder_uses_realistic_patch_endpoint():
    builder = OGGRestExtractAttachPayloadBuilder()
    spec = builder.build(
        [
            ExtractAttachCommand(
                table_id="T1",
                extract_group="EXT_01",
                source_schema="SRC",
                source_table="ORDERS",
                command_type="ADD_TABLE_TO_EXTRACT",
                command_text="EXTRACT EXT_01: ADD TABLE SRC.ORDERS;",
                mode="DRY_RUN",
                reason="TEST",
            )
        ]
    )
    assert spec.method == "PATCH"
    assert spec.endpoint == "/services/v2/extracts/EXT_01"
    assert spec.payload["tableRules"][0]["schemaName"] == "SRC"


def test_replicat_attach_payload_builder_uses_realistic_patch_endpoint():
    builder = OGGRestReplicatAttachPayloadBuilder()
    spec = builder.build(
        [
            ReplicatAttachCommand(
                table_id="T1",
                replicat_group="REP_01",
                source_schema="SRC",
                source_table="ORDERS",
                target_schema="DDS",
                target_table="ORDERS",
                command_type="ADD_MAP_TO_REPLICAT",
                command_text="REPLICAT REP_01: MAP SRC.ORDERS, TARGET DDS.ORDERS;",
                mode="DRY_RUN",
                reason="TEST",
            )
        ]
    )
    assert spec.method == "PATCH"
    assert spec.endpoint == "/services/v2/replicats/REP_01"
    assert spec.payload["mapRules"][0]["sourceSchema"] == "SRC"