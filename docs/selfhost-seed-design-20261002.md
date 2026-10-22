# Selfhost from a small seed, aimed at Embench (design, 2026-10-02)

Owner decision (2026-10-02): next to porting the 136k-line host compiler onto the Form record
(`docs/selfhost-core-rewrite-plan-20260930.md`, `docs/selfhost-efficiency-analysis-20261002.md`), build a
**seed compiler** in Kotoba that (1) compiles the 19 Embench ports in `bench/embench/ports/` to aarch64-macos code
whose `test-*` export returns 1, and (2) compiles its own source to byte-identical output (fixed point). Embench is
then measured on a selfhost-built compiler with no node, JVM or nbb process (rules 2, 4, 8, 11 of
`docs/selfhost-priority.md`). The seed then grows rung by rung.

The efficiency analysis rejected option (c), "a new subset compiler", because it would add a third semantics to keep
identical (section 2). This design handles that risk as follows. The seed accepts a **sound subset**: anything
outside it is refused by name, never guessed. Every accepted program is checked against stage-0 by running it
(results must be equal), not by comparing bytes. And the seed does not replace the big compiler's semantics until
rung R6.

Everything below was measured with greps and short scripts on this tree, osaho `wt-D-osaho`, kotoba-native
`wt-D-kotoba-native` and kotoba-lang `lang/conformance`. Line counts are estimates where marked "est.".

## 0. Summary

