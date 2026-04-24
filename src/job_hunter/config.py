from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Config:
    raw: dict[str, Any]

    @property
    def db_path(self) -> Path:
        return Path(self.raw.get("db_path", "data/job_hunter.db"))


def load_config(path: str) -> Config:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return Config(raw=raw)
