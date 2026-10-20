import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "outputs" / "pipeline.db"


def get_connection(db_path=None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(db_path=None):
    conn = get_connection(db_path)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS rows (
            review_id TEXT PRIMARY KEY,
            source_sha256 TEXT NOT NULL,
            review_text TEXT NOT NULL,
            review_rating TEXT NOT NULL,
            review_likes TEXT NOT NULL,
            app_version TEXT NOT NULL,
            review_timestamp TEXT NOT NULL,
            text_sha256 TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS records (
            review_id TEXT PRIMARY KEY,
            source_sha256 TEXT NOT NULL,
            status TEXT NOT NULL,
            topic TEXT,
            intent TEXT,
            sentiment REAL,
            severity INTEGER,
            entities TEXT,
            evidence_quote TEXT,
            needs_review INTEGER,
            label_config TEXT,
            cache_source_id TEXT,
            reason TEXT,
            phase TEXT
        );

        CREATE TABLE IF NOT EXISTS calls (
            request_id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            review_ids TEXT NOT NULL,
            model TEXT NOT NULL,
            phase TEXT,
            outcome TEXT NOT NULL,
            label_config TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS text_cache (
            cache_key TEXT PRIMARY KEY,
            source_review_id TEXT NOT NULL,
            FOREIGN KEY (source_review_id) REFERENCES records(review_id)
        );

        CREATE INDEX IF NOT EXISTS idx_rows_text_sha256 ON rows(text_sha256);
        CREATE INDEX IF NOT EXISTS idx_records_status ON records(status);
        CREATE INDEX IF NOT EXISTS idx_records_intent ON records(intent);
    """)
    conn.commit()
    return conn


def upsert_row(conn, review_id, source_sha256, review_text, review_rating,
               review_likes, app_version, review_timestamp, text_sha256_val):
    conn.execute(
        """INSERT OR REPLACE INTO rows
           (review_id, source_sha256, review_text, review_rating, review_likes, app_version, review_timestamp, text_sha256)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (review_id, source_sha256, review_text, review_rating, review_likes,
         app_version, review_timestamp, text_sha256_val)
    )


def upsert_record_pending(conn, review_id, source_sha256):
    conn.execute(
        """INSERT OR IGNORE INTO records (review_id, source_sha256, status)
           VALUES (?, ?, 'pending')""",
        (review_id, source_sha256)
    )


def upsert_record_quarantined(conn, review_id, source_sha256, reason):
    conn.execute(
        """INSERT OR REPLACE INTO records (review_id, source_sha256, status, reason)
           VALUES (?, ?, 'quarantined', ?)""",
        (review_id, source_sha256, reason)
    )


def write_completed_record(conn, review_id, source_sha256, topic, intent,
                           sentiment, severity, entities, evidence_quote,
                           needs_review, label_config, cache_source_id=None, phase=None):
    conn.execute(
        """INSERT OR REPLACE INTO records
           (review_id, source_sha256, status, topic, intent, sentiment, severity,
            entities, evidence_quote, needs_review, label_config, cache_source_id, phase)
           VALUES (?, ?, 'completed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (review_id, source_sha256, topic, intent, sentiment, severity,
         json.dumps(entities, ensure_ascii=False),
         evidence_quote, 1 if needs_review else 0, label_config, cache_source_id, phase)
    )


def write_call_entry(conn, request_id, role, review_ids, model, phase,
                     outcome, label_config, input_tokens, output_tokens):
    import datetime
    conn.execute(
        """INSERT OR REPLACE INTO calls
           (request_id, role, review_ids, model, phase, outcome, label_config,
            input_tokens, output_tokens, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (request_id, role, json.dumps(review_ids), model, phase, outcome,
         label_config, int(input_tokens), int(output_tokens),
         datetime.datetime.utcnow().isoformat())
    )


def get_cache_origin(conn, ck: str):
    row = conn.execute(
        "SELECT source_review_id FROM text_cache WHERE cache_key = ?", (ck,)
    ).fetchone()
    return row["source_review_id"] if row else None


def update_text_cache(conn, ck: str, review_id: str):
    conn.execute(
        "INSERT OR IGNORE INTO text_cache (cache_key, source_review_id) VALUES (?, ?)",
        (ck, review_id)
    )


def get_record(conn, review_id: str):
    row = conn.execute(
        "SELECT * FROM records WHERE review_id = ?", (review_id,)
    ).fetchone()
    return dict(row) if row else None


def get_review_text(conn, review_id: str) -> str:
    row = conn.execute(
        "SELECT review_text FROM rows WHERE review_id = ?", (review_id,)
    ).fetchone()
    return row["review_text"] if row else ""


def get_completed_ids(conn):
    rows = conn.execute(
        "SELECT review_id FROM records WHERE status = 'completed'"
    ).fetchall()
    return [r["review_id"] for r in rows]


def get_pending_ids(conn):
    rows = conn.execute(
        "SELECT review_id FROM records WHERE status = 'pending'"
    ).fetchall()
    return [r["review_id"] for r in rows]


def get_all_records(conn):
    rows = conn.execute("SELECT * FROM records").fetchall()
    return [dict(r) for r in rows]


def get_all_calls(conn):
    rows = conn.execute("SELECT * FROM calls").fetchall()
    return [dict(r) for r in rows]


def get_completed_complaints(conn):
    rows = conn.execute(
        """SELECT r.review_id, r.topic, r.severity, r.intent, r.evidence_quote,
                  r.source_sha256, r.sentiment, r.entities, r.needs_review,
                  r.label_config, r.cache_source_id
           FROM records r
           WHERE r.status = 'completed'
             AND r.intent IN ('complaint', 'cancellation')"""
    ).fetchall()
    return [dict(r) for r in rows]


def count_completed_complaints(conn) -> int:
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM records
           WHERE status = 'completed' AND intent IN ('complaint', 'cancellation')"""
    ).fetchone()
    return row["cnt"]


def get_all_rows(conn):
    rows = conn.execute("SELECT * FROM rows").fetchall()
    return [dict(r) for r in rows]
