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

## Re-measurement on the R1 seed and the proposed fix (agent HOUSE, 2026-10-02)

`SEED_BUILD=build/seed-r1 zsh scripts/seed/fuel.sh` on the R1 fixed-point seed (`c0526b73...`, 291,392 bytes) against the
same stage-0: identical to the R0 numbers. Total 1,986,036 (stage-0) vs 1,932,797 (seed) = x0.9732; over-charge on
exactly 4 rows: crc32 1,028 vs 2,051 (x1.995), slre 21 vs 41 (x1.952), probes `tab10` and `tabdef10` 12 vs 21 (+9). Every
other port and probe is at or below stage-0. R1's sugar (`dotimes`, `case`, `->`, `when`) adds no fuel difference: the
desugared forms charge like their R0 spellings. `fuel.sh` still exits 1 (T5 not met on 2 ports); G1 is unaffected.

Proposed fix for the 21-check owner (not applied here; one function plus its caller). `ck-op` has the first operand
`a` of the head; `30-lower` lowers `(vector-at V i)` to `OP-TAB` exactly when `lw-tabsel` finds a vector literal of
integer literals (directly or as the literal of a `def`). 21-check should skip the FUEL mark under the same test:

```
;; 1 when V (first operand of vector-at) is a vector literal of integer literals, or a symbol resolving to a def of one
(defn- ck-tab-operand [M :vector-i64 v :i64] :i64 ...)          ; mirrors lw-vlit + lw-allint (30-lower)
(defn- ck-op-fuel [M :vector-i64 hd :i64 f :i64 a :i64] :vector-i64
  (cond (not= (ck-op-rt hd) 1) (ck-touch M)
        (and (= hd HD-VECTOR-AT) (= (ck-tab-operand M a) 1)) (ck-touch M)
        :else (ck-fuel M f)))
;; ck-op: (ck-op-fuel M1 hd (ck-fx-f fx) a)
```

(`and` in a `cond` test is fine for the R1 seed; the stage-0 ICE of the old notes only affects a stage-0 build, which no
longer builds this module.) Acceptance: `scripts/seed/fuel.sh` exits 0, `tab10`/`tabdef10` equal 12, crc32 and slre drop
to about stage-0's value (predicted from the probe, not measured), G1 and the fixed point still pass. Because the fix
changes emitted code (no FUEL at the entry of such functions) the golden containers of G2/G4 stay equal between seed-0
and seed-1 only if both seeds carry it: apply it in one rung with the bridge protocol of `scripts/seed/bootstrap.sh`.
