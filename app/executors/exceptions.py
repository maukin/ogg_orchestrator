class ExecutorExecutionError(Exception):
    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message