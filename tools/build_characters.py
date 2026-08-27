"""Rebuild data/characters.js from the editable CSV files:
  data/characters_stats.csv
  data/characters_skills.csv

Run:  python tools/build_characters.py
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from js_lit import Call, write_value

ROOT = Path(__file__).parent.parent
STATS_CSV = ROOT / "data" / "characters_stats.csv"
SKILLS_CSV = ROOT / "data" / "characters_skills.csv"
OUT = ROOT / "data" / "characters.js"

ATTRIBUTE_GROUP_ORDER = ["太陽", "星", "月", "秩序", "混沌"]

HEADER = """// ===================== キャラクターデータ（味方プリセット） =====================
// このファイルは自動生成されます。手編集せず、
//   data/characters_stats.csv  （キャラクターごとのステータス）
//   data/characters_skills.csv （スキル・パッシブごとの強靭削り・BP付与量・効果など）
// を編集した上で `python tools/build_characters.py` を実行して再生成してください。
// defaultAllySkill() の定義後に読み込まれる必要があります。
const ALLY_CHARACTER_PRESETS = {
"""


def to_bool(s):
    return str(s).strip().upper() in ("TRUE", "1", "YES")


def to_number(s, default=0):
    s = (s or "").strip()
    if s == "":
        return default
    if "." in s:
        return float(s)
    return int(s)


def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_skill_call(row):
    extra = {}
    if row.get("extra_effects_json"):
        extra = json.loads(row["extra_effects_json"])
    atk_pct = row.get("atk_pct", "")
    if atk_pct not in (None, ""):
        # keep atkPct first for readability, matching original style loosely
        extra = {"atkPct": to_number(atk_pct), **extra}

    args = [
        row.get("name") or "",
        to_number(row.get("ct")),
        to_number(row.get("toughness")),
        to_number(row.get("burst_add")),
        to_number(row.get("burst_gain")),
        to_bool(row.get("extra_turn")),
        row.get("trigger_type") or "none",
        row.get("trigger_ct_mode") or "hasCT",
        to_number(row.get("self_gauge_gain")),
        to_number(row.get("burst_gauge_gain_add")),
        to_bool(row.get("requires_evade")),
        to_bool(row.get("targets_ally")),
        to_bool(row.get("gauge_to_target")),
        extra,
    ]
    return Call("defaultAllySkill", args)


def main():
    stat_rows = load_rows(STATS_CSV)
    skill_rows = load_rows(SKILLS_CSV)

    skills_by_char = {}
    for row in skill_rows:
        skills_by_char.setdefault(row["id"], {})[row["skill_type"]] = row

    char_ids_in_order = [r["id"] for r in stat_rows]

    lines = [HEADER.rstrip("\n")]
    entry_lines = []
    for row in stat_rows:
        char_id = row["id"]
        obj = {}
        obj["name"] = row.get("name") or ""
        obj["speed"] = to_number(row.get("speed"))
        obj["toughnessMax"] = to_number(row.get("toughnessMax"))
        obj["evasionRatePct"] = to_number(row.get("evasionRatePct"))
        obj["attribute"] = row.get("attribute") or ""
        obj["role"] = row.get("role") or ""

        char_skills = skills_by_char.get(char_id, {})

        passive_row = char_skills.get("passive")
        if passive_row:
            if passive_row.get("extra_effects_json"):
                obj.update(json.loads(passive_row["extra_effects_json"]))
            if passive_row.get("note"):
                obj["passiveNote"] = passive_row["note"]

        for st in ("basic", "special", "ultimate"):
            if st in char_skills:
                obj[st] = build_skill_call(char_skills[st])

        body = ", ".join(f"{k}:{write_value(v)}" for k, v in obj.items())
        entry_lines.append(f'    "{char_id}": {{ {body} }}')

    lines.append(",\n".join(entry_lines))
    lines.append("};\n")

    # ALLY_PRESET_LIST -- grouped by attribute in fixed order, preserving `order` within group
    def sort_key(r):
        try:
            o = float(r.get("order") or 0)
        except ValueError:
            o = 0
        return o

    groups = {}
    for row in stat_rows:
        if row["id"] == "custom":
            continue
        groups.setdefault(row.get("attribute") or "", []).append(row)
    for g in groups.values():
        g.sort(key=sort_key)

    ordered_attrs = [a for a in ATTRIBUTE_GROUP_ORDER if a in groups]
    ordered_attrs += [a for a in groups if a not in ATTRIBUTE_GROUP_ORDER]

    lines.append("// バッジ表示順（属性ごとにグルーピング）")
    lines.append("const ALLY_PRESET_LIST = [")
    for attr in ordered_attrs:
        lines.append(f"  // {attr}")
        entries = ", ".join(f'["{r["id"]}","{r["name"]}"]' for r in groups[attr])
        lines.append(f"  {entries},")
    lines.append("];")

    out_text = "\n".join(lines) + "\n"
    OUT.write_text(out_text, encoding="utf-8")
    print(f"Wrote {OUT} ({len(char_ids_in_order)} characters)")


if __name__ == "__main__":
    main()
