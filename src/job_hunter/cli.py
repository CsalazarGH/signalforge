from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .pipeline import enrich_contacts_with_details, notify_new_jobs, sync_jobs, write_drafts
from .shortlist import build_shortlist, write_shortlist
from .storage import Storage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find jobs, notify on matches, and draft outreach.")
    parser.add_argument("command", choices=["sync", "notify", "drafts", "list", "shortlist"])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--draft-dir", default="output/drafts")
    parser.add_argument("--output", default="output/shortlist.md")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args.config)
    storage = Storage(config.db_path)

    if args.command == "sync":
        result = sync_jobs(config.raw, storage)
        contacts = enrich_contacts_with_details(config.raw, storage, limit=args.limit)
        print(
            f"Matched {result['matched']} jobs, created {result['created']} records, "
            f"enriched {contacts['inserted']} contacts, warnings {result['warnings'] + len(contacts['warnings'])}."
        )
        for warning in result["warning_messages"]:
            print(f"WARN: {warning}")
        for warning in contacts["warnings"]:
            print(f"WARN: {warning}")
        for line in contacts["summary"]:
            print(f"INFO: {line}")
    elif args.command == "notify":
        count = notify_new_jobs(config.raw, storage, limit=args.limit)
        print(f"Sent notifications for {count} jobs.")
    elif args.command == "drafts":
        count = write_drafts(config.raw, storage, Path(args.draft_dir), limit=args.limit)
        print(f"Wrote {count} draft files to {args.draft_dir}.")
    elif args.command == "list":
        for row in storage.list_jobs(limit=args.limit):
            print(f"{row['title']} | {row['company']} | {row['location']} | {row['url']}")
    elif args.command == "shortlist":
        rows = build_shortlist(config.raw, storage, limit=args.limit)
        write_shortlist(Path(args.output), rows)
        print(f"Wrote {len(rows)} shortlist rows to {args.output}.")


if __name__ == "__main__":
    main()
