from __future__ import annotations

from typing import Iterable

from ..http import build_url, get_json
from ..models import JobOpening


def fetch_jobs(
    country: str,
    what: str,
    where: str,
    app_id: str,
    app_key: str,
    results_per_page: int = 20,
    page: int = 1,
) -> Iterable[JobOpening]:
    # This field mapping is inferred from Adzuna's official search examples.
    url = build_url(
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}",
        {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": results_per_page,
            "what": what,
            "where": where,
            "content-type": "application/json",
        },
    )
    data = get_json(url, headers={"Accept": "application/json"})
    for item in data.get("results", []):
        location = ((item.get("location") or {}).get("display_name")) or ""
        company = ((item.get("company") or {}).get("display_name")) or "Unknown"
        category = ((item.get("category") or {}).get("label")) or ""
        yield JobOpening(
            source="adzuna",
            company=company,
            job_id=str(item.get("id", "")),
            title=item.get("title", "") or "",
            location=location,
            url=item.get("redirect_url", "") or "",
            description=item.get("description", "") or "",
            employment_type=item.get("contract_type", "") or "",
            remote="remote" in location.lower(),
            metadata={
                "category": category,
                "created": item.get("created", ""),
                "salary_min": item.get("salary_min"),
                "salary_max": item.get("salary_max"),
                "source_label": "Jobs by Adzuna",
            },
        )
