# Selfhost: the minimal reach set and the definition ledger (2026-10-02)

Owner: amu-measure (agent/dual-runtime-port). Follows `docs/selfhost-efficiency-analysis-20261002.md`, which claimed
that the first self-build needs 122 of 177 reachable modules. This page verifies that claim with the require graph,
records the edges that were cut to make it true, and fixes the progress metric: a ledger of definitions that have a
real Kotoba body, not files OK.

## 0. Decisions adopted for this wave (owner, all reversible)

1. First 100% is aarch64-macos only. x86-64, wasm, component, EVM, JS, uefi, elf/pe backends are deferred. A deferred
   target is refused by name in the self-built binary until it is ported; nothing is deleted.
2. A `.kexe` run by the C loader (`tools/kexe_loader.c`) counts as the amu binary for milestone 1. A standalone
   Mach-O is milestone 2 (`kotoba/object/macho64` is therefore also outside the minimal set).
3. The native value-size limit (64 KiB string/bytes) is raised to at least 8 MiB (the ADR 0356 source bound) by an
   ADR. That ADR is a separate item of this wave; nothing on this page depends on it.
4. The KIR interpreter is frozen. In scope: `kir/lower`, and the evaluation `fold-def-value!` needs (constant
   folding). The verifier comes after the first self-build.
5. The JVM native-image checker is the stage-0 bootstrap compiler. It is labelled bootstrap-reference everywhere and
   stops counting at stage2 == stage3.

## 1. The claim, checked

`scripts/selfhost-wall/reach-minimal.py` computes the closure of the `ns` `:require` graph against the harness
classpath (`wall-cp-15.txt`). It has two views. The HOST view follows every reader branch (what nbb and the JVM
load). The KOTOBA view resolves each `ns` form the way the Kotoba reader does (`#?(:kotoba ..)` arm, else `:default`,
`:clj`/`:cljs` dropped); that is what the self-built compiler has to carry. Roots of the minimal set:
`nbb/aarch64-cli`, `nbb/cli`, `nbb/check-cli`, `nbb/refactor-cli`, `sema`, `native/aarch64`, plus `project`,
`project-files`, `module-lock`, `refactor-cli` and the refactor library. The last group is listed explicitly because
the Kotoba reading of its requirers is a placeholder today (`nbb/project-source` keeps the single-file read,
`nbb/refactor-cli` is `#?(:kotoba nil ..)`), so the Kotoba view alone would silently lose modules the self-built
binary must have.

| set (measured 2026-10-02 at 91ecd5b63 and after this change) | modules | lines | defn tokens |
|---|---|---|---|
| every `nbb/*_cli` entry, host view, before | 206 | 178.9k | 10206 |
| every `nbb/*_cli` entry, Kotoba view, before | 137 | 145.3k | 8581 |
| minimal roots, host view, before (check entry was `wasm-cli`) | 164 | 146.0k | 8810 |
| minimal roots, Kotoba view, before | 138 | 139.2k | 8447 |
| **minimal roots, Kotoba view, after** | **126** | **122.8k** | **7819** |
| minimal roots, host view, after | 152 | 129.6k | 8182 |

The efficiency analysis said 122 modules and 122.7k lines. The Kotoba view now gives 126 and 122.8k (the analysis
counted before the explicit linker and refactor roots, and with a different classpath resolution), so the claim holds
within a few modules: roughly 70% of the 177 to 206 modules the old reach list names are needed, and the rest is
deferred. What the cut removed from the Kotoba view (14 modules, 16.5k lines): `nbb/wasm-cli`, `wasm/core`,
`wasm/typed`, `nbb/native-package`, `native/linux-static`, `native/elf64`, `object/elf64`, `object/pe32plus`,
`packaging/pe32plus`, `verifier/linux-static`, `linux-static-handlers`, `limits` (only the Wasm driver read it),
`nbb/package-authoring` and `kir/descriptor`. Deferred as a whole (host-view closure of every entry at the old commit,
minus the minimal Kotoba set): 82 modules, 56.3k lines, of which 1420 `#?(:kotoba` arms sit in the
wasm/component/abi/io shims and the rest has none. The old claim "55 modules, 27k lines with no Kotoba reading" is
therefore a lower bound for the backends; the larger number includes host shims (`nbb/host/*`, `kotoba/io/*`) that
the Kotoba route replaces with abilities.

