from __future__ import annotations

from pathlib import Path

from app.integrations.ogg_process_status_builders import ReplicatStatusRequestBuilder
from app.integrations.ogg_rest_client import OGGRestClient
from app.models.ogg_process_status import OGGProcessStatusResult


class ReplicatStatusProbeService:
    def __init__(self, client: OGGRestClient):
        self.client = client
        self.builder = ReplicatStatusRequestBuilder()

    def probe(
        self,
        replicat_name: str,
        artifacts_dir: str | Path,
    ) -> OGGProcessStatusResult:
        request = self.builder.build(replicat_name)
        return self.client.probe_process_status(
            request=request,
            artifacts_dir=artifacts_dir,
        )