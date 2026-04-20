from __future__ import annotations

from app.models.deployment_reporting import (
    DeploymentExecutionSummary,
    StepExecutionSummary,
)
from app.models.executor import ExecutorResult


class DeploymentExecutionSummaryService:
    def build_summary(
        self,
        deployment_id: str,
        environment_name: str,
        step_results: list[tuple[str, object | None]],
    ) -> DeploymentExecutionSummary:
        rows: list[StepExecutionSummary] = []

        for step_name, result in step_results:
            if result is None:
                rows.append(
                    StepExecutionSummary(
                        step_name=step_name,
                        success=None,
                        executed_count=None,
                        skipped_count=None,
                        http_status=None,
                        request_artifact=None,
                        response_artifact=None,
                        raw_output=None,
                        error_code=None,
                        error_message="No result returned.",
                    )
                )
                continue

            success = getattr(result, "success", None)
            http_status = getattr(result, "http_status", None)
            request_artifact = getattr(result, "request_artifact", None)
            response_artifact = getattr(result, "response_artifact", None)
            raw_output = getattr(result, "raw_output", None)
            error_code = getattr(result, "error_code", None)
            error_message = getattr(result, "error_message", None)

            executed_count = getattr(result, "executed_count", None)
            skipped_count = getattr(result, "skipped_count", None)

            rows.append(
                StepExecutionSummary(
                    step_name=step_name,
                    success=success,
                    executed_count=executed_count,
                    skipped_count=skipped_count,
                    http_status=http_status,
                    request_artifact=request_artifact,
                    response_artifact=response_artifact,
                    raw_output=raw_output,
                    error_code=error_code,
                    error_message=error_message,
                )
            )

        return DeploymentExecutionSummary(
            deployment_id=deployment_id,
            environment_name=environment_name,
            step_results=rows,
        )