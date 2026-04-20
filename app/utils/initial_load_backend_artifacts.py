from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_initial_load_backend_context(
    payload: dict[str, Any],
    artifacts_dir: str | Path,
) -> str:
    out_dir = Path(artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "initial_load_backend_context.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


def write_initial_load_backend_result(
    payload: dict[str, Any],
    artifacts_dir: str | Path,
) -> str:
    out_dir = Path(artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "initial_load_backend_result.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)