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
    "你是专业的饮食热量估算教练，面向情侣减脂场景。"
    "只输出一个 JSON 对象，字段："
    "food_summary（中文：只写可食用的食物内容与大致份量，例如「米饭一碗、宫保鸡丁、青菜」；"
    "严禁写外卖盒、餐盒、包装、碗碟、筷子、桌面、背景等非食物）；"
    "kcal（整数，该餐估算总热量）、"
    "reason（中文，2～4 句，说明估卡依据：看到了什么食物、份量怎么判、参考热量区间、不确定性；"
    "容器/包装可在 reason 里提，但不要写进 food_summary）、"
    "advice（中文，2～4 句，细致可执行建议）。"
    "不要 markdown，不要其它键。"
)
_USER_TEXT = (
    "请识别这张餐食照片并估算总热量。"
    "food_summary 只要食物本身，不要容器包装。"
    "reason 必须让用户能判断准不准；advice 要具体可执行。"
)

_REFINE_SYSTEM = (
    "你是饮食热量估算教练。用户会基于上一轮估卡结果提出修正。"
    "只输出 JSON：food_summary,kcal,reason,advice。"
    "food_summary 仍然只写可食用食物与份量，不要外卖盒/包装/餐具。"
    "根据用户补充（如份量更大、酱多、还有饮料等）调整 kcal 与说明。"
    "reason 写清相对上一版改了什么；advice 仍要细致。"
    "不要 markdown。"
)

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
    """Parse model output into food_summary, kcal, reason, advice."""
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
    reason = data.get("reason")
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
        "reason": str(reason or "").strip() or "模型未给出详细依据，请结合实物核对份量。",
        "advice": str(advice).strip(),
    }


def _image_mime(path: Path) -> str:
    return _MIME_BY_SUFFIX.get(path.suffix.lower(), "image/jpeg")


def _image_part(path: Path) -> dict[str, Any]:
    raw_bytes = path.read_bytes()
    b64 = base64.standard_b64encode(raw_bytes).decode("ascii")
    mime = _image_mime(path)
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def estimate_calories_from_image(path: Path, cfg: dict | None = None) -> dict[str, Any]:
    """Estimate calories from a meal photo; raises MealAIError if parsing fails."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"image not found: {path}")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                _image_part(path),
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


def refine_calories_estimate(
    *,
    food_summary: str,
    kcal: int,
    reason: str,
    advice: str,
    user_message: str,
    image_path: Path | None = None,
    cfg: dict | None = None,
) -> dict[str, Any]:
    """Refine a previous estimate from user feedback (optional image still attached)."""
    msg = (user_message or "").strip()
    if not msg:
        raise MealAIError("empty refine message")

    content: list[dict[str, Any]] = []
    if image_path is not None and Path(image_path).is_file():
        content.append(_image_part(Path(image_path)))

    content.append(
        {
            "type": "text",
            "text": (
                f"上一轮结果：\n"
                f"- food_summary: {food_summary}\n"
                f"- kcal: {kcal}\n"
                f"- reason: {reason}\n"
                f"- advice: {advice}\n\n"
                f"用户补充/修正：{msg}\n"
                f"请输出更新后的 JSON。"
            ),
        }
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _REFINE_SYSTEM},
        {"role": "user", "content": content},
    ]
    result = call_llm.responses_chat_messages(messages, cfg, enable_thinking=False)
    return parse_estimate_json(result.text)


def format_advice_for_storage(reason: str, advice: str) -> str:
    reason = (reason or "").strip()
    advice = (advice or "").strip()
    if reason and advice:
        return f"【估卡依据】{reason}\n\n【建议】{advice}"
    return advice or reason
