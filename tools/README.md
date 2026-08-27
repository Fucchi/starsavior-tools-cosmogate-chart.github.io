# キャラクターデータ管理ツール

`data/characters.js`（味方キャラのステータス・スキルデータ）は、直接編集する代わりに
CSV（Excel／Googleスプレッドシートで開けます）から自動生成するようにしました。

## ファイル構成

- `data/characters_stats.csv` — キャラクター単位の**ステータスのみ**
  - `id, name, speed, toughnessMax, evasionRatePct, attribute, role, order`
  - `order` は `ALLY_PRESET_LIST`（属性ごとのプリセット表示順）に使う並び順の数値です
- `data/characters_skills.csv` — **スキル・パッシブの説明**（1キャラにつき `passive` / `basic` / `special` / `ultimate` の4行）
  - `id, skill_type, name, note, ct, toughness, burst_add, burst_gain, extra_turn, trigger_type, trigger_ct_mode, self_gauge_gain, burst_gauge_gain_add, requires_evade, targets_ally, gauge_to_target, atk_pct, extra_effects_json`
  - `skill_type` は `passive` / `basic` / `special` / `ultimate` のいずれか
  - `name` = スキル名（`passive` 行では空欄でOK）
  - `note` = パッシブの説明文（`passive` 行のみ使用。他のスキルでは空欄）
  - `toughness` = 強靭削り（非バースト時）
  - `burst_add` = バースト強化時に追加される強靭削り
  - `burst_gain` = このスキルで得られるバーストポイント(BP)量
  - `extra_effects_json` = バフ・デバフ・特殊トリガー・パッシブ実装フラグ等、上記に収まらない効果をJSONでまとめたもの（無ければ空欄でOK）

## 新規キャラクターを追加する

1. **`characters_stats.csv`** に1行追加する

   | id | name | speed | toughnessMax | evasionRatePct | attribute | role | order |
   |---|---|---|---|---|---|---|---|
   | `new_char` | 新キャラ名 | 180 | 3 | 0 | 太陽 | ストライカー | 999 |

   - `id` は他と被らない半角英数字（例: `new_char`）。以降このIDでskillsシートと紐付けます
   - `speed`/`toughnessMax`/`evasionRatePct` は多くのキャラで `180`/`3`/`0` が標準値です
   - `attribute`（太陽/星/月/秩序/混沌）と `role` は既存キャラの表記に合わせてください
   - `order` はプリセット選択欄での表示順。同じ属性の中でどこに並べたいか目安の数値を入れる（とりあえず大きい値=末尾でOK、後で調整可）

2. **`characters_skills.csv`** に4行追加する（同じ `id` で `passive`/`basic`/`special`/`ultimate`）

   ```
   new_char,passive,,このキャラのパッシブ説明文をここに,,,,,,,,,,,,,,
   new_char,basic,基本スキル名,,0,0,1,0,FALSE,none,hasCT,0,0,FALSE,FALSE,FALSE,,
   new_char,special,特殊スキル名,,3,0,1,1,FALSE,none,hasCT,0,0,FALSE,FALSE,FALSE,,
   new_char,ultimate,究極スキル名,,4,0,1,1,FALSE,none,hasCT,0,0,FALSE,FALSE,FALSE,,
   ```

   - `ct` はスキルのクールタイム、`toughness`/`burst_add`/`burst_gain` は前述の通り。まずは実測値を入れる
   - バフ・デバフなど複雑な効果を再現したい場合のみ `extra_effects_json` に書く（例: `{"selfStackGain":1}` や `{"selfBuff":{"name":"攻撃力アップ（+30%）","turns":2}}`）。分からなければ空欄のまま追加し、あとで既存の似た効果を持つキャラの行をコピーして調整するのが簡単です
   - `trigger_type`/`trigger_ct_mode` は特殊なトリガースキルでなければ `none`/`hasCT` のままでOK

3. リポジトリのルート（`starsavior-tools-cosmogate-chart.github.io/`）で再生成
   ```bash
   python tools/build_characters.py
   ```
4. `index.html` をブラウザで開き、プリセット選択欄に新キャラが出るか・スキル内容が正しいか確認

**ポイント**: 迷ったら `characters_stats.csv` / `characters_skills.csv` 内の `custom`（新規味方の空テンプレート行）や、近い性能の既存キャラの行をコピーして書き換えるのが一番早いです。

## 既存キャラを編集する場合

該当する行を直接編集して `python tools/build_characters.py` を実行するだけです。CSVを保存する際は文字コード UTF-8（BOM付き）のまま保存してください（Excelの「CSV UTF-8」形式でOK）。

## 既存データからCSVを作り直したい場合

`data/characters.js` を手で直接直してしまった場合など、CSV側を最新化したいときは:
```bash
python tools/extract_characters.py
```
（`data/characters.js` を読み込んで2つのCSVを上書き生成します）

## 検証

CSV編集後に再生成した `characters.js` が元の内容と意味的に一致しているか確認したい場合:
```bash
python tools/verify_roundtrip.py <比較元.js> data/characters.js
```
