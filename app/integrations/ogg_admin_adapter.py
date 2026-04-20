from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class AdminCommandResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int


class OGGAdminAdapter:
    def __init__(self, adminclient_path: str = "adminclient"):
        self.adminclient_path = adminclient_path

    def run_commands(self, commands: str) -> AdminCommandResult:
        process = subprocess.run(
            [self.adminclient_path],
            input=commands,
            capture_output=True,
            text=True,
            check=False,
        )
        return AdminCommandResult(
            success=process.returncode == 0,
            stdout=process.stdout,
            stderr=process.stderr,
            exit_code=process.returncode,
        )
