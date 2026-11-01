"""Only local storage settings are configurable in phase 1."""

import os
from pathlib import Path
from typing import Literal

from ari.core.models import DomainModel


class Settings(DomainModel):
    data_dir: Path
    read_only: Literal[True] = True
    simulation: Literal[True] = True

    @property
    def database_path(self) -> Path:
        return self.data_dir / "ari.sqlite3"

    @property
    def log_path(self) -> Path:
        return self.data_dir / "logs" / "ari.jsonl"

    @classmethod
    def from_environment(cls) -> "Settings":
        location = os.environ.get("ARI_DATA_DIR")
        if location is not None and not location.strip():
            raise ValueError("ARI_DATA_DIR cannot be empty")
        return cls(data_dir=Path(location or Path.cwd() / ".ari").expanduser().resolve())
