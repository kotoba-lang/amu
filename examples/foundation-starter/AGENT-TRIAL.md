# AI Agent に渡す Kotoba / Amu 独立試用・報告ガイド

下の指示を、試用者自身の AI Agent にそのまま渡せます。公開 issue / PR を作成する指示も含むため、試用者本人が内容を確認して渡してください。開発者側の CI・管理 VM と、独立試用者による結果は分けて集計します。開発者本人が起動した Agent の結果を外部ユーザーの人数に加えないでください。

---

Kotoba / Amu の初回実行を私の環境で確認し、結果を GitHub issue に報告してください。修正が必要で、小さく安全に直せる場合は PR まで作成してください。既存の作業・設定・認証情報は保護し、この依頼のために新しいアカウントを作ったり、有料リソースを契約したりしないでください。

## 目的と今回の範囲

新しい作業ディレクトリで、固定された公開ソース・compiler を取得し、digest 照合 → check → compile → run → 一行変更 → 再実行 → fuel / capability の拒否まで再現します。成功だけでなく、途中で止まった結果も有用です。独立試用の結果を得る前の engineering preview です。成功しても公開資格・正式対応・完全な安全性・相対性能を認定したとは書かないでください。

対象は native Linux x86_64。Linux ARM64（aarch64）は別枠の診断 preview で、正式対応済みとは扱いません。macOS / Windows は今回の対象外です。2つの異なる host profile の報告を集める計画ですが、一人で両方を用意する必要はありません。

## 1. 環境と作業場所を確認する

1. この環境に適用される AGENTS.md とユーザーの作業場所ルールを確認し、既存 WIP と分離した専用 task workspace を作ってください。以下の `TASK_WORKSPACE` はその絶対パスです。既存ディレクトリを削除・初期化しないでください。
2. `uname -s`、`uname -m`、`uname -r`、OS のバージョン、`git --version`、`python3 --version` を確認します。hostname / IP / 個人情報は報告不要です。
3. native / VM / container / emulation の区分を記録してください。不明なら unknown とします。VM / container / emulation の成功を native host の資格に読み替えません。
4. 対象 OS / CPU が合わない、前提が足りない、または環境の判定ができない場合は、勝手に VM や別 compiler を導入せず、その段階を報告してください。sudo、Homebrew、Node、JVM、NBB、C compiler / loader を追加して通さないでください。

## 2. 固定版を取得する

今回の実行対象は次の immutable snapshot です。ブランチ名や latest に差し替えないでください。

- Repository: https://github.com/kotoba-lang/amu
- Commit: `9af40f954bbbe92ad4a056590c05b2d345fe0538`
- x86 compiler SHA-256: `d545032000f25e30fd1990ca454f81ac469921e90d8dbac9e38680606174b242`
- ARM diagnostic compiler SHA-256: `9053ed1f8056635bc3ea08768dbb106deee02cbeb48a0d626fdbff80ca798493`
- 48-module source unity SHA-256: `6738e95294d854ab8dc8c1c098d649ad14ebfa662d20e3ac37dacc8953958e0e`

Git と Python 3 が既に利用できる対応 Linux で、専用 workspace 内から実行します。

```sh
set -e
cd "$TASK_WORKSPACE"
REVIEWED_REVISION=9af40f954bbbe92ad4a056590c05b2d345fe0538
GIT_TERMINAL_PROMPT=0 git -c credential.helper= clone --filter=blob:none --depth 1 --no-checkout https://github.com/kotoba-lang/amu.git amu-trial
cd amu-trial
GIT_TERMINAL_PROMPT=0 git -c credential.helper= fetch --filter=blob:none --depth 1 origin "$REVIEWED_REVISION"
test "$(git rev-parse FETCH_HEAD)" = "$REVIEWED_REVISION"
git sparse-checkout set --cone bin seed scripts examples
git checkout --detach "$REVIEWED_REVISION"
test "$(git rev-parse HEAD)" = "$REVIEWED_REVISION"
```

失敗時は止めてください。取得物や compiler を黙って別の版に置き換えないでください。partial clone は不足ファイルの追加取得が必要になる場合があります。

