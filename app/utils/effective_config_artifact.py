from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path


def write_effective_config_artifact(cfg, artifacts_dir: str | Path) -> str:
    out_dir = Path(artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = asdict(cfg)
    if payload.get("oracle_password"):
        payload["oracle_password"] = "***"
    if payload.get("ogg_rest_password"):
        payload["ogg_rest_password"] = "***"

    path = out_dir / "effective_runtime_config.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)