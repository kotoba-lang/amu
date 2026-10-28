# Kotoba / Amu first run

Read Kotoba, check and compile it with Amu, change the result, and inspect
two concrete execution boundaries. No Awai membership, account, model,
payment, network call or Itonami application is required.

**Starter engineering preview, not a public trial release.** The compiler
descriptor still records empty native generations and false qualification
flags. Separately, main CI run `40613036690` contains successful native
F1=F2=F3 and public-product receipts with exactly the same compiler bytes and
source-unity digest. `candidate.json` pins those evidence identities. This
descriptor/evidence mismatch needs upstream reconciliation; it must not be
silently relabelled. This new starter still needs its own native smoke,
second host profile, release review and external-user evidence.

Public compiler host: **native Linux x86_64**. macOS, Windows, Linux ARM64,
WSL, containers and emulation are not qualified by this starter. Do not run
the retired hosted launchers or install Node, JVM, NBB or a C loader as a
fallback. Python 3 is used only by the optional observation harness for
staging, hashes and native-process output; it does not compile or evaluate
Kotoba.

## What you will run

| Source | Operation | Expected observation |
| --- | --- | --- |
| `hello.kotoba` | Check, compile, run with empty guest authority | `:result 42` |
| Edited copy of `hello.kotoba` | Change `(+ 40 2)` to `(+ 40 3)`, recompile | Different ELF bytes and `:result 43` |
| `sum.kotoba` | Sum 1 through 10 with a finite fuel budget | `:result 55` |
| The same `sum` artifact | Run with fuel 1 | Exit 120 and `:budget/fuel` |
| `hash.kotoba` | Ask for local SHA-256 with no granted capability | Exit 120, wire 3 `:not-granted` |
| The same `hash` artifact | Grant only wire 3, local SHA-256 | `:result 64` (hex digest length) |

These are bounded native-runtime observations. They are not a universal
security guarantee, signed Cell receipt, AIUEOS boot, distributed execution
or comparative performance measurement.

## Run the native observation packet

Use a reviewed immutable checkout of this candidate on a native Linux
x86_64 host. Verify the compiler and fixture pins in `candidate.json`.
The observer also checks the current complete compiler source-unity digest.
Choose an absolute, **new** output directory in your task workspace:

```sh
python3 scripts/seed/native_build_queue.py -- \
  python3 scripts/seed/check-foundation-starter.py \
  --output /absolute/task-workspace/starter-observation \
  --host-profile linux-x86-64-your-os-version
```

The existing shared native-build queue admits at most two cooperating
builds. It does not stop other jobs. Each child compiler or guest gets
`PATH=/nonexistent`; the observer launches `bin/amu` directly and never
selects another compiler. Outputs include staged source locks, generated
ELFs, stdout/stderr logs and `starter-observation.json`. Existing output
directories are refused.

Expected terminal status is `PASS_STARTER_FUNCTIONAL_SMOKE`.
`publicReleaseReady` remains **false**, even if the functional smoke passes.
The manifest retains the source revision, image and observer hashes, host
profile, actual native results and the descriptor's qualification state.
It records **zero external users**; an author-run smoke is not a user cohort.

## Run and change a small program yourself

Work from the checkout root. Set `STARTER_OUTPUT` to a new absolute directory
under your task workspace, then create it. The compiler receives permission
to read and write only that scoped directory. The generated pure program
receives no capabilities:

```sh
STARTER_OUTPUT=/absolute/task-workspace/manual-first-run
mkdir "$STARTER_OUTPUT"
cp examples/foundation-starter/hello.kotoba "$STARTER_OUTPUT/hello.kotoba"

KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35="$STARTER_OUTPUT" \
  KEXE_STACK_BYTES=8388608 ./bin/amu check "$STARTER_OUTPUT/hello.kotoba"
KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35="$STARTER_OUTPUT" \
  KEXE_STACK_BYTES=8388608 ./bin/amu compile "$STARTER_OUTPUT/hello.kotoba" \
  --target x86_64-linux --output "$STARTER_OUTPUT/hello.elf" --format static
chmod 700 "$STARTER_OUTPUT/hello.elf"
KEXE_ALLOW=- KEXE_FUEL=1000000 KEXE_STRUCTURED_REPORT=1 \
  "$STARTER_OUTPUT/hello.elf"
```

Edit the copied source to `(+ 40 3)`, compile to a **new** output filename,
and run again. Expect `:result 43`. The static compiler requires the shown
argument order. The observation packet checks each input against a KSL1 lock
and exercises a wrong-lock-digest refusal (`E6015`). Static ELF compilation
does **not** accept that lock: adding it selects the separate locked-project
route, whose supported format is `kx64-v1`. The observer requires that
unsupported static/lock combination to refuse `E1` without an output file.
Its private staging and before/after source hashes are not an atomic
compiler-enforced lock at ELF compilation. An omitted compile target refuses
`E2`; always name the target explicitly.

## 日本語の進め方

1. 対応ホストは native Linux x86_64 です。これは公開資格が未完了の技術候補です。
   `candidate.json` と実行記録の資格状態を確認してください。
2. `hello.kotoba` を読み、Amuで検査・コンパイル・実行します。期待値は42です。
3. コピーの `(+ 40 2)` を `(+ 40 3)` に変更し、新しい成果物を作って43を確認します。
4. `sum.kotoba` の55と、同じ成果物の fuel 1 による停止を比較します。
5. `hash.kotoba` で権限なしの拒否を確認し、ローカルSHA-256のwire 3だけを許可して
   結果64を確認します。ネットワーク・ファイル・推論の権限は追加しません。
6. 自分の小さな整数計算に置き換え、期待値・実際の結果・対象host/revisionを残します。

技術基盤は Kotoba Foundation の言語・Amu compiler・AIUEOS OS です。
Awai Network / Itonami dapps はその基盤を使う応用・分散経済圏です。
このstarterは言語とcompilerの入口であり、OSやnetwork全体の資格を意味しません。

## If a step fails

- Wrong host: stop; use a qualified native Linux x86_64 environment.
- Digest/source-unity mismatch: stop and retain the exact revision and hashes.
  Do not disable the pin check or silently use a different image.
- Compiler diagnostic: retain the named `E...` and the command. Unsupported
  targets/flags refuse; do not select a legacy launcher.
- Fuel/capability refusal: these are expected only in the named negative
  cases. A refusal during a positive case is a failed smoke check.
- Timeout or missing result: retain raw logs; no successful observation file
  is produced. Do not count a partial run as activation.

Report the release/commit, non-identifying OS/CPU profile, step, diagnostic
and expected/actual result. Review logs before sharing them; do not attach
private code, environment variables or credentials. No telemetry is sent.

See [the five-minute technical walkthrough](DEMO.md) and
[native product scope](../../docs/native-public-entry.md).
