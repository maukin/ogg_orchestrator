from __future__ import annotations

from app.models.ogg_rest import OGGRestRequestSpec
from app.models.prepare import SourcePrepareCommand
from app.models.extract import ExtractAttachCommand
from app.models.replicat import ReplicatAttachCommand


class OGGRestPreparePayloadBuilder:
    def __init__(self, connection_name: str, trandata_scope: str = "TABLE"):
        self.connection_name = connection_name
        self.trandata_scope = trandata_scope.upper()

    def build(self, commands: list[SourcePrepareCommand]) -> OGGRestRequestSpec:
        if self.trandata_scope == "SCHEMA":
            schemas = sorted({c.source_schema for c in commands})
            payload = {
                "items": [
                    {
                        "schemaName": schema,
                    }
                    for schema in schemas
                ]
            }
            endpoint = f"/services/v2/connections/{self.connection_name}/trandata/schema"
            artifact_name = "ogg_rest_prepare_schema_request.json"
            operation_name = "prepare_source_schema_trandata"
        else:
            payload = {
                "items": [
                    {
                        "schemaName": c.source_schema,
                        "tableName": c.source_table,
                    }
                    for c in commands
                ]
            }
            endpoint = f"/services/v2/connections/{self.connection_name}/trandata/table"
            artifact_name = "ogg_rest_prepare_table_request.json"
            operation_name = "prepare_source_table_trandata"

        return OGGRestRequestSpec(
            operation_name=operation_name,
            method="POST",
            endpoint=endpoint,
            payload=payload,
            artifact_name=artifact_name,
        )


class OGGRestExtractAttachPayloadBuilder:
    def build(self, commands: list[ExtractAttachCommand]) -> OGGRestRequestSpec:
        if not commands:
            raise ValueError("No extract attach commands provided")

        extract_group = commands[0].extract_group
        payload = {
            "description": "Skeleton PATCH payload for Extract update. Adjust body to real deployment contract.",
            "managedProcessSettings": {
                "mode": "skeleton"
            },
            "tableRules": [
                {
                    "schemaName": c.source_schema,
                    "tableName": c.source_table,
                    "tableId": c.table_id,
                }
                for c in commands
            ],
        }

        return OGGRestRequestSpec(
            operation_name="attach_extract_patch",
            method="PATCH",
            endpoint=f"/services/v2/extracts/{extract_group}",
            payload=payload,
            artifact_name="ogg_rest_extract_patch_request.json",
        )


class OGGRestReplicatAttachPayloadBuilder:
    def build(self, commands: list[ReplicatAttachCommand]) -> OGGRestRequestSpec:
        if not commands:
            raise ValueError("No replicat attach commands provided")

        replicat_group = commands[0].replicat_group
        payload = {
            "description": "Skeleton PATCH payload for Replicat update. Adjust body to real deployment contract.",
            "managedProcessSettings": {
                "mode": "skeleton"
            },
            "mapRules": [
                {
                    "sourceSchema": c.source_schema,
                    "sourceTable": c.source_table,
                    "targetSchema": c.target_schema,
                    "targetTable": c.target_table,
                    "tableId": c.table_id,
                }
                for c in commands
            ],
        }

        return OGGRestRequestSpec(
            operation_name="attach_replicat_patch",
            method="PATCH",
            endpoint=f"/services/v2/replicats/{replicat_group}",
            payload=payload,
            artifact_name="ogg_rest_replicat_patch_request.json",
        )