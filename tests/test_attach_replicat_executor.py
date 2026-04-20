from pathlib import Path
import sys

from app.executors.attach_replicat_executor import (
    FileOnlyAttachReplicatExecutor,
    ScriptAttachReplicatExecutor,
)
from app.models.attach_replicat import AttachReplicatCommand


def test_file_only_attach_replicat_executor(tmp_path: Path):
    executor = FileOnlyAttachReplicatExecutor()

    cmd = AttachReplicatCommand(
        table_id="T1",
        source_schema="SRC",
        source_table="ORDERS",
        target_schema="DDS",
        target_table="ORDERS",
        replicat_group="REP_01",
        fragment_path=str(tmp_path / "cdc" / "replicat" / "REP_01.maps.prm"),
        command_type="ATTACH_REPLICAT",
        command_text="attach_replicat",
        mode="FILE_ONLY",
        reason="TEST",
    )

    result = executor.execute([cmd], tmp_path)

    assert result.success is True
    assert result.executed_count == 1
    assert result.group_name == "REP_01"


def test_script_attach_replicat_executor(tmp_path: Path):
    script_path = Path("scripts/mock_attach_replicat_runner.py").resolve()
    assert script_path.exists(), script_path

    executor = ScriptAttachReplicatExecutor(
        script_command=f'{sys.executable} "{script_path}" {{request}} {{response}}',
        timeout_sec=60,
    )

    cmd = AttachReplicatCommand(
        table_id="T1",
        source_schema="SRC",
        source_table="ORDERS",
        target_schema="DDS",
        target_table="ORDERS",
        replicat_group="REP_01",
        fragment_path=str(tmp_path / "cdc" / "replicat" / "REP_01.maps.prm"),
        command_type="ATTACH_REPLICAT",
        command_text="attach_replicat",
        mode="SCRIPT",
        reason="TEST",
    )

    result = executor.execute([cmd], tmp_path)

    assert result.success is True
    assert result.executed_count == 1
    assert result.group_name == "REP_01"
    assert result.restart_performed is True
    assert result.rollback_performed is False