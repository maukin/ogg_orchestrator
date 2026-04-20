from __future__ import annotations

from pathlib import Path
import json

from app.integrations.ogg_rest_client import OGGRestClient
from app.integrations.ogg_rest_payload_builders import OGGRestExtractAttachPayloadBuilder
from app.models.extract import ExtractAttachCommand
from app.models.executor import ExecutorResult
from app.utils.executor_artifacts import write_executor_result_artifact


class OGGRestExtractAttachExecutor:
    def __init__(self, client: OGGRestClient):
        self.client = client
        self.builder = OGGRestExtractAttachPayloadBuilder()

    def execute(
        self,
        commands: list[ExtractAttachCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        spec = self.builder.build(commands)

        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "extract_attach_commands.json").write_text(
            json.dumps(spec.payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        result = self.client.execute_spec(
            spec=spec,
            artifacts_dir=artifacts_dir,
        )

        write_executor_result_artifact(
            result=result,
            artifacts_dir=artifacts_dir,
            filename="ogg_rest_extract_attach_result.json",
        )
        return result