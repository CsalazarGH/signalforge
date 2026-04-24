from __future__ import annotations

from typing import Iterable

from ..http import build_url, get_json
from ..models import ContactCandidate

TITLE_SIGNALS = [
    "recruit",
    "talent",
    "sourc",
    "engineering manager",
    "head of engineering",
    "vp engineering",
]


def fetch_contacts(company: str, domain: str, api_key: str) -> Iterable[ContactCandidate]:
    if not api_key or not domain:
        return []
    url = build_url(
        "https://api.hunter.io/v2/domain-search",
        {
            "domain": domain,
            "type": "personal",
            "limit": 100,
            "api_key": api_key,
        },
    )
    payload = get_json(url)
    contacts = []
    for item in payload.get("data", {}).get("emails", []):
        position = (item.get("position") or "").lower()
        base_score = float(item.get("confidence", 0) or 0)
        if any(signal in position for signal in TITLE_SIGNALS):
            base_score += 35
        elif position:
            base_score += 5
        contacts.append(
            ContactCandidate(
                company=company,
                domain=domain,
                email=item.get("value", ""),
                full_name=" ".join(
                    part for part in [item.get("first_name", ""), item.get("last_name", "")] if part
                ).strip(),
                position=item.get("position", "") or "",
                confidence=item.get("confidence"),
                score=base_score,
            )
        )
    contacts.sort(key=lambda item: (item.score, item.confidence or 0), reverse=True)
    return contacts[:10]