### Edges cut

| edge | what was done | host behaviour |
|---|---|---|
| `check!` out of `nbb/wasm_cli` | `nbb/check_driver.cljk` (library: `check!`, `resolve-hir!`, `read-policy!`, `decode-policy!`, `package-verdict!`, `computed-definition-cids`, moved verbatim and made public) and `nbb/check_cli.cljk` (the `check` entry). `wasm_cli` calls the driver for the helpers it still shares and keeps answering `check` for a direct spawn. `bin/amu` and `bin/kotoba` route `check` to `check_cli.cljk`. | `check` output of `wasm_cli` and `check_cli` compared byte for byte on a repo module (20031 bytes each, identical). `bin/amu check` and `bin/amu compile --target aarch64-macos` run. |
| `nbb/native-package` -> `native.linux-static`, `native.elf64`, `verifier.linux-static`, `packaging.pe32plus`, `linux-static-handlers` | `aarch64-cli` no longer requires `native-package`; its `package` slot answers nil for a target with no packaged form (what `native-package/package` answered) and refuses the two packaged aarch64 targets by name. The new entry `aarch64_packaged_cli.cljk` is the old `aarch64_cli` wiring; `bin/amu`, `bin/kotoba` and `scripts/test-linux-static-handlers.cljk` route `aarch64-aiueos-kernel-v1` and `aarch64-linux-static` there. x86-64 is unchanged. | `bin/amu compile --target aarch64-linux-static` still reaches the linux-static packager (it refuses the sample program for its own reason, as before). The aarch64-macos artifact of `examples/approval-queue-app.kotoba` is byte-identical to the previous commit's (57086 bytes, `cmp` clean). |
| `verifier` -> `native.x86-64` | The Kotoba reading of `target-contracts` carries aarch64 only (`#?(:kotoba .. :default ..)`); the `ns` form already omitted x86-64 from the Kotoba branch. Pushed in kotoba-verifier (`b03553f`, branch agent/dual-runtime-port-D). | The `:default` arm is the old map. The native checker gives the same refusal for `verifier.cljk` before and after. In the HOST view the edge stays, because nbb and the JVM still verify x86-64 artifacts. |
| `nbb/cli` -> `uefi-operations` | **Not cut, and the analysis was wrong about it.** `uefi-operations` is not the UEFI backend: it holds `reject-outside-uefi-target!` and `reject-rodata-literals-outside-native-targets!`, target gates that `nbb/cli` runs for every target including aarch64-macos ("a gate on one route is not a gate"). Cutting it would change what compiles. It is 227 lines, requires only `coll` and `kir/target`, and stays in the minimal set. | none |
| `nbb/project-source` -> `project`, `project-files` | Not an edge to cut: the Kotoba reading refuses project mode today. The two modules and `module-lock` are explicit roots instead (section 1). | none |

Residual deferred modules in the minimal Kotoba view: only `uefi-operations`, for the reason above. In the host view
the minimal set still reaches `native/x86_64` (the `:clj`/`:cljs` branch of the verifier `ns`), 8 `nbb/host/*`,
`kotoba/io/*` and `kotoba/lang/edn` / `lang/io/*` shims. These are host seams. They are the list of modules the Kotoba
route must replace with abilities or port; the ledger below counts them only where the Kotoba view reaches them.

Reproduce:

    python3 scripts/selfhost-wall/reach-minimal.py <amu-root> /private/tmp/wall-cp-15.txt <kotoba-lang>            # Kotoba view
    python3 scripts/selfhost-wall/reach-minimal.py <amu-root> /private/tmp/wall-cp-15.txt <kotoba-lang> --host     # every branch
    python3 scripts/selfhost-wall/reach-minimal.py ... --full [--host]                                              # old reach list
    python3 scripts/selfhost-wall/reach-minimal.py ... --roots=ns1,ns2                                              # arbitrary roots

The Kotoba-view list is `/private/tmp/reach-minimal.txt` (126 paths, one per line).

## 2. The ledger

