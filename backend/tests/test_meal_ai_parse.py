"""Unit tests for meal AI JSON parsing (no live API)."""

from __future__ import annotations

import pytest

from backend.app.services.meal_ai import MealAIError, parse_estimate_json


def test_parse_estimate_json_ok():
    raw = '{"food_summary":"鸡胸肉沙拉","kcal":420,"advice":"蛋白质不错，少酱料"}'
    d = parse_estimate_json(raw)
    assert d["kcal"] == 420
    assert "鸡胸" in d["food_summary"]
    assert d["advice"]


def test_parse_estimate_json_embedded():
    raw = '好的\n{"food_summary":"米饭","kcal":300,"advice":"控量"}\n'
    assert parse_estimate_json(raw)["kcal"] == 300


def test_parse_estimate_json_missing_kcal_raises():
    with pytest.raises(MealAIError):
        parse_estimate_json('{"food_summary":"x","advice":"y"}')


def test_parse_estimate_json_invalid_raises():
    with pytest.raises(MealAIError):
        parse_estimate_json("not json at all")
