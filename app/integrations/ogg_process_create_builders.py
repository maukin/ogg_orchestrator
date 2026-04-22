from __future__ import annotations

from app.models.ogg_rest import OGGRestRequestSpec
from app.utils.ogg_group_name import validate_ogg_group_name


class ExtractCreateRequestBuilder:
    def build(
        self,
        *,
        group_name: str,
        credential_alias: str,
        credential_domain: str | None,
        trail_name: str,
        mode: str,
        base_config_lines: list[str],
    ) -> OGGRestRequestSpec:
        validate_ogg_group_name(group_name)

        payload = {
            "source": "tranlogs",
            "config": base_config_lines,
            "credentials": {
                "alias": credential_alias,
            },
            "registration": "default",
            "begin": "now",
            "targets": [
                {
                    "name": trail_name,
                    "sizeMB": 500,
                    "sequence": 0,
                    "offset": 0,
                    "remote": False,
                }
            ],
        }

        if credential_domain:
            payload["credentials"]["domain"] = credential_domain

        return OGGRestRequestSpec(
            operation_name="create_extract_group",
            method="POST",
            endpoint=f"/services/v2/extracts/{group_name}",
            payload=payload,
            artifact_name="bootstrap_extract_create_request.json",
        )


class ReplicatCreateRequestBuilder:
    def build(
        self,
        *,
        group_name: str,
        credential_alias: str,
        credential_domain: str | None,
        trail_name: str,
        mode: str,
        base_config_lines: list[str],
    ) -> OGGRestRequestSpec:
        validate_ogg_group_name(group_name)

        config_lines = list(base_config_lines)

        payload = {
            "config": config_lines,
            "source": {
                "name": trail_name,
            },
            "credentials": {
                "alias": credential_alias,
            },
            "checkpoint": {
                "table": "GGADMIN.CHECKPOINT_TAB",
            },
            "mode": {
                "type": "nonintegrated" if mode.upper() == "NONINTEGRATED" else mode.lower(),
                "parallel": False,
            },
        }

        if credential_domain:
            payload["credentials"]["domain"] = credential_domain

        return OGGRestRequestSpec(
            operation_name="create_replicat_group",
            method="POST",
            endpoint=f"/services/v2/replicats/{group_name}",
            payload=payload,
            artifact_name="bootstrap_replicat_create_request.json",
        )