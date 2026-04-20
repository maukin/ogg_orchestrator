from __future__ import annotations

import json
from pathlib import Path

from app.services.service_schema_validator import SchemaValidationResult


def write_schema_validation_report(
    result: SchemaValidationResult,
    artifacts_dir: str | Path,
) -> str:
    out_dir = Path(artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "ok": result.ok,
        "issues_count": len(result.issues),
        "issues": [
            {
                "table_name": issue.table_name,
                "column_name": issue.column_name,
                "expected_type_prefix": issue.expected_type_prefix,
                "actual_type": issue.actual_type,
                "issue_type": issue.issue_type,
            }
            for issue in result.issues
        ],
    }

    path = out_dir / "schema_validation_report.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)