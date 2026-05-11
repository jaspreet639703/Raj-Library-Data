"""
storage.py — SQLite persistence and CSV export
"""

import sqlite3
import csv
import os
from datetime import datetime

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "exports")

COLUMNS = [
    "place_id", "name", "owner_name", "address", "phone", "rating",
    "website", "email", "instagram", "facebook", "youtube",
    "google_maps_url", "state", "district", "tehsil", "entity_type",
    "scraped_at",
]

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS libraries (
    place_id    TEXT PRIMARY KEY,
    name        TEXT,
    owner_name  TEXT,
    address     TEXT,
    phone       TEXT,
    rating      TEXT,
    website     TEXT,
    email       TEXT,
    instagram   TEXT,
    facebook    TEXT,
    youtube     TEXT,
    google_maps_url TEXT,
    state       TEXT,
    district    TEXT,
    tehsil      TEXT,
    entity_type TEXT,
    scraped_at  TEXT
);
"""


def _get_db_path(district: str) -> str:
    sanitized_district = district.strip().lower().replace(" ", "_")
    return os.path.join(os.path.dirname(__file__), "..", "data", f"{sanitized_district}_libraries.db")


def _conn(district: str):
    db_path = _get_db_path(district)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(district: str):
    with _conn(district) as con:
        con.execute(CREATE_TABLE_SQL)
    print(f"  DB ready: {_get_db_path(district)}")


def save_record(record: dict, district: str) -> bool:
    """Insert a record; skip if place_id already exists. Returns True if inserted."""
    record.setdefault("scraped_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    record.setdefault("place_id", record.get("name", "") + record.get("address", ""))

    placeholders = ", ".join("?" for _ in COLUMNS)
    values = [record.get(c, "") for c in COLUMNS]

    with _conn(district) as con:
        try:
            con.execute(
                f"INSERT INTO libraries ({', '.join(COLUMNS)}) VALUES ({placeholders})",
                values,
            )
            return True
        except sqlite3.IntegrityError:
            return False  # Duplicate place_id — skip


def get_all_records(district: str) -> list[dict]:
    with _conn(district) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM libraries ORDER BY tehsil, name").fetchall()
    return [dict(r) for r in rows]


def export_csv(district: str) -> str:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_district = district.strip().replace(" ", "_")
    path = os.path.join(EXPORT_DIR, f"{sanitized_district}_Libraries_{timestamp}.csv")

    records = get_all_records(district)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)

    print(f"  Exported {len(records)} records for {district} → {path}")
    return path