`scripts/selfhost-wall/ledger.sh` (pure text analysis over `ledger.py`; no JVM, no node) counts DEFINITIONS per module
of the minimal set. A definition is a top-level `def`, `defn`, `defn-`, `defonce`, `defmacro` or `defmulti`, found at
top level, inside a top-level `do`, or as an arm of a top-level reader conditional. Its Kotoba reading is the
`#?(:kotoba ..)` arm if there is one, else the `:default` arm, else the plain form; a form with only `:clj`/`:cljs`
arms has none.

| class | meaning |
|---|---|
| REAL | the Kotoba reading has a body that does something, and the module is admitted by the native checker (`check-native.sh`) |
| unverified (arm) | real body in an explicit `#?(:kotoba ..)` arm, in a module the checker does not admit (yet) |
| unverified (plain) | the Kotoba reading is shared host code that has never been admitted |
| nil | the definition exists only on the host (`#?(:kotoba nil ..)`, or `:clj`/`:cljs` only) |
| refusal | the Kotoba arm is a short stub that says "not available on the Kotoba route" |
| stub | the body is `nil`, `false`, `0`, `""`, `[]` or `{}` (a constant such as `4096` is real) |

REAL is the headline and the other columns are the work that remains. Agreement with the host is a second column: `LEDGER_DIFF=<tsv>` takes `module<TAB>name<TAB>cases<TAB>disagreements` from the differential
recordings, and `LEDGER_ROWS=<file>` writes one row per definition (`module, name, host-lines, kotoba-body,
diff-cases, disagreements`) as the analysis asks. No differential recording exists in that shape yet, so
`covered-by-differential` is 0 in the baseline; wiring `vx`, `ds`, `abort` and `mir` recordings into it is the next
step of the metric, not of this page. The classification is a heuristic over the source text: a body that merely
looks real counts as real, which is why REAL requires the checker and why the differential column is the arbiter.

    WALL_CP=/private/tmp/wall-cp-15.txt WALL_K=/private/tmp/wt-K-kotoba-lang scripts/selfhost-wall/ledger.sh
    # per-module TSV, then TOTAL lines. LEDGER_SCAN=<tsv from check-native.sh> sets the checker status.

### Baseline (2026-10-02)

Native checker (`check-native.sh`, bootstrap-reference, run on the Kotoba-view list today with `wall-cp-15.txt`):
**84 of 126 modules admitted** (a diagnostic, not the metric). Ledger over those 126 modules (line counts here are a little above section 1's because the shared worktrees moved
between the two measurements; `native/machine_ir` alone grew by about 400 lines under its owner):

```
TOTAL	modules=126	defs=9233	REAL=4853 (52.6%)	unverified-arm=1038	unverified-plain=2071	nil=1263	refusal=2	stub=6	covered-by-differential=0
REAL-HOST-LINES	33223 of 124831 module lines (26.6%)
```

- Definitions in the minimal set: **9233**. **REAL: 4853 (52.6%)**, in 33.2k of 124.8k lines.
- Not yet REAL: 3109 definitions have a Kotoba reading that the checker does not admit (1038 in explicit
  `#?(:kotoba ..)` arms, 2071 plain host code), 1263 exist only on the host (`nil`), 8 are refusal or hollow stubs.
