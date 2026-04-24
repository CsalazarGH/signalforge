from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class JobOpening:
    source: str
    company: str
    job_id: str
    title: str
    location: str
    url: str
    description: str = ""
    team: str = ""
    employment_type: str = ""
    remote: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def unique_key(self) -> str:
        return f"{self.source}:{self.company}:{self.job_id}"


@dataclass
class ContactCandidate:
    company: str
    domain: str
    email: str
    full_name: str = ""
    position: str = ""
    confidence: Optional[int] = None
    source: str = "hunter"
    score: float = 0.0
