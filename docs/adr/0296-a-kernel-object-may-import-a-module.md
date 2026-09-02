# ADR 0296: a kernel object may import a module

- Status: accepted
- Date: 2026-09-02

## Decision

The project route reaches the NATIVE driver. `amu compile <entry> --source-path
<dir>` and `amu compile --module-lock <lock> --blocks <dir>` now link a closed
module graph for every target the JDK-free native path serves — the four aiueos
profiles included — and the aiueos kernel profile packages the linked unit into
the same one-public-symbol ET_REL object it has always produced.

`resolve-source!` moved out of `kotoba.compiler.nbb.wasm-cli` into
`kotoba.compiler.nbb.project-source`, which both drivers require. There is one
resolver, not two.

## Why this was not a target problem

Nothing about a kernel object made it single-file. `project/link-source` is
portable `.cljc`, both resolvers beneath it already ran on Node (amu#717 for
the PATH resolver, ADR 0298 for the lock), and every aiueos profile reaches
the same two ISA emitters as the ordinary native targets. The function that
called them was simply written inside the Wasm driver.

The native driver read `(second args)` and nothing else. So `--source-path`
and `--module-lock` were accepted on the command line and **read and
discarded**:

```
$ amu compile entry.kotoba --target x86_64-aiueos-kernel-v1 --jvm-free
:kotoba.error/namespace-require-needs-project

$ amu compile entry.kotoba --source-path src --unpinned \
    --target x86_64-aiueos-kernel-v1 --jvm-free
:kotoba.error/namespace-require-needs-project      # byte-identical
```

Measured 2026-09-02 on b1fdaad2, both bodies identical down to the span. An
invocation that named its source roots and one that did not got the same
answer, and the answer told the caller to pass the flag they had just passed.
`--module-lock` failed one step earlier and further from the cause: `source
input must use .kotoba, .cljk, or .cljc`, because `--module-lock` was being
read as the input path.

## The cost outside this repository

aiueos. A kernel object that cannot import anything has to inline every helper
it uses, so SHA-256 is copied into `sha256.kotoba`, `hkdf-sha256.kotoba` and
`tls13-record.kotoba`, and was about to be copied into the handshake, the NIC
and the Qwen objects. Three copies of a hash function is not a style problem —
it is three things to fix when one of them is wrong.

## The single-export contract is not weakened

kotoba-native `elf64/package-kernel-object` requires exactly one exported
`kotoba_aiueos_*` symbol, and the aiueos verifier
(`os/aiueos/scripts/verify-kotoba-kernel-object.py`) checks it on the
container. A multi-module *source* project still produces that object, because
`link-source` emits every non-root function as `defn-`: **a dependency's
exports are not exports of the linked unit.**

Measured on the two-module fixture (`kproj.helper` exports
`aiueos-not-a-symbol`, a name `kernel-object-entries` does not carry;
`kproj.entry` requires it and exports `aiueos-fnv1a`):

| | |
|---|---|
| `check --source-path` exports | `[aiueos-fnv1a main]` |
| `.symtab` | 5 entries, 1 GLOBAL FUNC: `kotoba_aiueos_fnv1a` |
| `.o` from `--source-path` | `d80560c7…d14d6ef9` |
| `.o` from `--module-lock` | `d80560c7…d14d6ef9` |
| `.o` from the JVM (`clojure -M:run compile --source-path`) | `d80560c7…d14d6ef9` |

The same unlisted `aiueos-` name is harmless in a dependency and fatal in the
entry module, which is the discriminating pair: only the entry module's
exports are the object's exports.

## Route parity

The three routes agree on the object byte for byte. They do **not** agree on
provenance, in exactly one field:

```
:build-metadata-sha256  JVM  4731c3f7…21db5cb7
                        Node 44136fa3…1caaff8a   (= sha256 of {})
```

`kotoba.compiler.core/compile-project` passes `:module-graph-digest` and
`:module-source-digests` as build metadata; the Node route passes only
`--fuel`. This divergence is **pre-existing and not introduced here** — it is
already true of the Wasm project route, which has been on Node since amu#717,
and it is recorded in the workspace CLAUDE.md. It is not fixed in this change
because closing it changes the provenance hash of every existing project-route
Wasm artifact, which is a separate decision with its own consumers. A consumer
that compares provenance across routes cannot treat the two as the same build;
one that compares artifacts can.

## The single-file route is unchanged

`examples/i64-semantics.kotoba` at `x86_64-aiueos-kernel-v1`, compiled by
b1fdaad2 and by this branch: `093ac51c…50f27562` both times, with byte-identical
`.provenance.edn` and `.publication.edn`. The Wasm route is likewise unchanged
(`8d622369…d0674a11` single-file, `afe2bdb2…9d7b5277` project) — the refactor
moved the resolver, it did not change it.

One key is added to the native `compile` result: `:kotoba.compile/inputs`
(`:single-file` / `:unpinned-source-path` / `:module-lock`, plus `:module-lock`
and `:lock-cid` for a pinned build). The Wasm driver has always reported it;
the native one could not, because it had no answer to give.

## A packager's refusal is not an internal compiler error

`kotoba.native.elf64` refuses a source claiming an `aiueos-` export with no
admitted symbol, and it says so — but it raises `ex-info` with no `:phase`, and
`cli-support/exit-code` reads `:phase`. So every deliberate packaging refusal
arrived as `:internal`, exit 70, with its own sentence replaced by the words
`internal compiler error`. Measured 2026-09-02 on b1fdaad2, single-file and
project route alike.

`kotoba.compiler.nbb.native-package/refusal-is-not-a-defect` gives those
refusals `:phase :artifact-target` (exit 65). Only an error CARRYING `ex-data`
is re-tagged: raising `ex-info` is how a packager says it decided to refuse. A
`TypeError` out of a packager IS a compiler defect and still says so —
re-tagging everything would turn every internal packaging bug into "your source
is wrong", which is the same mistake pointed the other way.

## What each gate was shown to catch

Every one was run red on a deliberate break and green unchanged, and the red
had to be the gate's own sentence — `scripts/jdk-free-native-conformance.cljs`,
section 1–8.

| break | gate that fired |
|---|---|
| drop `refusal-is-not-a-defect` | `the unlisted-export refusal named a different cause: … :error :internal … "internal compiler error"` |
| swallow a graph that will not load | the `required module is missing from the explicit source paths` literal is absent (the run fails, but as `project source map is empty` — a different cause, which is the point of pinning the literal) |
| `link-source` exports every module's interface | `:exports [aiueos-fnv1a aiueos-not-a-symbol main twice]` — both halves of the export-surface assertion |
| the two resolvers hand the linker different sources | two distinct `.o` hashes where the gate requires one |

One assertion was written and then **removed before landing**: a check that no
symbol in `.symtab` contained the dependency's export name. It cannot fail. A
kernel object names one public symbol and `kotoba_source_entry` whatever the
Kotoba exports were, so that check passes by construction — it would have
counted as evidence for a property it never looked at. The export surface is
asserted on `check --source-path` instead, where it can go red.

## Not done

- The `:build-metadata-sha256` route divergence above.
- The nbb route does not enforce `--unpinned` for a `--source-path` compile;
  the JVM route refuses with `a multi-module compile needs pinned inputs`.
  Measured 2026-09-02: `compile --source-path` without `--unpinned` succeeds on
  Node and is refused on the JVM. Pre-existing on the Wasm route since amu#717
  and inherited unchanged here rather than newly decided.
- `x86_64-aiueos-kernel-v1 --artifact image` is still refused on this route
  (kotoba-native ADR-0036, the live-boot GDT/TSS twin divergence). Unchanged.
