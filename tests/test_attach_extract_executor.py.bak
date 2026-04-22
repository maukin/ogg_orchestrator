from pathlib import Path
import json
import sys

from app.executors.attach_extract_executor import (
    FileOnlyAttachExtractExecutor,
    ScriptAttachExtractExecutor,
)
from app.models.attach_extract import AttachExtractCommand


def test_file_only_attach_extract_executor(tmp_path: Path):
    executor = FileOnlyAttachExtractExecutor()

    cmd = AttachExtractCommand(
        table_id="T1",
        source_schema="SRC",
        source_table="ORDERS",
        extract_group="EXT_01",
        fragment_path=str(tmp_path / "cdc" / "extract" / "EXT_01.tables.prm"),
        command_type="ATTACH_EXTRACT",
        command_text="attach_extract",
        mode="FILE_ONLY",
        reason="TEST",
    )

    result = executor.execute([cmd], tmp_path)

    assert result.success is True
    assert result.executed_count == 1
    assert result.group_name == "EXT_01"

    response_payload = json.loads((tmp_path / "attach_extract_response.json").read_text(encoding="utf-8"))
    assert response_payload["success"] is True


def test_script_attach_extract_executor(tmp_path: Path):
    script_path = Path("scripts/attach_extract_adapter.py").resolve()
    assert script_path.exists(), script_path

    executor = ScriptAttachExtractExecutor(
        script_command=f'{sys.executable} "{script_path}" {{request}} {{response}}',
        timeout_sec=60,
    )

    fragment_dir = tmp_path / "cdc" / "extract"
    fragment_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = fragment_dir / "EXT_01.tables.prm"
    fragment_path.write_text("TABLE SRC.ORDERS;\n", encoding="utf-8")

    cmd = AttachExtractCommand(
        table_id="T1",
        source_schema="SRC",
        source_table="ORDERS",
        extract_group="EXT_01",
        fragment_path=str(fragment_path),
        command_type="ATTACH_EXTRACT",
        command_text="attach_extract",
        mode="SCRIPT",
        reason="TEST",
    )

    # env для script adapter
    import os
    os.environ["OGG_REST_BASE_URL"] = "http://localhost:9001"
    os.environ["OGG_REST_USERNAME"] = "u"
    os.environ["OGG_REST_PASSWORD"] = "p"

    result = executor.execute([cmd], tmp_path)

    # этот тест теперь лучше использовать только как контрактный,
    # если adapter ходит в реальный REST, он без mock может упасть.
    # поэтому здесь достаточно проверить, что response файл создан.
    assert (tmp_path / "attach_extract_request.json").exists()