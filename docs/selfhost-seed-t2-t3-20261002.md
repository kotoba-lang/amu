# Seed risk tests T2 and T3 (2026-10-02)

Design: `docs/selfhost-seed-design-20261002.md` section 6. Everything below was run on this Mac (aarch64-macos) on
2026-10-02. Files: `seed/tests/t2/t2_asm.py`, `seed/tests/t3/t3_copy.kotoba`, `seed/tests/t3/t3_hex.kotoba`,
`seed/tests/t3/nbbc.sh`, `scripts/seed/t2_t3.sh` (replays T2 fully, T3 once the compile steps below have run).

## Verdict

| test | result |
|---|---|
| T2 hand-encoded AArch64 meets ABI v11 | **PASS.** 276 words encoded by a 70-line Python encoder; clang/otool agree word for word (0 mismatches). The blob runs under `tools/kexe_loader.c` and returns the expected 10536, writes the expected bytes, and charges exactly 1313 fuel units (trap at 1312) |
| T3 arbitrary bytes through wire 35 `:bytes` | **PASS at run time, with one blocker at compile time.** Copy and generation of 0..255 data is byte-exact (1 MiB, and 8 MiB minus the request prefix), in command mode and in `-DKEXE_EMBEDDED` mode. But the **stable stage-0 image refuses the program** (see T3.1): it needs a rebuild with osaho e77ffff or later. Until then the compile step runs on nbb (BOOTSTRAP) or the seed must emit hex |

