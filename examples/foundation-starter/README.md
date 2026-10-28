# Kotoba / Amu first run

Read Kotoba, check and compile it with Amu, change the result, and inspect
two concrete execution boundaries. No Awai membership, account, model,
payment or Itonami application is required. Acquiring the candidate and
any omitted files requires network access; the example guests themselves
run without network authority.

**Starter engineering preview, not a public trial release.** The compiler
descriptor still records empty native generations and false qualification
flags. [Main CI run 40759416436](https://github.com/kotoba-lang/amu/actions/runs/40759416436)
passed for upstream revision `3e7780f7c346a7fba8dbb3e29d787ae02b264acf`;
qualification of this starter revision remains open. At the older
PR revision `e967ae44c1117a4a19b6a82579f0b826db7603b1`, with a different compiler, the
[Linux native workflow](https://github.com/kotoba-lang/amu/actions/runs/40753510291)
and [Mac and Linux cross workflow](https://github.com/kotoba-lang/amu/actions/runs/40753510318)
completed successfully. These results apply to that revision; check the PR
for the current revision and its checks. They are bounded engineering
observations, not a change to the descriptor's qualification flags. Current-image
qualification and descriptor flags need upstream reconciliation. A second
host profile, release review and independent user evidence remain open.

Public compiler host: **native Linux x86_64**. macOS, Windows, Linux ARM64,
WSL, containers and emulation are not qualified by this starter. Do not run
the retired hosted launchers or install Node, JVM, NBB or a C loader as a
fallback. Python 3 is used only by the optional observation harness for
staging, hashes and native-process output; it does not compile or evaluate
Kotoba.

## Check the host first

Run `uname -s` and `uname -m`: this candidate expects `Linux` and `x86_64`.
Also check that `git --version` and `python3 --version` succeed. These checks
identify basic prerequisites; they do not prove the machine is native or that
its host profile has been independently qualified. If they do not match, stop
and record the results rather than trying a different compiler.

## Obtain and verify the candidate

The Amu repository is available under the [Apache License 2.0](../../LICENSE).
This is an engineering-preview procedure, not a release download. On a native
Linux x86_64 machine with Git and Python 3, first identify the full 40-character
commit you have reviewed on [the starter draft PR](https://github.com/kotoba-lang/amu/pull/1640).
Put that exact commit in `REVIEWED_REVISION` below; do not substitute a moving
branch name. In a dedicated shell, run these commands in a new directory of
your choice. `set -e` stops that shell if acquisition or any check fails:

```sh
set -e
git clone --filter=blob:none --depth 1 --no-checkout https://github.com/kotoba-lang/amu.git amu-starter
cd amu-starter
git fetch --filter=blob:none --depth 1 origin pull/1640/head
REVIEWED_REVISION=replace-with-reviewed-40-character-commit
test "$(git rev-parse FETCH_HEAD)" = "$REVIEWED_REVISION"
git sparse-checkout set --cone bin seed scripts examples
git checkout --detach "$REVIEWED_REVISION"
test "$(git rev-parse HEAD)" = "$REVIEWED_REVISION"
python3 - <<'PY'
import hashlib, json
from pathlib import Path

candidate = json.loads(Path('examples/foundation-starter/candidate.json').read_text())
files = {'bin/amu': candidate['compilerImage']}
files.update({f'examples/foundation-starter/{name}': spec
              for name, spec in candidate['fixtures'].items()})
for name, spec in files.items():
    data = Path(name).read_bytes()
    if len(data) != spec['bytes'] or hashlib.sha256(data).hexdigest() != spec['sha256']:
        raise SystemExit(f'mismatch: {name}')
    print(f'verified: {name}')
PY
```

The fetched PR head must still match the commit you reviewed. If it changed,
stop and review the new head before trying again. The pin manifest is part
of the reviewed commit; matching it checks the local bytes, not the
trustworthiness of an unreviewed commit. Stop on a mismatch.
The observation packet below also checks compiler source unity. Partial clone
may download omitted files later; keep network access available for those
operations. Public release availability and independently qualified host
profiles remain separate gates.

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
python3 scripts/seed/check-foundation-starter.py \
  --output /absolute/task-workspace/starter-observation \
  --host-profile linux-x86-64-your-os-version
```

The observer runs its compiler and guest calls sequentially. Each child gets
`PATH=/nonexistent`; the observer launches `bin/amu` directly and never
selects another compiler. Outputs include staged source locks, generated
ELFs, stdout/stderr logs and `starter-observation.json`. Existing output
directories are refused.

The host-profile label is 1–64 characters: start with a lowercase ASCII
letter or digit, then use only lowercase ASCII letters, digits and hyphens.
For example, use `linux-x86-64-ubuntu-24-04`, not `ubuntu-24.04`. The label
describes the environment; choosing it does not qualify the host.

Expected terminal status is `PASS_STARTER_FUNCTIONAL_SMOKE`.
`publicReleaseReady` remains **false**, even if the functional smoke passes.
The manifest retains the reviewed upstream revision, the descriptor's
reported source revision, image and observer hashes, host profile, actual
native results and the descriptor's qualification state. The descriptor's
reported source revision is historical metadata. Reconstructing its 48 source
modules yields SHA-256 `18e98b761f744f27d567a9cd0a50a6fcd9e27a27ca800d9653d17f5701f0dabf`,
which differs from the pinned source unity `2127d9d9...`. Reconstructing the
modules at the candidate's upstream revision yields the pinned unity; this
match alone does not establish the binary's source-to-image provenance.
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

## Adapt the sum for your own range

For a first calculation of your own, copy `sum.kotoba` into the same scoped
`STARTER_OUTPUT` directory. Change the upper bound `(> i 10)` to a positive
integer relevant to your task. For example, `(> i 20)` sums 1 through 20;
the expected result is `210`. Keep the original example unchanged:

```sh
cp examples/foundation-starter/sum.kotoba "$STARTER_OUTPUT/sum-custom.kotoba"
# Edit sum-custom.kotoba and change (> i 10) to (> i 20).
KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35="$STARTER_OUTPUT" \
  KEXE_STACK_BYTES=8388608 ./bin/amu check "$STARTER_OUTPUT/sum-custom.kotoba"
KEXE_ALLOW=35,37,38,39 KEXE_CAP_RESOURCES_35="$STARTER_OUTPUT" \
  KEXE_STACK_BYTES=8388608 ./bin/amu compile "$STARTER_OUTPUT/sum-custom.kotoba" \
  --target x86_64-linux --output "$STARTER_OUTPUT/sum-custom.elf" --format static
chmod 700 "$STARTER_OUTPUT/sum-custom.elf"
KEXE_ALLOW=- KEXE_FUEL=1000000 KEXE_STRUCTURED_REPORT=1 \
  "$STARTER_OUTPUT/sum-custom.elf"
```

Compare the result to the independently calculated value before changing the
range again. This example uses signed 64-bit integers and a finite fuel budget;
large bounds can overflow or exhaust fuel. Choose a new output filename when
recompiling. The compiler can access only the scoped directory and this guest
receives no capabilities.

## 日本語の進め方

1. 対応候補は native Linux x86_64 です。上の「Check the host first」で OS、CPU、
   Git、Python 3 を確認します。候補と不足ファイルの取得にはネットワークが必要です。
   一致しても host の公開資格を証明したことにはなりません。
2. 「Obtain and verify the candidate」で、レビューした PR の40文字 commit を指定して
   取得し、compiler とサンプルの hash を照合します。不一致の場合は止めてください。
3. 「Run the native observation packet」で新しい出力ディレクトリを指定して20操作を
   実行します。host profile は英小文字・数字・ハイフンのみの1〜64文字で、先頭は英小文字か
   数字です。例えば `ubuntu-24.04` ではなく `linux-x86-64-ubuntu-24-04` とします。
   成功表示は機能確認であり、公開資格や第三者試用の完了ではありません。
4. 「Run and change a small program yourself」で `hello.kotoba` を検査・コンパイル・
   実行し42を確認します。コピーを `(+ 40 3)` に変え、別の成果物を作ると43です。
5. observation packet で `sum.kotoba` の55と、同じ成果物の fuel 1 による停止を比較します。
   `hash.kotoba` では権限なしの拒否を確認し、ローカルSHA-256のwire 3だけを許可して
   結果64を確認します。ネットワーク・ファイル・推論の権限は追加しません。
6. 「Adapt the sum for your own range」で上限を20に変えると結果は210です。自分の小さな整数計算に
   置き換え、期待値・実際の結果・対象host/revisionを残します。

問題が起きた場合は「If a step fails」を参照し、commit、OS/CPUの大まかな区分、
失敗した手順、診断、期待値と実際の結果を記録します。公開できる内容は
[Amu の issue](https://github.com/kotoba-lang/amu/issues) へ報告できます。ログから
秘密情報や個人情報を除いてください。対応時間を約束する窓口ではありません。

技術基盤は Kotoba Foundation の言語・Amu compiler・AIUEOS OS です。
Awai Network / Itonami dapps はその基盤を使う応用・分散経済圏です。
このstarterは言語とcompilerの入口であり、OSやnetwork全体の資格を意味しません。

## If a step fails

- Wrong host: stop; this preview targets native Linux x86_64 only. A matching
  host is not by itself a qualified release or independent reproduction.
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
private code, environment variables or credentials. For an issue that can be
shared publicly, use [the Amu issue tracker](https://github.com/kotoba-lang/amu/issues).
The tracker is public; do not post sensitive information there. No telemetry
is sent. An issue tracker link is not a promise of support response time.

See [the five-minute technical walkthrough](DEMO.md). To read the native
product scope from this same reviewed commit, run
`git show HEAD:docs/native-public-entry.md` (which may fetch that file).

Maintainers can pass `--experimental-arm64` to the observer on Linux ARM64 to
exercise the pinned ARM bootstrap root. This is a diagnostic observation, not
a supported public compiler profile or third-party qualification. Its receipt
identifies the experimental mode and keeps `publicReleaseReady` false.
The [ARM64 diagnostic preview](ARM64-PREVIEW.md) documents acquisition checks
and direct first-run commands for review.
