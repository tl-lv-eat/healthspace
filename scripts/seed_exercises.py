#!/usr/bin/env python3
"""Load curated strength exercises into SQLite from backend/data/exercises_seed.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.db import SessionLocal, init_db
from backend.app.models import Exercise

GIF_BASE = "https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@v1.1.0"
SEED_PATH = ROOT / "backend" / "data" / "exercises_seed.json"


def gif_url(muscle: str, slug: str) -> str:
    return f"{GIF_BASE}/{muscle}/{slug}.gif"


def load_seed_rows() -> list[dict]:
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit(f"Expected JSON array in {SEED_PATH}")
    return raw


def seed() -> None:
    if not SEED_PATH.is_file():
        raise SystemExit(f"Missing seed file: {SEED_PATH}")
    rows = load_seed_rows()
    init_db()
    inserted = 0
    updated = 0
    with SessionLocal() as db:
        for item in rows:
            slug = str(item["slug"])
            muscle = str(item["muscle"])
            existing = db.query(Exercise).filter(Exercise.slug == slug).first()
            fields = {
                "name_zh": str(item["name_zh"]),
                "name_en": str(item.get("name_en", "")),
                "body_part": str(item["body_part"]),
                "gif_url": gif_url(muscle, slug),
                "instructions_zh": str(item.get("instructions_zh", "")),
                "is_custom": False,
                "owner_user_id": None,
            }
            if existing is None:
                db.add(Exercise(slug=slug, **fields))
                inserted += 1
            else:
                for key, value in fields.items():
                    setattr(existing, key, value)
                updated += 1
        db.commit()
    print(f"Seed complete: {inserted} inserted, {updated} updated ({len(rows)} in file).")


if __name__ == "__main__":
    seed()
