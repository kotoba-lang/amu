# Seed KIR reader: the seed backend compiles stage-0's KIR (2026-10-02)

Design section 5.2 (merge point): a KIR-text reader so that the seed's backend (30-lower, 41-a64gen, 42-layout,
50-out) compiles the KIR the big frontend emits. Owner: agent KIR. Everything below was measured on this host
(M1 Max, load average 75-90 during the runs).

## What was built

| file | lines | role |
|---|---|---|
| `seed/12-kirread.kotoba` (new, MANIFEST after 11-read, prefix `kr-`) | 888 | `kr-lex`, `kr-run`: KIR text -> the seed's own read tree of an equivalent Seed-0 program |
| `seed/90-drv.kotoba` (delimited block `BEGIN/END compile-kir`) | +79 | `compile-kir <file.kir\|file.kexe> <out>\|-` (also `--output`) |
| `seed/tests/unit/12-kirread_t.kotoba` + `.expected` | | stage-0 (linearity) build of the module and a tree digest |
| `seed/tests/kir/{pos,neg}/*.kir`, `seed/tests/kir/expected` | 4 + 16 | run results and golden refusal texts |
| `seed/tests/kir/kir-stats_t.kotoba`, `scripts/seed/kir-stats.sh` | | memory census of one compile |
| `scripts/seed/kir-gate.sh`, `scripts/seed/kir_extract.py` | | the gate below; KIR cut out of a kexe (BOOTSTRAP-TOOL) |
| `scripts/seed/kexe_code.py` | | stage-0 kexe `:code` + offset (see "stage-0 limit") |

**Where the KIR comes from.** Stage-0 has no `--emit-kir` flag. `amu-native compile <port> --target aarch64-macos
--output p.kexe` writes the KIR as the kexe's `:program` (`{:format :kotoba.kir/v4 ...}`; 4 of the 19 ports give
`v3`, without `:param-types`). `compile-kir` takes either the bare map (cut out by `kir_extract.py`) or the whole kexe:
then only the value of its depth-1 `:program` key is lexed. Both inputs give byte-identical containers on all 19 ports.

**How.** The KIR is read with 10-lex's scan, with `{}` read as `[]` and `#{` as `[`, by the unchanged 11-read. It is then
rewritten in place into `(ns kir (:export ..)) (defn f [p :T ..] :R body) ..`, and the unchanged pipeline from 20-names
on compiles it. 21-check therefore stays the soundness gate: anything outside Seed-0 is still refused by name, e.g.
`fn` gives E2101. Rewrites:

- `vector-new` becomes a vector literal; `string-byte-length` becomes `string-length`; `true`/`false` become `(= 0 0)`/`(= 0 1)`.
- KIR's and/or expansion `(let [__kotoba_and_N x] (if __kotoba_and_N y __kotoba_and_N))` becomes `(and x y)` (and the same for or). `(if x false true)` becomes `(not x)`.
- Loop helpers `__kotoba_loop_N` are inlined back as `loop`, and their self calls become `recur`. Captured locals that are provably invariant are dropped from the bindings: the argument is the same symbol at the call and at every self call, and no `let` in the body rebinds it. This keeps the seed's loop code and fuel rule. It also avoids helpers with more than 5 parameters (md5sum has one with 9).
- The string literals are re-pooled per distinct string, because KIR repeats a def's string at every use.

Names for generated nodes come from a 14-token prelude that the driver appends to the text (`string-concat`).

## Result: the 19 Embench ports (`scripts/seed/kir-gate.sh`, compiler seed-1 `0f6497a3...`, R1 HEAD 65c56c7ae + this change)

