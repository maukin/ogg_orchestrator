from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import json

from app.models.deployment import DeploymentPlan
from app.utils.plan_actions import PREPARE_ATTACH_ACTIONS


class ArtifactRenderer:
    def render_plan_artifacts(
        self,
        plan: DeploymentPlan,
        output_dir: str | Path,
    ) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        extract_changes: list[dict] = []
        replicat_changes: list[dict] = []
        source_prereq: list[str] = []
        deployment_actions: list[dict] = []

        action_counter: Counter[str] = Counter()
        tables_by_action: dict[str, list[str]] = defaultdict(list)

        for action in plan.actions:
            action_counter[action.action_type] += 1
            if action.table_id:
                tables_by_action[action.action_type].append(action.table_id)

            deployment_actions.append(
                {
                    "action_type": action.action_type,
                    "table_id": action.table_id,
                    "group_name": action.group_name,
                    "payload": action.payload,
                }
            )

            if action.action_type == "REGISTER_NEW_TABLE":
                payload = action.payload
                if payload.get("desired_extract_group"):
                    extract_changes.append(
                        {
                            "action": "ADD_TABLE",
                            "extract_group": payload.get("desired_extract_group"),
                            "source_schema": payload.get("source_schema"),
                            "source_table": payload.get("source_table"),
                            "table_id": action.table_id,
                        }
                    )

            if action.action_type in PREPARE_ATTACH_ACTIONS:
                payload = action.payload
                source_schema = payload.get("source_schema")
                source_table = payload.get("source_table")

                prereq_stmt = (
                    f"-- {action.table_id}\n"
                    f"-- PREPARE FOR INSTANTIATION\n"
                    f"-- REASON: {payload.get('reason')}\n"
                )

                if source_schema and source_table:
                    prereq_stmt += f"-- ADD TRANDATA {source_schema}.{source_table}"
                else:
                    prereq_stmt += "-- ADD TRANDATA <resolved later from registry>"

                source_prereq.append(prereq_stmt)

            if action.action_type in {"REGISTER_NEW_TABLE", "UPDATE_TABLE_DESIRED_STATE"}:
                payload = action.payload
                replication_mode = payload.get("desired_replication_mode")
                replicat_group = payload.get("desired_replicat_group")
                target_schema = payload.get("target_schema")
                target_table = payload.get("target_table")
                source_schema = payload.get("source_schema")
                source_table = payload.get("source_table")

                if (
                    replication_mode != "INITIAL_LOAD_ONLY"
                    and replicat_group
                    and source_schema
                    and source_table
                    and target_schema
                    and target_table
                ):
                    replicat_changes.append(
                        {
                            "action": "ADD_MAP",
                            "replicat_group": replicat_group,
                            "source_schema": source_schema,
                            "source_table": source_table,
                            "target_schema": target_schema,
                            "target_table": target_table,
                            "table_id": action.table_id,
                        }
                    )

        (out / "extract_changes.json").write_text(
            json.dumps(extract_changes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out / "replicat_changes.json").write_text(
            json.dumps(replicat_changes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out / "source_prereq.sql").write_text(
            "\n\n".join(source_prereq),
            encoding="utf-8",
        )
        (out / "deployment_actions.json").write_text(
            json.dumps(deployment_actions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out / "plan_summary.json").write_text(
            json.dumps(
                {
                    "deployment_id": plan.deployment_id,
                    "environment_name": plan.environment_name,
                    "actions_count": len(plan.actions),
                    "actions_by_type": dict(action_counter),
                    "tables_by_action": dict(tables_by_action),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


    def render_status_report(
        self,
        report,
        output_dir: str | Path,
    ) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        category_counts: dict[str, int] = {}
        state_counts: dict[str, int] = {}

        for s in report.table_statuses:
            category_counts[s.category] = category_counts.get(s.category, 0) + 1
            state_counts[s.state] = state_counts.get(s.state, 0) + 1

        payload = {
            "deployment_id": report.deployment_id,
            "environment_name": report.environment_name,
            "summary": {
                "tables_count": len(report.table_statuses),
                "category_counts": category_counts,
                "state_counts": state_counts,
            },
            "table_statuses": [
                {
                    "table_id": s.table_id,
                    "state": s.state,
                    "desired_enabled": s.desired_enabled,
                    "category": s.category,
                    "message": s.message,
                    "next_expected_step": s.next_expected_step,
                }
                for s in report.table_statuses
            ],
        }

        (out / "deployment_status_report.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def render_execution_summary(
        self,
        summary,
        output_dir: str | Path,
    ) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        total_steps = len(summary.step_results)
        successful_steps = sum(1 for s in summary.step_results if s.success is True)
        failed_steps = sum(1 for s in summary.step_results if s.success is False)
        unknown_steps = sum(1 for s in summary.step_results if s.success is None)

        payload = {
            "deployment_id": summary.deployment_id,
            "environment_name": summary.environment_name,
            "summary": {
                "total_steps": total_steps,
                "successful_steps": successful_steps,
                "failed_steps": failed_steps,
                "unknown_steps": unknown_steps,
            },
            "step_results": [
                {
                    "step_name": s.step_name,
                    "success": s.success,
                    "executed_count": s.executed_count,
                    "skipped_count": s.skipped_count,
                    "http_status": s.http_status,
                    "request_artifact": s.request_artifact,
                    "response_artifact": s.response_artifact,
                    "raw_output": s.raw_output,
                    "error_code": s.error_code,
                    "error_message": s.error_message,
                }
                for s in summary.step_results
            ],
        }

        (out / "deployment_execution_summary.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def render_reconciliation_report(
        self,
        report,
        output_dir: str | Path,
    ) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        blocked_count = sum(1 for row in report.rows if row.is_blocked)
        error_count = sum(1 for row in report.rows if row.has_error)

        payload = {
            "deployment_id": report.deployment_id,
            "environment_name": report.environment_name,
            "summary": {
                "tables_count": len(report.rows),
                "blocked_count": blocked_count,
                "error_count": error_count,
            },
            "rows": [
                {
                    "table_id": row.table_id,
                    "desired_enabled": row.desired_enabled,
                    "registry_state": row.registry_state,
                    "validation_status": row.validation_status,
                    "has_error": row.has_error,
                    "is_blocked": row.is_blocked,
                    "block_reason": row.block_reason,
                    "next_recommended_step": row.next_recommended_step,
                    "notes": row.notes,
                }
                for row in report.rows
            ],
        }

        (out / "deployment_reconciliation_report.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def render_cdc_config_bundle(
        self,
        bundle,
        output_dir: str | Path,
    ) -> None:
        out = Path(output_dir)
        extract_dir = out / "cdc" / "extract"
        replicat_dir = out / "cdc" / "replicat"

        extract_dir.mkdir(parents=True, exist_ok=True)
        replicat_dir.mkdir(parents=True, exist_ok=True)

        for group in bundle.extract_groups:
            path = extract_dir / f"{group.group_name}.tables.prm"
            content = "\n".join(group.lines).strip()
            if content:
                content += "\n"
            path.write_text(content, encoding="utf-8")

        for group in bundle.replicat_groups:
            path = replicat_dir / f"{group.group_name}.maps.prm"
            content = "\n".join(group.lines).strip()
            if content:
                content += "\n"
            path.write_text(content, encoding="utf-8")

