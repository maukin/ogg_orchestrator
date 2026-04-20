import json
from pathlib import Path

from app.utils.initial_load_backend_artifacts import (
    write_initial_load_backend_context,
    write_initial_load_backend_result,
)


def test_initial_load_backend_artifacts_are_written(tmp_path: Path):
    context_path = write_initial_load_backend_context(
        {"selected_backend": "DataPumpBackend", "table_id": "T1"},
        tmp_path,
    )
    result_path = write_initial_load_backend_result(
        {"success": True, "load_batch_id": "batch1"},
        tmp_path,
    )

    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    result = json.loads(Path(result_path).read_text(encoding="utf-8"))

    assert context["selected_backend"] == "DataPumpBackend"
    assert result["success"] is True
    assert result["load_batch_id"] == "batch1"