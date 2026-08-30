# ADR 0285: `(:require ...)` is frontend policy, and the wall in front of it was a launcher routing defect

- Status: accepted
- Date: 2026-08-30

## Decision

Multi-file guest projects were already supported, and they still are supported
by the same mechanism: `kotoba.compiler.project/module-info` admits
`(:require [ns :as alias])`, `kotoba.compiler.project-files` resolves the
closed graph, `project/link-source` links it, and `compile --source-path` /
`compile --module-lock` reach all three. `kotoba.sema`'s single-module frontend
does not admit `:require` and is not changed here — a module cannot resolve
`util/answer` without the linker, so admitting the clause one file at a time
would admit what nothing in that path can lower.

What changes is everything between the caller and that working mechanism:

1. **`check` gains project mode** (`--source-path <dir>`, or
   `--module-lock <lock> --blocks <dir>`), via a new
   `kotoba.compiler.core/check-project`. Before this, `compile` took those
   flags and `check` took neither: a multi-file guest could be **built but
   never checked**.
2. **The launchers stop routing project-mode invocations to the nbb
   entrypoints.** `kotoba.compiler.nbb.*` has no linker; it compiled the one
   file it was handed and *silently dropped* `--source-path` /
   `--module-lock`. `bin/amu` and `bin/kotoba` now send any invocation
   carrying either flag to the JVM entrypoint that owns the linker.
3. **The refusal is renamed and carries the working commands.** A `:require`
   clause reaching the single-module path now reports
   `:kotoba.error/namespace-require-needs-project` with the four measured
   invocations in `:details`, instead of "only a bounded `:export` vector is
   admitted in namespace clauses" — the message written for a malformed
   `:export`, reached through the same fall-through `case` branch.

Nothing is admitted that was not admitted before. `ex-data`'s
`:kotoba.error/code` is left exactly as the frontend set it; the rename happens
at the reporting boundary only, so subset corpora keep asserting the frontend's
own code.

## Evidence boundary

Host: MacBookPro18,4, macOS. Every command below was run through the shipped
launcher on the real sources in
`com-junkawasaki/orgs/kotoba-lang/org-iso-h264/src` — `h264/sps.kotoba`, which
declares `(:require [h264.expgolomb :as eg] [h264.rbsp :as rbsp])`, plus the
two siblings it names. Timings are wall clock from `time`, with the `load1`
that stood beside them; this workstation ran at load1 10-370 from concurrent
sessions throughout, so treat them as upper bounds and as evidence only that
the commands terminate, not as a performance claim.

### What was measured

**Both failure shapes, before the change:**

| invocation | exit | reported |
|---|---|---|
| `amu check sps.kotoba` | 65 | `:kotoba.error/namespace-export-clause`, "only a bounded :export vector is admitted in namespace clauses" |
| `amu compile sps.kotoba --source-path src --unpinned --target wasm32 --output /tmp/sps.wasm` | 65 | *the same diagnostic* — the flags never reached a linker |

The second row is the routing defect, and it is separable from the first: the
identical arguments sent to the JVM entrypoint directly
(`clojure -M:run compile ...`) exited **0** and wrote a 6,561-byte `.wasm`
(load1 27.21, 10.3 s wall). Same arguments, same tree, two answers — the only
difference was which entrypoint `bin/amu` picked.

**After the change**, every command named in the new diagnostic was run and
observed:

| invocation | exit | result | wall | load1 |
|---|---|---|---|---|
| `amu check sps.kotoba --source-path src` | 0 | `effects=#{} exports=[parse-baseline parse-ebsp-baseline] modules=["h264.expgolomb" "h264.rbsp" "h264.sps"]` | 8.6 s | 11.2 |
| `amu module-lock sps.kotoba --source-path src --blocks <dir>` | 0 | 3 modules, lock CID `bafkreigxpr7hfgw34doohso5intzzzrbcujz5hfw5cfmujlxjcdk4nh54y` | 6.8 s | 10.4 |
| `amu check --module-lock <lock> --blocks <dir>` | 0 | same three modules | 7.4 s | 10.4 |
| `amu compile --module-lock <lock> --blocks <dir> --target wasm32` | 0 | `:kotoba.compile/inputs :module-lock` | 8.2 s | 10.4 |
| `amu compile sps.kotoba --source-path src --unpinned --target wasm32` | 0 | 6,561-byte `.wasm`, `:kotoba.compile/inputs :unpinned-source-path` | 7.5 s | 12.9 |
| `amu compile sps.kotoba --source-path src --unpinned --target js` | 0 | `.mjs` + provenance sidecar | 9.2 s | 26.0 |
| `kotoba -M check sps.kotoba --source-path src` | 0 | same three modules (compat front fixed too) | — | — |

