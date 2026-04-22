from __future__ import annotations

import time
from pathlib import Path

from app.integrations.ogg_process_create_builders import (
    ExtractCreateRequestBuilder,
    ReplicatCreateRequestBuilder,
)
from app.integrations.ogg_rest_client import OGGRestClient, OGGProcessStatusRequest
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
            endpoint = "/services/v2/extracts"
            probe_result = self.client.probe_process_status(
                OGGProcessStatusRequest(
                    process_type="extract",
                    process_name=request.group_name,
                    endpoint=endpoint,
                    artifact_prefix=f"bootstrap_probe_extract_{request.group_name}",
                ),
                artifacts_dir=artifacts_dir,
            )

            if probe_result.success:
                return ExecutorResult(
                    success=True,
                    executed_count=0,
                    skipped_count=1,
                    raw_output=f"extract already exists: {request.group_name}",
                    error_code=None,
                    error_message=None,
                    http_status=getattr(probe_result, "http_status", None),
                    request_artifact=getattr(probe_result, "request_artifact", None),
                    response_artifact=getattr(probe_result, "response_artifact", None),
                )

            spec = self.extract_builder.build(
                group_name=request.group_name,
                credential_alias=request.credential_alias,
                credential_domain=request.credential_domain,
                trail_name=request.trail_name or "lt",
                mode=request.mode,
                base_config_lines=request.base_config_lines,
            )
            create_result = self.client.execute_spec(spec, artifacts_dir)

            if not create_result.success:
                return create_result

            return self._wait_until_visible(
                process_type="extract",
                process_name=request.group_name,
                endpoint="/services/v2/extracts",
                artifacts_dir=artifacts_dir,
                request_artifact=create_result.request_artifact,
                response_artifact=create_result.response_artifact,
                raw_output=create_result.raw_output,
                http_status=create_result.http_status,
            )

        if request.group_type == "replicat":
            endpoint = "/services/v2/replicats"
            probe_result = self.client.probe_process_status(
                OGGProcessStatusRequest(
                    process_type="replicat",
                    process_name=request.group_name,
                    endpoint=endpoint,
                    artifact_prefix=f"bootstrap_probe_replicat_{request.group_name}",
                ),
                artifacts_dir=artifacts_dir,
            )

            if probe_result.success:
                return ExecutorResult(
                    success=True,
                    executed_count=0,
                    skipped_count=1,
                    raw_output=f"replicat already exists: {request.group_name}",
                    error_code=None,
                    error_message=None,
                    http_status=getattr(probe_result, "http_status", None),
                    request_artifact=getattr(probe_result, "request_artifact", None),
                    response_artifact=getattr(probe_result, "response_artifact", None),
                )

            spec = self.replicat_builder.build(
                group_name=request.group_name,
                credential_alias=request.credential_alias,
                credential_domain=request.credential_domain,
                trail_name=request.trail_name or "lt",
                mode=request.mode,
                base_config_lines=request.base_config_lines,
            )
            create_result = self.client.execute_spec(spec, artifacts_dir)

            if not create_result.success:
                return create_result

            return self._wait_until_visible(
                process_type="replicat",
                process_name=request.group_name,
                endpoint="/services/v2/replicats",
                artifacts_dir=artifacts_dir,
                request_artifact=create_result.request_artifact,
                response_artifact=create_result.response_artifact,
                raw_output=create_result.raw_output,
                http_status=create_result.http_status,
            )

        raise ValueError(f"Unsupported group_type for bootstrap: {request.group_type}")

    def _wait_until_visible(
        self,
        *,
        process_type: str,
        process_name: str,
        endpoint: str,
        artifacts_dir: str | Path,
        request_artifact: str | None,
        response_artifact: str | None,
        raw_output: str | None,
        http_status: int | None,
        attempts: int = 10,
        delay_sec: float = 1.5,
    ) -> ExecutorResult:
        last_probe = None

        for attempt in range(1, attempts + 1):
            last_probe = self.client.probe_process_status(
                OGGProcessStatusRequest(
                    process_type=process_type,
                    process_name=process_name,
                    endpoint=endpoint,
                    artifact_prefix=f"bootstrap_wait_{process_type}_{process_name}_{attempt}",
                ),
                artifacts_dir=artifacts_dir,
            )

            if last_probe.success:
                return ExecutorResult(
                    success=True,
                    executed_count=1,
                    skipped_count=0,
                    raw_output=raw_output or f"{process_type} created: {process_name}",
                    error_code=None,
                    error_message=None,
                    http_status=http_status,
                    request_artifact=request_artifact,
                    response_artifact=response_artifact,
                )

            time.sleep(delay_sec)

        return ExecutorResult(
            success=False,
            executed_count=0,
            skipped_count=0,
            raw_output=raw_output,
            error_code="BOOTSTRAP_NOT_VISIBLE",
            error_message=(
                f"{process_type} was created but not visible after polling: {process_name}"
            ),
            http_status=http_status,
            request_artifact=request_artifact,
            response_artifact=response_artifact,
        )