- Covered by a recorded differential: 0 (no recording is in the ledger's input format yet). Until it is, REAL is an
  upper bound on honest progress: admitted by the checker, not yet shown equal to the host.

By group:

| group | modules | lines | defs | REAL | unverified (arm) | unverified (plain) | nil / refusal / stub |
|---|---|---|---|---|---|---|---|
| frontend (sema) | 20 | 48244 | 3957 | 1735 | 975 | 754 | 493 |
| kir / hir / mir | 14 | 25322 | 1760 | 1284 | 0 | 201 | 275 |
| native backend (machine_ir, aarch64) | 13 | 20416 | 1379 | 765 | 62 | 473 | 79 |
| libraries (lang, io, bytes, edn, crypto, ...) | 21 | 10282 | 820 | 510 | 0 | 153 | 157 |
| nbb drivers | 15 | 5503 | 388 | 193 | 0 | 36 | 159 |
| compiler leaves (limits, text, identity, ...) | 16 | 4830 | 334 | 247 | 0 | 38 | 49 |
| verifier / security | 6 | 4790 | 259 | 110 | 1 | 142 | 6 |
| refactor library | 17 | 2865 | 212 | 0 | 0 | 177 | 35 |
| project / linker | 4 | 2579 | 124 | 9 | 0 | 97 | 18 |
| **total** | **126** | **124831** | **9233** | **4853** | **1038** | **2071** | **1271** |


The fifteen modules with the most definitions that are not yet REAL:

| module | unverified defs (arm + plain) | nil | native check |
|---|---|---|---|
| `kotoba/compiler/frontend.cljk` | 795 | 88 | refused |
| `kotoba/compiler/frontend/desugar.cljk` | 591 | 92 | refused |
| `kotoba/native/machine_ir.cljk` | 443 | 0 | refused |
| `kotoba/kir.cljk` | 201 | 0 | refused |
| `kotoba/compiler/frontend/state_ability.cljk` | 161 | 2 | refused |
| `kotoba/verifier.cljk` | 143 | 0 | refused |
| `kotoba/native/aarch64.cljk` | 92 | 0 | refused |
| `kotoba/compiler/frontend/analyze.cljk` | 86 | 3 | refused |
| `kotoba/compiler/project.cljk` | 85 | 1 | refused |
| `kotoba/lang/text.cljk` | 62 | 0 | refused |
| `kotoba/string.cljk` | 45 | 0 | refused |
| `kotoba/lang/coll.cljk` | 40 | 0 | refused |
| `kotoba/compiler/kotoba_reader.cljk` | 35 | 0 | refused |
| `kotoba/compiler/refactor/cst.cljk` | 34 | 0 | refused |
| `kotoba/compiler/nbb/cli.cljk` | 26 | 0 | refused |


### Per module

Columns: `unv. arm` / `unv. plain` are real-looking definitions in modules the checker refuses; `ref/stub` is refusal plus stub.

| module | lines | defs | REAL | unv. arm | unv. plain | nil | ref/stub | native check |
|---|---|---|---|---|---|---|---|---|
| `kotoba/compiler/definition_identity.cljk` | 2063 | 145 | 108 | 0 | 0 | 37 | 0 | OK |
| `kotoba/compiler/bounded_edn.cljk` | 459 | 25 | 22 | 0 | 0 | 3 | 0 | OK |
| `kotoba/compiler/provenance.cljk` | 356 | 23 | 16 | 0 | 0 | 7 | 0 | OK |
| `kotoba/compiler/diagnostic.cljk` | 340 | 21 | 21 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/effect_classification.cljk` | 296 | 12 | 0 | 0 | 12 | 0 | 0 | refused |
| `kotoba/compiler/kexe_fs_forms.cljk` | 247 | 21 | 19 | 0 | 0 | 2 | 0 | OK |
| `kotoba/compiler/uefi_operations.cljk` | 228 | 11 | 0 | 0 | 11 | 0 | 0 | refused |
| `kotoba/compiler/posix_path.cljk` | 178 | 18 | 18 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/capability_names.cljk` | 141 | 9 | 0 | 0 | 9 | 0 | 0 | refused |
| `kotoba/compiler/effect_row.cljk` | 117 | 6 | 0 | 0 | 6 | 0 | 0 | refused |
| `kotoba/compiler/json_text.cljk` | 89 | 6 | 6 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/text_bytes.cljk` | 88 | 11 | 11 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/decimal_text.cljk` | 76 | 10 | 10 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/process_wire.cljk` | 72 | 7 | 7 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/host_integer.cljk` | 49 | 7 | 7 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/base64_text.cljk` | 31 | 2 | 2 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/frontend/desugar.cljk` | 10652 | 683 | 0 | 591 | 0 | 92 | 0 | refused |
| `kotoba/compiler/frontend/infer.cljk` | 8495 | 573 | 515 | 0 | 0 | 58 | 0 | OK |
| `kotoba/compiler/frontend/expand.cljk` | 3852 | 235 | 188 | 0 | 0 | 47 | 0 | OK |
| `kotoba/compiler/frontend/base.cljk` | 3432 | 269 | 219 | 0 | 0 | 50 | 0 | OK |
| `kotoba/compiler/frontend/analyze.cljk` | 2837 | 89 | 0 | 19 | 67 | 3 | 0 | refused |
| `kotoba/compiler/frontend/namespace_defs.cljk` | 2654 | 205 | 124 | 0 | 0 | 81 | 0 | OK |
| `kotoba/compiler/frontend/state_ability.cljk` | 2283 | 163 | 0 | 161 | 0 | 2 | 0 | refused |
| `kotoba/compiler/frontend_tables.cljk` | 2050 | 93 | 93 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/affine.cljk` | 2049 | 204 | 184 | 0 | 0 | 20 | 0 | OK |
| `kotoba/compiler/frontend/closure_types.cljk` | 1731 | 125 | 104 | 0 | 0 | 21 | 0 | OK |
| `kotoba/compiler/frontend/record_projection.cljk` | 1427 | 23 | 0 | 6 | 14 | 3 | 0 | refused |
| `kotoba/compiler/frontend/validate.cljk` | 1424 | 51 | 39 | 0 | 0 | 12 | 0 | OK |
| `kotoba/compiler/frontend/kernel_region.cljk` | 1334 | 100 | 88 | 0 | 0 | 12 | 0 | OK |
| `kotoba/compiler/validate_expr.cljk` | 1046 | 103 | 103 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/frontend.cljk` | 910 | 883 | 0 | 198 | 597 | 88 | 0 | refused |
| `kotoba/compiler/kotoba_reader.cljk` | 793 | 35 | 0 | 0 | 35 | 0 | 0 | refused |
| `kotoba/compiler/frontend/row.cljk` | 563 | 19 | 0 | 0 | 18 | 1 | 0 | refused |
| `kotoba/compiler/value_type.cljk` | 371 | 56 | 56 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/schema.cljk` | 225 | 25 | 22 | 0 | 0 | 2 | 1 | OK |
| `kotoba/sema.cljk` | 116 | 23 | 0 | 0 | 23 | 0 | 0 | refused |
| `kotoba/mir.cljk` | 7717 | 494 | 396 | 0 | 0 | 98 | 0 | OK |
| `kotoba/kir.cljk` | 6134 | 201 | 0 | 0 | 201 | 0 | 0 | refused |
| `kotoba/kir/value.cljk` | 2871 | 152 | 56 | 0 | 0 | 96 | 0 | OK |
| `kotoba/gmir.cljk` | 2493 | 199 | 183 | 0 | 0 | 16 | 0 | OK |
| `kotoba/kir/definition_identity.cljk` | 1127 | 85 | 47 | 0 | 0 | 38 | 0 | OK |
| `kotoba/kir/xml.cljk` | 1119 | 146 | 136 | 0 | 0 | 10 | 0 | OK |
| `kotoba/kir/alpha_normalization.cljk` | 932 | 106 | 100 | 0 | 0 | 6 | 0 | OK |
| `kotoba/hir.cljk` | 841 | 98 | 88 | 0 | 0 | 9 | 1 | OK |
| `kotoba/kir/decimal.cljk` | 625 | 103 | 102 | 0 | 0 | 1 | 0 | OK |
| `kotoba/form.cljk` | 459 | 102 | 102 | 0 | 0 | 0 | 0 | OK |
| `kotoba/kir/admission.cljk` | 402 | 33 | 33 | 0 | 0 | 0 | 0 | OK |
| `kotoba/kir/target.cljk` | 281 | 5 | 5 | 0 | 0 | 0 | 0 | OK |
| `kotoba/kir/iq_codebook.cljk` | 240 | 24 | 24 | 0 | 0 | 0 | 0 | OK |
| `kotoba/kir/compatibility.cljk` | 81 | 12 | 12 | 0 | 0 | 0 | 0 | OK |
| `kotoba/bytes.cljk` | 1249 | 56 | 56 | 0 | 0 | 0 | 0 | OK |
| `kotoba/lang/package_contract.cljk` | 1159 | 85 | 59 | 0 | 0 | 26 | 0 | OK |
| `json/core.cljk` | 986 | 66 | 42 | 0 | 0 | 24 | 0 | OK |
| `kotoba/lang/text.cljk` | 892 | 62 | 0 | 0 | 62 | 0 | 0 | refused |
| `multiformats/core.cljk` | 884 | 82 | 46 | 0 | 0 | 36 | 0 | OK |
| `cbor/core.cljk` | 828 | 81 | 58 | 0 | 0 | 23 | 0 | OK |
| `ed25519/core.cljk` | 691 | 64 | 34 | 0 | 0 | 30 | 0 | OK |
| `kotoba/lang/coll.cljk` | 542 | 40 | 0 | 0 | 40 | 0 | 0 | refused |
| `sha2/sha512.cljk` | 487 | 38 | 37 | 0 | 0 | 1 | 0 | OK |
| `x25519/field.cljk` | 431 | 30 | 24 | 0 | 0 | 6 | 0 | OK |
| `sha2/core.cljk` | 344 | 27 | 26 | 0 | 0 | 1 | 0 | OK |
| `ed25519/edwards.cljk` | 315 | 23 | 22 | 0 | 0 | 1 | 0 | OK |
| `kotoba/artifact/core.cljk` | 314 | 23 | 22 | 0 | 0 | 1 | 0 | OK |
| `ed25519/sign.cljk` | 267 | 21 | 18 | 0 | 0 | 3 | 0 | OK |
| `kotoba/bytes/sha256.cljk` | 231 | 33 | 33 | 0 | 0 | 0 | 0 | OK |
| `ed25519/scalar.cljk` | 206 | 15 | 15 | 0 | 0 | 0 | 0 | OK |
| `multiformats/base32.cljk` | 160 | 10 | 5 | 0 | 0 | 5 | 0 | OK |
| `clojure/set.kotoba` | 130 | 6 | 0 | 0 | 6 | 0 | 0 | refused |
| `clojure/string.kotoba` | 74 | 10 | 10 | 0 | 0 | 0 | 0 | OK |
| `kotoba/string.cljk` | 71 | 45 | 0 | 0 | 45 | 0 | 0 | refused |
| `kotoba/lang/json.cljk` | 21 | 3 | 3 | 0 | 0 | 0 | 0 | OK |
| `kotoba/native/machine_ir.cljk` | 10194 | 443 | 0 | 62 | 381 | 0 | 0 | refused |
| `kotoba/native/aarch64.cljk` | 1673 | 92 | 0 | 0 | 92 | 0 | 0 | refused |
| `kotoba/native/interrupt_abi.cljk` | 1580 | 102 | 99 | 0 | 0 | 3 | 0 | OK |
| `kotoba/native/document.cljk` | 1523 | 138 | 129 | 0 | 0 | 9 | 0 | OK |
| `kotoba/native/aggregate_abi.cljk` | 1244 | 127 | 117 | 0 | 0 | 10 | 0 | OK |
| `kotoba/native/vector_region.cljk` | 890 | 126 | 113 | 0 | 0 | 13 | 0 | OK |
| `kotoba/codegen/layout.cljk` | 736 | 46 | 32 | 0 | 0 | 14 | 0 | OK |
| `kotoba/native/string_index.cljk` | 674 | 102 | 92 | 0 | 0 | 10 | 0 | OK |
| `kotoba/codegen/mc.cljk` | 648 | 38 | 30 | 0 | 0 | 8 | 0 | OK |
| `kotoba/native/string_search.cljk` | 597 | 87 | 79 | 0 | 0 | 8 | 0 | OK |
| `kotoba/native/keyword_equality.cljk` | 525 | 71 | 67 | 0 | 0 | 4 | 0 | OK |
| `kotoba/native/image_scratch.cljk` | 74 | 6 | 6 | 0 | 0 | 0 | 0 | OK |
| `kotoba/native/peephole.cljk` | 58 | 1 | 1 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/nbb/package_lock.cljk` | 1120 | 83 | 62 | 0 | 0 | 21 | 0 | OK |
| `kotoba/compiler/nbb/verdict_cache.cljk` | 1013 | 84 | 42 | 0 | 0 | 42 | 0 | OK |
| `kotoba/compiler/nbb/cli.cljk` | 769 | 26 | 0 | 0 | 26 | 0 | 0 | refused |
| `kotoba/compiler/nbb/cli_support.cljk` | 627 | 52 | 12 | 0 | 0 | 36 | 4 | OK |
| `kotoba/compiler/nbb/io.cljk` | 450 | 27 | 27 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/nbb/compile_cache.cljk` | 368 | 32 | 18 | 0 | 0 | 14 | 0 | OK |
| `kotoba/compiler/nbb/project_source.cljk` | 275 | 10 | 3 | 0 | 0 | 7 | 0 | OK |
| `kotoba/compiler/nbb/host/fs.cljk` | 222 | 20 | 2 | 0 | 0 | 18 | 0 | OK |
| `kotoba/compiler/nbb/output_set.cljk` | 188 | 23 | 15 | 0 | 0 | 8 | 0 | OK |
| `kotoba/compiler/nbb/check_driver.cljk` | 119 | 6 | 0 | 0 | 6 | 0 | 0 | refused |
| `kotoba/compiler/nbb/host/process.cljk` | 109 | 7 | 1 | 0 | 0 | 6 | 0 | OK |
| `kotoba/compiler/nbb/fs_tree.cljk` | 98 | 11 | 11 | 0 | 0 | 0 | 0 | OK |
| `kotoba/compiler/nbb/refactor_cli.cljk` | 78 | 3 | 0 | 0 | 0 | 2 | 1 | OK |
| `kotoba/compiler/nbb/aarch64_cli.cljk` | 45 | 3 | 0 | 0 | 3 | 0 | 0 | refused |
| `kotoba/compiler/nbb/check_cli.cljk` | 22 | 1 | 0 | 0 | 1 | 0 | 0 | refused |
| `kotoba/compiler/project.cljk` | 1918 | 86 | 0 | 0 | 85 | 1 | 0 | refused |
| `kotoba/compiler/module_lock.cljk` | 291 | 17 | 1 | 0 | 0 | 16 | 0 | OK |
| `kotoba/compiler/project_files.cljk` | 186 | 12 | 0 | 0 | 12 | 0 | 0 | refused |
| `kotoba/compiler/source_path.cljk` | 184 | 9 | 8 | 0 | 0 | 1 | 0 | OK |
| `kotoba/compiler/refactor/rules/dynvars.cljk` | 406 | 20 | 0 | 0 | 20 | 0 | 0 | refused |
| `kotoba/compiler/refactor_cli.cljk` | 388 | 35 | 0 | 0 | 0 | 34 | 1 | OK |
| `kotoba/compiler/refactor/graph.cljk` | 294 | 18 | 0 | 0 | 18 | 0 | 0 | refused |
| `kotoba/compiler/refactor/partition.cljk` | 241 | 12 | 0 | 0 | 12 | 0 | 0 | refused |
| `kotoba/compiler/refactor/extract.cljk` | 237 | 16 | 0 | 0 | 16 | 0 | 0 | refused |
| `kotoba/compiler/refactor/rules/destructure.cljk` | 229 | 15 | 0 | 0 | 15 | 0 | 0 | refused |
| `kotoba/compiler/refactor/cst.cljk` | 225 | 34 | 0 | 0 | 34 | 0 | 0 | refused |
| `kotoba/compiler/refactor/rules/reject.cljk` | 205 | 11 | 0 | 0 | 11 | 0 | 0 | refused |
| `kotoba/compiler/refactor/diff.cljk` | 140 | 9 | 0 | 0 | 9 | 0 | 0 | refused |
| `kotoba/compiler/refactor/core.cljk` | 95 | 7 | 0 | 0 | 7 | 0 | 0 | refused |
| `kotoba/compiler/refactor/rules/lowerloops.cljk` | 85 | 6 | 0 | 0 | 6 | 0 | 0 | refused |
| `kotoba/compiler/refactor/verify.cljk` | 62 | 7 | 0 | 0 | 7 | 0 | 0 | refused |
| `kotoba/compiler/refactor/edit.cljk` | 61 | 10 | 0 | 0 | 10 | 0 | 0 | refused |
| `kotoba/compiler/refactor/rules/kwcallback.cljk` | 58 | 4 | 0 | 0 | 4 | 0 | 0 | refused |
| `kotoba/compiler/refactor/rules.cljk` | 50 | 4 | 0 | 0 | 4 | 0 | 0 | refused |
| `kotoba/compiler/refactor/rules/letdestructure.cljk` | 47 | 2 | 0 | 0 | 2 | 0 | 0 | refused |
| `kotoba/compiler/refactor/prelude.cljk` | 42 | 2 | 0 | 0 | 2 | 0 | 0 | refused |
| `kotoba/verifier.cljk` | 3455 | 143 | 0 | 1 | 142 | 0 | 0 | refused |
| `kotoba/security/crypto_policy.cljk` | 545 | 42 | 41 | 0 | 0 | 1 | 0 | OK |
| `kotoba/security/abac.cljk` | 258 | 25 | 20 | 0 | 0 | 5 | 0 | OK |
| `kotoba/security/information_flow.cljk` | 234 | 17 | 17 | 0 | 0 | 0 | 0 | OK |
| `kotoba/verifier/seal.kotoba` | 215 | 26 | 26 | 0 | 0 | 0 | 0 | OK |
| `kotoba/security/hardware.cljk` | 83 | 6 | 6 | 0 | 0 | 0 | 0 | OK |


## 3. Reading the baseline

1. **The frontend is the largest block and the one closest to done.** 20 modules, 48.2k lines, 3957 definitions:
   1735 REAL. `frontend/base`, `closure_types`, `expand`, `kernel_region`, `namespace_defs`, `validate`, `infer`,
   `affine`, `schema`, `validate_expr`, `value_type` and `frontend_tables` are admitted. Refused: the facade
   `frontend.cljk` and `analyze` and `record_projection`, `row` and `kotoba_reader` (the `[k _]` / `[k v]`
   destructuring wall in a dependency or in the module), `state_ability` (a `case` with unbounded constants) and
   `desugar`, which stops at "linked project exports exceed limit" (the project bound of 1024 exports, item C5 of
   the analysis; 591 definitions wait behind it). Seven refusals hold about 1.7k definitions, so moving them moves
   more than files OK shows.
2. **The native backend is the largest unported block.** `native/machine_ir` (443 definitions, 62 with a Kotoba arm,
   10.2k lines and growing under another owner) and `native/aarch64` (92, no arms) are plain host code. With
   `kir.cljk` (201, no arms) and `verifier.cljk` (143, one arm) that is about 880 definitions in four modules.
3. **The driver and the refactor library have no Kotoba reading.** `project` (85 unverified), `nbb/cli` (26), the
   refactor library (177 unverified, 35 nil) and `refactor-cli` (34 nil: on the Kotoba route it states a refusal).
   They are small next to the backend.
4. **1263 definitions are `nil`.** They are host-only branches (`#?(:clj ..)`, `#?(:kotoba nil ..)`). For the
   self-build each is replaced by an ability (the `nbb/host/*` seams), ported, or refused by name. The count is
   the size of that decision, not of a deficit: 493 are in the frontend, mostly the host mechanism the Form
   rewrite replaced.
5. **Leaf libraries are mostly done** (`lang`, `io`, `bytes`, `edn`, `crypto`: 510 REAL of 820). Three of them,
   `lang/coll`, `lang/text` and `string` (147 definitions), are refused for a template or `set` operation and are the
   highest fan-in leaf work on the list.

The metric to report each wave is the TOTAL line of `ledger.sh` (REAL / defs and REAL host lines / lines), with the
module admission count beside it as a diagnostic. A wave that raises files OK without raising REAL has moved a
dependency, not the work.

## 4. What this page does not do

- It does not port anything and does not rebuild the native-image checker (the central rebuild is scheduled; nothing
  here asked for one).
- It does not decide the 8 MiB value-size ADR, the frozen interpreter boundary or the verifier schedule; section 0
  records them as adopted.
- Entries other than `check_cli` and `aarch64_cli` (wasm, x86-64, trust, test, run, js, evm) are untouched and still
  work on nbb and the JVM; they are simply no longer on the path of the first self-build.
- `scripts/selfhost-wall/check-one.sh` still checks through `wasm_cli` (it needs only the HIR stage); the native
  checker's build entry is whatever `build-native.sh` names and was not changed.
