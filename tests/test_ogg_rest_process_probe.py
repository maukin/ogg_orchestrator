from app.integrations.ogg_rest_client import OGGRestClient, OGGRestConfig
from app.integrations.ogg_process_status_builders import ExtractStatusRequestBuilder


def test_probe_process_status_in_skeleton_mode(tmp_path):
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

    request = ExtractStatusRequestBuilder().build("EXT_01")
    result = client.probe_process_status(request=request, artifacts_dir=tmp_path)

    assert result.success is True
    assert result.request_artifact is not None
    assert result.response_artifact is not None