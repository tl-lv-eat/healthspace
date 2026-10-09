import pytest

from backend.app.services.meal_ai import MealAIError, format_advice_for_storage, parse_estimate_json


def test_parse_estimate_json_ok():
    raw = (
        '{"food_summary":"鸡胸肉沙拉","kcal":420,'
        '"reason":"鸡胸约150g按165kcal/100g，配菜与轻酱合计约170",'
        '"advice":"蛋白质不错；酱料可减半，配一拳主食会更稳"}'
    )
    d = parse_estimate_json(raw)
    assert d["kcal"] == 420
    assert "鸡胸" in d["food_summary"]
    assert "150g" in d["reason"] or "酱" in d["reason"]
    assert "酱" in d["advice"] or "蛋白" in d["advice"]


def test_parse_estimate_json_embedded():
    raw = '好的\n{"food_summary":"米饭","kcal":300,"reason":"一碗白米","advice":"控量"}\n'
    assert parse_estimate_json(raw)["kcal"] == 300
    assert parse_estimate_json(raw)["reason"]


def test_parse_estimate_json_missing_reason_defaults():
    raw = '{"food_summary":"面","kcal":500,"advice":"少油"}'
    d = parse_estimate_json(raw)
    assert d["reason"]


def test_parse_estimate_json_missing_kcal_raises():
    with pytest.raises(MealAIError):
        parse_estimate_json('{"food_summary":"x","advice":"y"}')


def test_parse_estimate_json_invalid_raises():
    with pytest.raises(MealAIError):
        parse_estimate_json("not json at all")


def test_format_advice_for_storage():
    text = format_advice_for_storage("依据A", "建议B")
    assert "估卡依据" in text
    assert "依据A" in text
    assert "建议B" in text
