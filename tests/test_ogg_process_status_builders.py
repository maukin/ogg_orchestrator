from app.integrations.ogg_process_status_builders import (
    ExtractStatusRequestBuilder,
    ReplicatStatusRequestBuilder,
)


def test_extract_status_request_builder():
    builder = ExtractStatusRequestBuilder()
    request = builder.build("EXT_01")

    assert request.process_type == "EXTRACT"
    assert request.process_name == "EXT_01"
    assert request.endpoint == "/services/v2/extracts"
    assert request.artifact_prefix == "ogg_rest_extract_status"


def test_replicat_status_request_builder():
    builder = ReplicatStatusRequestBuilder()
    request = builder.build("REP_01")

    assert request.process_type == "REPLICAT"
    assert request.process_name == "REP_01"
    assert request.endpoint == "/services/v2/replicats"
    assert request.artifact_prefix == "ogg_rest_replicat_status"