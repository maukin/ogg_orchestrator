from __future__ import annotations

from pathlib import Path

from app.integrations.ogg_process_create_builders import (
    ExtractCreateRequestBuilder,
    ReplicatCreateRequestBuilder,
)
from app.integrations.ogg_rest_client import OGGRestClient
from app.models.executor import ExecutorResult
from app.models.group_bootstrap import GroupBootstrapRequest


class OGGProcessBootstrapService:
    def __init__(self, client: OGGRestClient):
        self.client = client
        self.extract_builder = ExtractCreateRequestBuilder()
        self.replicat_builder = ReplicatCreateRequestBuilder()

    def bootstrap_process(
        self,
        request: GroupBootstrapRequest,
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        if request.group_type == "extract":
            spec = self.extract_builder.build(
                group_name=request.group_name,
                credential_alias=request.credential_alias,
                credential_domain=request.credential_domain,
                trail_name=request.trail_name or "lt",
                mode=request.mode,
                base_config_lines=request.base_config_lines,
            )
            return self.client.execute_spec(spec, artifacts_dir)

        if request.group_type == "replicat":
            spec = self.replicat_builder.build(
                group_name=request.group_name,
                credential_alias=request.credential_alias,
                credential_domain=request.credential_domain,
                trail_name=request.trail_name or "lt",
                mode=request.mode,
                base_config_lines=request.base_config_lines,
            )
            return self.client.execute_spec(spec, artifacts_dir)

        raise ValueError(f"Unsupported group_type for bootstrap: {request.group_type}")