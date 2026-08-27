import csv, json, sys
from collections import defaultdict
from pathlib import Path

if len(sys.argv) > 1:
    sys.stdout = open(sys.argv[1], "w", encoding="utf-8")

ROOT = Path(__file__).parent.parent

with open(ROOT / 'data' / 'characters_stats.csv', encoding='utf-8-sig') as f:
    names = {r['id']: r['name'] for r in csv.DictReader(f)}

by_type = defaultdict(list)
relic_flags = defaultdict(list)

with open(ROOT / 'data' / 'characters_skills.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        cid = row['id']
        name = names.get(cid, cid)
        if row['skill_type'] == 'passive':
            extra = json.loads(row['extra_effects_json']) if row['extra_effects_json'] else {}
            if extra.get('hasPincerAttack'):
                relic_flags['挟撃(hasPincerAttack)'].append(name)
            if extra.get('hasWaterBombReactAttack'):
                relic_flags['水爆弾リアクト(hasWaterBombReactAttack)'].append(name)
            if extra.get('relics'):
                for k in extra['relics']:
                    relic_flags[f'専用遺物:{k}'].append(name)
            continue
        tt = row['trigger_type']
        if tt and tt != 'none':
            extra = json.loads(row['extra_effects_json']) if row['extra_effects_json'] else {}
            flags = [k for k in extra if k.startswith('trigger') or k in ('consumeStackOnlyIfMax', 'firesAfterAnyOwnAttack')]
            if row['requires_evade'].upper() == 'TRUE':
                flags.append('requiresEvade')
            by_type[tt].append(f"{name} - {row['skill_type']}「{row['name']}」 [{', '.join(flags) if flags else '追加条件なし'}]")

for tt in sorted(by_type):
    print(f"\n=== trigger_type: {tt} ({len(by_type[tt])}件) ===")
    for line in by_type[tt]:
        print(" -", line)

print("\n=== 遺物・特殊フラグ系（trigger_typeとは別枠のトリガー） ===")
for k in sorted(relic_flags):
    print(f" - {k}: {', '.join(relic_flags[k])}")
