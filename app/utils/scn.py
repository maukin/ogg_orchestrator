from __future__ import annotations

import hashlib


def generate_simulated_scn(table_id: str, suffix: str) -> int:
    seed = f"{table_id}:{suffix}".encode("utf-8")
    digest = hashlib.sha256(seed).hexdigest()
    # Берём кусок хеша и превращаем в положительное число разумного масштаба
    value = int(digest[:12], 16)
    return 10_000_000_000 + value