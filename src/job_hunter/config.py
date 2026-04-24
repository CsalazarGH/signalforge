from __future__ import annotations

import json
import os
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

    # Allow secrets to stay out of config files and git history.
    hunter_api_key = os.environ.get("HUNTER_API_KEY", "").strip()
    if hunter_api_key:
        raw.setdefault("hunter", {})
        raw["hunter"]["api_key"] = hunter_api_key

    adzuna_app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
    adzuna_app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if adzuna_app_id or adzuna_app_key:
        raw.setdefault("adzuna", {})
    if adzuna_app_id:
        raw["adzuna"]["app_id"] = adzuna_app_id
    if adzuna_app_key:
        raw["adzuna"]["app_key"] = adzuna_app_key

    return Config(raw=raw)
