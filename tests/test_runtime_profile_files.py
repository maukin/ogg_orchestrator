from pathlib import Path


def test_runtime_profile_files_exist():
    assert Path("profiles/datapump_pilot.env.example").exists()
    assert Path("profiles/ogg_single_pilot.env.example").exists()
    assert Path("scripts/run_real_pilot.ps1").exists()