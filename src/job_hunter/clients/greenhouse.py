from __future__ import annotations

from typing import Iterable

from ..http import get_json
from ..models import JobOpening


def fetch_jobs(board_token: str) -> Iterable[JobOpening]:
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs")
    for item in data.get("jobs", []):
        location = ((item.get("location") or {}).get("name")) or ""
        absolute_url = item.get("absolute_url", "")
        metadata = {
            "updated_at": item.get("updated_at"),
            "internal_job_id": item.get("internal_job_id"),
            "requisition_id": item.get("requisition_id"),
        }
        yield JobOpening(
            source="greenhouse",
            company=board_token,
            job_id=str(item["id"]),
            title=item.get("title", ""),
            location=location,
            url=absolute_url,
            metadata=metadata,
            remote="remote" in location.lower(),
        )
