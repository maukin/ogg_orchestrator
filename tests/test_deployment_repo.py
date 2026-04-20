from app.repositories.deployment_repo import DeploymentRepository


class FakeCursor:
    def __init__(self, rowcount_after_update):
        self.rowcount_after_update = rowcount_after_update
        self.rowcount = 0
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        if "UPDATE etl_deployments" in sql:
            self.rowcount = self.rowcount_after_update
        else:
            self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, rowcount_after_update):
        self.cursor_obj = FakeCursor(rowcount_after_update)

    def cursor(self):
        return self.cursor_obj


def test_record_failure_updates_existing_deployment():
    connection = FakeConnection(rowcount_after_update=1)
    repo = DeploymentRepository(connection)

    repo.record_failure(
        deployment_id="dep1",
        environment_name="dev",
        git_branch="main",
        git_commit_sha="sha",
        pipeline_id="pipe",
        error_message="boom",
    )

    assert len(connection.cursor_obj.calls) == 1
    assert connection.cursor_obj.calls[0][1]["status"] == "FAILED"


def test_record_failure_inserts_when_deployment_row_missing():
    connection = FakeConnection(rowcount_after_update=0)
    repo = DeploymentRepository(connection)

    repo.record_failure(
        deployment_id="dep1",
        environment_name="dev",
        git_branch="main",
        git_commit_sha="sha",
        pipeline_id="pipe",
        error_message="boom",
    )

    assert len(connection.cursor_obj.calls) == 2
    insert_params = connection.cursor_obj.calls[1][1]
    assert insert_params["deployment_id"] == "dep1"
    assert insert_params["status"] == "FAILED"
    assert insert_params["error_message"] == "boom"
