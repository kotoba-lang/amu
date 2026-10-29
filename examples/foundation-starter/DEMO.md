# Technical demo: source, native result, execution boundary

This is a five-minute presentation outline, not a performance claim or a
promise that setup takes five minutes. Run the observation harness in the
[starter guide](README.md) on the declared host before presenting it. Show
the current qualification banner and actual logs; do not fabricate output
or label a recorded replay as a live run.

| Segment | Show | Explain |
| --- | --- | --- |
| 0:00–0:45 | `hello.kotoba`, compiler/fixture pins, host profile | Kotoba is the language; Amu checks and emits the native artifact. This candidate is not a qualified release. |
| 0:45–1:45 | `hello-check`, `hello-compile`, `hello-run` logs | The actual public entry compiled this source; the guest reports result 42. |
| 1:45–2:30 | Edited source and `hello-changed-run` | Change an expression, rebuild, observe different bytes and result 43. No remote service evaluates the source. |
| 2:30–3:15 | `sum-run` and `sum-low-fuel` | The same native artifact reports 55 with a finite budget and refuses when that budget is insufficient. |
| 3:15–4:15 | `hash-denied` then `hash-local-grant` | Authority starts empty. Grant exactly local SHA-256, wire 3; do not grant network or file access to this guest. |
| 4:15–5:00 | Observation JSON and the next source edit | Separate observed results, compiler qualification, public availability and real user adoption. Invite one small calculation with a known result. |

## 日本語の説明軸

「コードを読む→検査する→成果物を作る→動かす→変更する」を最初に見せます。
次に、同じ成果物について資源上限と明示的な権限の有無で結果が変わることを
実ログで示します。言語/コンパイラの説明を、速度の一般論に置き換えません。

Kotoba Foundationの Language / Compiler / OS が技術基盤、Awai Networkの
dapps・独立Cell・ノード・経済活動が実利用です。このデモではAIUEOSのboot、
別nodeへの復元、分散実行、決済、推論は実演していません。

## Evidence to retain

Keep `starter-observation.json`, its raw stdout/stderr, exact source/artifact
hashes and the actual presentation mode (live or recorded). The author-run
packet is internal functional evidence. External clean-host reproduction,
the 20-success cohort and D7/D30 retention are separate gates.