**The refined diagnostic appears on both entrypoints.** `amu check` (nbb path)
and `amu compile --target js` (JVM path) both now exit 65 with
`:kotoba.error/namespace-require-needs-project` and
`:details {:problem :namespace/require-needs-project, :pin ..., :then ...,
:check ..., :override ...}`. The two envelopes previously disagreed on
`:details` entirely — the nbb one carried none.

**The refinement stops where it should.** `(:import [java.lang String])` still
exits 65 with `:kotoba.error/namespace-export-clause` and the original message,
verbatim. `:import` and `:use` are forbidden outright by the guest-grammar
authority (`kotoba-lang/lang/guest-grammar.edn` `:diagnostic-hints`); naming a
project invocation for them would advertise a path that does not exist.

**One further defect was found by doing this and is fixed here.**
`check-project`'s first implementation refused its own linker's output:
`project/link-source` renames cross-module symbols with the reserved
`__kotoba_` prefix that authored source may not use, and `check-source` had no
way to accept them. Measured: `amu check --source-path` exited 65 with
`symbol uses the reserved __kotoba_ prefix` at `sps.kotoba:4:113`.
`compile-source` already reads `:admit-linked-synthetics?` from its build
metadata for exactly this; `check-source` now reads the same key from `opts`,
and only `check-project` passes it.

### Which authority was consulted

`kotoba-lang/lang/guest-grammar.edn` (the source-surface authority, read at
`orgs/kotoba-lang/kotoba-lang`) **does not mention the `ns` `:require`
clause at all**. Its one `require` entry is the *call head* `require`, listed
in `:forbidden-heads` beside `eval`, `load-file` and `resolve`, with the hint
"forbidden: guests cannot require; use host imports + package-lock (CID
packages on L3)". That is ambient runtime namespace loading, a different thing
from a namespace-header import resolved at link time — and "package-lock (CID
packages on L3)" is a description of `module-lock`, the path this ADR
surfaces. The authority is therefore silent on the clause, and the frontend's
refusal is `kotoba-sema`'s own policy (`frontend.cljc` `namespace-parts`:
"Import/require clauses remain fail-closed"), not an authority requirement.

### What was NOT done, and why

**The frontend was not made to admit `:require`.** This is the ADR 0284 rule
applied to itself: a gate that admits what nothing behind it can lower is the
defect. `kotoba-sema`'s single-module path has no module resolver, so a source
admitted there could name `util/answer` with nothing to bind it. The refusal is
correct; only its signage was wrong.

**The nbb entrypoints did not gain a project linker.** They are the JDK-free
fast path for one file. Teaching them to walk a directory graph would duplicate
`project-files` in a second language with a second set of symlink-escape and
cross-root-ambiguity rules. Routing is the smaller and more honest fix. The
consequence is stated plainly: project mode requires the JVM entrypoint, hence
a JDK.

**`check --source-path` does not require `--unpinned`, unlike `compile`.**
That flag exists (ADR-2608580000 D5) because a path-resolved *artifact* cannot
say which inputs produced it. `check` writes no artifact, so there is no
provenance record for an unpinned read to falsify. `check --module-lock` is
available for callers who want the pinned read anyway, and it was measured.

**`:schemas` in project mode is still refused.** Linking several modules'
schema tables needs a collision rule for identically-named schemas, which is a
separate decision (`project/module-info` says so already). Unchanged.

### Limits of this evidence

- **`check` and `compile` say the sources are admissible and lowerable. They do
  not say the decoder is correct.** No H.264 bitstream was decoded, and no
  artifact produced here was executed. The wall this ADR removes was in front
  of the decoder, not in it.
- Three modules, two edges. `max-project-modules` is 256 and
  `max-project-depth` 64; neither bound was approached, and the graph has no
  diamond, no cycle and no cross-root namespace.
- Only `wasm32` and `js` targets were compiled from a project through the
  launcher. `component`, native and `evm` project compiles go through the same
  `cond` in `cli.clj` and were not run.
- The behaviour of a machine with **no JDK** invoking project mode was not
  measured. It will reach `runCompiler`'s `clojure` spawn and fail there rather
  than being mis-diagnosed by the nbb path, but that failure was not observed.
- Timings are wall clock on a host at load1 10-370. They bound termination, not
  cost.
