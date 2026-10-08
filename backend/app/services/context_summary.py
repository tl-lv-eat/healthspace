"""Pure functions: compact Chinese summaries for LLM prompts."""

from __future__ import annotations

from typing import Any


def _meal_line(m: dict[str, Any]) -> str:
    mt = m.get("meal_type") or "餐"
    kcal = m.get("user_kcal")
    summary = (m.get("food_summary") or "").strip()
    if kcal is not None:
        part = f"{mt} {kcal}kcal"
    else:
        part = str(mt)
    if summary:
        part += f"（{summary}）"
    return part


def _workout_line(w: dict[str, Any]) -> str:
    kind = w.get("kind") or "运动"
    payload = w.get("payload") or {}
    if kind == "cardio":
        mins = payload.get("duration_min")
        ctype = payload.get("cardio_type") or ""
        detail = f"{mins}分钟" if mins else ""
        if ctype:
            detail = f"{ctype} {detail}".strip()
        return f"有氧{detail or ''}".strip()
    if kind == "strength":
        sets = payload.get("sets") or []
        return f"力量 {len(sets)}组"
    return str(kind)


def build_user_day_blob(
    date: str,
    meals: list[dict[str, Any]],
    water: dict[str, Any] | None,
    workouts: list[dict[str, Any]],
    done: dict[str, bool],
) -> str:
    """Single-day blob for one user."""
    water = water or {}
    total_ml = water.get("total_ml", 0)
    target_ml = water.get("target_ml", 2000)
    meal_part = "；".join(_meal_line(m) for m in meals) if meals else "无记录"
    wo_part = "；".join(_workout_line(w) for w in workouts) if workouts else "无"
    meal_ok = done.get("meal", False)
    water_ok = done.get("water", False)
    workout_ok = done.get("workout", False)
    flags = (
        f"饮食={'完成' if meal_ok else '未完成'}，"
        f"饮水={'完成' if water_ok else '未完成'}，"
        f"运动={'完成' if workout_ok else '未完成'}"
    )
    return (
        f"【{date}】\n"
        f"饮食：{meal_part}\n"
        f"饮水：{total_ml}/{target_ml} ml\n"
        f"运动：{wo_part}\n"
        f"打卡：{flags}（workout={workout_ok}）"
    )


def build_user_range_summary(days: list[dict[str, Any]]) -> str:
    """Concatenate day snapshots (each dict has date, meals, water, workouts, done)."""
    if not days:
        return "（近几日无记录）"
    blobs = [
        build_user_day_blob(
            d["date"],
            d.get("meals") or [],
            d.get("water"),
            d.get("workouts") or [],
            d.get("done") or {},
        )
        for d in days
    ]
    return "\n\n".join(blobs)
