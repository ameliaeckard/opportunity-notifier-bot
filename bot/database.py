from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from bot.models import Opportunity, Subscriber


UTC = timezone.utc


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS subscribers (
                    discord_user_id INTEGER PRIMARY KEY,
                    opted_in INTEGER NOT NULL DEFAULT 0,
                    internships_enabled INTEGER NOT NULL DEFAULT 0,
                    hackathons_enabled INTEGER NOT NULL DEFAULT 0,
                    frequency TEXT CHECK (frequency IN ('daily', 'weekly') OR frequency IS NULL),
                    last_notification TEXT,
                    opted_in_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS opportunities (
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('internship', 'hackathon')),
                    organization TEXT NOT NULL,
                    title TEXT NOT NULL,
                    location TEXT NOT NULL,
                    url TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    discovered_at TEXT NOT NULL,
                    notify_eligible INTEGER NOT NULL DEFAULT 1,
                    raw_json TEXT,
                    PRIMARY KEY (source, external_id)
                );

                CREATE TABLE IF NOT EXISTS deliveries (
                    discord_user_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    delivered_at TEXT NOT NULL,
                    PRIMARY KEY (discord_user_id, source, external_id),
                    FOREIGN KEY (source, external_id) REFERENCES opportunities(source, external_id)
                );

                CREATE TABLE IF NOT EXISTS source_state (
                    source TEXT PRIMARY KEY,
                    initialized INTEGER NOT NULL DEFAULT 0,
                    last_checked_at TEXT
                );

                CREATE TABLE IF NOT EXISTS scheduler_runs (
                    run_key TEXT PRIMARY KEY,
                    ran_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_opportunities_kind_discovered
                ON opportunities(kind, discovered_at);

                CREATE INDEX IF NOT EXISTS idx_subscribers_frequency
                ON subscribers(opted_in, frequency);
                """
            )

    def get_subscriber(self, user_id: int) -> Subscriber | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM subscribers WHERE discord_user_id = ?",
                (user_id,),
            ).fetchone()
        return self._row_to_subscriber(row) if row else None

    def save_preferences(self, user_id: int, internships: bool, hackathons: bool, frequency: str) -> None:
        if frequency not in {"daily", "weekly"}:
            raise ValueError("frequency must be daily or weekly")
        now = utc_now_iso()
        current = self.get_subscriber(user_id)
        opted_in_at = current.opted_in_at if current and current.opted_in and current.opted_in_at else now
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO subscribers (
                    discord_user_id, opted_in, internships_enabled, hackathons_enabled,
                    frequency, last_notification, opted_in_at, updated_at
                ) VALUES (?, 1, ?, ?, ?, NULL, ?, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    opted_in = 1,
                    internships_enabled = excluded.internships_enabled,
                    hackathons_enabled = excluded.hackathons_enabled,
                    frequency = excluded.frequency,
                    opted_in_at = excluded.opted_in_at,
                    updated_at = excluded.updated_at
                """,
                (user_id, int(internships), int(hackathons), frequency, opted_in_at, now),
            )

    def opt_out(self, user_id: int) -> None:
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO subscribers (
                    discord_user_id, opted_in, internships_enabled, hackathons_enabled,
                    frequency, last_notification, opted_in_at, updated_at
                ) VALUES (?, 0, 0, 0, NULL, NULL, NULL, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    opted_in = 0,
                    internships_enabled = 0,
                    hackathons_enabled = 0,
                    frequency = NULL,
                    opted_in_at = NULL,
                    updated_at = excluded.updated_at
                """,
                (user_id, now),
            )

    def subscribers_for_frequency(self, frequency: str) -> list[Subscriber]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM subscribers WHERE opted_in = 1 AND frequency = ?",
                (frequency,),
            ).fetchall()
        return [self._row_to_subscriber(row) for row in rows]

    def source_initialized(self, source: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT initialized FROM source_state WHERE source = ?",
                (source,),
            ).fetchone()
        return bool(row and row["initialized"])

    def mark_source_checked(self, source: str, initialized: bool = True) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO source_state(source, initialized, last_checked_at)
                VALUES (?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET
                    initialized = excluded.initialized,
                    last_checked_at = excluded.last_checked_at
                """,
                (source, int(initialized), utc_now_iso()),
            )

    def store_opportunities(self, opportunities: list[Opportunity], notify_eligible: bool) -> int:
        inserted = 0
        discovered_at = utc_now_iso()
        with self._connect() as conn:
            for item in opportunities:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO opportunities (
                        source, external_id, kind, organization, title, location, url,
                        start_date, end_date, discovered_at, notify_eligible, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.source,
                        item.external_id,
                        item.kind,
                        item.organization,
                        item.title,
                        item.location,
                        item.url,
                        item.start_date,
                        item.end_date,
                        discovered_at,
                        int(notify_eligible),
                        json.dumps(item.metadata, ensure_ascii=False),
                    ),
                )
                inserted += cursor.rowcount
        return inserted

    def pending_opportunities(self, subscriber: Subscriber, kind: str, limit: int = 10) -> list[Opportunity]:
        if not subscriber.opted_in_at:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT o.*
                FROM opportunities o
                WHERE o.kind = ?
                  AND o.notify_eligible = 1
                  AND o.discovered_at >= ?
                  AND NOT EXISTS (
                      SELECT 1 FROM deliveries d
                      WHERE d.discord_user_id = ?
                        AND d.source = o.source
                        AND d.external_id = o.external_id
                  )
                ORDER BY o.discovered_at ASC
                LIMIT ?
                """,
                (kind, subscriber.opted_in_at, subscriber.discord_user_id, limit),
            ).fetchall()
        return [self._row_to_opportunity(row) for row in rows]

    def mark_delivered(self, user_id: int, opportunities: list[Opportunity]) -> None:
        if not opportunities:
            return
        delivered_at = utc_now_iso()
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO deliveries(discord_user_id, source, external_id, delivered_at)
                VALUES (?, ?, ?, ?)
                """,
                [(user_id, item.source, item.external_id, delivered_at) for item in opportunities],
            )
            conn.execute(
                "UPDATE subscribers SET last_notification = ?, updated_at = ? WHERE discord_user_id = ?",
                (delivered_at, delivered_at, user_id),
            )

    def scheduler_run_exists(self, run_key: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM scheduler_runs WHERE run_key = ?",
                (run_key,),
            ).fetchone()
        return row is not None

    def mark_scheduler_run(self, run_key: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO scheduler_runs(run_key, ran_at) VALUES (?, ?)",
                (run_key, utc_now_iso()),
            )

    @staticmethod
    def _row_to_subscriber(row: sqlite3.Row) -> Subscriber:
        return Subscriber(
            discord_user_id=int(row["discord_user_id"]),
            opted_in=bool(row["opted_in"]),
            internships_enabled=bool(row["internships_enabled"]),
            hackathons_enabled=bool(row["hackathons_enabled"]),
            frequency=row["frequency"],
            last_notification=row["last_notification"],
            opted_in_at=row["opted_in_at"],
        )

    @staticmethod
    def _row_to_opportunity(row: sqlite3.Row) -> Opportunity:
        return Opportunity(
            source=row["source"],
            external_id=row["external_id"],
            kind=row["kind"],
            organization=row["organization"],
            title=row["title"],
            location=row["location"],
            url=row["url"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            metadata=json.loads(row["raw_json"] or "{}"),
        )
