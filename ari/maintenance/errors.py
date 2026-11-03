"""Static public failures: never include artifact data, paths or validation errors."""


class MaintenanceError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("Offline maintenance rejected the request.")
