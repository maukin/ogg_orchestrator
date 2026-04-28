from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any

import requests

from app.models.executor import ExecutorResult
from app.models.ogg_rest import OGGRestRequestSpec
from app.models.ogg_process_status import OGGProcessStatusRequest, OGGProcessStatusResult


@dataclass(frozen=True)
class OGGRestConfig:
    base_url: str
    username: str
    password: str
    deployment_name: str
    verify_ssl: bool = False
    mode: str = "OGG_REST_SKELETON"


class OGGRestClient:
    def __init__(self, config: OGGRestConfig):
        self.config = config

    def build_request_data(
        self,
        spec: OGGRestRequestSpec,
    ) -> dict[str, Any]:
        return {
            "base_url": self.config.base_url,
            "deployment_name": self.config.deployment_name,
            "method": spec.method.upper(),
            "endpoint": spec.endpoint,
            "payload": spec.payload,
            "verify_ssl": self.config.verify_ssl,
            "mode": self.config.mode,
            "operation_name": spec.operation_name,
        }

    def write_json_artifact(
        self,
        data: dict[str, Any],
        artifacts_dir: str | Path,
        filename: str,
    ) -> str:
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(path)

    def execute_spec(
        self,
        spec: OGGRestRequestSpec,
        artifacts_dir: str | Path,
    ) -> ExecutorResult:
        request_data = self.build_request_data(spec)
        request_artifact = self.write_json_artifact(
            data=request_data,
            artifacts_dir=artifacts_dir,
            filename=spec.artifact_name,
        )

        response_artifact_name = spec.artifact_name.replace("_request.json", "_response.json")
        if response_artifact_name == spec.artifact_name:
            response_artifact_name = f"{spec.operation_name}_response.json"

        if self.config.mode == "OGG_REST_SKELETON":
            response_data = {
                "operation_name": spec.operation_name,
                "mode": self.config.mode,
                "http_executed": False,
                "http_status": None,
                "success": True,
                "message": "Skeleton mode: request artifact generated, no HTTP call executed.",
            }
            response_artifact = self.write_json_artifact(
                data=response_data,
                artifacts_dir=artifacts_dir,
                filename=response_artifact_name,
            )

            return ExecutorResult(
                success=True,
                executed_count=1,
                skipped_count=0,
                raw_output=response_data["message"],
                error_code=None,
                error_message=None,
                http_status=None,
                request_artifact=request_artifact,
                response_artifact=response_artifact,
            )

        url = f"{self.config.base_url.rstrip('/')}/{spec.endpoint.lstrip('/')}"
        response = requests.request(
            method=spec.method.upper(),
            url=url,
            json=spec.payload,
            auth=(self.config.username, self.config.password),
            verify=self.config.verify_ssl,
            timeout=30,
        )

        response_data = {
            "operation_name": spec.operation_name,
            "mode": self.config.mode,
            "http_executed": True,
            "http_status": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response_text": response.text,
        }
        response_artifact = self.write_json_artifact(
            data=response_data,
            artifacts_dir=artifacts_dir,
            filename=response_artifact_name,
        )

        if 200 <= response.status_code < 300:
            return ExecutorResult(
                success=True,
                executed_count=1,
                skipped_count=0,
                raw_output=response.text,
                error_code=None,
                error_message=None,
                http_status=response.status_code,
                request_artifact=request_artifact,
                response_artifact=response_artifact,
            )

        return ExecutorResult(
            success=False,
            executed_count=0,
            skipped_count=0,
            raw_output=response.text,
            error_code=str(response.status_code),
            error_message=f"OGG REST request failed: {response.status_code}",
            http_status=response.status_code,
            request_artifact=request_artifact,
            response_artifact=response_artifact,
        )

    def probe_process_status(
        self,
        request: OGGProcessStatusRequest,
        artifacts_dir: str | Path,
    ) -> OGGProcessStatusResult:
        request_data = {
            "base_url": self.config.base_url,
            "deployment_name": self.config.deployment_name,
            "method": "GET",
            "endpoint": request.endpoint,
            "verify_ssl": self.config.verify_ssl,
            "mode": self.config.mode,
            "process_type": request.process_type,
            "process_name": request.process_name,
        }

        request_artifact = self.write_json_artifact(
            data=request_data,
            artifacts_dir=artifacts_dir,
            filename=f"{request.artifact_prefix}_request.json",
        )

        if self.config.mode == "OGG_REST_SKELETON":
            response_data = {
                "process_type": request.process_type,
                "process_name": request.process_name,
                "http_executed": False,
                "http_status": None,
                "success": True,
                "found": True,
                "message": "Skeleton mode: status request artifact generated, no HTTP call executed.",
            }
            response_artifact = self.write_json_artifact(
                data=response_data,
                artifacts_dir=artifacts_dir,
                filename=f"{request.artifact_prefix}_response.json",
            )
            return OGGProcessStatusResult(
                process_type=request.process_type,
                process_name=request.process_name,
                success=True,
                http_status=None,
                request_artifact=request_artifact,
                response_artifact=response_artifact,
                raw_output=response_data["message"],
                error_code=None,
                error_message=None,
            )

        url = f"{self.config.base_url.rstrip('/')}/{request.endpoint.lstrip('/')}"
        response = requests.get(
            url=url,
            auth=(self.config.username, self.config.password),
            verify=self.config.verify_ssl,
            timeout=30,
        )

        found = False
        found_item = None
        parsed_json = None

        if 200 <= response.status_code < 300:
            try:
                parsed_json = response.json()
                items = parsed_json.get("response", {}).get("items", [])
                wanted = str(request.process_name).upper()

                for item in items:
                    item_name = str(item.get("name", "")).upper()
                    if item_name == wanted:
                        found = True
                        found_item = item
                        break
            except Exception:
                found = False

        response_data = {
            "process_type": request.process_type,
            "process_name": request.process_name,
            "http_executed": True,
            "http_status": response.status_code,
            "http_success": 200 <= response.status_code < 300,
            "found": found,
            "matched_item": found_item,
            "response_text": response.text,
        }
        response_artifact = self.write_json_artifact(
            data=response_data,
            artifacts_dir=artifacts_dir,
            filename=f"{request.artifact_prefix}_response.json",
        )

        if not (200 <= response.status_code < 300):
            return OGGProcessStatusResult(
                process_type=request.process_type,
                process_name=request.process_name,
                success=False,
                http_status=response.status_code,
                request_artifact=request_artifact,
                response_artifact=response_artifact,
                raw_output=response.text,
                error_code=str(response.status_code),
                error_message=f"Status probe failed: {response.status_code}",
            )

        if not found:
            process_kind = request.process_type.lower()
            return OGGProcessStatusResult(
                process_type=request.process_type,
                process_name=request.process_name,
                success=False,
                http_status=response.status_code,
                request_artifact=request_artifact,
                response_artifact=response_artifact,
                raw_output=response.text,
                error_code="NOT_FOUND",
                error_message=f"{process_kind} group not found: {request.process_name}",
            )

        return OGGProcessStatusResult(
            process_type=request.process_type,
            process_name=request.process_name,
            success=True,
            http_status=response.status_code,
            request_artifact=request_artifact,
            response_artifact=response_artifact,
            raw_output=response.text,
            error_code=None,
            error_message=None,
        )

    def execute_process_command(
        self,
        *,
        process_type: str,
        process_name: str,
        command: str,
        artifacts_dir: str | Path,
        artifact_prefix: str,
    ) -> ExecutorResult:
        endpoint_type = process_type.lower()
        if endpoint_type not in {"extract", "replicat"}:
            raise ValueError(f"Unsupported process_type: {process_type}")

        endpoint = f"/services/v2/{endpoint_type}s/{process_name}/command"
        request_data = {
            "base_url": self.config.base_url,
            "deployment_name": self.config.deployment_name,
            "method": "POST",
            "endpoint": endpoint,
            "verify_ssl": self.config.verify_ssl,
            "mode": self.config.mode,
            "process_type": process_type,
            "process_name": process_name,
            "payload": {
                "$schema": "er:command",
                "command": command.upper(),
            },
        }

        request_artifact = self.write_json_artifact(
            data=request_data,
            artifacts_dir=artifacts_dir,
            filename=f"{artifact_prefix}_request.json",
        )

        if self.config.mode == "OGG_REST_SKELETON":
            response_data = {
                "process_type": process_type,
                "process_name": process_name,
                "command": command.upper(),
                "http_executed": False,
                "http_status": None,
                "success": True,
                "message": "Skeleton mode: process command artifact generated, no HTTP call executed.",
            }
            response_artifact = self.write_json_artifact(
                data=response_data,
                artifacts_dir=artifacts_dir,
                filename=f"{artifact_prefix}_response.json",
            )
            return ExecutorResult(
                success=True,
                executed_count=1,
                skipped_count=0,
                raw_output=response_data["message"],
                error_code=None,
                error_message=None,
                http_status=None,
                request_artifact=request_artifact,
                response_artifact=response_artifact,
            )

        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = requests.post(
            url=url,
            auth=(self.config.username, self.config.password),
            json=request_data["payload"],
            verify=self.config.verify_ssl,
            timeout=30,
        )

        response_data = {
            "process_type": process_type,
            "process_name": process_name,
            "command": command.upper(),
            "http_executed": True,
            "http_status": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response_text": response.text,
        }
        response_artifact = self.write_json_artifact(
            data=response_data,
            artifacts_dir=artifacts_dir,
            filename=f"{artifact_prefix}_response.json",
        )

        if 200 <= response.status_code < 300:
            return ExecutorResult(
                success=True,
                executed_count=1,
                skipped_count=0,
                raw_output=response.text,
                error_code=None,
                error_message=None,
                http_status=response.status_code,
                request_artifact=request_artifact,
                response_artifact=response_artifact,
            )

        return ExecutorResult(
            success=False,
            executed_count=0,
            skipped_count=0,
            raw_output=response.text,
            error_code=str(response.status_code),
            error_message=f"OGG REST process command failed: {response.status_code}",
            http_status=response.status_code,
            request_artifact=request_artifact,
            response_artifact=response_artifact,
        )