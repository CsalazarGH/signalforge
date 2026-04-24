from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .pipeline import enrich_contacts, notify_new_jobs, sync_jobs, write_drafts
from .storage import Storage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find jobs, notify on matches, and draft outreach.")
    parser.add_argument("command", choices=["sync", "notify", "drafts", "list"])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--draft-dir", default="output/drafts")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    storage = Storage(config.db_path)

    if args.command == "sync":
        result = sync_jobs(config.raw, storage)
        contacts = enrich_contacts(config.raw, storage, limit=args.limit)
        print(
            f"Matched {result['matched']} jobs, created {result['created']} records, "
            f"enriched {contacts} contacts, warnings {result['warnings']}."
        )
        for warning in result["warning_messages"]:
            print(f"WARN: {warning}")
    elif args.command == "notify":
        count = notify_new_jobs(config.raw, storage, limit=args.limit)
        print(f"Sent notifications for {count} jobs.")
    elif args.command == "drafts":
        count = write_drafts(config.raw, storage, Path(args.draft_dir), limit=args.limit)
        print(f"Wrote {count} draft files to {args.draft_dir}.")
    elif args.command == "list":
        for row in storage.list_jobs(limit=args.limit):
            print(f"{row['title']} | {row['company']} | {row['location']} | {row['url']}")


if __name__ == "__main__":
    main()
