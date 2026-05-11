"""
District Library Scraper
Scrapes Google Maps for libraries in each tehsil of districts from CSV.
Collects: name, address, phone, rating, website, email, Instagram, Facebook, YouTube
"""

import asyncio
import csv
import os
import sys
from scraper.browser import scrape_libraries_in_tehsil
from scraper.storage import init_db, save_record, export_csv
from scraper.checkpoint import load_checkpoint, save_checkpoint

# ── Config ────────────────────────────────────────────────────────────────────
ENTITY_TYPES = [
    "library",
    "study library",
    "reading room",
    "coaching library",
    "public library",
]


def load_locations_from_csv():
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "dholpur_tehsils.csv")
    locations = {}
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
        return locations

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            district = row["district"]
            if district not in locations:
                locations[district] = []
            locations[district].append({
                "state": row["state"],
                "district": district,
                "tehsil": row["tehsil"],
            })
    return locations


async def run():
    print("=" * 60)
    print("  District Library Data Collector")
    print("  Target: Locations loaded from CSV")
    print("=" * 60)

    locations_by_district = load_locations_from_csv()
    if not locations_by_district:
        return

    completed = load_checkpoint()

    for district, locations in locations_by_district.items():
        print(f"\nProcessing District: {district}")
        init_db(district)
        total_saved = 0

        for location in locations:
            tehsil = location["tehsil"]

            for entity in ENTITY_TYPES:
                job_key = f"{district}::{tehsil}::{entity}"

                if job_key in completed:
                    print(f"  [SKIP] Already done: {district} — {tehsil} — {entity}")
                    continue

                print(f"\n→ Scraping: '{entity}' in {tehsil}, {district}, {location['state']}")

                try:
                    records = await scrape_libraries_in_tehsil(
                        state=location["state"],
                        district=district,
                        tehsil=tehsil,
                        entity=entity,
                    )

                    for record in records:
                        saved = save_record(record, district)
                        if saved:
                            total_saved += 1
                            print(f"    ✓ Saved: {record.get('name', 'Unknown')}")

                    save_checkpoint(job_key)
                    print(f"  ✅ Done: {tehsil}/{entity} — {len(records)} found")

                except Exception as e:
                    print(f"  ✗ Error on {tehsil}/{entity}: {e}")
                    continue

        print(f"\n{'='*60}")
        print(f"  COMPLETE for {district} — Total new records saved: {total_saved}")
        print(f"{'='*60}")

        csv_path = export_csv(district)
        print(f"\n📄 CSV exported for {district} to: {csv_path}")


if __name__ == "__main__":
    asyncio.run(run())