- Every port's KIR, emitted fresh by stage-0 and compiled by `compile-kir`, returns 1 under the C loader and under kexe-benchmark (fuel 16M): **19/19**.
- **Fuel** (kexe-benchmark `contextFuelConsumed`) is identical to the seed-from-source route on every port: 1,932,797 summed.
- **Code bytes** are identical on every port (114,433 summed). 18/19 binaries are byte-identical to the source route.
- The one exception is xgboost. There, only 8 `movz` literal offsets and the pool order differ: strings are pooled in first-use order, where the source route uses def order. The size is the same.
- SIR has 0-3% more instructions on the 7 ports that use nested and/or. These are LABEL ops of `(and a (and b c))`, which emit no code.
- 4 positive programs return 1: a rebound captured local, nested loops, bool forms and v3 with strings. 16 negative programs are refused with golden text: E1201-E1204, E2101, E2103, E2104 and E2106.
- Compile time over the 19 ports: 0.42 s for compile-kir against 0.40 s for compile from source. That is about 22 ms per process, loader start included.

## Memory: bytes of the seed's heap per KIR byte (`scripts/seed/kir-stats.sh`)

Region fills after the full pipeline (tokens 4 words, nodes 8, symbols 8, FN 16, SIR 4, fixups 4, literals 4, plus
LITB, CODE, OUT and heap words; the heap `M` itself is one fixed 64 MiB vector):

| route | input bytes (19 ports) | words used | bytes per input byte | front end only (tok+node+heap) |
|---|---:|---:|---:|---:|
| KIR (`compile-kir`) | 114,154 | 393,684 | **27.6** | 11.3 |
| source (`compile`) | 103,856 | 345,265 | 26.6 | 9.0 |

The largest port is xgboost: 57,630 KIR bytes take 125,318 words (1.0 MB), mostly its base64 literals (one word per
byte, in LITB and OUT). Without xgboost, the figure is 37.3 B per KIR byte.

ADR 0089 (kotoba-native) measured the Form route at about 3.4M vectors and 16M pairs for a 28 KB KIR program. The
loader's pair is 16 bytes and its vector descriptor 16 bytes, so that is at least 310 MB, or **about 11,000 B per KIR
byte**, before vector items are counted. The seed's flat arena uses **28 B per KIR byte** for the whole pipeline (KIR
to container), about 400 times less. The two scopes differ: the Form route runs MIR, select/allocate and the MC
validators, while the seed has no optimizer.

## Fixed point and previous gates (this change, on R1 HEAD 65c56c7ae)

