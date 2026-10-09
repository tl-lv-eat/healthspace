#!/usr/bin/env python3
"""Rebuild exercises_seed.json from ExerciseGymGifsDB with verified GIF URLs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "data" / "exercises_seed.json"
BASE = "https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@v1.1.0"

# (slug, name_zh, body_part_for_app, instructions_zh)
# body_part_for_app: anatomical OR bodyweight/kettlebell browsing buckets
CURATED: list[tuple[str, str, str, str]] = [
    # chest / back / shoulders / legs / arms / core (gym)
    ("barbell-bench-press", "杠铃卧推", "chest", "肩胛收紧，杠铃触胸后推起。"),
    ("dumbbell-bench-press", "哑铃卧推", "chest", "哑铃下放至胸侧，推起时勿碰撞。"),
    ("dumbbell-fly", "哑铃飞鸟", "chest", "肘微屈，弧形合拢，感受胸肌拉伸。"),
    ("cable-cross-over-variation", "绳索夹胸", "chest", "身体略前倾，双手在胸前交汇。"),
    ("archer-push-up", "弓箭手俯卧撑", "chest", "重心偏向一侧，对侧手臂伸直。"),
    ("pull-up", "引体向上", "back", "宽握上拉至下巴过杠，控制下放。"),
    ("chin-up", "反手引体", "back", "窄握反握，侧重背阔与肱二头。"),
    ("cable-lat-pulldown-full-range-of-motion", "高位下拉", "back", "挺胸沉肩，将横杠拉至锁骨附近。"),
    ("barbell-bent-over-row", "杠铃俯身划船", "back", "髋铰链俯身，将杠铃拉向腹部。"),
    ("dumbbell-one-arm-bent-over-row", "单臂哑铃划船", "back", "一手扶凳，将哑铃拉向髋部。"),
    ("cable-seated-row", "坐姿划船", "back", "坐直后拉，肩胛后缩夹紧。"),
    ("dumbbell-seated-shoulder-press", "哑铃肩推", "shoulders", "坐姿哑铃推至手臂接近伸直，勿耸肩。"),
    ("dumbbell-standing-overhead-press", "站姿哑铃推举", "shoulders", "核心收紧，哑铃从头侧推起。"),
    ("dumbbell-lateral-raise", "哑铃侧平举", "shoulders", "肘微屈，抬至肩高，缓慢下放。"),
    ("band-reverse-fly", "弹力带反向飞鸟", "shoulders", "俯身或站姿，向后打开双臂。"),
    ("barbell-full-squat", "杠铃深蹲", "legs", "杠铃置于斜方肌，蹲至大腿至少平行。"),
    ("barbell-front-squat", "杠铃前蹲", "legs", "杠铃架于前肩，躯干更直立。"),
    ("sled-45-leg-press", "腿举", "legs", "脚位适中，膝与脚尖方向一致。"),
    ("dumbbell-lunge", "哑铃弓步", "legs", "步幅适中，后膝接近触地。"),
    ("barbell-deadlift", "杠铃硬拉", "legs", "髋铰链起杠，背中立，杠贴近小腿。"),
    ("barbell-romanian-deadlift", "罗马尼亚硬拉", "legs", "膝微屈，髋向后推，感受腘绳肌拉伸。"),
    ("barbell-glute-bridge", "杠铃臀桥", "legs", "上背靠凳或仰卧，顶髋至身体成直线。"),
    ("barbell-curl", "杠铃弯举", "arms", "肘贴身体，弯举至肩前，控制下放。"),
    ("dumbbell-hammer-curl", "锤式弯举", "arms", "中性握距，侧重肱肌与前臂。"),
    ("cable-pushdown", "绳索下压", "arms", "大臂固定，将绳索压至完全伸直。"),
    ("crunch-floor", "卷腹", "core", "下背贴地，上背离地，勿拉颈。"),
    ("hanging-leg-raise", "悬垂举腿", "core", "悬挂抬腿至水平或更高，避免摆动。"),
    ("power-point-plank", "平板支撑", "core", "肘在肩下，身体成一直线，收紧核心。"),
    # bodyweight bucket
    ("push-up", "标准俯卧撑", "bodyweight", "身体成直线，胸部接近地面后推起。"),
    ("wide-hand-push-up", "宽距俯卧撑", "bodyweight", "双手略宽于肩，更侧重胸部。"),
    ("diamond-push-up", "钻石俯卧撑", "bodyweight", "双手呈菱形，侧重肱三头。"),
    ("kneeling-push-up-male", "跪姿俯卧撑", "bodyweight", "膝盖着地降低难度，保持核心。"),
    ("decline-push-up", "下斜俯卧撑", "bodyweight", "脚垫高，难度上升。"),
    ("burpee", "波比跳", "bodyweight", "深蹲撑地、后踢、俯卧撑、跳起连贯完成。"),
    ("mountain-climber", "登山跑", "bodyweight", "高平板姿势，交替快速收膝。"),
    ("jump-squat", "跳蹲", "bodyweight", "蹲下后爆发跳起，落地缓冲。"),
    ("forward-lunge-male", "弓步蹲", "bodyweight", "向前迈步下蹲，后膝接近触地。"),
    ("walking-lunge", "行走弓步", "bodyweight", "连续向前弓步，保持躯干稳定。"),
    ("low-glute-bridge-on-floor", "臀桥", "bodyweight", "仰卧顶髋，顶峰夹紧臀部。"),
    ("inchworm", "毛毛虫爬", "bodyweight", "站立俯身手撑地爬出成平板再走回。"),
    ("bear-crawl", "熊爬", "bodyweight", "四肢着地，膝离地交替爬行。"),
    ("chest-dip", "双杠臂屈伸", "bodyweight", "双杠支撑下降再推起，肘略外展。"),
    ("assisted-pull-up", "辅助引体", "bodyweight", "弹力带或器械辅助完成引体。"),
    ("3-4-sit-up", "仰卧起坐", "bodyweight", "仰卧屈膝起身，控制下放。"),
    ("cross-body-crunch", "交叉卷腹", "bodyweight", "对侧肘膝靠近，锻炼斜腹。"),
    # kettlebell bucket
    ("kettlebell-swing", "壶铃摆动", "kettlebell", "髋铰链发力，壶铃摆至胸肩高度。"),
    ("kettlebell-goblet-squat", "壶铃高脚杯深蹲", "kettlebell", "双手持壶铃于胸前深蹲。"),
    ("kettlebell-front-squat", "壶铃前蹲", "kettlebell", "壶铃架于肩前完成深蹲。"),
    ("kettlebell-turkish-get-up-squat-style", "壶铃土耳其起立", "kettlebell", "单手持壶铃按步骤从躺到站。"),
    ("kettlebell-one-arm-snatch", "壶铃单臂抓举", "kettlebell", "单手从摆动翻至头顶锁定。"),
    ("kettlebell-one-arm-clean-and-jerk", "壶铃单臂挺举", "kettlebell", "翻站后借力推至头顶。"),
    ("kettlebell-thruster", "壶铃推举深蹲", "kettlebell", "深蹲接推举，连贯发力。"),
    ("kettlebell-one-arm-row", "壶铃单臂划船", "kettlebell", "俯身单臂将壶铃拉向髋部。"),
    ("kettlebell-alternating-row", "壶铃交替划船", "kettlebell", "俯身交替两侧划船。"),
    ("kettlebell-sumo-high-pull", "壶铃相扑高拉", "kettlebell", "宽站距拉起壶铃至胸高。"),
    ("kettlebell-windmill", "壶铃风车", "kettlebell", "一手举壶铃，俯身触地侧链拉伸。"),
    ("kettlebell-one-arm-floor-press", "壶铃地板卧推", "kettlebell", "仰卧于地，单臂推起壶铃。"),
]


def fetch_exercises() -> dict[str, dict]:
    url = f"{BASE}/api/en/exercises.json"
    with urllib.request.urlopen(url, timeout=90) as resp:
        data = json.load(resp)
    return {e["slug"]: e for e in data["exercises"]}


def gif_ok(muscle: str, slug: str) -> bool:
    url = f"{BASE}/{muscle}/{slug}.gif"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=12) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return False


def main() -> None:
    catalog = fetch_exercises()
    rows: list[dict] = []
    missing: list[str] = []
    broken: list[str] = []
    for slug, name_zh, body_part, instructions_zh in CURATED:
        api = catalog.get(slug)
        if api is None:
            missing.append(slug)
            continue
        muscle = str(api["muscle"])
        if not gif_ok(muscle, slug):
            broken.append(slug)
            continue
        rows.append(
            {
                "slug": slug,
                "name_zh": name_zh,
                "name_en": str(api.get("name") or slug),
                "body_part": body_part,
                "muscle": muscle,
                "instructions_zh": instructions_zh,
            }
        )
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} exercises -> {OUT}")
    if missing:
        print("MISSING slugs:", ", ".join(missing))
    if broken:
        print("BROKEN gif:", ", ".join(broken))
    parts: dict[str, int] = {}
    for r in rows:
        parts[r["body_part"]] = parts.get(r["body_part"], 0) + 1
    print("by body_part:", parts)


if __name__ == "__main__":
    main()