Layout implication (decision for the `02-io` module and the seed's output path): see the last section.

## T2: hand-encoded words against the runtime interface

`python3 seed/tests/t2/t2_asm.py build/t2.bin --oracle` writes a raw code blob (1146 bytes: 276 instructions, then two
string literals) and prints `main offset 68`. No compiler is involved. `--oracle` assembles the same mnemonics with
`clang -c -target arm64-apple-macos -x assembler` and compares `otool -t -X` words with the encoder's: `instructions 276,
oracle words 276, mismatches 0`. clang and otool are encoding oracles only; the blob is the encoder's output.

What the program does (all from the one blob, `main` has arity 0):

| piece | ABI element exercised | expected | measured |
|---|---|---|---|
| ctx in x7 at entry, saved to `[sp,#16]`, reloaded before every helper call (helpers are C functions `(ctx, a, b, c)`: `ldr x7,[sp,#16]; ldr x16,[x7,#slot]; mov x0,x7; ...; blr x16`) | context pointer, slot calling convention | | works |
| `vector_alloc`(200), `vector_assoc_in_place`(208), `vector_at`(176): `v[i]=i*i+1`, sum of 8 | vector slots | 148 | included in the total |
| string literal = `pair_new`(56)`(offset_in_blob, 7)` over `"aé€x"` (61 c3a9 e282ac 78), `string_code_point_at`(144) at byte offsets 0,1,3,6, `pair_second`(72), `string_equal`(112) of two handles for the same literal | literal = code-relative offset (`code_base` is the start of the raw file), UTF-8 decoding, byte offsets | 97+233+8364+120, 7, 1 | included |
| guest-to-guest `bl spin`; `spin(1000)` leaf uses x7 as received | internal call keeps x7 | 1000 | included |
| `typed_cap_call`(128) kind 1 string to string on wire 37 (`:io/write`) with the literal, result handle read with `string_code_point_at` | kind 1 | stdout `aé€x`, '7' = 55 | `aé€x` printed, included |
| request vector (path + `WRITE_SEP` + 0..255 built with `string_code_point_at` and `vector_assoc_in_place`), `bytes_from_vector`(360), `typed_cap_call` wire 35 kinds 8,8, `vector_count`(168) and `vector_at` on the answer | kind 8, ABI v11 bytes slot | 256, 255 | included; the file holds exactly bytes 0..255 |
| fuel: `ldr x16,[x7,#8]; subs x16,x16,#1; b.hs +8; brk #0; str x16,[x7,#8]` at every function entry and loop head (the sequence of `kotoba-native` `aarch64.cljk` `fuel-charge`) | fuel at `[x7,#8]` | 1+9+9+1002+35+257 = 1313 | 1313 |

Commands and results (loader built with `cc tools/kexe_loader.c -std=c11 -O2 -o $T/loader`, `T=/private/tmp/t23`):

```
KEXE_CAP_RESOURCES_35=$T/d $T/loader $T/t2.bin 68 0 aarch64 35,37
  -> aé€x10536          (stdout of wire 37, then the loader prints the result 10536 = 148+8814+7+1+1000+55+256+255); exit 0
  -> $T/d/t2.bin == bytes(range(256))                                       (checked with python)
KEXE_FUEL=100000 KEXE_STRUCTURED_REPORT=1 ...  -> :fuel {:initial 100000 :remaining 98687}   (= 1313 charges)
KEXE_FUEL=1313 ...  -> ok, :remaining 0          KEXE_FUEL=1312 ... -> KEXE_TRAP {:kind :budget :reason :budget/fuel}, exit 120
... grant 35 without 37  -> KEXE_TRAP SIGILL (the capability gate holds for a hand-written caller)
KEXE_COMMAND=1 ... -> exit status 40 (= 10536 mod 256)
```

Findings that the design table did not have:
- The raw blob needs no container: the loader maps the file, `offset` selects the entry, `code_base` is the file start,
  so a string literal's `pair_new` offset is its byte offset in the blob. Literals follow the code, 8-aligned.
- Entry arity is read from the loader command line; x7 carries the context only because the loader's 8-argument call
  puts it there (`kexe_fn8` on aarch64). A fixture must therefore not use x7 for anything before saving it.
- x7 and x16 are caller-saved scratch across `blr`; a guest function that calls a helper must reload x7 from its saved
  copy (the reference code does the same, `[sp,#16]` here).
- Slots needed by the seed so far (all non-NULL in the real loader): 56, 72, 112, 120 (string_concat, not yet
  exercised here), 128, 144, 168, 176, 200, 208, 360. `kexe-benchmark` NULLs cap_call and bytes slots; the seed's own
  runs use the loader, so that is fine, but G1 under `kexe-benchmark` stays valid only because no port uses them.
- Not done: running the blob under `kexe-benchmark raw` (the design's alternative). The loader run is the one that
  matters for the packaged command.

## T3: arbitrary bytes through wire 35

Program: `seed/tests/t3/t3_copy.kotoba` (26 lines). argv through `typed-cap-call :cli/args`, read `typed-cap-call
:fs/app-data-bytes :bytes :bytes (string-to-utf8 path)`, write
`(bytes-concat (string-to-utf8 (string-concat out "WRITE_SEP")) data)` to a second path, then build N bytes in a
`:vector-i64` (`vector-alloc`, linear `vector-assoc!`), `bytes-from-vector-i64`, and write them to a third path.

Spelling facts learned (each cost a failed compile):
- bytes kinds use wire name `:fs/app-data-bytes` (the `:fs/app-data` wire is `:string :string` only: "expected bytes,
  got string").
- the builtin is `string-to-utf8` (not `utf8-bytes`); `vector-assoc!` is linear and returns the vector, so a fill loop
  threads the vector as a parameter and result (the `wikisort` style), and `[bytes-from-vector-i64 ...]` copies.
- request for the file read is the path bytes; the request for a write is the whole `path WRITE_SEP content` as one
  bytes value, so the **payload limit is 8 MiB minus path minus 9** (`bytes/too-large`, ADR 0362).

### T3.1 Stage-0 admission (the blocker)

```
amu-native compile seed/tests/t3/t3_copy.kotoba --target aarch64-macos --policy p.edn --output x.kexe     (stable image, built 00:24)
  -> :error :target "typed values currently require the kotoba-script web target ... qualified native one-word ... slice"
amu-native extract-native x.kexe ...  (kexe from nbb)  -> :error :verify "runtime KIR typed capability call rejected"
```

Bisected with one-line programs: `bytes-from-vector-i64`, `bytes-concat`, `string-to-utf8`, `string-from-utf8`,
`bytes-count` all compile; every `typed-cap-call` with a `:bytes` kind is refused, `:string :string` is accepted.
The osaho source (`wt-D-osaho` `src/kotoba/kir.cljk`, commit e77ffff of 00:19 "native admits typed-cap-call 35 over
[:string :bytes] and [:bytes :bytes]") has the clause, so the image predates it or links an older osaho.
**Action:** the next native-image build (in progress in `build/native-image-next`) must carry osaho e77ffff or later;
re-run `amu-native compile seed/tests/t3/t3_copy.kotoba` on it. This check is the first line of `scripts/seed/t2_t3.sh`'s
successor for T3 and gates seed module `02-io`.

Compile used here instead (BOOTSTRAP-REFERENCE, node only at compile time; the run is C only): nbb with a classpath
whose kotoba-sema is `git archive 452269a` (the working checkout at HEAD fd6ad70 is broken: `Unable to resolve symbol:
definition-heads` in `frontend/analyze.cljk:179`):

```
git -C /Users/junkawasaki/github/kotoba-lang/kotoba-sema archive 452269a | tar -x -C $T/sema
sed "s|/Users/junkawasaki/github/kotoba-lang/kotoba-sema/|$T/sema/|g" /private/tmp/wall-cp-16.txt > $T/cp.txt
echo '{:allow #{[:cap/call 35] [:cap/call 38] [:cap/call 39]}}' > $T/policy.edn
seed/tests/t3/nbbc.sh seed/tests/t3/t3_copy.kotoba $T/t3.kexe        # nbb aarch64_cli compile --jvm-free, 5 s
node ... x86_64_cli.cljk extract-native $T/t3.kexe --symbol main --output $T/t3.bin    # -> :offset 3176 (nbb, as bytes-cap.sh does)
```

### T3.2 Run results (command mode)

```
KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$T/d KEXE_STRING_POOL=268435456 KEXE_VECTOR_ITEMS=134217728 \
  $T/loader $T/t3.bin 3176 0 aarch64 35,38,39 -- $T/d/in.bin $T/d/copy.bin $T/d/gen.bin <N>
```

| case | result |
|---|---|
| 1 MiB from `/dev/urandom` (all 256 values), N=1048576 | exit 0 in 48 ms; `cmp in.bin copy.bin` identical; `gen.bin` equals the python-computed pattern, 256 distinct values |
| 8388572 bytes (8 MiB minus the 36-byte request prefix) | exit 0 in 0.25 s; copy identical; `gen.bin` identical |
| 8388573 bytes | `KEXE_TRAP {:kind :value :reason :bytes/too-large}`, exit 120, no file written |
| no `KEXE_CAP_RESOURCES_35` / grant without 35 / grant without 38 | SIGILL / SIGTRAP: the gates hold |
| embedded: `cc -O2 -std=c11 -I . -include kexe_embedded.h tools/kexe_loader.c -o t3emb` with the header `scripts/package-command.cljk` writes (ALLOW `35,38,39`, SCOPE35 = the data dir, STRING_POOL 256 MiB, VECTOR_ITEMS 128M), `otool -L`: libSystem only | `./t3emb in.bin copy.bin gen.bin 8388572`: exit 0, copy identical, 8388572 bytes generated. A target path outside the baked scope (`/private/tmp/copyout.bin`) gives SIGILL and no file |

**Budgets are the real constraint.** The default string pool is 64 KiB (`KEXE_STRING_POOL_BYTES 65536`): a bytes request
and its answer are both interned as strings by the provider (`fs_app_data_bytes_provider`: `intern_utf8`), and a read
answer is copied into the vector arena at 8 bytes per byte. Measured minimum budgets for the 8388572-byte case (one
read, two writes, one bytes concat and one `bytes-from-vector` in flight): **string pool about 42.8 MB (5.1 B per
payload byte), vector items about 59.3 M words (7.1 words per payload byte)**; for 1 MiB the pool needed between 4 and
8 MiB and items between 4 and 6 M. The packaged seed must bake `KEXE_EMBEDDED_STRING_POOL` and
`KEXE_EMBEDDED_VECTOR_ITEMS` for its largest output, and note that the seed's own heap `M` (design section 2.3) shares
the vector arena.

### T3.3 Fallback measured: hex on `:io/write`

`seed/tests/t3/t3_hex.kotoba` builds the 512 hex digits of bytes 0..255 in a vector, `string-from-utf8
(bytes-from-vector-i64 ...)`, and writes them with `typed-cap-call :io/write :string :string`. The **stable image
compiles and extracts it** (only wire 37 in the policy; `:offset 344, :length 216`), and
`KEXE_COMMAND=1 $T/loader hex.bin 344 0 aarch64 37 | xxd -r -p` returns bytes equal to `range(256)`. So the fallback
works today on stage-0 as it is, at 2x output size, one extra process (`xxd`), and a 4 MiB cap per single `:io/write`
string (8 MiB string limit, repeated writes are allowed).

## Layout implication

1. **Binary output is feasible and is the plan**: the seed writes its code bytes with one `typed-cap-call
   :fs/app-data-bytes :bytes :bytes "<path>WRITE_SEP<code>"` from a `bytes-from-vector-i64` of `M`. This is the design
   table's row for kind 8, now measured. Per output file the limit is 8 MiB minus path minus 9; the seed's code is far
   below it (the 19 ports are 104 KB of source), and a bigger output would use `APPEND_SEP` chunks.
2. **Gate on stage-0**: until the native image links osaho e77ffff or later, the seed (which contains this call) cannot
   be compiled by the stable `amu-native`. Step 1 of the bootstrap protocol therefore needs the rebuilt image
   (or nbb as an explicitly labelled stage-0). The hex path (`:io/write` + `xxd -r -p`) compiles on the stable image and
   is the zero-dependency fallback: if the rebuild slips, `02-io` ships `io-write-hex` and the protocol's `cmp` steps
   compare the decoded files.
3. `02-io` and the packaged-binary step must set the budgets (string pool at least 6x and vector items at least 8x the
   largest single write, on top of the seed's heap), and `KEXE_CAP_RESOURCES_35` (or `KEXE_EMBEDDED_SCOPE35`) must
   contain the output directory; reads and writes outside it trap with SIGILL, so a bad `--output` is a trap, not an
   error message. `main` should check the path prefix itself and print through wire 39 first.
4. The hand-written-fixture route of `41-a64gen` is validated: the ABI facts above (x7, slot offsets, literal =
   blob offset, fuel sequence, kinds 1 and 8) are enough to emit working code without reading `machine_ir.cljk`.
   `seed/tests/t2/t2_asm.py` is a ready oracle-checked encoder for the instruction subset and can seed the `enc` unit test.
