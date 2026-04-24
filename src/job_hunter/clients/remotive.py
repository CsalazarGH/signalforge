from __future__ import annotations

from typing import Iterable

from ..http import build_url, get_json
from ..models import JobOpening


def fetch_jobs(search: str = "", category: str = "software-dev", limit: int = 50) -> Iterable[JobOpening]:
    url = build_url(
        "https://remotive.com/api/remote-jobs",
        {
            "category": category,
            "search": search,
            "limit": limit,
        },
    )
    data = get_json(url)
    for item in data.get("jobs", []):
        yield JobOpening(
            source="remotive",
            company=item.get("company_name", "") or "Unknown",
            job_id=str(item.get("id", "")),
            title=item.get("title", "") or "",
            location=item.get("candidate_required_location", "") or "Remote",
            url=item.get("url", "") or "",
            description=item.get("description", "") or "",
            employment_type=item.get("job_type", "") or "",
            remote=True,
            metadata={
                "category": item.get("category", ""),
                "publication_date": item.get("publication_date", ""),
                "salary": item.get("salary", ""),
                "company_logo": item.get("company_logo", ""),
                "source_label": "Remotive",
            },
        )
