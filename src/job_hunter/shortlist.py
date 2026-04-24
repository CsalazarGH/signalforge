from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .storage import Storage

CONTACT_PRIORITY_SIGNALS = [
    "recruit",
    "talent",
    "sourc",
    "engineering manager",
    "head of engineering",
    "vp engineering",
    "director of engineering",
]


@dataclass
class ShortlistRow:
    fit_score: int
    company: str
    title: str
    location: str
    apply_url: str
    outreach_recommendation: str
    contact_name: str
    contact_email: str
    contact_title: str
    company_domain: str
    notes: str


def build_shortlist(config: dict, storage: Storage, limit: int = 25) -> list[ShortlistRow]:
    jobs = storage.list_jobs(limit=limit)
    profile = config.get("candidate_profile", {})
    rows: list[ShortlistRow] = []

    for job in jobs:
        contact = _select_best_contact(storage, job["company"])
        fit_score, notes = _score_job(job, profile)
        company_domain = _extract_company_domain(job)
        rows.append(
            ShortlistRow(
                fit_score=fit_score,
                company=str(job["company"]),
                title=str(job["title"]),
                location=str(job["location"] or ""),
                apply_url=str(job["url"]),
                outreach_recommendation=_recommend_action(contact),
                contact_name=_contact_value(contact, "full_name"),
                contact_email=_contact_value(contact, "email"),
                contact_title=_contact_value(contact, "position"),
                company_domain=company_domain,
                notes=notes,
            )
        )

    rows.sort(key=lambda row: (-row.fit_score, row.company.lower(), row.title.lower()))
    return rows


def write_shortlist(output_path: Path, rows: list[ShortlistRow]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".csv":
        _write_csv(output_path, rows)
    else:
        _write_markdown(output_path, rows)


def _write_csv(output_path: Path, rows: list[ShortlistRow]) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "fit_score",
                "company",
                "title",
                "location",
                "apply_url",
                "outreach_recommendation",
                "contact_name",
                "contact_email",
                "contact_title",
                "company_domain",
                "notes",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.fit_score,
                    row.company,
                    row.title,
                    row.location,
                    row.apply_url,
                    row.outreach_recommendation,
                    row.contact_name,
                    row.contact_email,
                    row.contact_title,
                    row.company_domain,
                    row.notes,
                ]
            )


def _write_markdown(output_path: Path, rows: list[ShortlistRow]) -> None:
    lines = [
        "# Job Shortlist",
        "",
        "| Fit | Company | Role | Location | Apply Here | Cold Outreach | Contact | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        apply_link = f"[Apply]({row.apply_url})"
        outreach = row.outreach_recommendation
        contact_bits = " / ".join(part for part in [row.contact_name, row.contact_email, row.contact_title] if part)
        lines.append(
            f"| {row.fit_score} | {row.company} | {row.title} | {row.location} | {apply_link} | "
            f"{outreach} | {contact_bits or 'No contact found'} | {row.notes} |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _score_job(job, profile: dict) -> tuple[int, str]:
    title = str(job["title"]).lower()
    location = str(job["location"] or "").lower()
    metadata = json.loads(job["metadata_json"]) if job["metadata_json"] else {}
    description = str(job["description"] or "").lower()
    skills = [skill.lower() for skill in profile.get("skills", [])]
    preferred_locations = [location_item.lower() for location_item in profile.get("locations", [])]

    score = 50
    notes: list[str] = []

    title_signals = {
        "senior": 12,
        "software engineer": 15,
        "backend": 12,
        "full stack": 10,
        "platform": 10,
        "infrastructure": 10,
    }
    for signal, points in title_signals.items():
        if signal in title:
            score += points
            notes.append(f"title:{signal}")

    if any(skill in description or skill in title for skill in skills):
        matched_skills = [skill for skill in skills if skill in description or skill in title]
        score += min(20, len(matched_skills) * 5)
        if matched_skills:
            notes.append("skills:" + ", ".join(matched_skills[:4]))

    if any(preferred in location for preferred in preferred_locations):
        score += 10
        notes.append("preferred location")
    elif job["remote"]:
        score += 8
        notes.append("remote")

    if metadata.get("team"):
        team = str(metadata["team"]).lower()
        if "engineer" in team or "platform" in team or "infrastructure" in team:
            score += 5
            notes.append(f"team:{metadata['team']}")

    return min(score, 100), "; ".join(notes) or "general fit"


def _select_best_contact(storage: Storage, company: str):
    contacts = storage.list_contacts_for_company(company)
    if not contacts:
        return None

    def contact_rank(contact) -> tuple[float, int, str]:
        title = str(contact["position"] or "").lower()
        signal_bonus = 0
        if any(signal in title for signal in CONTACT_PRIORITY_SIGNALS):
            signal_bonus = 50
        return (
            float(contact["score"] or 0) + signal_bonus,
            int(contact["confidence"] or 0),
            str(contact["email"]),
        )

    return sorted(contacts, key=contact_rank, reverse=True)[0]


def _recommend_action(contact) -> str:
    if not contact:
        return "Apply only"
    if _contact_value(contact, "email"):
        return "Apply + cold outreach"
    return "Apply, then research contact"


def _contact_value(contact, key: str) -> str:
    if not contact:
        return ""
    return str(contact[key] or "")


def _extract_company_domain(job) -> str:
    if not job["metadata_json"]:
        return ""
    metadata = json.loads(job["metadata_json"])
    return str(metadata.get("company_domain", ""))
