#!/usr/bin/env python3
"""Send a PushPlus test message."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.pushplus import PushPlusError, send_pushplus


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    try:
        send_pushplus(args.token, "健康space · 测试", "Smoke test OK")
    except PushPlusError as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        return 1
    print("Sent OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
