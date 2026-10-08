#!/usr/bin/env python3
"""Generate a daily AI report for a user (requires LLM API key)."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import call_llm
from backend.app.db import SessionLocal, init_db
from backend.app.services.daily_report import generate_daily_report


def _has_api_key() -> bool:
    if os.environ.get("DASHSCOPE_API_KEY", "").strip():
        return True
    config_path = ROOT / "config.yaml"
    if not config_path.is_file():
        return False
    try:
        cfg = call_llm.load_config(config_path)
    except OSError:
        return False
    key = (cfg.get("llm") or {}).get("api_key") or ""
    return bool(str(key).strip() and str(key).strip() != "your-api-key-here")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="dragon")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not _has_api_key():
        print("Skip: set DASHSCOPE_API_KEY or llm.api_key in config.yaml.", file=sys.stderr)
        return 0

    init_db()
    day = date.fromisoformat(args.date)
    with SessionLocal() as db:
        row = generate_daily_report(db, args.user, day, force=args.force)
        print(row.content_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
