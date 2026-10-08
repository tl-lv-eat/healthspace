"""Meal photo calorie estimation via vision LLM."""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import call_llm  # noqa: E402

_SYSTEM_PROMPT = (
    "你是饮食热量估算助手。只输出 JSON：food_summary,kcal,advice。"
    "kcal 为整数。不要 markdown。"
)
_USER_TEXT = "估算这餐大概卡路里，并给一句简短建议。"

_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class MealAIError(Exception):
    """LLM response could not be parsed into a meal estimate."""


def parse_estimate_json(raw: str) -> dict[str, Any]:
    """Parse model output into food_summary, kcal, advice."""
    text = (raw or "").strip()
    if not text:
        raise MealAIError("empty model response")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise MealAIError("no JSON object in model response") from None
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError as exc:
            raise MealAIError("invalid JSON in model response") from exc

    if not isinstance(data, dict):
        raise MealAIError("estimate JSON must be an object")

    food_summary = data.get("food_summary")
    advice = data.get("advice")
    kcal_raw = data.get("kcal")

    if food_summary is None or advice is None or kcal_raw is None:
        raise MealAIError("missing food_summary, kcal, or advice")

    try:
        kcal = int(kcal_raw)
    except (TypeError, ValueError) as exc:
        raise MealAIError("kcal must be an integer") from exc

    return {
        "food_summary": str(food_summary).strip(),
        "kcal": kcal,
        "advice": str(advice).strip(),
    }


def _image_mime(path: Path) -> str:
    return _MIME_BY_SUFFIX.get(path.suffix.lower(), "image/jpeg")


def estimate_calories_from_image(path: Path, cfg: dict | None = None) -> dict[str, Any]:
    """Estimate calories from a meal photo; raises MealAIError if parsing fails."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"image not found: {path}")

    raw_bytes = path.read_bytes()
    b64 = base64.standard_b64encode(raw_bytes).decode("ascii")
    mime = _image_mime(path)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": _USER_TEXT},
            ],
        },
    ]

    result = call_llm.responses_chat_messages(
        messages,
        cfg,
        enable_thinking=False,
    )
    return parse_estimate_json(result.text)
