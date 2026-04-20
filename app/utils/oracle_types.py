from __future__ import annotations

import json
from typing import Any


def read_lob(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "read"):
        return value.read()
    return value


def char_flag_to_bool(value: str | None) -> bool:
    return (value or "").upper() == "Y"


def bool_to_char_flag(value: bool) -> str:
    return "Y" if value else "N"


def load_json_lob(value: Any, default: Any = None) -> Any:
    raw = read_lob(value)
    if raw is None or raw == "":
        return default
    return json.loads(raw)