# Seed risk test T1: one 4-5k-line file through stage-0 (2026-10-02)

Question (design section 6, T1): can stage-0 compile a single 4-5k-line Kotoba file in reasonable time and memory, so that the
seed can stay one unity file? **Answer: yes. Time is linear in source size, RSS is flat (below 0.5 GB native, 1.4 GB JVM), no
admission limit is anywhere near. Keep the unity file. T1 does not force a module split.**

Stage-0 here is BOOTSTRAP-REFERENCE (JVM-built). Measurements on a host at load average 90-107, so wall times are upper bounds;
user CPU is the better number. Command shape: `ulimit -s 65500; /usr/bin/time -l <stage-0> compile F --target aarch64-macos --output F.kexe`
(single file, no `--source-path`, which would demand a module lock).

## Input

`scripts/seed/t1_gen.py <copies> <out> [port,port,...]` concatenates the Embench ports `copies` times into one module, dropping each
port's `ns`, giving every `defn`/`defn-`/`def` name a `-<port>-<copy>` suffix (token-exact rename) and exporting every renamed
export. Only the Seed-0 forms the ports use (i64, bool, string, vector-i64). Port code is dense: about 97 bytes/line on average
but table-heavy lines are far longer, so these inputs are larger per line than normal source (a 5k-line seed is likely 250 KB;
the rows below reach 290-530 KB). Rows are therefore conservative on bytes and on lowered nodes per line.
Note the design text said "40 copies = 4.4k lines"; the 19 ports are 1111 lines, so 4.4k lines is 4 copies (40 copies is 44k).

## Stage-0 native image (`build/native-image/amu-native`)

Only 7 of 19 ports compile in this image (list below), so the native series uses those 7 (crc32 huffbench matmult-int nsichneu
picojpeg sglib-combined statemate).

| copies | lines | bytes | defs | wall s | user CPU s | peak RSS MB | kexe bytes |
|---|---|---|---|---|---|---|---|
| 1 | 260 | 17 937 | 38 | 2.84 | 1.82 | 156 | 196 867 |
| 2 | 519 | 35 850 | 76 | 4.36 | 3.57 | 308 | 391 355 |
| 4 | 1 037 | 71 676 | 152 | 9.56 | 7.60 | 192 | 780 345 |
| 8 | 2 073 | 143 328 | 304 | 19.61 | 16.22 | 245 | 1 558 340 |
| 16 | 4 145 | 287 208 | 608 | 64.73 | 42.90 | 476 | 3 115 266 |
| 20 | 5 181 | 359 244 | 760 | 92.61 | 69.04 | 306 | 3 893 847 |

User CPU per KB of source: 0.10 (1 copy), 0.10, 0.11, 0.11, 0.15, 0.19. So linear up to 2k lines and mildly super-linear
(about n^1.2) from 4k to 5k lines, the same exponent ADR 0360 measured for `check`. 5.2k lines cost 69 s CPU and 0.3-0.5 GB.
RSS is noise around 0.2-0.5 GB (no growth trend), far below the memory wall of the port path.

## Stage-0 on the JVM (same sources, `java -Xss512m`, Temurin 21, default heap)

All ports except `slre` (see defects); 18 ports per copy.

| copies | lines | bytes | defs | wall s | user CPU s | peak RSS MB | kexe bytes |
|---|---|---|---|---|---|---|---|
| 1 | 1 082 | 106 864 | 162 | 14.01 | 20.42 | 1 091 | 616 475 |
| 2 | 2 163 | 213 704 | 324 | 23.01 | 32.61 | 1 340 | 1 056 659 |
| 4 | 4 325 | 427 384 | 648 | 48.59 | 58.71 | 1 396 | 1 937 351 |
| 5 | 5 406 | 534 224 | 810 | 77.97 | 82.64 | 1 328 | 2 377 640 |

Same picture: about 0.15 s CPU per KB at 5k lines, RSS capped near 1.4 GB (JVM heap behaviour, not growth with input).

## Admission limits

None hit. Largest accepted: 5 406 lines / 534 KB / 810 definitions / 280 exports (JVM) and 5 181 lines / 760 definitions (native).
Reference bounds (ADR 0356, 0358, 0360): source 8 MiB, max-functions 16 384, expression-node budget 2^22. Ours is 6% of the
source bound and 5% of max-functions; node count was not read from the CLI (the CLI does not print it), but ADR 0360's 60-155
nodes/KB puts 530 KB at 32k-83k nodes, about 1-2% of 2^22. A literal over 64 KiB is not involved (the largest port literal,
xgboost's, compiles inside the 8 MiB value bound of ADR 0362). A first failure of the synthetic file was "duplicate constant name":
`def` constants must be renamed per copy too (a generator bug, fixed, not a limit).

## Defects found in stage-0 (not seed problems, recorded for the stage-0 owner)

1. **Native image `amu-native` (built 2026-10-02 00:24) answers `internal compiler error` (exit 70) on 12 of the 19 ports when
   compiling**: aha-mont64 depthconv edn md5sum nettle-aes nettle-sha256 qrduino slre tarfind ud wikisort xgboost. The same
   sources compile on the JVM from the same classes (`build/native-image/work`), so it is a missing native-image reflection
   entry on a compile-only path (the tracing agent in `build-native.sh` runs `check` only). ADR 0360 records the same class of
   failure for `BigInteger(String)`. The seed's bootstrap step 1 needs `amu-native compile` on the seed unity file, so the
   native image must be rebuilt with an agent run over `compile` of all 19 ports (or the JVM is the stage-0 for step 1).
   The failing exception is hidden by `cli.cljk`'s `catch Throwable`; a debug env that prints the class would shorten this.
2. **`slre` fails on the JVM too**: `IllegalArgumentException: No matching method toString found taking 1 args for class
   java.lang.Integer` at `kotoba.native.machine_ir/hex-of-bytes` (`machine_ir.cljc:1171`, reached from `lower-kir-expression` for a
   `string-code-point-at` over an ASCII literal). It takes the `:cljs` arm `(.toString (int %) 16)` of the reader conditional in
   the staged classes. Any seed program that indexes a string literal (the design plans a string literal with `code_point_at`)
   hits this until stage-0 is fixed or the staged build selects the `:clj` arm.
3. The `check-native.sh` source-path / policy flags make `compile` demand pinned inputs ("a multi-module compile needs pinned
   inputs"); a single unity file must be compiled WITHOUT `--source-path`, as above. The design's bootstrap line already has
   that shape.

## Decision

One unity file stays. Stage-0 cost for the planned seed size (about 5k lines, 250-350 KB) is about one minute of CPU on this
loaded Mac and under 0.5 GB native, and the growth law leaves room for 2-3x (to 10-15k lines, a few minutes). The
split into modules (needing R5 `:require` early) is not warranted by T1. Open risks: the two stage-0 defects above (the native
image must be rebuilt before the seed's step 1 can use it; string literals with `code_point_at` need the `slre` defect fixed or
avoided); the exponent turns up beyond 4k lines, so re-measure at the real seed size when `seed/` is complete.

Reproduce: `python3 scripts/seed/t1_gen.py 4 /tmp/u4.kotoba <ports>`; JVM: `scripts/seed/t1_jvm.sh /tmp/u4.kotoba`.
Raw inputs/logs were kept under `/private/tmp/t1w/` (not committed).
