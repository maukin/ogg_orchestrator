from app.integrations.ogg_admin_adapter import OGGAdminAdapter


class DummyCompletedProcess:
    def __init__(self, returncode=0, stdout="ok", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_commands_passes_input_directly_to_subprocess(monkeypatch):
    captured = {}

    def fake_run(args, input=None, capture_output=None, text=None, check=None):
        captured["args"] = args
        captured["input"] = input
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["check"] = check
        return DummyCompletedProcess()

    monkeypatch.setattr("subprocess.run", fake_run)

    adapter = OGGAdminAdapter(adminclient_path="adminclient")
    result = adapter.run_commands("CONNECT test\nINFO ALL\n")

    assert result.success is True
    assert captured["args"] == ["adminclient"]
    assert captured["input"] == "CONNECT test\nINFO ALL\n"
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["check"] is False
