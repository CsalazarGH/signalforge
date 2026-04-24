from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import ContactCandidate, JobOpening


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                unique_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                company TEXT NOT NULL,
                job_id TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                url TEXT NOT NULL,
                description TEXT,
                team TEXT,
                employment_type TEXT,
                remote INTEGER NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notified_at TEXT
            );

            CREATE TABLE IF NOT EXISTS contacts (
                company TEXT NOT NULL,
                domain TEXT NOT NULL,
                email TEXT NOT NULL,
                full_name TEXT,
                position TEXT,
                confidence INTEGER,
                source TEXT NOT NULL,
                score REAL NOT NULL,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (company, email)
            );
            """
        )
        self.conn.commit()

    def upsert_jobs(self, jobs: Iterable[JobOpening]) -> int:
        created = 0
        for job in jobs:
            existed = self.conn.execute(
                "SELECT 1 FROM jobs WHERE unique_key = ?",
                (job.unique_key,),
            ).fetchone()
            self.conn.execute(
                """
                INSERT INTO jobs (
                    unique_key, source, company, job_id, title, location, url,
                    description, team, employment_type, remote, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(unique_key) DO UPDATE SET
                    title = excluded.title,
                    location = excluded.location,
                    url = excluded.url,
                    description = excluded.description,
                    team = excluded.team,
                    employment_type = excluded.employment_type,
                    remote = excluded.remote,
                    metadata_json = excluded.metadata_json,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (
                    job.unique_key,
                    job.source,
                    job.company,
                    job.job_id,
                    job.title,
                    job.location,
                    job.url,
                    job.description,
                    job.team,
                    job.employment_type,
                    int(job.remote),
                    json.dumps(job.metadata),
                ),
            )
            if not existed:
                created += 1
        self.conn.commit()
        return created

    def upsert_contacts(self, contacts: Iterable[ContactCandidate]) -> None:
        for contact in contacts:
            self.conn.execute(
                """
                INSERT INTO contacts (
                    company, domain, email, full_name, position, confidence, source, score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company, email) DO UPDATE SET
                    full_name = excluded.full_name,
                    position = excluded.position,
                    confidence = excluded.confidence,
                    score = excluded.score
                """,
                (
                    contact.company,
                    contact.domain,
                    contact.email,
                    contact.full_name,
                    contact.position,
                    contact.confidence,
                    contact.source,
                    contact.score,
                ),
            )
        self.conn.commit()

    def list_jobs(self, limit: int = 50, only_unnotified: bool = False) -> list[sqlite3.Row]:
        query = """
            SELECT *
            FROM jobs
        """
        params: tuple[object, ...] = ()
        if only_unnotified:
            query += " WHERE notified_at IS NULL"
        query += " ORDER BY first_seen_at DESC LIMIT ?"
        params = (limit,)
        return list(self.conn.execute(query, params))

    def mark_notified(self, unique_keys: Iterable[str]) -> None:
        keys = list(unique_keys)
        if not keys:
            return
        placeholders = ",".join("?" for _ in keys)
        self.conn.execute(
            f"UPDATE jobs SET notified_at = CURRENT_TIMESTAMP WHERE unique_key IN ({placeholders})",
            keys,
        )
        self.conn.commit()

    def list_contacts_for_company(self, company: str) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT *
                FROM contacts
                WHERE company = ?
                ORDER BY score DESC, confidence DESC, email ASC
                """,
                (company,),
            )
        )
