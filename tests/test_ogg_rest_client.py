from app.integrations.ogg_rest_client import OGGRestClient, OGGRestConfig
from app.models.ogg_rest import OGGRestRequestSpec


def test_ogg_rest_client_builds_request_data():
    client = OGGRestClient(
        OGGRestConfig(
            base_url="http://localhost:9001",
            username="user",
            password="pass",
            deployment_name="DEPLOY1",
            verify_ssl=False,
            mode="OGG_REST_SKELETON",
        )
    )

    spec = OGGRestRequestSpec(
        operation_name="prepare_source",
        method="POST",
        endpoint="/services/v2/ogg/prepare-source",
        payload={"hello": "world"},
        artifact_name="request.json",
    )

    request_data = client.build_request_data(spec)

    assert request_data["base_url"] == "http://localhost:9001"
    assert request_data["method"] == "POST"
    assert request_data["endpoint"] == "/services/v2/ogg/prepare-source"
    assert request_data["payload"]["hello"] == "world"
    assert request_data["operation_name"] == "prepare_source"


def test_ogg_rest_client_execute_spec_in_skeleton_mode(tmp_path):
    client = OGGRestClient(
        OGGRestConfig(
            base_url="http://localhost:9001",
            username="user",
            password="pass",
            deployment_name="DEPLOY1",
            verify_ssl=False,
            mode="OGG_REST_SKELETON",
        )
    )

    spec = OGGRestRequestSpec(
        operation_name="prepare_source",
        method="POST",
        endpoint="/services/v2/ogg/prepare-source",
        payload={"hello": "world"},
        artifact_name="ogg_rest_prepare_request.json",
    )

    result = client.execute_spec(spec=spec, artifacts_dir=tmp_path)

    assert result.success is True
    assert result.request_artifact is not None
    assert result.response_artifact is not None