## 3. 実行前に bytes を照合する

checkout root で次を実行します。この検査は compiler を起動しません。

```sh
python3 - <<'PY_VERIFY'
import hashlib, json
from pathlib import Path

def pin(path):
    b = Path(path).read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

c = json.loads(Path('examples/foundation-starter/candidate.json').read_text())
p = json.loads(Path('native-product.json').read_text())
a = json.loads(Path('seed/bootstrap/aarch64-linux-static-root.json').read_text())
assert pin('bin/amu') == c['compilerImage'] == p['image']
assert p['image']['sha256'] == 'd545032000f25e30fd1990ca454f81ac469921e90d8dbac9e38680606174b242'
assert pin('seed/bootstrap/aarch64-linux-static-root.elf') == a['image']
assert a['image']['sha256'] == '9053ed1f8056635bc3ea08768dbb106deee02cbeb48a0d626fdbff80ca798493'
for name, expected in c['fixtures'].items():
    assert pin('examples/foundation-starter/' + name) == expected, name
paths = [line for line in Path(p['sourceManifest']).read_text().splitlines()
         if line and not line.startswith('#')]
assert len(paths) == len(set(paths)) == 48
unity = b''.join(Path(name).read_bytes() + b'\n' for name in paths)
actual = {'bytes': len(unity), 'sha256': hashlib.sha256(unity).hexdigest()}
assert actual == c['compilerSourceUnity'] == p['sourceUnity'] == a['sourceUnity']
assert actual['sha256'] == '6738e95294d854ab8dc8c1c098d649ad14ebfa662d20e3ac37dacc8953958e0e'
print('PASS_TRIAL_BYTES')
PY_VERIFY
```

不一致なら実行を止め、その段階を報告します。hash 一致だけで build provenance や host 資格まで証明したとは書かないでください。

## 4. 初回実行と拒否例を確認する

`TRIAL_OUTPUT` は checkout の外にある、まだ存在しない絶対パスにしてください。出力がある場所を消して使い回さないでください。`HOST_PROFILE` は例のような英小文字・数字・ハイフンだけのラベルです。実際の OS に合わせ、個人名や端末名を入れないでください。

Linux x86_64 の例:

```sh
TRIAL_OUTPUT="$TASK_WORKSPACE/trial-result-x86"
HOST_PROFILE=linux-x86-64-ubuntu-24-04
python3 scripts/seed/check-foundation-starter.py --output "$TRIAL_OUTPUT" --host-profile "$HOST_PROFILE"
```

Linux ARM64 の診断例:

```sh
TRIAL_OUTPUT="$TASK_WORKSPACE/trial-result-arm"
HOST_PROFILE=linux-arm64-ubuntu-24-04
python3 scripts/seed/check-foundation-starter.py --experimental-arm64 --output "$TRIAL_OUTPUT" --host-profile "$HOST_PROFILE"
```

両方を同じ機械で無理に実行しないでください。observer は compiler の代わりではなく、固定サンプルの staging、hash、実 native process とログを観測するものです。

20操作で次を確認します。

- hello の check / compile / run が成功し、結果42。
- 一行変更した別 artifact の結果43。変更前後の artifact bytes が異なる。
- sum の結果55、上限を20に変えた sum の結果210。
- 同じ sum artifact を fuel=1 で実行すると exit120、`:budget/fuel`。
- hash の権限なし実行は exit120、wire3 `:not-granted`。
- 同じ hash artifact に local SHA-256 の wire3 だけを許可すると結果64。
- 間違った lock digest、未対応の locked-static combination、target 未指定を拒否し、拒否時に成果物を残さない。

完了表示は `PASS_STARTER_FUNCTIONAL_SMOKE` です。出力の `starter-observation.json`、生成物、raw logs をローカルに保存してください。この版の static ELF compile は atomic source lock を提供しません。check の source lock と compile を同一の保証に読み替えたり、未採用の修正 PR を勝手に混ぜたりしないでください。

## 5. 実測と失敗を区別する

開始時刻、完了または停止時刻、待機を含む所要時間を記録します。所要時間は初回導入の記録であり、compiler 性能比較ではありません。

