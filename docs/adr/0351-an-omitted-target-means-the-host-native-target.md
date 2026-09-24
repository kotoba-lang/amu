# ADR 0351 — An omitted `--target` means the host's native target

- Date: 2026-09-24
- Status: Accepted
- Deciders: owner (2026-09-24)
- Related: superproject ADR-2609241300 (amu's native compiler is the first
  execution path; wasm is one build target), ADR 0237 (it did not make native
  the default — this ADR does, and 0237 now points here), ADR 0347 (the JVM
  route is removed), ADR 0286.

## Context

Superproject ADR-2609241300 made amu's native compiler (`--target <isa>`,
kotoba-native x86-64 / AArch64 AOT, run through the kexe loader) the first
execution path and wasm one build target among several, chosen for hosts where
native cannot run. It left the CLI default alone, as a separate decision for
amu: `amu compile <file>` with no `--target` still produced a wasm32 module.

How it did so is what this change had to take apart. Nothing chose wasm32 on
purpose at the launcher: `bin/amu` put `undefined` in its set of nbb targets,
and `nbbEntrypoint` read `target === undefined` as "the Wasm driver", whose
`compile!` then filled in `"wasm32"`. The same `undefined` carried
`amu module-lock` — which takes no target — to the Wasm driver, where the
module-lock writer lives. `bin/kotoba` had its own copy of the rule (`nil` in
its target set, `(nil? target)` → Wasm).

A workspace-wide audit (2026-09-24) found no live caller that omits
`--target`: every gate, npm script and deploy passes one.

## Decision

1. **An omitted `--target` on `amu compile` and `amu worker` is the host's
   native target**, as Go's GOOS/GOARCH, Rust's host triple and Zig's native
   target default to the machine you are on. `bin/amu` resolves it to a NAME
   before routing, from Node's `process.platform` / `process.arch`:

   | host (`platform/arch`) | target            |
   |------------------------|-------------------|
   | `darwin/arm64`         | `aarch64-macos`   |
   | `darwin/x64`           | `x86_64-macos`    |
   | `linux/arm64`          | `aarch64-linux`   |
   | `linux/x64`            | `x86_64-linux`    |
   | `win32/arm64`          | `aarch64-windows` |
   | `win32/x64`            | `x86_64-windows`  |
   | `android/arm64`        | `aarch64-android` |

   Any other host is **refused by name** (exit 64), never defaulted to wasm:
   a fallback there would be the old default returning silently on exactly
   the machines nobody measured.

2. **`AMU_TARGET` sets the default** when `--target` is omitted; an explicit
   `--target` always wins; an empty `AMU_TARGET` is unset.

3. **Target-independent commands are routed by name, not by the absence of a
   target.** `check`, `definition-cids`, `module-lock`, `package-manifest`,
   `package-lock` and `package-fetch` go to the Wasm driver's namespace
   (which hosts the linker, the lock writer and the package commands) because
   they are listed, not because `target === undefined`. `module-lock` had to
   be added to that list: without it, flipping the default would have sent it
   to the native driver, which implements only `compile` and
   `extract-native`.

4. **No silent wasm.** When the native admission gate refuses a program, the
   refusal now names the first refused form (`does not qualify `map-new` (in
   function `main`: ...)`) or boundary type, names the wasm32 targets that
   carry typed values (`--target wasm32-browser` for a browser / Worker,
   `--target wasm32-wasi` for a WASI host), says nothing was written, and —
   only when amu chose the target — says the target was the host default (or
   `AMU_TARGET`) and that amu did not fall back to wasm. The locator asks the
   same `kotoba.kir/only-native-word-typed-features?` smaller questions rather
   than keeping a second admission table. The wasm hint is given for an
   explicit native target too: the person who asked for native by name needs
   to know where the feature is qualified just as much, and the message before
   this ADR already pointed at the typed Wasm target. The launcher tells the
   driver where the target came from through `AMU_TARGET_ORIGIN`, which it
   writes or removes on every spawn, so an ambient value is never believed.

5. **One rule, two launchers.** `bin/amu` exports `defaultTarget` /
   `hostNativeTarget` when it is required rather than run; `bin/kotoba`
   requires it instead of keeping a copy.

6. **The in-process JVM twin (`kotoba.compiler.cli`) refuses an omitted
   target** (`:phase :usage`, `:problem :compile/missing-target`) instead of
   defaulting to wasm32. No launcher spawns it (ADR 0347); a JVM copy of the
   host table would be a second answer to keep in step for a route being
   removed, and a wasm32 default there would contradict the launchers
   silently. Its only callers (the in-process test suite) all pass a target.

7. The Wasm driver (`nbb/wasm_cli.cljk`) keeps its internal `"wasm32"`
   fallback, now commented: the launcher only spawns it with a `wasm32*`
   target, so the fallback serves a caller that spawned the Wasm driver
   itself and has thereby already chosen Wasm.

## Consequences

- `amu compile x.kotoba` on an Apple-silicon Mac writes an `aarch64-macos`
  kexe; on the `ubuntu-latest` / `ubuntu-24.04-arm` / `macos-14` runners it
  writes `x86_64-linux` / `aarch64-linux` / `aarch64-macos`.
- Programs using features native does not yet qualify (maps, transcendental
  f64, typed collections at a host boundary, nested aggregates, documents —
  ADR 0237's list) now need `--target wasm32-browser` or `wasm32-wasi` written
  out. That is the point: the target is a host choice, stated.
- A native worker request that omits `--target` inside the NDJSON stream is
  still refused by the native driver (it has no per-request default); the
  worker's own target is what the default sets.

## Evidence

`scripts/test-default-target.cljk` (`npm run test-default-target`, also a
step in `test.yml`): 33 checks — the host table including the three CI
runners' hosts, four injected unknown hosts refused, AMU_TARGET precedence,
a defaulted compile run to `42` through `extract-native` + `kexe_loader.c`,
`--target wasm32-browser` still Wasm, `check` / `module-lock` byte-identical
with and without `AMU_TARGET`, the worker's ready line, `bin/kotoba` writing
`bin/amu`'s bytes, and the named refusal with no file written. On base
`c0105f73` the same script fails 11 checks, each for the default being wasm32
(or the refusal being unnamed); `check` and `module-lock` pass on both, as
they must.
