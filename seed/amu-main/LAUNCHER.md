# The native `amu` launcher (agent CMD, 2026-10-04)

Question: what replaces `bin/amu` (a 677-line Node script that spawns nbb) on the product path, so that `amu <args>` runs
with no node, nbb, JVM or shell process? Labels: **M** measured here, **E** estimate. Host load 35-45 during every run, so
no time on this page is a result. Stage-0 (`build/native-image/amu-native`, sha256 `d2cb84f6`) and `node bin/amu` are
BOOTSTRAP-REFERENCE oracles of the parity runs only, never in the launcher's process tree.

## 1. Design

The launcher is not a program in front of the compiler. It is ONE Mach-O: the C loader `tools/kexe_loader.c` built with
`KEXE_EMBEDDED` around the seed-built code of `amu.main` (this directory), the same image shape as amu-one. bin/amu's job
(route a command to a compiler process) becomes a Kotoba function in that image:

| bin/amu did (Node) | the launcher does (Kotoba, in-process) |
|---|---|
| no command, `-h`, `--help`: usage text, exit 0 | `amu.main/usage-text`: the same 43 lines, byte for byte (**M**, L1) |
| drop `--jvm-free` anywhere | `amu.cli/argx` skips it for the command and source positions |
| omitted `--target` for `compile` -> host native target (ADR 0351) | `amu.compile`: no `--target` flag = aarch64-macos (this host). `AMU_TARGET` is not read: the image holds no `:env/read` wire |
| resolve caller paths, spawn nbb with a computed classpath | nothing to resolve: the guest reads paths through wire 35 relative to the caller's cwd |
| `check` -> nbb check_cli (or `AMU_FRONT`) | `amu.check` (k/): the frontend's `analyze`, linked in as objects compiled from source (FRONTSRC) |
| `compile` -> nbb aarch64_cli | `amu.compile` (l/): the seed compiler in-process, `:kotoba.kexe/v1` artifact + stage-0's side files and ok line |
| `refactor` -> nbb refactor_cli | `amu.refactor` (REFAC's dispatcher) |
| `extract-native` | `amu.main/extract-native`: a `:kotoba.kexe/v1` artifact read by `amu.kexe/extract` (stage-0's texts); a KSEED1 container -> the seed driver |
| (none) | `link`, `modules` -> the seed driver (the image rebuilds itself, FRONTSRC) |
| the other 21 commands (module-lock, package-*, inspect, test, run, sign, verify, ...) | declared stub, exit 69, naming the command (never counted as behaviour) |

Runtime boundary: wires 3 (sha256), 35 (files, scoped), 37/38/39 (stdout, argv, stderr); never 20 (spawn); libSystem only.
The only fork is the loader's own supervisor fork (budgets), never followed by an exec.

## 2. Build and gate

```
zsh scripts/seed/launcher/build.sh                         # build/launcher/amu (+ amu.info); --front DIR picks the frontend objects
zsh scripts/seed/launcher/test.sh build/launcher/amu       # L1 argument layer, L2 Embench, L3 no host process, L4 static
```

`build.sh`: git HEAD's seed/ (split + `patch-split.py`, a no-op once seed.main exports `drv-compile-file`), the frontend
objects of `build/frontsrc/two/o` (compiled from source by the r6j seed compiler, no kir-dump), the split and the amu modules
compiled by rung r6j's recorded seed, `seed link`, `extract-native`, package. No stage-0, JVM, node or nbb at any step.

## 3. Results (**M**, image `build/launcher/amu`, 5,019,384 B, sha256 `7ca1ea5e`)

- L1 `usage-parity.sh`: 37 cases, 33 SAME (exit status, stdout, stderr and created files byte-identical to stage-0's in-process
  CLI, or to `node bin/amu` for its launcher-only cases, or to stage-0 with `--target aarch64-macos` for the host default;
  extract-native of stage-0's own kexe: same bytes and line), 4 DECLARED (the seed's refusal line; a program only stage-0
  compiles; module locks; `inspect` as a named stub), 0 DIFF.
- L2 Embench: 19/19 ports compiled to `:kotoba.kexe/v1` with a valid seal, 114 export runs from the launcher's code and from
  stage-0's under the C loader: all SAME.
- L3: 6 runs under the exec interposer (empty PATH, `env -i`): 6 loads, 6 supervisor forks, 0 exec/spawn/system/popen.
- L4: `/usr/lib/libSystem.B.dylib` only; wires 3,35,37,38,39.
- Corpus (391 programs, `parity.sh`): see seed/amu-main/README.md section 7.

## 4. What it does not replace yet

- `bin/amu` itself stays in the repository (bootstrap launcher of the nbb/JVM routes; every test harness calls it). The
  product command is `build/launcher/amu`; flipping `bin/amu` to it is an owner decision once `check` traps are gone (README 7).
- `bin/kotoba`, `bin/kotoba-compiler`, `bin/amu.cmd` (the other three PRODUCT launchers) are not addressed.
- 21 bin/amu commands are named stubs; `compile` writes aarch64-macos only; `AMU_TARGET` is ignored; `-M` boundaries are not
  stripped (bin/amu drops `-M`, `-M:compiler`, `-M:compile`).
