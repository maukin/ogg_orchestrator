from __future__ import annotations

from pathlib import Path
import json

from app.integrations.ogg_rest_client import OGGRestClient
from app.integrations.ogg_rest_payload_builders import OGGRestPreparePayloadBuilder
from app.models.prepare import SourcePrepareCommand
from app.models.executor import ExecutorResult
from app.utils.executor_artifacts import write_executor_result_artifact


class OGGRestPrepareExecutor:
    def __init__(
        self,
        client: OGGRestClient,
        connection_name: str,
        trandata_scope: str = "TABLE",
    ):
        self.client = client
        self.builder = OGGRestPreparePayloadBuilder(
            connection_name=connection_name,
            trandata_scope=trandata_scope,
        )

    def execute(
        self,
        commands: list[SourcePrepareCommand],
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        spec = self.builder.build(commands)

        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "source_prepare_commands.json").write_text(
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
            filename="ogg_rest_prepare_result.json",
        )
        return result