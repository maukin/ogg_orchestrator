from __future__ import annotations

import json
from dataclasses import asdict

from app.config import AppConfig


def main() -> int:
    cfg = AppConfig.from_env()
    payload = asdict(cfg)
    if payload.get("oracle_password"):
        payload["oracle_password"] = "***"
    if payload.get("ogg_rest_password"):
        payload["ogg_rest_password"] = "***"

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())