# Job Hunter

`job_hunter` is a local-first CLI that helps you monitor software engineering jobs, enrich likely hiring contacts, and generate outreach/application drafts for human review.

## What It Does

- Pulls public jobs from Greenhouse and Lever board endpoints.
- Pulls broader jobs from Remotive search queries.
- Optionally pulls market-wide jobs from Adzuna search queries.
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

If you want to keep your Hunter key out of files entirely, set it as an environment variable instead:

```bash
export HUNTER_API_KEY="your_hunter_api_key"
```

For broader non-ATS search, you can also set Adzuna credentials:

```bash
export ADZUNA_APP_ID="your_adzuna_app_id"
export ADZUNA_APP_KEY="your_adzuna_app_key"
```

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

6. Build an action list:

```bash
python3 -m src.job_hunter.cli shortlist --config config.json --limit 25 --output output/shortlist.md
```

## Configuration

The config is JSON-based and supports:

- `candidate_profile`: your name, locations, resume path, and keywords.
- `filters`: title/location keywords and exclusions.
- `sources.greenhouse_companies`: Greenhouse board tokens to scan.
- `sources.lever_companies`: Lever site names to scan.
- `sources.remotive_searches`: broader remote job keyword searches.
- `sources.adzuna_searches`: broader market job keyword/location searches.
- `hunter.api_key`: optional Hunter API key for contact enrichment.
- `adzuna.app_id` and `adzuna.app_key`: optional Adzuna API credentials.
- `notifications.slack_webhook_url`: optional Slack incoming webhook.
- `notifications.email`: optional SMTP settings.

## Shortlist Output

The `shortlist` command creates a ranked list with:

- job fit score
- apply link
- best contact found
- a recommended next action such as `Apply + cold outreach`

## Broader Search

To move beyond a fixed company list, add searches under `remotive_searches` and `adzuna_searches`.

- Remotive is good for broad remote software jobs.
- Adzuna is good for wider market search across locations, but it requires `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.

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
- [Remotive Remote Jobs Public API](https://remotive.com/remote-jobs/api)
- [Adzuna API overview](https://developer.adzuna.com/overview)
