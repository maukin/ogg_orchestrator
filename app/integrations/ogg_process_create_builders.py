from __future__ import annotations

from app.models.ogg_rest import OGGRestRequestSpec


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
        integrated = mode.upper() == "INTEGRATED"

        payload = {
            "name": group_name,
            "config": base_config_lines,
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
            "credentials": {
                "alias": credential_alias,
            },
        }

        if credential_domain:
            payload["credentials"]["domain"] = credential_domain

        if integrated:
            payload["mode"] = {
                "type": "integrated",
            }

        return OGGRestRequestSpec(
            operation_name="create_extract_group",
            method="POST",
            endpoint="/services/v2/extracts",
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
        payload = {
            "name": group_name,
            "config": base_config_lines,
            "source": {
                "name": trail_name,
            },
            "credentials": {
                "alias": credential_alias,
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
            endpoint="/services/v2/replicats",
            payload=payload,
            artifact_name="bootstrap_replicat_create_request.json",
        )