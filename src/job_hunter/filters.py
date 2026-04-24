from __future__ import annotations

from .models import JobOpening


def matches_filters(job: JobOpening, filters: dict) -> bool:
    title = job.title.lower()
    location = (job.location or "").lower()

    include_titles = [item.lower() for item in filters.get("include_titles", [])]
    exclude_titles = [item.lower() for item in filters.get("exclude_titles", [])]
    include_locations = [item.lower() for item in filters.get("include_locations", [])]

    if include_titles and not any(token in title for token in include_titles):
        return False
    if exclude_titles and any(token in title for token in exclude_titles):
        return False
    if include_locations and not any(token in location for token in include_locations):
        return False
    return True
