"""Compare the semantic content of two characters.js-shaped files (parsed as
JS literals) to confirm a CSV round-trip did not lose or change any data.

Usage: python tools/verify_roundtrip.py <original.js> <rebuilt.js>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_characters import load_block
from js_lit import parse, Call


# defaultAllySkill(name, ct, toughness, burstAdd, burstGain, extraTurn, triggerType,
#   triggerCtMode, selfGaugeGain, burstGaugeGainAdd, requiresEvade, targetsAlly,
#   gaugeToTarget, extraEffects) -- trailing omitted args fall back to these JS defaults
# (mirrors the `x || default` / `!!x` logic in defaultAllySkill's body in index.html).
SKILL_ARG_DEFAULTS = [None, None, None, None, None, False, "none", "hasCT", 0, 0, False, False, False, {}]


def pad_call_args(args):
    padded = list(args) + [None] * (len(SKILL_ARG_DEFAULTS) - len(args))
    return [
        (default if (a is None and default is not None) else a)
        for a, default in zip(padded, SKILL_ARG_DEFAULTS)
    ]


def normalize(v):
    if isinstance(v, Call):
        args = pad_call_args(v.args) if v.name == "defaultAllySkill" else v.args
        return ("__call__", v.name, [normalize(a) for a in args])
    if isinstance(v, dict):
        return {k: normalize(val) for k, val in v.items()}
    if isinstance(v, list):
        return [normalize(x) for x in v]
    if isinstance(v, float) and v == int(v):
        return int(v)
    return v


def diff(a, b, path="root"):
    a, b = normalize(a), normalize(b)
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        keys = set(a) | set(b)
        for k in sorted(keys, key=str):
            if k not in a:
                diffs.append(f"{path}.{k}: missing in ORIGINAL, present in REBUILT = {b[k]!r}")
            elif k not in b:
                diffs.append(f"{path}.{k}: present in ORIGINAL = {a[k]!r}, missing in REBUILT")
            else:
                diffs.extend(diff(a[k], b[k], f"{path}.{k}"))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f"{path}: length differs original={len(a)} rebuilt={len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            diffs.extend(diff(x, y, f"{path}[{i}]"))
    else:
        if a != b:
            diffs.append(f"{path}: original={a!r} rebuilt={b!r}")
    return diffs


def main():
    orig_path, rebuilt_path = sys.argv[1], sys.argv[2]
    orig_text = Path(orig_path).read_text(encoding="utf-8")
    rebuilt_text = Path(rebuilt_path).read_text(encoding="utf-8")

    orig_presets = parse(load_block(orig_text, "ALLY_CHARACTER_PRESETS"))
    rebuilt_presets = parse(load_block(rebuilt_text, "ALLY_CHARACTER_PRESETS"))
    orig_list = parse(load_block(orig_text, "ALLY_PRESET_LIST"))
    rebuilt_list = parse(load_block(rebuilt_text, "ALLY_PRESET_LIST"))

    diffs = diff(orig_presets, rebuilt_presets, "ALLY_CHARACTER_PRESETS")
    diffs += diff(orig_list, rebuilt_list, "ALLY_PRESET_LIST")

    if diffs:
        print(f"FOUND {len(diffs)} DIFFERENCE(S):")
        for d in diffs:
            print(" -", d)
        sys.exit(1)
    else:
        print("OK: rebuilt file is semantically identical to the original.")


if __name__ == "__main__":
    main()
