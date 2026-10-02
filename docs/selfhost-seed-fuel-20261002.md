# Seed fuel accounting versus stage-0 (FF-FUEL over-charge), 2026-10-02

Measured with `scripts/seed/fuel.sh` (owner GATES) on the self-built seed-1 (fixed point `fe2c20ae...`) and the stable
native stage-0 (`build/native-image/amu-native`, JVM-built, bootstrap-reference). Fuel is `contextFuelConsumed` from
`kexe-benchmark raw <bin> <off> aarch64 0 1 0 16777216`. For every port both builds were also run with fuel = consumed
(must return 1) and consumed-1 (must not): the consumed value is exactly the minimal passing fuel for all 19 ports and
both compilers, so the table below is the minimal-fuel table of design risk T5.

## Result

| | stage-0 | seed-1 |
|---|---|---|
| total fuel over the 19 ports | 1,986,036 | 1,932,797 (x0.9732) |
| ports where the seed charges MORE | | **2: crc32, slre** |
| largest port (xgboost) | 1,641,277 | 1,587,388 (9.5 % of the 16,777,216 cap) |

| port | stage-0 | seed | seed/stage-0 |
|---|---|---|---|
| crc32 | 1,028 | **2,051** | **1.995** |
| slre | 21 | **41** | **1.952** |
| aha-mont64 | 866 | 848 | 0.979 |
| depthconv | 483 | 450 | 0.932 |
| edn | 12,653 | 12,602 | 0.996 |
| huffbench | 33 | 32 | 0.970 |
| matmult-int | 10,811 | 10,806 | 1.000 |
| md5sum | 4,152 | 4,132 | 0.995 |
| nettle-aes | 638 | 582 | 0.912 |
| nettle-sha256 | 2,050 | 2,042 | 0.996 |
| nsichneu | 3,003 | 3,002 | 1.000 |
| picojpeg | 387 | 386 | 0.997 |
| qrduino | 139 | 138 | 0.993 |
| sglib-combined | 5,457 | 5,455 | 1.000 |
| statemate | 260 | 259 | 0.996 |
| tarfind | 7,440 | 7,332 | 0.986 |
| ud | 1,138 | 1,061 | 0.932 |
| wikisort | 294,200 | 294,190 | 1.000 |
| xgboost | 1,641,277 | 1,587,388 | 0.967 |

## Cause of the over-charge (reproduced by probes, `seed/tests/fuel/`)

A function whose body has no call and no runtime call except `(vector-at TABLE i)` over a constant table (a vector
literal, or a `def` of integer literals) is lowered by 30-lower to `OP-TAB` (no runtime call, integration change of
2026-10-02), but 21-check's `ck-op-fuel` still treats every `vector-at` as an RT head and sets `FF-FUEL`, so the
function gets a FUEL at entry. Stage-0 does not charge such a function. `tab10`/`tabdef10`: 10 calls, stage-0 12,
seed 21 (+9: one per call, the loop's own cost is equal). `crc32`'s `table-at` is called 1,024 times (+1,023), `slre`
has the same shape (+20).

The fix is one line in 21-check (do not mark FF-FUEL for a TAB-eligible `vector-at`); 41-a64gen emits FUEL only
for the `OP-FUEL` it is given and needs no change. Logged in `seed/CONTRACT-REQUESTS.md` (2026-10-02 GATES); no
module source was changed here. Until it is fixed `fuel.sh` exits 1 (T5 is not met on 2 ports); G1 is unaffected
(both ports return 1 with more than 99.98 % of the cap unused).

## The other direction (informational, safe)

| probe | situation | stage-0 | seed |
|---|---|---|---|
| loop10 | 10 recur, no call | 12 | 10 |
| loopinloop | 5 x 4 nested recur | 32 | 25 |
| strlit10 | function returning a string literal, called 10 times | 22 | 11 |
| veclit10 | function returning a vector literal, called 10 times | 22 | 11 |
| leaf10, wrap10, condcall, strlen10, vecat10 | calls/RT in the callee | 12/22/22/22/22 | 11/21/21/21/21 |
| fib, selftail, wrap3, leaf, empty | recursion, self tail call, call chain | 178/12/3/1/0 | 178/12/3/1/0 |

Stage-0 additionally charges loop entry (a loop helper entry, +1 per loop entry, +1 for the enclosing function) and
every function that builds a string or vector literal; the seed charges per `recur`, per entry of a function with a
user call, runtime call or capability call. Unbounded execution needs a loop or recursion, and both are charged in the
seed per back-edge and per call, so termination is still bounded by the fuel counter. Equality of the two rules on
recursion (`fib`, `selftail`) and call chains (`wrap3`, `leaf`) was measured, not assumed.

Reproduce: `zsh scripts/seed/fuel.sh` (about 20 s on a quiet host; table on stdout, `build/seed/fuel.tsv`).
