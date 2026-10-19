# C-free x86-64 seed runner: admission + run receipt (JUN-29, 2026-10-19)

Implements open measurement 3 of `native-seed-c-free-runner-surface.md`
("where admission verification must run in a runner that has no C; the
receipt must bind runner, compiler, source graph and output hashes"). This
record claims code and one measured receipt; it does **not** claim the
C-free runner exists yet. The kernel-profile slice the runner must be
emitted under (the seed subset's indirect-call refusal, open measurement 2)
is still an open dependency.

## 1. What was implemented

* `src/kotoba/compiler/runner_slice.cljk` — `kotoba.compiler.runner-slice`,
  the admission decision and `:kotoba.runner-receipt/v1` contract. Pure
  data + cross-checking, host-portable (no `node:crypto`, no
  `java.security`); byte digests are computed at the edges (the runner's
  own SHA-256; Python orchestration on the measurement side).
* `test/kotoba/compiler/runner_slice_test.cljk` — registered in both
  `run-tests.cljk` and `test/kotoba/compiler/test_runner.cljk` (the
  completeness test refuses a namespace named in neither). Vectors are the
  measured digests of the 2026-10-19 chain below, not invented ones.
* `scripts/runner-slice-receipt.cljk` — seals and re-verifies one receipt
  from a digest JSON, so the recorded receipt is one `verify` actually
  accepted.

The call-site contract (`:kotoba.call-site-contract/v1`) is embedded in the
receipt: the byte-measured dispatch discipline of the kx64-v1 emitters
(`native-seed-c-free-runner-call-abi-20261019.md`, 25 payloads, anomaly 0)
— entry-by-call, 16-byte frames, `mov rdi,[rbp-8]` + `call [rdi+disp32]`
host dispatch with the disp32 inside the admitted slot set
(56,64,72,112,120,128,136,144,160,168,176,184,200,208,216,240,352,360),
r9 reload at guest call and return, r9 restore after host calls. A runner
whose vtable layout disagrees with that set cannot pass `admit!` under this
contract version.

## 2. Where admission runs

In the C-free runner: after the arenas are mapped (the measured loader
never admits `mmap`/`mprotect` inside the sandbox), before the guest entry
is called. `admit!` refuses unless the source-graph digest matches the pin,
the container digest matches the expected container, and the call-site
contract is admitted. Nothing is normalised and nothing falls back. The
decision is sealed (`:admission-sha256`) so a receipt can bind which
admission it passed.

## 3. Measured receipt (2026-10-19 x86-64 build chain)

Runner slot caveat: the `runner` digest below is the **trusted C loader
build used for measurement** (the bootstrap vehicle, JUN-29's explicit
bootstrap provenance). It is replaced by the C-free runner digest when that
runner exists; the binding shape does not change.

| field | value | artifact |
|---|---|---|
| `runner-sha256` | `05798f17613db2936cf8fe29c16590c8c2b7513fc80e5b2334e89d16b482f7aa` | `kexe-loader`, 198,760 B (measurement build of `seed/bootstrap/adopted-loader-20261012.c`) |
| `compiler-sha256` | `32fe88f0dc850728c44a4b4320b6c180292a38e98672c80759859a59469e3f34` | G1 compiler payload code section, 1,231,648 B |
| `container-sha256` | `5f9b446c4445c12038ed8aa1eb4ad3984a671fba52e5f78e2de736f08822ce67` | G1 kseed container, 2,575,371 B |
| `output-sha256` | `101995a7fbf9e6a93400d7a178ed7c66e1c8dec6be515702d734c829c565d2e2` | G2 rebuild artifact, 2,575,344 B |
| `source-graph-sha256` | `8935d969ae4665c63baaf4f3dd42c0f192d388d397ced7b5c335561a2f1f5700` | canonical 21-entry manifest of the pinned seed source graph |
| `call-site-contract-sha256` | `35397c0b1b6a2f6d46d55f7f660730bd9ed5e9e2fb67d19c2424370c1fce680b` | the contract above |
| `receipt-sha256` | `b16d1d533ae420ca648cd0c695311b8de04f046eb113c08eaf6399d11b863965` | `:kotoba.runner-receipt/v1` over the run (status `:ok`, 1792403476–1792403796) |
| `admission-sha256` | `73c7761f9a191d721e6e4a8d5b0323253d5a35d54d4fee8e8fec65dea75ae95c` | `admit!` with the source-graph and container digests as pins |

* G1 = G2 byte-identical (both digests equal the G1 artifacts): the fixed
  point this chain measured, now bound in one receipt.
* `source-graph-sha256` is SHA-256 over the `sha256sum`-spelling manifest
  (sorted `sha256  path` lines, 21 entries: 17 seed `.kotoba` sources,
  `X86_64-LINUX-MANIFEST`, `adopted-20261012.bin`,
  `adopted-loader-20261012.c`). Computed independently twice — once by the
  Python harness over `report.json`'s input list, once inside
  `runner-slice-receipt.cljk` through `source-graph-manifest` — and both
  answers are `8935d969…`.
* `verify` re-checked the sealed receipt against the same artifacts and
  answered `{:verified? true …}`; `admit!` answered `{:admitted? true …}`.

Reproduce:

```
kbb --backend sci --classpath "src:$(kbb -Spath -M:test | tail -1)" \
    scripts/runner-slice-receipt.cljk <digests.json>
```

Tests (`test/kotoba/compiler/runner_slice_test.cljk`):

```
Ran 6 tests containing 34 assertions.
0 failures, 0 errors.
```

covering sealing/verification round-trip, fail-closed tamper cases
(digest swap per field, receipt body tamper, schema removal), contract
refusal (entry-by-call off, frame alignment 8, a disp32 slot outside the
measured set), manifest canonicalisation and injection refusal (duplicate
path, newline path, malformed digest), and `admit!` pin refusal.

## 4. Still open (unchanged)

1. The kernel-profile slice: the seed compiler subset refuses indirect
   calls/capabilities/floats, while the runner must dispatch vtable calls
   and named traps. Until the subset (or a kernel-profile extension)
   expresses them, the runner cannot be emitted from Kotoba source and this
   receipt's `runner` slot stays a bootstrap-provenance entry.
2. The runner implementation itself (arena mapping, seccomp base+fs-scope
   sets, `openat2 RESOLVE_BENEATH` containment, resource envelopes) — the
   receipt contract is now the surface it must satisfy, not a substitute
   for it.
