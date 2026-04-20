from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.models.group_bootstrap import GroupBootstrapRequest, GroupBootstrapResult
from app.models.groups import GroupConfig
from app.repositories.group_repo import GroupRepository
from app.services.ogg_process_bootstrap_service import OGGProcessBootstrapService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GroupBootstrapService:
    def __init__(
        self,
        group_repo: GroupRepository,
        ogg_process_bootstrap_service: OGGProcessBootstrapService | None = None,
    ):
        self.group_repo = group_repo
        self.ogg_process_bootstrap_service = ogg_process_bootstrap_service

    def bootstrap(
        self,
        request: GroupBootstrapRequest,
        artifacts_dir: str | Path,
    ) -> GroupBootstrapResult:
        started_at = _utc_now()
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        request_artifact = out_dir / f"bootstrap_{request.group_type}_{request.group_name}_request.json"
        response_artifact = out_dir / f"bootstrap_{request.group_type}_{request.group_name}_response.json"

        request_payload = {
            "group_name": request.group_name,
            "group_type": request.group_type,
            "environment_name": request.environment_name,
            "source_system": request.source_system,
            "target_system": request.target_system,
            "credential_alias": request.credential_alias,
            "credential_domain": request.credential_domain,
            "trail_name": request.trail_name,
            "mode": request.mode,
            "base_config_lines": request.base_config_lines,
            "notes": request.notes,
        }
        request_artifact.write_text(
            json.dumps(request_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        try:
            process_result = None
            if self.ogg_process_bootstrap_service is not None:
                process_result = self.ogg_process_bootstrap_service.bootstrap_process(
                    request=request,
                    artifacts_dir=artifacts_dir,
                )
                if not process_result.success:
                    response_payload = {
                        "success": False,
                        "message": process_result.error_message or process_result.error_code,
                        "group_name": request.group_name,
                        "group_type": request.group_type,
                        "request_artifact": process_result.request_artifact,
                        "response_artifact": process_result.response_artifact,
                    }
                    response_artifact.write_text(
                        json.dumps(response_payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    return GroupBootstrapResult(
                        success=False,
                        group_name=request.group_name,
                        group_type=request.group_type,
                        started_at=started_at,
                        finished_at=_utc_now(),
                        request_artifact=str(request_artifact),
                        response_artifact=str(response_artifact),
                        raw_output=process_result.raw_output,
                        error_code=process_result.error_code or "OGG_BOOTSTRAP_FAILED",
                        error_message=process_result.error_message or process_result.raw_output,
                    )

            self.group_repo.create_group(
                GroupConfig(
                    group_name=request.group_name,
                    group_type=request.group_type,
                    environment_name=request.environment_name,
                    source_system=request.source_system,
                    target_system=request.target_system,
                    max_tables=None,
                    priority_class=None,
                    active_flag=True,
                    notes=request.notes,
                )
            )

            response_payload = {
                "success": True,
                "message": "Bootstrap group created successfully.",
                "group_name": request.group_name,
                "group_type": request.group_type,
                "mode": request.mode,
                "base_config_lines": request.base_config_lines,
                "ogg_request_artifact": process_result.request_artifact if process_result else None,
                "ogg_response_artifact": process_result.response_artifact if process_result else None,
            }
            response_artifact.write_text(
                json.dumps(response_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            return GroupBootstrapResult(
                success=True,
                group_name=request.group_name,
                group_type=request.group_type,
                started_at=started_at,
                finished_at=_utc_now(),
                request_artifact=str(request_artifact),
                response_artifact=str(response_artifact),
                raw_output=response_payload["message"],
                error_code=None,
                error_message=None,
            )
        except Exception as exc:
            response_payload = {
                "success": False,
                "message": str(exc),
                "group_name": request.group_name,
                "group_type": request.group_type,
            }
            response_artifact.write_text(
                json.dumps(response_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            return GroupBootstrapResult(
                success=False,
                group_name=request.group_name,
                group_type=request.group_type,
                started_at=started_at,
                finished_at=_utc_now(),
                request_artifact=str(request_artifact),
                response_artifact=str(response_artifact),
                raw_output=None,
                error_code="GROUP_BOOTSTRAP_FAILED",
                error_message=str(exc),
            )