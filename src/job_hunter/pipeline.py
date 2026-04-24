from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from .clients import greenhouse, hunter, lever
from .filters import matches_filters
from .http import HttpError
from .models import JobOpening
from .notify import send_email, send_slack
from .storage import Storage


def sync_jobs(config: dict, storage: Storage) -> dict[str, int]:
    filters = config.get("filters", {})
    matched_jobs: list[JobOpening] = []
    warnings: list[str] = []

    for item in config.get("sources", {}).get("greenhouse_companies", []):
        board_token = item["board_token"] if isinstance(item, dict) else item
        company = item.get("company", board_token) if isinstance(item, dict) else board_token
        domain = item.get("domain", "") if isinstance(item, dict) else ""
        try:
            for job in greenhouse.fetch_jobs(board_token):
                job.company = company
                if domain:
                    job.metadata["company_domain"] = domain
                if matches_filters(job, filters):
                    matched_jobs.append(job)
        except HttpError as exc:
            warnings.append(f"Greenhouse {board_token}: {exc}")

    for item in config.get("sources", {}).get("lever_companies", []):
        site = item["site"] if isinstance(item, dict) else item
        company = item.get("company", site) if isinstance(item, dict) else site
        domain = item.get("domain", "") if isinstance(item, dict) else ""
        try:
            for job in lever.fetch_jobs(site):
                job.company = company
                if domain:
                    job.metadata["company_domain"] = domain
                if matches_filters(job, filters):
                    matched_jobs.append(job)
        except HttpError as exc:
            warnings.append(f"Lever {site}: {exc}")

    created = storage.upsert_jobs(matched_jobs)
    return {"matched": len(matched_jobs), "created": created, "warnings": len(warnings), "warning_messages": warnings}


def enrich_contacts(config: dict, storage: Storage, limit: int = 25) -> int:
    api_key = config.get("hunter", {}).get("api_key", "")
    if not api_key:
        return 0

    jobs = storage.list_jobs(limit=limit)
    inserted = 0
    for row in jobs:
        domain = _extract_domain(row)
        if not domain:
            continue
        try:
            contacts = hunter.fetch_contacts(row["company"], domain, api_key)
        except HttpError:
            continue
        storage.upsert_contacts(contacts)
        inserted += len(contacts)
    return inserted


def notify_new_jobs(config: dict, storage: Storage, limit: int = 10) -> int:
    jobs = storage.list_jobs(limit=limit, only_unnotified=True)
    if not jobs:
        return 0

    lines = ["New software engineering jobs:"]
    for row in jobs:
        lines.append(f"- {row['title']} at {row['company']} ({row['location']})")
        lines.append(f"  {row['url']}")

    message = "\n".join(lines)
    notifications = config.get("notifications", {})
    try:
        send_slack(notifications.get("slack_webhook_url", ""), message)
    except HttpError:
        pass
    try:
        send_email(notifications.get("email", {}), "New software engineering jobs", message)
    except OSError:
        pass
    storage.mark_notified([row["unique_key"] for row in jobs])
    return len(jobs)


def write_drafts(config: dict, storage: Storage, output_dir: Path, limit: int = 10) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    profile = config.get("candidate_profile", {})
    jobs = storage.list_jobs(limit=limit)
    count = 0
    for row in jobs:
        contacts = storage.list_contacts_for_company(row["company"])
        contact = contacts[0] if contacts else None
        body = _build_outreach_draft(profile, row, contact)
        filename = f"{row['company']}_{row['job_id']}.md".replace("/", "_")
        (output_dir / filename).write_text(body, encoding="utf-8")
        count += 1
    return count


def _extract_domain(row) -> str:
    metadata = row["metadata_json"]
    if metadata:
        parsed = json.loads(metadata)
        if parsed.get("company_domain"):
            return parsed["company_domain"]
    host = urlparse(row["url"]).netloc.lower()
    if host.startswith("boards.greenhouse.io"):
        return ""
    if host.startswith("jobs.lever.co"):
        return ""
    return host.replace("www.", "")


def _build_outreach_draft(profile: dict, row, contact) -> str:
    full_name = profile.get("full_name", "Candidate")
    skills = ", ".join(profile.get("skills", [])[:4])
    intro_target = contact["full_name"] if contact and contact["full_name"] else "Hiring Team"
    intro_line = f"Hi {intro_target},"
    contact_line = ""
    if contact:
        contact_line = f"Likely contact: {contact['full_name'] or 'Unknown'} <{contact['email']}> ({contact['position']})\n\n"

    return (
        f"# Outreach Draft\n\n"
        f"Company: {row['company']}\n"
        f"Role: {row['title']}\n"
        f"Location: {row['location']}\n"
        f"Apply URL: {row['url']}\n\n"
        f"{contact_line}"
        f"{intro_line}\n\n"
        f"My name is {full_name}, and I’m reaching out because I’m interested in the {row['title']} role at {row['company']}.\n\n"
        f"I’ve been working across {skills}, and the role looks closely aligned with the kind of engineering work I enjoy most.\n\n"
        f"I’d love to be considered, and I’m happy to send over any additional context beyond my application materials.\n\n"
        f"Best,\n"
        f"{full_name}\n"
        f"{profile.get('email', '')}\n"
        f"{profile.get('linkedin_url', '')}\n"
    )
