from __future__ import annotations

from datetime import datetime
import uuid


def generate_deployment_id(prefix: str = "dep") -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_uid = uuid.uuid4().hex[:8]
    return f"{prefix}_{ts}_{short_uid}"