# Job Hunter

`job_hunter` is a local-first CLI that helps you monitor software engineering jobs, enrich likely hiring contacts, and generate outreach/application drafts for human review.

## What It Does

- Pulls public jobs from Greenhouse and Lever board endpoints.
- Filters for software-engineering roles using configurable keywords.
- Stores and deduplicates results in a local SQLite database.
- Enriches likely recruiting contacts with Hunter's Domain Search API.
- Sends notifications through Slack or email.
- Generates outreach drafts and application notes for review.

## What It Does Not Do

- It does not submit applications automatically.
- It does not send cold email automatically.
- It does not scrape private or gated data sources.

Those choices are deliberate: fully automated applications and outreach tend to be brittle, spammy, and risky for your accounts. This version keeps the repetitive work automated while leaving the final send/apply decision with you.

## Quick Start

1. Copy the example config:

```bash
cp config.example.json config.json
```

2. Edit `config.json` with your target companies and optional integrations.

3. Run a sync:

```bash
python3 -m src.job_hunter.cli sync --config config.json
```

4. See saved matches:

```bash
python3 -m src.job_hunter.cli list --config config.json
```

5. Generate drafts:

```bash
python3 -m src.job_hunter.cli drafts --config config.json
```

## Configuration

The config is JSON-based and supports:

- `candidate_profile`: your name, locations, resume path, and keywords.
- `filters`: title/location keywords and exclusions.
- `sources.greenhouse_companies`: Greenhouse board tokens to scan.
- `sources.lever_companies`: Lever site names to scan.
- `hunter.api_key`: optional Hunter API key for contact enrichment.
- `notifications.slack_webhook_url`: optional Slack incoming webhook.
- `notifications.email`: optional SMTP settings.

## Example Scheduler

Run every morning at 8am:

```bash
0 8 * * * cd /Users/chrissalazar/Documents/Codex/2026-04-23/i-need-to-build-a-tool && python3 -m src.job_hunter.cli sync --config config.json && python3 -m src.job_hunter.cli notify --config config.json
```

## Data Sources

This tool is built around public ATS endpoints and official docs:

- [Greenhouse API overview](https://support.greenhouse.io/hc/en-us/articles/10568627186203-Greenhouse-API-overview)
- [Lever Postings API](https://github.com/lever/postings-api)
- [Hunter API documentation](https://hunter.io/api-documentation)
