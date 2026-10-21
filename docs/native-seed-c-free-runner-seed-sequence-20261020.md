# C-free x86-64 seed runner: the run sequence, wired (JUN-29)

2026-10-20. `kotoba.compiler.runner-seed` is the runner body between the
two slices already recorded: `runner-slice` (admission + receipt) and
`runner-bookkeeping` (`pre-entry!` / `post-run!` digests). It is the
host-portable **executable specification** of the runner's control flow —
the sequence the compiler-emitted runner (vehicle (a),
`native-seed-c-free-runner-surface.md`) must perform. It claims no x86-64
emission; the guest entry is a callable, mapping and seccomp install are
hooks.

## 1. The one order the phases may run in

```
map-arenas -> install-sandbox -> pre-entry -> call-guest -> post-run
```

Each edge is load-bearing, all measured (surface doc, loader lines cited
there):

* `map-arenas` FIRST: `mmap`/`mprotect` are never admitted inside the
  sandbox (loader line 4807), so every arena is mapped before the sandbox
  is installed or it can never be mapped. The measured envelopes are
  `KEXE_VECTORS=4194304`, `KEXE_VECTOR_ITEMS=134217728`,
  `KEXE_STRING_POOL=268435456`, `KEXE_PAIRS=16777216`, launch stack
  >= 1 MiB with 512 KiB pre-reserved.
* `install-sandbox` before `pre-entry` keeps admission the LAST
  fail-closed point before guest code executes. The admission digests are
  pure `sha2.core` over bytes already in hand — it needs no mapping or
  file access inside the sandbox.
* `call-guest` runs only after `pre-entry!` answers `:admitted? true`. A
  refusal throws (`:phase :runner-admission` / `:runner-bookkeeping`) and
  the guest is never entered — "nothing runs if it refuses" is structural,
  and a test holds the guest counter at 0 across a pin mismatch.
* `post-run` seals `:kotoba.runner-receipt/v1` and re-verifies it before
  anyone can quote it.

## 2. What the tests reproduce (11 tests / 59 assertions, kbb/sci)

* The seccomp tables as measured: base 11 / fs-scope 11 / app-data 6
  names, the pinned numbers `openat2 437`, `faccessat2 439`,
  `renameat 264`, `mmap`/`mprotect` absent everywhere, `renameat2`
  deliberately denied while `renameat` is admitted.
* The grant decomposition: `#{}` -> 11 calls, `#{34}` -> 22, `#{35}` -> 28
  (and the compiler command path `#{35 37 38 39}` -> 28).
* The arena envelopes, byte for byte as the measured run.
* **The 2026-10-19 x86-64 G1->G2 chain through the FULL sequence**:
  `run!` over the recorded chain's digests reproduces admission
  `73c7761f9a191d721e6e4a8d5b0323253d5a35d54d4fee8e8fec65dea75ae95c`
  and receipt
  `b16d1d533ae420ca648cd0c695311b8de04f046eb113c08eaf6399d11b863965`
  (contract digest `35397c0b…680b`, verified `true`). The fixture lives
  in one place (`runner-bookkeeping-test`, recorded-pin data) and is
  required, not copied.
* Fail-closed at every boundary: a capability outside the served surface
  (`#{34 35 37 38 39}` — brokers 20/42/43-47 refused, out of slice) is
  rejected before ANY hook runs; a wrong pin refuses at `pre-entry` with
  the guest counter still 0; a guest output that is neither bytes nor a
  digest seals nothing.

## 3. Scope boundary (unchanged)

The seed compiler subset still refuses indirect calls / capabilities /
floats (E7101-E7102), so emitting THIS sequence as x86-64 still needs the
**kernel-profile slice** (JUN-30/JUN-102) — a recorded dependency, not
worked around. The Linux process semantics (seccomp BPF emission,
`openat2` `RESOLVE_BENEATH` containment, `RLIMIT_AS`) remain future work;
this slice pins the surface and the order, not the syscalls' emission.
