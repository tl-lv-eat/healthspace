#!/usr/bin/env python3
"""Smoke test: vision calorie estimate on data/img/*.jpg (requires API key)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import call_llm
from backend.app.services.meal_ai import MealAIError, estimate_calories_from_image


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
    if not _has_api_key():
        print(
            "Skip smoke test: set DASHSCOPE_API_KEY or llm.api_key in config.yaml.",
            file=sys.stderr,
        )
        return 0

    img_dir = ROOT / "data" / "img"
    if not img_dir.is_dir():
        print(f"No image directory: {img_dir}", file=sys.stderr)
        return 0

    images = sorted(img_dir.glob("*.jpg")) + sorted(img_dir.glob("*.jpeg"))
    if not images:
        print(f"No *.jpg in {img_dir}", file=sys.stderr)
        return 0

    cfg = None
    if (ROOT / "config.yaml").is_file():
        cfg = call_llm.load_config()

    for path in images:
        print(f"\n--- {path.name} ---")
        try:
            estimate = estimate_calories_from_image(path, cfg=cfg)
            print(json.dumps(estimate, ensure_ascii=False, indent=2))
        except MealAIError as exc:
            print(f"parse error: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"API error: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
