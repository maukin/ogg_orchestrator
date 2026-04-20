from __future__ import annotations

import json
from pathlib import Path

from app.models.group_bootstrap import GroupBootstrapRequest
from app.services.group_bootstrap_service import GroupBootstrapService


class FakeGroupRepo:
    def __init__(self):
        self.created_groups = []

    def create_group(self, config):
        self.created_groups.append(config)


class FailingGroupRepo:
    def create_group(self, config):
        raise RuntimeError("insert failed")


def _request() -> GroupBootstrapRequest:
    return GroupBootstrapRequest(
        group_name="EXT_NEW",
        group_type="extract",
        environment_name="dev",
        source_system="SRCDB",
        target_system="TGTDB",
        credential_alias="GGADMIN",
        credential_domain="OracleGoldenGate",
        trail_name="lt",
        mode="INTEGRATED",
        base_config_lines=[
            "EXTRACT EXT_NEW",
            "USERIDALIAS GGADMIN",
            "EXTTRAIL lt",
            "TRANLOGOPTIONS INTEGRATEDPARAMS (max_sga_size 128)",
        ],
        notes="Auto-bootstrap extract group from desired state.",
    )


def test_group_bootstrap_service_success(tmp_path: Path):
    repo = FakeGroupRepo()
    service = GroupBootstrapService(group_repo=repo)

    result = service.bootstrap(
        request=_request(),
        artifacts_dir=tmp_path,
    )

    assert result.success is True
    assert result.group_name == "EXT_NEW"
    assert result.group_type == "extract"
    assert result.error_code is None
    assert result.error_message is None
    assert result.request_artifact is not None
    assert result.response_artifact is not None

    assert len(repo.created_groups) == 1
    created = repo.created_groups[0]
    assert created.group_name == "EXT_NEW"
    assert created.group_type == "extract"
    assert created.environment_name == "dev"

    request_path = Path(result.request_artifact)
    response_path = Path(result.response_artifact)

    assert request_path.exists()
    assert response_path.exists()

    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    response_payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert request_payload["group_name"] == "EXT_NEW"
    assert request_payload["group_type"] == "extract"
    assert request_payload["credential_alias"] == "GGADMIN"
    assert "EXTRACT EXT_NEW" in request_payload["base_config_lines"]

    assert response_payload["success"] is True
    assert response_payload["group_name"] == "EXT_NEW"
    assert response_payload["group_type"] == "extract"


def test_group_bootstrap_service_failure(tmp_path: Path):
    repo = FailingGroupRepo()
    service = GroupBootstrapService(group_repo=repo)

    result = service.bootstrap(
        request=_request(),
        artifacts_dir=tmp_path,
    )

    assert result.success is False
    assert result.group_name == "EXT_NEW"
    assert result.group_type == "extract"
    assert result.error_code == "GROUP_BOOTSTRAP_FAILED"
    assert "insert failed" in (result.error_message or "")

    assert result.request_artifact is not None
    assert result.response_artifact is not None

    request_path = Path(result.request_artifact)
    response_path = Path(result.response_artifact)

    assert request_path.exists()
    assert response_path.exists()

    response_payload = json.loads(response_path.read_text(encoding="utf-8"))
    assert response_payload["success"] is False
    assert "insert failed" in response_payload["message"]