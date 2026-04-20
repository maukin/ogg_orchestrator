from pathlib import Path
import sys

from app.executors.script_initial_load_executor import ScriptInitialLoadExecutor
from app.models.initial_load import InitialLoadCommand


def test_script_initial_load_executor_runs_external_script(tmp_path: Path):
    script_path = Path("scripts/mock_initial_load_runner.py").resolve()

    executor = ScriptInitialLoadExecutor(
        script_command=f'{sys.executable} "{script_path}" {{request}} {{response}}',
        timeout_sec=60,
    )

    command = InitialLoadCommand(
        table_id="T1",
        source_schema="SRC",
        source_table="ORDERS",
        target_schema="DDS",
        target_table="ORDERS",
        load_method="DATAPUMP",
        extract_group="EXT_01",
        replicat_group="REP_01",
        registration_scn=123456,
        metadata_file="metadata/orders.json",
        command_type="INITIAL_LOAD",
        command_text="run_initial_load --source SRC.ORDERS --target DDS.ORDERS",
        mode="SCRIPT",
        reason="TEST",
    )

    result = executor.execute([command], tmp_path)

    assert result.success is True
    assert result.executed_count == 1
    assert result.load_batch_id is not None
    assert result.request_artifact is not None
    assert result.response_artifact is not None
    assert (tmp_path / "initial_load_request.json").exists()
    assert (tmp_path / "initial_load_response.json").exists()
    assert (tmp_path / "initial_load_stdout.log").exists()
    assert (tmp_path / "initial_load_stderr.log").exists()