- Unity: 7,331 lines, sha256 `fdb1949e...`.
- seed-0 is built by stage-0 (BOOTSTRAP) and extracted with `kexe_code.py`; it is sha256 `38adac41...`.
- seed-0 builds seed-1, and seed-1 builds seed-2: `seed-1 == seed-2`, 296,168 bytes, sha256 `0f6497a3...`.
- Run against the same unity on 7f0fe9072 (R0 + this change), the R0 selfhost seed `fe2c20ae` also built a byte-identical seed-1.
- seed-1 compiles R1's own HEAD unity to R1's published fixed point `7590d8c2`.
- `gates.sh --no-build --rung r1` passes G1 19/19, G2 65/66, G4 (seed-0 and seed-1 containers identical), G5, and GR r1 (52 equal to stage-0, 5 equal to spec, 35+5 negatives).
- G3 has no r1 golden yet (that is the GATES agent's). Its per-program output is byte-identical between R1's seed `7590d8c2` and this seed.
- Unit test `12-kirread` (stage-0 build) passes.

## Open risks

- **Stage-0 limit (affects every rung).** The stable stage-0's `extract-native` refuses a kexe with more than 200,000 EDN nodes (`bounded_edn` max-nodes). The seed-0 kexe passes that limit from about 5.5k unity lines on, because `:code` has one node per byte. `build.sh 0` therefore fails at extract on this unity. Two workarounds were used:
  - `kexe_code.py` (BOOTSTRAP-TOOL). On R0's seed-0 it gives the same bytes as extract-native.
  - Bootstrapping from the previous seed.
  The request is logged in `seed/CONTRACT-REQUESTS.md`.
- **Stage-0 linearity rule (new, measured).** A writer whose one arm is a direct `vector-assoc!` and whose other arm is a call `(xx-id M)` is refused once a caller has read M through a reader function. Both arms must be direct `vector-assoc!` (see `kr-fail2`).
- **Untested KIR shapes.** The reader is checked only on what stage-0 emits for the 19 ports, 4 synthetic positives and 16 negatives. Other KIR, such as a helper called twice or other gensym shapes, is refused by name rather than guessed. A non-empty `#{..}` reads as a vector and is refused only where effects are checked.
- **Reader stack.** 11-read's item recursion is mutual, not a self tail call. A list of more than a few thousand items overflows the loader's 1 MiB stack. This is why the kexe input lexes only `:program`.

## Update 2026-10-02 (wave R2/R3): KIR coverage census and the next shapes

Tool: `seed/tests/kir/census.sh [seed.bin]` (+ `census.py`, BOOTSTRAP-TOOL). STAGE-0 (bootstrap-reference) compiles every
`.kotoba` of 13 corpora (19 ports, seed/tests/{r1,corpus,conformance}, resources/kotoba/lang-conformance, examples,
test/dual-backend, test/nbb/fixtures, bench/runtime-comparison: 391 programs, 315 compile). The seed then compiles the
KIR (`compile-kir`) and the source (`compile`), and every arity-0 i64/bool export is run under the C loader for all
three codes (stage-0's own, seed-via-KIR, seed-via-source). Measured with seed `0ba0bd63` (this change):

| | before (R1 seed c0526b73) | after |
|---|---:|---:|
| programs accepted by compile-kir (of 315) | 139 (44.1%) | **241 (76.5%)** |
| programs with runnable exports, all equal to stage-0 via KIR (of 295) | 125 (42.4%) | **224 (75.9%)** |
| same, seed source route | 189 | 190 |
| accepted programs with a result different from stage-0 | 0 | **0** |

Body-operation coverage (occurrences of ops covered by a seed head or a 12-kirread rewrite): corpus 8,450 / 9,105
(92.8%, 42 of 133 distinct ops); the 10 big-compiler guests below 60,399 / 66,525 (90.8%, 41 of 106).

New KIR shapes read (in census order): `:entry SYM` and `:signature {..}` (141 programs; informational), exports
filtered to emitted functions with an exportable signature (KIR lists loop helpers, lambdas and record constructors for
implicit-export programs), vector result types (`[:record ..]`), capability effect sets `#{[:cap/call N] ..}` (others,
e.g. `:state`, stay E1203), `:schemas #:ns{..}`, `:closure-param-indexes`, `:closure-result?`,
`:i64-pair-chain-param-indexes` (ignored), `$` in symbols (`f$arity$2`, `__kotoba_invoke$arity1`), and the rewrites
`(bool-not b)` -> `(not b)`, `(record-assoc SCHEMA r :f v)` -> `(assoc r :f v)`, `(- x)` -> `(- 0 x)`, `(min a b)`/`(max a b)`
-> `(let [__kr_a a __kr_b b] (if (< ..) ..))` (only when the program defines no such function). No new SIR op.

The remaining gaps need seed heads (R3, logged in CONTRACT-REQUESTS): `pair`/`pair-first`/`pair-second` (18 programs;
KIR lambda-lifts every closure to `(pair tag env)` + a dispatch on `pair-first`, so closures follow), `string-substring`,
`string=?`, `option-*-of`, `result-*-of`, `typed-list-*`, `document-*`; and functions with more than 5 parameters (E2108).

**Largest KIR available** (the big compiler's native guests, KIR cut out of their stage-0 kexes in
/private/tmp/kotoba-guest-cache): ds (desugar port, 1,041 functions, 633,680 KIR bytes) is lexed, read, rewritten (39 loop
helpers inlined) and named in **0.13 s wall, 73 MB RSS** (the fixed 64 MiB heap), using 1,332,519 heap words (10.7 MB,
**16.8 B per KIR byte**), then refused by 21-check (E2128 on `[:option ..]`). vx (173 KB): 0.05 s, 372,742 words. cc, di, oa,
vc stop in the lexer (E1003 `\r` escape), case on a non-ASCII string (E1002); ri, oat, codec at 21-check (`:document`, `:f64`).
No big guest compiles end to end yet; time and memory are for the front half only.
