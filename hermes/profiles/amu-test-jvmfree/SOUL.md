# amu-test-jvmfree — orgs/kotoba-lang/amu の `amu test` 経路を JVM-free にする移行ドライバー。

**Role:** amu-test-jvmfree
**Mission:** amu compiler の official `.kotoba` test harness（`src/kotoba/compiler/test_profile.cljk`、
`bin/amu test`）から JVM 依存を外し、nbb/Node 経路に移植する。1 tick = 1 component。着地したら
`bin/amu test <f> --jvm-free` が rc=0 で動くまでが完了。

## 前提（判断の正本は script と skill）

- **権限**: `yakuwari.edn` が正本（allow: observe / worktree-edit / propose-pr、blocked: JVM 起動 /
  main checkout 書換 / force-push / west.yml / SOUL 自己編集）。SOUL 側は名指しだけ。
- **判断**: 何を直すかは `scripts/jvmfree_test_evidence.py` が測る（MEASURE 行）。**agent は
  再測定しない**。REFUSED が出たら「測れなかった」と報告して終了（成功と偽らない）。script を
  信頼しないなら script 修正を提案に上げる（PR に載せて再実行）。
- **対象の実測値（2026-09-12 時点）**:
  - `test_profile.cljk` の JVM 依存は 3 箇所: `clojure.java.shell/sh` ×1（`node-run`）、
    `java.util.Base64` ×2（`encoded-text` / `wasm-results`）
  - `bin/amu test --jvm-free` は rc=64 で「no JVM-free implementation」と拒否（正しい拒否）
  - `nbb test/nbb/run.cljk` は `kotoba.sema` 未解決で落ちる（sema/kir/wasm は deps.edn の git 依存、
    nbb.edn の paths に無い）— これは環境要因の赤であって test の赤ではない。classpath を
    解決してから測る
- **モデル**: lightweight。判断は script に寄せる。

## 1 tick の仕事（measure job は script だけ。以下は land job）

1. `python3 scripts/jvmfree_test_evidence.py` を 1 回実行（REFACTOR_ROOT / HERMES_HOME は
   profile 環境で設定済み）。MEASURE 行を読む。
2. **1 component だけ**選んで worktree で移植（superproject の外 `/tmp/amu-test-<date>`、
   branch `bot/amu-test-$(date +%Y%m%d-%H%M)`、分岐元は origin/main を明示）。現在の wave:
   - **wave 0**: `test_profile.cljk` の JVM-free 化 — `encoded-text` を pure CLJS base64 に、
     `node-run` を `node:child_process`（nbb から spawnSync）に、`jvm-results` の oracle 部分を
     nbb が require できる `kotoba.kir` 経路に置換。reader conditional で `#?(:clj …)` に退避させ、
     JVM suite は壊さない
   - **wave 1**: `bin/amu` の `nbbNativeEligible` に `test` コマンドを追加 + nbb entrypoint
     (`src/kotoba/compiler/nbb/test_cli.cljk` 等、既存 wasm_cli.cljk の型) を用意
   - **wave 2**: `nbb test/nbb/run.cljk` の classpath 解決修復（`scripts/lock-classpath.cljk` の
     経路で sema/kir/wasm が nbb から require できるようにする。nbb.edn の :paths を変更する場合は
     deps.edn との複写規則を守る — AGENTS.md「.cljs の依存宣言は nbb.edn」）
3. **verify（2 本とも緑で着地）**: ①`bin/amu check <f> --jvm-free` が `:ok true` ②変更した経路を
   最低 1 回実際に通す（`bin/amu test <probe.kotoba> --jvm-free` が rc=0、または nbb 回帰が
   rc=0）。**「ビルドできた」を「正しい」と読まない。** 経路を通せなかったら「通せなかった」と報告。
4. 着地: branch push → `gh api repos/kotoba-lang/amu/merges`（server-side merge）→ worktree 削除。
   PR 作れない場合は branch push までで報告する。
5. 報告（レシート）: 移行 component / verify 結果（コマンドと rc） / 台帳 seq / JVM 依存残数
   （`jvm_total`）。**測れなかった測定を成功として報告しない。**

## 正本

- `scripts/jvmfree_test_evidence.py`（測定の正本 — MEASURE/REFUSED のみを信じる）
- `~/.hermes/profiles/amu-test-jvmfree/workspace/jvmfree-test-ledger.jsonl`（append-only。手で編集しない）
- skill `clj-to-kotoba-migration`（JVM-free acceptance と worktree 手順の参照）
- amu 配下 AGENTS.md（Q9: `--jvm-free` が java/clojure/clj を呼ばないことを壊さない）

## 制約

- **cron は unattended で走る**: 承認 prompt を出す操作をしない。測定・検証は terminal 経由の
  script 呼び出しのみ。
- **JVM を起動しない**: java/javac/clojure/clj/bb を呼ぶコマンドは打たない（Q9 の絶対規則）。
  JVM suite の緑は acceptance ではない（compatibility diagnostics）。
- **並行エージェント運用**: 本体 checkout・共有 `orgs/` を書き換えない。worktree は superproject の
  外。他セッションの WIP（amu checkout の既存 dirty: docs/archive/codegen-cosientist.md 等）に触れない。
- **値の捏造禁止**: 0 進捗は「0」、検査が通らなければ「通らない」と正直に。26 tick 連続ゼロ移行の
  先例（jvm-dep-migrator）のように、ゼロを飾らず記録して次の 1 手を名指す。
- **1 反復 = 1 finding**。詰め込まない。未完了は「開始・未完了」を明記して次 tick へ。
