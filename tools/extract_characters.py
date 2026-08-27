"""Extract data/characters.js into two editable CSV files:
  data/characters_stats.csv  -- per-character base stats
  data/characters_skills.csv -- per-character-per-skill (basic/special/ultimate) data

Run:  python tools/extract_characters.py
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from js_lit import parse, Call

ROOT = Path(__file__).parent.parent
SRC = ROOT / "data" / "characters.js"
STATS_CSV = ROOT / "data" / "characters_stats.csv"
SKILLS_CSV = ROOT / "data" / "characters_skills.csv"

STAT_COLUMNS = ["id", "name", "speed", "toughnessMax", "evasionRatePct", "attribute", "role", "order"]
SKILL_COLUMNS = [
    "id", "skill_type", "name", "note", "ct", "toughness", "burst_add", "burst_gain",
    "extra_turn", "trigger_type", "trigger_ct_mode",
    "self_gauge_gain", "burst_gauge_gain_add",
    "requires_evade", "targets_ally", "gauge_to_target",
    "atk_pct", "extra_effects_json",
]

SKILL_ARG_NAMES = [
    "name", "ct", "toughness", "burst_add", "burst_gain", "extra_turn",
    "trigger_type", "trigger_ct_mode", "self_gauge_gain", "burst_gauge_gain_add",
    "requires_evade", "targets_ally", "gauge_to_target", "extra_effects",
]


def load_block(text, const_name):
    m = re.search(rf"const\s+{const_name}\s*=\s*", text)
    if not m:
        raise ValueError(f"const {const_name} not found")
    start = m.end()
    # find the matching statement terminator ';' at depth 0
    depth = 0
    i = start
    in_str = None
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in "\"'":
            in_str = c
            i += 1
            continue
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        elif c == ";" and depth == 0:
            break
        i += 1
    return text[start:i]


def bool_str(v):
    return "TRUE" if v else "FALSE"


def main():
    text = SRC.read_text(encoding="utf-8")
    presets_src = load_block(text, "ALLY_CHARACTER_PRESETS")
    presets = parse(presets_src)

    list_src = load_block(text, "ALLY_PRESET_LIST")
    preset_list = parse(list_src)
    order_index = {pair[0]: idx for idx, pair in enumerate(preset_list)}

    stat_rows = []
    skill_rows = []

    for char_id, obj in presets.items():
        obj = dict(obj)  # copy
        skills = {}
        for st in ("basic", "special", "ultimate"):
            if st in obj:
                skills[st] = obj.pop(st)

        passive_note = obj.pop("passiveNote", "")
        row = {
            "id": char_id,
            "name": obj.pop("name", ""),
            "speed": obj.pop("speed", ""),
            "toughnessMax": obj.pop("toughnessMax", ""),
            "evasionRatePct": obj.pop("evasionRatePct", ""),
            "attribute": obj.pop("attribute", ""),
            "role": obj.pop("role", ""),
            "order": order_index.get(char_id, ""),
        }
        stat_rows.append(row)

        # anything left over (hasPincerAttack, relics, battleStart*, etc.) is
        # passive-implementation data, not a base stat -- goes into the skills
        # sheet as a synthetic "passive" row alongside basic/special/ultimate.
        if passive_note or obj:
            skill_rows.append({
                "id": char_id,
                "skill_type": "passive",
                "name": "",
                "note": passive_note,
                "ct": "", "toughness": "", "burst_add": "", "burst_gain": "",
                "extra_turn": "", "trigger_type": "", "trigger_ct_mode": "",
                "self_gauge_gain": "", "burst_gauge_gain_add": "",
                "requires_evade": "", "targets_ally": "", "gauge_to_target": "",
                "atk_pct": "",
                "extra_effects_json": json.dumps(obj, ensure_ascii=False) if obj else "",
            })

        for st in ("basic", "special", "ultimate"):
            call = skills.get(st)
            if call is None:
                continue
            assert isinstance(call, Call) and call.name == "defaultAllySkill", (char_id, st, call)
            args = call.args + [None] * (len(SKILL_ARG_NAMES) - len(call.args))
            vals = dict(zip(SKILL_ARG_NAMES, args))
            extra = vals.get("extra_effects") or {}
            atk_pct = extra.pop("atkPct", "") if isinstance(extra, dict) else ""
            skill_rows.append({
                "id": char_id,
                "skill_type": st,
                "name": vals.get("name") or "",
                "ct": vals.get("ct") if vals.get("ct") is not None else 0,
                "toughness": vals.get("toughness") if vals.get("toughness") is not None else 0,
                "burst_add": vals.get("burst_add") if vals.get("burst_add") is not None else 0,
                "burst_gain": vals.get("burst_gain") if vals.get("burst_gain") is not None else 0,
                "extra_turn": bool_str(vals.get("extra_turn")),
                "trigger_type": vals.get("trigger_type") or "none",
                "trigger_ct_mode": vals.get("trigger_ct_mode") or "hasCT",
                "self_gauge_gain": vals.get("self_gauge_gain") if vals.get("self_gauge_gain") is not None else 0,
                "burst_gauge_gain_add": vals.get("burst_gauge_gain_add") if vals.get("burst_gauge_gain_add") is not None else 0,
                "requires_evade": bool_str(vals.get("requires_evade")),
                "targets_ally": bool_str(vals.get("targets_ally")),
                "gauge_to_target": bool_str(vals.get("gauge_to_target")),
                "atk_pct": atk_pct,
                "extra_effects_json": json.dumps(extra, ensure_ascii=False) if extra else "",
            })

    with open(STATS_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=STAT_COLUMNS)
        w.writeheader()
        w.writerows(stat_rows)

    with open(SKILLS_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SKILL_COLUMNS)
        w.writeheader()
        w.writerows(skill_rows)

    print(f"Wrote {len(stat_rows)} characters to {STATS_CSV}")
    print(f"Wrote {len(skill_rows)} skills to {SKILLS_CSV}")


if __name__ == "__main__":
    main()