失敗時は止まった手順、command の種類、exit / diagnostic、期待結果と実際の結果を残します。自分の入力ミス・環境差・手順の不備・compiler の不具合は、根拠がある範囲で分け、不明なら unknown とします。元の固定版の結果を残してから修正候補を別の checkout / worktree で試してください。

## 6. GitHub issue に報告する

GitHub の既存接続を使い、まず https://github.com/kotoba-lang/amu/issues を検索してください。同じ担当者・同じ host / commit の報告や同じ不具合があれば更新・追記し、重複 issue を増やさないでください。なければ、この依頼の範囲で公開の試用報告 issue を1件作成してください。修正不要の成功報告も対象です。

GitHub 認証や書込み権限がなければ、新しいアカウントや認証を勝手に作らず、投稿できる完成済みの issue 本文を返してください。投稿できなかったことを明記します。

タイトル例: `[Starter trial] Linux x86_64 / Ubuntu 24.04 / 9af40f954`

本文に次を含めます。

```text
対象commit: 9af40f954bbbe92ad4a056590c05b2d345fe0538
OS / version / CPU architecture / kernel:
実行区分: native / VM / container / emulation / unknown
実施者: 試用者のAI Agent
管理上の独立性: 開発者管理外 / 開発者管理下 / unknown
取得・digest照合: PASS / FAIL / NOT RUN
42 → 43: PASS / FAIL / NOT RUN
sum 55 / 210: PASS / FAIL / NOT RUN
fuel拒否: PASS / FAIL / NOT RUN
権限拒否 → SHA許可64: PASS / FAIL / NOT RUN
lock / target拒否: PASS / FAIL / NOT RUN
20操作の最終status:
所要時間:
止まった手順・期待値と実測・最小再現:
分かりにくかった説明:
変更したファイル: なし / 一覧
証拠: 必要部分だけを伏字処理した結果・digest
未検証: 独立した別host、一般公開資格、正式ARM対応、性能、OS/network全体など
```

ログや JSON を丸ごと貼る前に、ユーザー名、ローカル絶対パス、認証情報、個人情報、私有コードを取り除いてください。原本はローカルに残し、公開用のコピーを使います。成功を観測しただけで qualification flags を変更しないでください。

## 7. 修正できる場合は PR まで進める

手順の誤記、小さい観測器の不具合、期待結果が明確な最小回帰テストなど、この再現結果に直接必要な変更だけを扱ってください。compiler / runtime / capability policy / resource limit の変更、公開資格の昇格、release・本番切替はこの依頼に含みません。大きい問題は issue と再現資料までで止めてください。

1. 現 upstream main と対象 issue / open PR を確認し、同じ修正が進んでいれば重複 PR を作らず報告します。元の固定版の測定結果は維持します。
2. 既存 WIP と別の専用 branch / worktree に、必要な差分だけを作ります。upstream のローカル AGENTS.md と attribution / tracking 規則に従ってください。
3. 関連する正例・拒否例または文面の正確性を確認し、`git diff --check` を実行します。失敗を隠す期待値変更、検査の削除、fallback の追加は行いません。
4. GitHub の既存権限を使って commit → push → PR を作成します。upstream に push できない場合は既存 fork を使い、必要ならこの公開ソースの修正用 fork を作成して構いません。認証や公開への本人の制約がある場合は従い、完成済み patch と PR 本文を返してください。force-push、merge、release は行いません。
5. PR 本文に「何が失敗したか → 何を変えたか → 固定版と修正版で何を確認したか → 未検証」を書き、報告 issue を link します。実 CI 結果は pending / pass / fail を区別します。
6. issue に PR URL、修正後の結果、残る制約を追記します。修正不要なら PR を作らず、その理由を書いてください。

## 8. 私への最終報告

issue URL、PR URL（または不要／未作成の理由）、元の固定版での実測、修正版での検証、CI 状態、残件を短くまとめてください。投稿できなかった場合は、その理由とそのまま投稿できる本文も提示してください。外部の人へDM・メールを送ったり、他のチャットへ報告したりする必要はありません。