| question | answer |
|---|---|
| What the 19 ports use | 1111 lines / 104 KB in total, 157 functions, 37 heads (8 definition and binding forms, 29 operations). Types are `:i64`, `:bool`, `:string`, `:vector-i64` only. No f64, records, maps, keywords-as-values, closures, effects or modules (section 1.1) |
| Seed-E (ports) vs Seed-C (the seed's own source) | Not the same. Seed-C = Seed-E plus 6 items: mutual recursion, `typed-cap-call` (3 wires), `bytes-from-vector-i64`, `string-concat`, an arity-0 `main` command entry, and `cond` sugar. **R0 = Seed-E ∪ Seed-C = "Seed-0", 41 heads** (section 1.3) |
| IR | Not KIR-as-Forms: measured cost is 3.4M vectors and 16M pairs for a 28 KB KIR program (kotoba-native ADR 0089). Instead a flat **stack IR (SIR)** stored in one i64 heap. KIR stays the semantic reference and a later interchange format (section 2.2) |
| Data | One preallocated `:vector-i64` heap `M` (8M words, 64 MiB), mutated with `vector-assoc!`, plus the source `:string`. No Forms and no GC. Estimate: about 15 MB live for self-compile, against 16-30 GB for the Form pipeline (3f496aefd) (section 2.3) |
| Size | about 5.0k lines of Kotoba in 12 files, plus about 1.5k lines of test corpus and 300 lines of bash (est.) |
| Stage-0 | `build/native-image/amu-native` (bootstrap-reference). It compiles a test module today (0.33 s, 51 MB RSS) |
| Fixed point | seed-0 (built by stage-0) builds seed-1; seed-1 builds seed-2; require `seed-1.bin == seed-2.bin`, and seed-0 and seed-1 give identical outputs on every port and corpus program (section 3) |
| First Embench | `run_native_qualification.py` unchanged, with `--compiler` set to the seed-1 command (loader + seed-1 code, built with `-DKEXE_EMBEDDED`) and `--runner kexe-benchmark` (section 3.4) |
| ETA (est.) | R0 (first Embench on a self-built compiler): **4-7 days** with 6-7 agents. Seed compiles the big compiler's Kotoba reading (R6): 6-10 weeks. Seed *replaces* the big compiler: 3-5 months, and not recommended as a goal (section 5) |

## 1. Language subset census

### 1.1 Feature x port matrix (Seed-E)

Columns are ports (aha=aha-mont64, crc, dep=depthconv, edn, huf=huffbench, mat=matmult-int, md5=md5sum,
aes=nettle-aes, sha=nettle-sha256, nsi=nsichneu, pjp=picojpeg, qrd=qrduino, sgl=sglib-combined, slr=slre,
stm=statemate, tar=tarfind, ud, wks=wikisort, xgb=xgboost). The matrix was produced by a regex scan with comments
stripped. "self-rec" was checked with a balanced-paren parser.

| feature | aha | crc | dep | edn | huf | mat | md5 | aes | sha | nsi | pjp | qrd | sgl | slr | stm | tar | ud | wks | xgb | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ns` + `:export`, `defn`/`defn-` | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | 19 |
| `+ - *` (i64 wrap) | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | 19 |
| `quot` | . | . | x | x | . | x | . | . | . | x | x | . | . | . | x | x | x | x | x | 10 |
| `= <` | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | 19 |
| `> <= >=` | . | . | x | x | . | . | . | x | . | x | x | x | x | . | . | . | x | x | x | 10 |
| `and or not` | x | . | x | . | . | . | x | . | x | . | . | . | . | x | . | x | x | x | x | 9 |
| `bit-and/or/xor` | x | x | x | x | x | . | x | x | x | x | x | x | . | . | . | x | . | x | x | 14 |
| `bit-not` | . | x | . | . | . | . | x | . | x | . | . | . | . | . | . | . | . | . | . | 3 |
| `u64-shift-right` | x | x | x | . | x | . | x | x | x | x | . | x | . | . | . | x | . | x | x | 12 |
| `i64-shift-left` | x | . | x | . | . | . | x | . | x | . | . | . | . | . | . | . | . | . | x | 5 |
| `i64-shift-right` | x | . | x | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | 2 |
| `let` | x | x | x | . | x | x | x | x | x | x | x | . | x | x | . | x | x | x | x | 16 |
| `loop`/`recur` | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | 19 |
| `loop` as a value (not tail) | . | . | x | . | . | . | x | . | x | . | . | . | . | . | . | . | x | . | . | 4 |
| self-recursion outside `loop` | . | . | . | . | . | . | . | . | . | . | . | . | x | . | . | . | . | x | . | 2 |
| vector literal `[1 2 ..]` | . | x | x | x | . | x | x | x | x | . | . | x | . | . | . | . | x | x | . | 10 |
| `vector-at` | x | x | x | x | . | x | x | x | x | . | . | x | x | . | . | x | x | x | x | 14 |
| `vector-conj` | . | . | . | . | . | x | x | . | x | . | . | . | . | . | . | x | x | . | . | 5 |
| `vector-assoc` | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | x | . | . | 1 |
| `vector-assoc!`, `vector-alloc` | . | . | . | . | . | . | . | . | . | . | . | . | x | . | . | . | . | x | . | 2 |
| top-level `def` (string/vector const) | . | . | x | . | . | . | . | . | . | . | . | . | . | x | . | . | . | . | x | 3 |
| string literal (all ASCII) | . | . | x | . | . | . | . | . | . | . | . | . | . | x | . | . | . | . | x | 3 |
| `string-code-point-at` | . | . | x | . | . | . | . | . | . | . | . | . | . | x | . | . | . | . | x | 3 |
| `string-length` | . | . | . | . | . | . | . | . | . | . | . | . | . | x | . | . | . | . | . | 1 |
| `:bool` result type | x | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | 1 |
| `:vector-i64` param/result | x | . | . | . | . | x | x | . | x | . | . | . | x | . | . | x | x | x | . | 8 |
| `:string` param | . | . | x | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . | x | 2 |
| integer literal >= 2^31 (incl. -2^63) | x | x | x | x | x | . | x | x | x | . | x | . | . | . | . | x | . | x | . | 11 |

Shape limits seen in the ports: at most **5 parameters** (md5sum, xgboost), at most 10 loop bindings (ud), longest
vector literal 64 items, longest string literal 10,924 bytes (xgboost base64 data), deepest indentation 53 columns
(sha256). None of these appear anywhere in the 19 ports: f64, `fn`, `do`, `when`, `cond`, `case`, keywords as
values, maps or sets, records, options/results, `try`/`throw`, effects, atoms, `:require`, or `string=?`/concat.

### 1.2 Seed-E: the minimal union (37 heads + 4 types)

`ns :export defn defn- def let loop recur if and or not = < > <= >= + - * quot bit-and bit-or bit-xor bit-not
u64-shift-right i64-shift-left i64-shift-right vector-at vector-conj vector-assoc vector-assoc! vector-alloc
string-code-point-at string-length` over the types `:i64 :bool :string :vector-i64`. Literals: i64 (full 64-bit
range), ASCII strings, vector literals of i64 expressions.

The semantics that must match stage-0 exactly (the oracle is the reference native backend; `kir/interp.cljk` op
codes 15-18 for the bit and shift ops):
- `+ - *` wrap modulo 2^64.
- `quot` truncates toward zero and **traps** (`brk`) when the divisor is 0 or on MIN/-1 (`aarch64.cljk`
  `signed-division`).
- Shift counts follow kotoba.kir. The `sem` owner pins them with edge tests first.
- `vector-at` out of range traps (SIGILL).
- `string-code-point-at` takes a byte offset (the loader's `checked_string_code_point_at`). It equals the code-point
  index only for ASCII, so R0 refuses non-ASCII literals by name.
- Fuel: one unit on entry to every function whose body contains a call, runtime call or capability call, and one
  unit per `recur`. This is the rule of `machine-ir/entry-fuel-prefixes` with loop helpers, and it keeps xgboost
  under the runner's 16,777,216 fuel.

### 1.3 Seed-C: what the seed's own source needs

The seed is a compiler written "C-style": one flat i64 heap plus the source string (section 2.3). It needs:

| need | how the seed source expresses it | in Seed-E? | R0 adds (seed lines, est.) |
|---|---|---|---|
| arrays, tables, AST, code buffer | `vector-alloc`, `vector-assoc!`, `vector-at` on one heap `M` | yes | 0 |
| hashing and interning names | i64 arithmetic over `string-code-point-at` | yes | 0 |
| recursive descent and the type walk | mutually recursive `defn`s (forward references) | **no** (ports self-recurse only) | call by symbol index, ~30 |
| read the input file and argv | `typed-cap-call :fs/app-data :string :string path` (wire 35), `:cli/args` (wire 38, index as the literals "0".."9") | **no** | context slot `typed_cap_call` + kind table, ~120 |
| write the code bytes | build in `M`, `bytes-from-vector-i64`, `typed-cap-call :fs/app-data :bytes :bytes "<path>WRITE_SEP<code>"` (kind 8) | **no** | ABI v11 `bytes_from_vector` slot, ~40 |
| diagnostics on stderr | `:io/write-error` (wire 39), with `string-concat` of literal pieces and digits | **no** | `string_concat` slot, ~20 |
| command entry | arity-0 `main` returning the exit status (loader command mode) | no (exports take a token) | ~30 |
| readable dispatch over 41 heads | `cond` with a mandatory `:else`, desugared to nested `if` | no | ~40 |
| at most 5 parameters, no `do`, effects sequenced by `let [_ (vector-assoc! ..)]` | the wikisort style | yes | 0 |

**Answer: not the same subset.** Seed-C is Seed-E plus 6 items, about 280 seed lines. They cannot be deferred to
a later rung, because the fixed point needs the seed to compile itself. So **R0's language is Seed-0 = Seed-E ∪
Seed-C: 41 heads (the 37 of Seed-E plus `typed-cap-call`, `bytes-from-vector-i64`, `string-concat`, `cond`), 4 types, 3 capability wires (35, 38, 39)**. Everything else is refused by name with the head and
the byte offset. Stage-0 already compiles all of Seed-0 natively: the guest wrappers in `guest-run.sh` use
`typed-cap-call`, and the context slots exist in ABI v11.

Conformance fit (scan of `lang/conformance/*/*.kotoba`, 55 programs): **1 of 55** (`entry_extensions/main`) lies
inside Seed-E. The rest use `get`, `fn`, `try`/`catch`, `perform`/`handle` (8 each), `pair`, `nth`, `atom`, ...
For R0 the conformance corpus is therefore a **refusal** gate: 54 programs must be refused by name. It becomes an
acceptance gate from R1 on.

### 1.4 Rung ladder

Each rung's compiler compiles the next rung's source. The new source uses the new features, so the rung proves
itself. Every rung ends with the fixed point and the gates of the previous rungs.

| rung | adds | gate (all must pass, scripted) |
|---|---|---|
| **R0** | Seed-0 (sections 1.2-1.3). Stack IR, depth-indexed temporaries, C runtime calls for vector and string ops | (G1) 19 ports: `test-*` = 1 under `kexe-benchmark` with fuel 16M. (G2) `seed/tests/corpus`, about 80 edge programs (wrap, quot traps, shifts, MIN literal, 10-binding loops, loop as a value, deep nesting, long literals): result equal to stage-0's on every case. (G3) refusal: 54 conformance programs and 30 seed negatives refused, with golden reason text. (G4) fixed point `seed-1.bin == seed-2.bin`, and seed-0 and seed-1 outputs byte-identical on G1+G2. (G5) `no-host-processes.sh` clean on `seed-1 compile` |
| R1 | sugar and enums: `do`, `when`, `cond`, `case` on i64/keywords, `->`/`->>`, `dotimes`/`doseq` over ranges and vectors, keywords as interned i64, **flat records** (`:record` schemas, pair-chain ABI as stage-0 lowers them) | R0 gates + conformance `control/` (9), `records/` (1), `values/` (1) accepted with results equal to stage-0. Seed source rewritten to use records and `case` |
| R2 | performance, no new language: inline `vector-at`/`vector-assoc!`/`pair-*` through ABI v9 pointers (offsets 288-328), linear-scan allocation over SIR temporaries, constant folding, counted-loop fuel prepay | R0-R1 gates + Embench execute medians within 1.5x of the 2026-09-29 bootstrap-reference, and code bytes within 1.5x |
| R3 | values: options/results, `try`/`throw`/abort, typed lists `[:list T]`, typed maps and sets, full strings (`string=?`, substring, from-i64, non-ASCII) | conformance `abort/` (9), `collections/` (7), `stdlib/` (9) |
| R4 | functions: `fn` (non-escaping first, then closures), multi-arity, `invoke`, `map`/`filter`/`reduce` over typed lists | conformance `functions/` (7) |
| R5 | modules and effects: `ns :require`, qualified names, exports, `perform`/`handle`/`defhandler`, `atom`/`swap!`, local state, capability policy | conformance `namespace_priority/`, `entry_extensions/`, `state/`, `local-state/`, `reader_target/` (23). Compiles `kotoba-lang lang/compat/kotoba/{string,edn,walk}` |
| R6 | Forms: `:form/r` schemas and the `kotoba.form` ops, `:document` ops, `#?(:kotoba ..)` reading. **Convergence point**: the seed compiles the big compiler's Kotoba reading module by module (126 modules, `docs/selfhost-minimal-reach-20261002.md`) | per module: the seed-built native guest agrees with the stage-0-built guest on the existing differentials (vx, ds, abort, mir, machine-ir corpora) |
| R7 | (optional) the seed's frontend and backend *are* amu's: full checker rules (757 `reject!` sites), definition CIDs, `check`/`refactor`/`compile` driver | rule 11 on the seed lineage |

## 2. Architecture

### 2.1 Pipeline and components

`source :string` -> **lex** -> tokens -> **read** -> node tree -> **names** + **check** -> typed tree -> **lower**
-> SIR -> **a64gen** (using **a64enc**) -> code words + fixups -> **layout** -> code bytes + export table ->
**out** (kseed container) -> **driver** (CLI). All of it lives in `seed/src/*.kotoba`, one owner per file. A
**unity build** joins the files in manifest order into `build/seed-unity.kotoba`, under one `ns` from `00-ns`. Names
are prefixed by module (`lx-`, `rd-`, ...), so R0 needs no multi-module linker, and stage-0 compiles one file.

| # | file | interface: exported fns (all take `M :vector-i64` first; i64 in and out) | lines (est.) | reuses (as spec or oracle, not code) | intentionally NOT reproduced |
|---|---|---|---|---|---|
| 00 | `00-ns.kotoba` (driver) | `main [] :i64`; `drv-check`, `drv-compile`, `drv-extract` | 180 | CLI shapes of `nbb/cli.cljk` (`check`, `compile --target --output`, `extract-native --symbol --output` printing `:offset N`) | kexe/v1 sealing, policy files, verdict cache, `--json` definition CIDs, other targets (refused by name) |
| 01 | `01-mem.kotoba` | `mem-new`, `mem-alloc M words`, `mem-vec-push`, `mem-hash`, `mem-u2dec` (i64 to decimal string), the byte-buffer helpers | 250 | the loader's `KEXE_VECTOR_ITEM_LIMIT` (16M per vector) | any collector or arena reset |
| 02 | `02-io.kotoba` | `io-read-file M path`, `io-argc`, `io-arg i`, `io-write-bytes M path base len`, `io-err msg` | 150 | wires 35/38/39 as documented in `tools/kexe_loader.c` (`fs_app_data_dispatch`, `:cli/args`) | other capabilities |
| 10 | `10-lex.kotoba` | `lx-run M S` -> token count. Token record: kind, start, end, value | 450 | the reader rules of `kotoba_reader` for the subset | `#?`, `#{}`, `#"`, tagged literals, ratios, chars (refused by name) |
| 11 | `11-read.kotoba` | `rd-run M S` -> root node. Node record: kind, first child, next sibling, token, aux | 350 | none | metadata, reader conditionals |
| 20 | `20-names.kotoba` | `nm-intern M S start end` -> symbol id; `nm-builtin id` -> head code or 0; scope push and pop | 350 | the head list of section 1.2 | namespaces, aliases, `:refer` |
| 21 | `21-check.kotoba` | `ck-run M S` -> 0 or error code; writes a type per node and a slot per local | 800 | `kir/lowering.cljk` validation rules (loop-helper `recur` only in tail position, `let` and `if` shapes); arity and type rules for the 41 heads | effects/abilities, inference beyond the 4 types, the 757 `reject!` sites of the big frontend (the seed's refusals are its own, subset-only) |
| 30 | `30-lower.kotoba` | `lw-run M` -> SIR length. Plus the test-only `lw-interp M fn args` (SIR interpreter, about 200 lines) | 700 | KIR core-form meaning (`kir.cljk` `lower`): one SIR function per `defn`, `loop` inlined as a block | KIR as Forms, oracle sealing, the KIR interpreter, alpha normalization, descriptors |
| 40 | `40-a64enc.kotoba` | about 45 pure `enc-*` fns -> 32-bit word (`add/sub/mul/sdiv/and/orr/eor/mvn/lsl/lsr/asr` reg forms, `movz/movk/movn`, `cmp/cset`, `ldr/str` imm, `stp/ldp` pre/post, `b`, `b.cond`, `cbz/cbnz`, `bl`, `blr`, `ret`, `adr`, `brk`) | 450 | the bit patterns of `kotoba-native aarch64.cljk` (`insn`, `movz`/`movk`, `sub-sp`, `b-cond`, ...) and the machine_ir a64 encoders | x86-64, peephole, kernel windows |
| 41 | `41-a64gen.kotoba` | `gn-run M` -> words. Frame, temporaries, calls, runtime slots, fuel, string literals, `typed-cap-call` | 900 | the context ABI v11 (`bench/runtime-comparison/kexe-benchmark.c` struct, offsets asserted), the fuel sequence of `aarch64.cljk` `fuel-charge` (`ldr x16,[x7,#8]; subs; b.hs; brk; str`), and the string literal as `data-address` + `pair_new(address, length)` (`machine_ir.cljk` `string-literal-value`) | GMIR/MIR/MC, SSA, coalescing, hoisting, string-index/search/document augmentation |
| 42 | `42-layout.kotoba` | `ly-run M` -> code length. Two-pass label resolution (b imm26, b.cond/cbz imm19, adr imm21), literal pool after the last function, export offsets | 250 | the algorithm of `codegen/layout.cljk` (`label-offsets`, `resolve-tokens`), rewritten over `M` (its Kotoba twin is `:document`-typed, and ADR 0089 repeats it over Forms) | relocations, object formats |
| 50 | `50-out.kotoba` | `out-write M path`, `out-extract M kseed symbol path` -> offset | 200 | the `extract-native` result shape | `:kotoba.kexe/v1` (it carries KIR that the reference verifier re-emits with the big backend, so seed code would be refused), sha sealing, provenance |
| | **total** | | **about 5,030** | | |

Test-only, outside the unity build: `seed/tests/corpus/*.kotoba` (about 80 programs, about 1.5k lines),
`seed/tests/unit/<mod>_t.kotoba`, `seed/tests/neg/*.kotoba` (30), and `scripts/seed/{build-stage,fixed-point,gates,
embench}.sh` (bash, about 300 lines).

### 2.2 IR decision: a stack IR, not KIR

| option | cost for self-compile (about 220 KB of seed source) | verdict |
|---|---|---|
| KIR as `:form/r` Forms (reuse `kir.cljk` and `kir/lowering.cljk` directly) | ADR 0089 measured 3.4M vectors and 16M pairs for a 28 KB KIR program, about 0.6M pairs per KB. The seed's KIR would be about 0.5-1 MB, so 300-600M pairs, over `KEXE_PAIR_MAX` (64M) | **rejected for R0** |
| KIR text as an interchange format (`--emit-kir`, and later a KIR text reader) | a printer of about 200 lines (R1) and a reader of about 400 (R5) | **adopt later.** Uses: a differential against stage-0's `:program` on the ports, and convergence (section 5.2) |
| SIR: flat stack IR in `M`, 4 words per instruction | about 1.3 words per source byte | **adopt for R0** |

SIR instructions (opcode, a, b, c): `CONST t k`, `LGET t slot`, `LSET slot t`, `BIN op t` (operands t and t+1,
result t), `CMP cc t`, `NOT t`, `LABEL l`, `BR l`, `BRZ t l`, `CALL f argbase n`, `RT slot argbase n`
(runtime call through the context), `CAP wire kind t`, `STR t lit`, `VEC t n` (alloc + assoc), `FUEL`, `RET t`,
`FN f nparams nslots`. `t` is the **expression depth**, so the temporary index equals the operand-stack height.
Loop variables are frame slots, and `recur` is `LSET`s, `FUEL` and `BR header`.

Register allocation, simplest correct approach (R0):
- Temporary depth k maps to `x9+k` for k < 7 (x9-x15, caller-saved). Depth 7 and up spill to frame slots. The
  deepest operand stack in the ports is below 7. Expression nesting is mostly `let`/`if`, which uses slots, not
  depth.
- Every parameter, `let` binding and loop variable gets a frame slot `[fp, #16+8i]`. Slots are reused after their
  scope ends.
- The context pointer arrives in x7 and is saved to slot 0. A guest call reloads `x7` from it. A runtime call
  passes the context as x0, because the helpers are C functions `(ctx, a, b, c)`.
- Around any call, live temporaries below `argbase` are stored to spill slots and reloaded afterwards. Arguments go
  in x0-x4, at most 5, the same as the reference fuel ABI (`aarch64.cljk` `emit-function`). The result is in x0.
- Prologue: `stp fp,lr,[sp,#-16]!; mov fp,sp; sub sp,sp,#frame`. Then FUEL when the function has a call or a loop.
  Epilogue: the mirror image.

R2 replaces the depth mapping with linear scan over SIR temporaries. SIR does not change, so lower is untouched.

### 2.3 Data representation and memory budget

- **One heap `M`**: `vector-alloc 8388608` (64 MiB, under the 16M-item per-vector limit). It is mutated only by
  `vector-assoc!` (in place, `vector_assoc_in_place`). `M[0..255]` is the **memory map**: region bases and fill
  counters for tokens, nodes, symbols, the hash table, types, SIR, code, fixups, literals and exports. Each owner
  appends only to its own region. Record layouts are fixed offsets, so the memory map is the interface contract.
- Why not typed records or Forms: a `:vector-i64` handle cannot be stored in a `:vector-i64`. With at most 5
  parameters, separate arrays per table would not fit through the call signatures. A flat heap is the shape the
  native ABI handles best (no pairs, no vector-table entries per node). Forms cost 7 pairs plus a vector per node
  (ADR 0089).
- Budget for self-compile (est.): 220 KB of source gives about 50k tokens x 4 words, 50k nodes x 5, types and slots
  1 each, SIR about 75k x 4, code words about 120k, fixups and literals about 50k. That is **about 1.0-1.5M words
  (8-12 MB)**, plus about 50k pairs for symbol substrings and literals (0.8 MB). Compare (3f496aefd,
  `docs/selfhost-native-memory-20261002.md`): desugar alone keeps 616 B of heap per source byte, about 2 GB for the
  compiler and 16-30 GB for the whole Form pipeline. The seed's whole pipeline is about **50 B per source byte**,
  12x less than one Form pass. It fits one loader process with no reclamation. Loader budgets:
  `KEXE_EMBEDDED_VECTOR_ITEMS` at least 12M, `..._PAIRS` 1M, `..._CPU_SECONDS` 60.
- Strings: the source is one `:string` read through wire 35. Names are byte spans of it. R0 creates a string value
  only for diagnostics.

## 3. Bootstrapping protocol

### 3.1 Stages

| step | command (bash; no node/JVM after step 1) | output | check |
|---|---|---|---|
| 0 | `cat $(cat seed/MANIFEST) > build/seed-unity.kotoba` | unity source | its sha256 is recorded |
| 1 (bootstrap) | `amu-native compile build/seed-unity.kotoba --target aarch64-macos --output build/seed-0.kexe` (compile-time grant 35,38,39), then `amu-native extract-native build/seed-0.kexe --symbol main --output build/seed-0.bin` | seed-0.bin and the offset of `main` | stage-0 sha256 recorded, **BOOTSTRAP-labelled** |
| 2 | `KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$PWD/build:$PWD/seed kexe-loader build/seed-0.bin $OFF 0 aarch64 35,38,39 -- compile build/seed-unity.kotoba --output build/seed-1.kseed` | seed-1 (the seed backend's bytes) | exit 0 |
| 3 | the same with seed-1 | seed-2 | **`cmp seed-1.bin seed-2.bin`** (G4) |
| 4 | seed-0 and seed-1 each compile G1+G2 | 2 x 99 outputs | byte-identical pairwise (G4) |
| 5 | `xxd -i seed-1.bin > build/seed_code.h; cc -O2 -DKEXE_EMBEDDED -DKEXE_EMBEDDED_OFFSET=.. -DKEXE_EMBEDDED_ALLOW=.. -DKEXE_EMBEDDED_SCOPE=.. tools/kexe_loader.c -o build/seed` | the `seed` Mach-O command | `otool -L`: libSystem only |

Notes:
- **The loader is used two ways, both unchanged**: plain command mode (`KEXE_COMMAND=1`, guest argv after `--`)
  for steps 2-4, and the packaged command (`KEXE_EMBEDDED`, arity-0 entry, argv through wire 38) for the measured
  binary. The C loader as the runtime of the "amu binary" for milestone 1 is an owner decision already in force
  (minimal-reach section 0, item 2).
- **kseed/v1 container** (written by `out`): an ASCII header line `KSEED1 <code-length> <n-exports>`, then
  `<name> <offset> <arity>` lines, `\n\n`, then the raw code with its literal pool. `extract-native` writes the
  code slice and prints `{:ok true :symbol S :offset N :arity A}`. That is the shape the runner's regex reads.
- **Determinism**: no hash-iteration order reaches the output (symbol ids follow first occurrence, the hash table
  is used only for lookup), no clock, no environment.
- **Trusting trust**: seed-0 comes from a JVM-built compiler. The cheap mitigation is diverse double compiling.
  Build seed-0' through a second stage-0 (the nbb route of `bin/amu`, or a stage-0 at another commit) and require
  that seed-1' == seed-1.

### 3.2 Zero node/JVM/nbb at runtime

After step 1, the chain runs only `kexe-loader` (C, built once with `cc`), the seed guest, `cmp`, `xxd` and `cc`.
`scripts/selfhost-wall/no-host-processes.sh -- build/seed compile bench/embench/ports/crc32.kotoba --output
/tmp/c.kseed` must report one exec (the seed itself), and likewise for `build/seed compile build/seed-unity.kotoba`.
The seed spawns nothing; wire 20 is not granted. Python (the qualification runner) and stage-0 are BOOTSTRAP-TOOL.
They are never in the compiler's process tree.

### 3.3 What counts, and the label

The Embench numbers come from a compiler whose bytes were produced by itself (`seed-1.bin == seed-2.bin`), so they
are a **selfhost-built** result under rule 2. They are labelled **"seed R0 (selfhost-built subset compiler)"**, not
"amu". The `amu` rule-11 claim (check/refactor/compile of amu's own sources) is unchanged and still open.

### 3.4 First Embench measurement

`python3 bench/embench/run_native_qualification.py --compiler build/seed --runner kexe-benchmark --upstream
<embench-iot@09c2ed8c> --output <dir>`, on a quiet host (rule 4). The runner needs no change because the seed CLI
answers `check <f> --jvm-free`, `compile <f> --target aarch64-macos --jvm-free --output X` and `extract-native X
--symbol S --output R` (printing `:offset N`). The empty `PATH` and the `otool -L` check apply as before. A
10-line addition records `seed-1.bin` sha256, the fixed-point proof (`seed-2.bin` sha256), the unity source sha256
and the stage-0 sha256 in `qualification.json`. The report goes in `bench/embench/REPORT-<date>-seed-r0.md`, with
the 2026-09-29 bootstrap-reference columns beside it (check ms, compile ms, execute, raw code bytes). Expected
(est.): compile 2-20 ms per port (no JVM image start, about 100 KB of input), execute 1.5-3x slower than the
reference (no register allocation or inlining in R0), raw code 1.5-2.5x larger. R2 closes that gap.

## 4. Parallel work plan

### 4.1 Contracts (day 0, one strong agent, before anyone codes)

1. `seed/MEMORY-MAP` (an EDN table in the repo): the `M[0..255]` header slots, each region's record layout, and
   each owner's write rights.
2. Head codes 1..41 and type codes (`i64=1 bool=2 string=3 vec=4`), plus the error code table
   (`E<module><nn>` -> golden text).
3. The SIR opcode table (section 2.2) and the a64gen register and frame conventions.
4. `seed/MANIFEST` (unity order) and the module-prefix rule.
5. The test harness: `scripts/seed/unit.sh <mod>` concatenates MANIFEST-prefix + module + `tests/unit/<mod>_t`,
   compiles with stage-0, runs under the loader, and diffs against `tests/unit/<mod>.expected`.

### 4.2 Modules

| module | owner (model) | depends on (contract only) | isolated test | agent-hours / output tokens (est.) |
|---|---|---|---|---|
| contracts + `00-ns` driver + integration | **strong** (Opus) | all | end-to-end G1-G5 | 6 + 6 h / 150k |
| `01-mem`, `02-io` | mid (Sonnet) | memory map | unit: hash vectors, growth, decimal; io round-trip of 256 distinct bytes through WRITE_SEP and back | 3 h / 60k |
| `10-lex` | mid | memory map, token layout | token dump of the 19 ports and the corpus = golden (golden made by a 60-line Python BOOTSTRAP-TOOL) | 3 h / 70k |
| `11-read` | mid | token layout | `print(read(src))` = whitespace-canonical source for the ports | 2.5 h / 50k |
| `20-names` | mid | node layout | intern and scope tests; collision test with 50k synthetic names | 2.5 h / 50k |
| `21-check` | **strong** | names, node layout | accepts 19 ports + corpus + its own unity source; refuses 54 conformance + 30 negatives with golden reasons | 6 h / 140k |
| `30-lower` (+ SIR interpreter) | mid-strong | checked-tree layout, SIR table | SIR dump goldens. **The SIR interpreter runs all 19 ports to `test-*` = 1 before any backend exists** | 5 h / 120k |
| `40-a64enc` | mid | none | about 300 (form, operands) -> word vectors, oracle from `clang -c` + `otool -t` on a generated `.s` (system tools) | 2.5 h / 60k |
| `41-a64gen` | **strong** | SIR table, enc, ABI v11 | hand-written SIR fixtures (calls, spills, loops, runtime calls, string literal, cap call) run under `kexe-benchmark`/loader with expected results | 8 h / 180k |
| `42-layout` | mid | code and fixup layout | synthetic fixups at the imm19/imm26 boundaries; literal pool alignment | 2 h / 40k |
| `50-out` | cheap-mid | layout's export table | container round-trip; extract offset = header offset | 1.5 h / 30k |
| corpus + negatives + refusal goldens | cheap (Haiku) | head table | each corpus program compiled by stage-0, its result recorded as `.expected` | 3 h / 60k |

Total about 58 agent-hours and about 1.0M output tokens (est., from the frontend port's rate of about 400 host lines
per agent-hour, discounted to about 150 new lines per hour with tests). Concurrency follows the efficiency
analysis's rules: one writer per file, stage-0 compiles at most 2 at a time, no sweep waves.

### 4.3 Critical path

```
day 0    contracts (strong)            + risk tests T1-T3 (section 6)
day 1-2  lex -> read -> names -> check     |  enc -> a64gen     |  mem, io, layout, out, corpus
         lower (+SIR interp: ports green on SIR)                |
day 3    integration: unity build by stage-0 = seed-0; G1 on seed-0 (ports via seed-0)
day 4    seed-1, seed-2, fixed point G4; refusal G3; no-host G5
day 5    package, Embench run on a quiet host, report              (+2-3 days risk tail)
```

Longest chain: contracts -> check (6 h) -> lower (5 h) -> integration -> fixed point. a64gen (8 h) runs in
parallel on SIR fixtures. Integration debugging is the usual 40-60% overhead (efficiency analysis, section 3.3).

## 5. Comparison with the port-the-host-compiler path

### 5.1 Side by side

| | port path (Form rewrite of 122.7k lines) | seed path |
|---|---|---|
| what it yields first | the real `amu` self-built (rule 11) | a self-built *subset* compiler that runs Embench |
| code to write | about 28k host lines left on the pruned set (efficiency analysis, section 1.4) | about 5k new lines |
| memory at self-compile | 16-30 GB in one process; needs process-per-pass (+2-4 days) | about 15 MB in one process |
| ETA, first selfhost-built Embench | at S5 only: 9-15 days + 3-7 risk (analysis), so realistically 2-4 weeks | **4-7 days** |
| ETA, rule 11 (amu check/refactor/compile itself) | 9-22 days | not addressed by R0-R5. R6: 6-10 weeks. R7: 3-5 months |
| semantic risk | one semantics (the host's, ported) | a third semantics. Mitigated by the subset refusals, result differentials against stage-0, and the frozen rung gates |
| failure mode | slow convergence, memory wall at S5 | the subset never grows enough to matter beyond Embench |
| value if the other path wins | none lost | an independent oracle (DDC for the big compiler's S5), a 15 MB backend, and Embench evidence weeks earlier |

### 5.2 Convergence plan

1. **Shared now**: `tools/kexe_loader.c`, `kexe-benchmark.c`, the context ABI v11, the capability wire table, the
   conformance corpus, the qualification runner and the a64 encoding tables (the seed's `40-a64enc` test oracle
   checks the same words the big backend emits).
2. **R3-R5: the seed backend becomes a KIR consumer.** A KIR-text reader (about 400 lines) lets the big frontend's
   KIR (the kexe's `:program`) be compiled by the seed's lower/a64gen. That gives an alternative to
   `native/machine_ir` (15k lines, 220/392 definitions real, and 16M pairs per 28 KB KIR on the Kotoba route per
   ADR 0089). This is the most valuable merge point. The memory wall of the port path is mostly in
   machine_ir/mir, so swapping in the seed backend could remove most of it. The verifier's re-emission check would
   then re-emit with the seed backend (one owner decision).
3. **R6: the seed builds the big compiler** (it compiles the Kotoba reading of the 126 modules), replacing the JVM
   stage-0 permanently. From then on stage-0 is a regression reference only.
4. Recommendation: **do not aim at R7** ("seed replaces the big compiler") until R2 and the merge in step 2 are
   measured. The better end state is one compiler, made of the ported frontend and the seed-lineage backend, built
   by itself.

## 6. The riskiest assumptions, each with a cheap test

| # | assumption | why it could fail | cheap test (time) | if it fails |
|---|---|---|---|---|
| T1 | Stage-0 compiles a single 5-6k-line i64/vector module natively, in bounded time and RSS | Every port is under 110 lines, and the 2026-09-29 compile times grow with code (matmult, 103 lines: 658 ms). A super-linear pass in the big backend (`mir` select/allocate) could take minutes or GBs at 50x | concatenate the 19 ports 40x with renamed functions (about 4.4k lines, 157x40 fns) and run `/usr/bin/time -l amu-native compile` on one core (15 min) | split the unity file into 4-6 modules (needs R5's `:require` in the seed earlier) or lift the specific pass |
| T2 | An independent emitter can meet the runtime ABI: context in x7 and runtime helpers through slots, `pair_new` for string literals over `code_base`, fuel at `[x7,#8]`, `typed_cap_call` kinds 1 and 8, `bytes_from_vector` | The ABI is documented by code, not by spec. Several slots are NULL in `kexe-benchmark` (cap_call, bytes): **a port must not need them, and none does** | hand-encode 3 functions (vector_alloc/assoc!/at; a string literal with code_point_at; a FUEL loop) as words (a 40-line BOOTSTRAP-TOOL script), run them under `kexe-benchmark raw` and `kexe-loader` (2 h) | read the missing contract from `machine_ir.cljk` and record it in the memory-map doc |
| T3 | A guest can read a file, read argv and write arbitrary bytes up to 8 MiB through wire 35 `:bytes` WRITE_SEP in command and embedded mode, and stage-0 admits `typed-cap-call :fs/app-data :bytes :bytes` | the native gate admits only some kind pairs. The embedded-mode scope and budget macros are untested for a compiler-sized output | a 25-line Kotoba program compiled by stage-0 that copies a 1 MB binary file through `M`; `cmp` (30 min) | emit hex on `:io/write` and decode with `xxd -r -p` (a system tool), at the cost of one more process in the chain |
| T4 | Seed-C (the flat-heap style) is writable by agents at about 150 lines per hour, and self-compile stays under 64 MiB and 2 s | i64-only code is error-prone (index confusion), and per-access C calls for `vector-at` in R0 code | after `10-lex` + `11-read` land: stage-0-build them, read the seed's own unity source with `KEXE_ARENA_USE=1`, and fit words per source byte (1 h) | allow `:record` types in the seed earlier (R1 features into R0), or inline `vector-at` in R0 |
| T5 | Seed code matches stage-0 semantics on the subset, including fuel consumption (xgboost runs 1.9 s under the 16M fuel cap) | shift-count edges, `quot` traps, `string-length` on non-ASCII, and fuel counting per entry/`recur` that differs from `entry-fuel-prefixes` + counted prepay | (a) record stage-0 results on 80 edge programs now (they become G2). (b) Binary-search the minimal passing fuel of each port on stage-0 output (19 x about 24 runs, about 10 min), record it, and require the seed's minimal fuel to be no greater | adopt the reference's exact charging rule (charge only functions that re-enter; prepay counted loops) earlier, in R0 |
| (T6) | "KIR is not needed for R0" | someone may require KIR in the kexe for verification or admission | none needed: the measured Form cost (ADR 0089) rules out KIR-as-Forms in one process. KIR text emission is R1 work (differential only) | the KIR printer moves into R0 (+200 lines) |
| (T7) | instruction selection coverage for the 19 ports is about 45 encodings | the 29 operations above map to about 25 data-processing forms and 20 memory/branch forms | the `40-a64enc` oracle table enumerates them; any port SIR op without an encoder fails `gn-run` by name | add the encoder |

## 7. Recommendation on R0 scope

Keep R0 to Seed-0 exactly (41 heads, 4 types, 3 wires, stack IR, depth-indexed temporaries, C runtime calls, a
single unity file, the kseed container) and **no** records, KIR emission or inline vector ops. Those are R1/R2,
where they are measured against R0's Embench baseline. Run T1-T3 on day 0, before the modules start: they decide the
two layout choices (unity file vs modules, bytes vs hex output) that every owner codes against. Run the seed path
next to the port path and merge at the KIR-consumer point (section 5.2), not by growing the seed into a second
full compiler.
