from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from .clients import adzuna, greenhouse, hunter, lever, remotive
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

    for item in config.get("sources", {}).get("remotive_searches", []):
        search = item.get("search", "") if isinstance(item, dict) else str(item)
        category = item.get("category", "software-dev") if isinstance(item, dict) else "software-dev"
        limit = item.get("limit", 50) if isinstance(item, dict) else 50
        try:
            for job in remotive.fetch_jobs(search=search, category=category, limit=limit):
                if matches_filters(job, filters):
                    matched_jobs.append(job)
        except HttpError as exc:
            warnings.append(f"Remotive {search or category}: {exc}")

    adzuna_config = config.get("adzuna", {})
    app_id = adzuna_config.get("app_id", "")
    app_key = adzuna_config.get("app_key", "")
    for item in config.get("sources", {}).get("adzuna_searches", []):
        what = item.get("what", "") if isinstance(item, dict) else str(item)
        where = item.get("where", "") if isinstance(item, dict) else ""
        country = item.get("country", "us") if isinstance(item, dict) else "us"
        results_per_page = item.get("results_per_page", 20) if isinstance(item, dict) else 20
        if not app_id or not app_key:
            warnings.append(f"Adzuna {what or country}: missing ADZUNA_APP_ID or ADZUNA_APP_KEY.")
            continue
        try:
            for job in adzuna.fetch_jobs(
                country=country,
                what=what,
                where=where,
                app_id=app_id,
                app_key=app_key,
                results_per_page=results_per_page,
            ):
                if matches_filters(job, filters):
                    matched_jobs.append(job)
        except HttpError as exc:
            warnings.append(f"Adzuna {what or country}: {exc}")

    created = storage.upsert_jobs(matched_jobs)
    return {"matched": len(matched_jobs), "created": created, "warnings": len(warnings), "warning_messages": warnings}


def enrich_contacts(config: dict, storage: Storage, limit: int = 25) -> int:
    result = enrich_contacts_with_details(config, storage, limit=limit)
    return result["inserted"]


def enrich_contacts_with_details(config: dict, storage: Storage, limit: int = 25) -> dict[str, object]:
    api_key = config.get("hunter", {}).get("api_key", "")
    if not api_key:
        return {
            "inserted": 0,
            "checked": 0,
            "warnings": ["Hunter API key not configured."],
            "summary": [],
        }

    jobs = storage.list_jobs(limit=limit)
    inserted = 0
    checked = 0
    warnings: list[str] = []
    summary: list[str] = []
    seen_company_domains: set[tuple[str, str]] = set()
    for row in jobs:
        domain = _extract_domain(row)
        company_name = str(row["company"])
        company_domain_key = (company_name, domain or company_name.lower())
        if company_domain_key in seen_company_domains:
            continue
        seen_company_domains.add(company_domain_key)
        checked += 1
        try:
            contacts = hunter.fetch_contacts(company_name, domain, api_key)
        except HttpError as exc:
            target = domain or company_name
            warnings.append(f"{company_name} ({target}): {exc}")
            continue
        storage.upsert_contacts(contacts)
        inserted += len(contacts)
        target = domain or company_name
        summary.append(f"{company_name} ({target}): {len(contacts)} contacts")
    return {
        "inserted": inserted,
        "checked": checked,
        "warnings": warnings,
        "summary": summary,
    }


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
    if row["source"] in {"remotive", "adzuna"}:
        return ""
    if host.startswith("boards.greenhouse.io"):
        return ""
    if host.startswith("jobs.lever.co"):
        return ""
    if host.endswith("remotive.com"):
        return ""
    if host.endswith("adzuna.com") or host.endswith("adzuna.co.uk"):
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
