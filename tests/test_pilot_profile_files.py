from pathlib import Path


def test_test_pilot_profile_files_exist():
    assert Path("profiles/test_pilot.env.example").exists()
    assert Path("docs/test_pilot_checklist.md").exists()
    assert Path("scripts/print_effective_config.py").exists()