from __future__ import annotations

from typing import Iterable

from ..http import get_json
from ..models import JobOpening


def fetch_jobs(site: str) -> Iterable[JobOpening]:
    data = get_json(f"https://api.lever.co/v0/postings/{site}?mode=json")
    for item in data:
        categories = item.get("categories") or {}
        location = categories.get("location", "") or ""
        metadata = {
            "team": categories.get("team", ""),
            "department": categories.get("department", ""),
            "commitment": categories.get("commitment", ""),
            "workplace_type": categories.get("workplaceType", ""),
        }
        yield JobOpening(
            source="lever",
            company=site,
            job_id=item.get("id", ""),
            title=item.get("text", ""),
            location=location,
            url=item.get("hostedUrl", ""),
            description=item.get("descriptionPlain", "") or "",
            team=categories.get("team", "") or "",
            employment_type=categories.get("commitment", "") or "",
            remote="remote" in location.lower() or metadata["workplace_type"].lower() == "remote",
            metadata=metadata,
        )
