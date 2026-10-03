# `amu refactor` on the Kotoba route (agent REFAC)

Question: which `amu refactor` sub-commands run in the seed-built amu image with the host's exact answers, and what
is still a declared stub? Oracle: `bin/amu refactor` (node + nbb, BOOTSTRAP-REFERENCE, never in the image's process).

## Layout

- `src/amu/refactor_cli.kotoba` (ns amu.refactor-cli): the dispatcher. `src/amu/refactor.kotoba`, the module amu.main
  calls, stays the stub until every amu build puts the kotoba-lang compat root on its source path (CONTRACT-REQUESTS,
  REFAC -> CMD). It then becomes a one-line delegate. The dispatcher covers refactor-cli `run`/`parse-args` and nbb refactor_cli `main`
  printing: value flags and switches, "unknown flag", "needs a value", the sub-command routing, the usage, rule,
  path and file refusals.
- `src/amu/refactor_io.kotoba`: the I/O record over wires 35 (read, STAT, WRITE, RENAME, MKDIR) and 34 (browse), plus
  `expand-paths`, `refuse` (`:kotoba.cli-error/v1`, exit 64/65/74) and nbb's `js/Number` integer flags.
- `src/amu/refactor_graph.kotoba`: graph-cmd. It turns the graph twin's answer into EDN.
- `src/amu/edn.kotoba`: cljs `pr-str`, byte for byte. That covers array-map insertion order versus PersistentHashMap
  HAMT order (cljs murmur3 hashes) and string escapes.
- The library: kotoba-lang `lang/compat/kotoba/compiler/refactor/*.kotoba` guest twins (branch
  `agent/refactor-cst-twin`): cst, edit, diff, prelude (PORT/INTEGRATE), graph, rules, cljs-order (REFAC).

## Status (the sub-commands)

| sub-command | Kotoba route | differential |
|---|---|---|
| (argument layer, every sub-command) | real | `seed/tests/refactor/cases-args.txt` |
| list-rules | real | same |
| graph (full, --summary, --out) | real | `cases-graph.txt`, `cases-graph-src.txt` (every amu src/**/*.cljk) |
| plan, apply | arguments, rule spec and path expansion are real; the rewrite is a STUB (69) | core + rules twins are not written |
| partition | arguments are real; the rest is a STUB | partition twin is not written |
| split | arguments are real; the rest is a STUB | extract and partition twins are not written |
| verify | arguments are real; the run is a STUB | it needs wire 20 (spawn), which the image never holds |

Measured 2026-10-04 with seed r6j 4b2498ec: args 31/31, graph 20/20, graph-src 109/109 SAME, plus 3 kotoba-sema
frontend files of 347-603 KB SAME. The whole amu.main with the delegate compiles to 963,738 B of code. That image gives
list-rules SAME and graph 20/20 SAME, and `compile` still works (crc32 port).

Reproduce:

```
source scripts/seed/refactor/lib.sh
rf_compile seed/tests/refactor/entry.kotoba build/refac/t1/rf seed/amu-main/src <kotoba-lang>/lang/compat
zsh scripts/seed/refactor/diff.sh build/refac/t1/rf seed/tests/refactor/cases-graph-src.txt build/refac/d3
```

## Known differences (declared)

- Paths: bin/amu resolves relative paths against the caller's cwd. The Kotoba dispatcher takes paths as given, so
  resolving them is the launcher's job.
- A path outside the loader's KEXE_CAP_RESOURCES_35/34 scope TRAPS (SIGILL). nbb would instead answer "no such
  file" for it.
- Offsets are UTF-8 bytes in the twins and UTF-16 units on the host. They agree on ASCII text.
- cljs `sort` of strings uses UTF-16 order, the twins use byte order. These differ only between astral characters
  and characters in U+E000..U+FFFF.
- `--modules` / `--stack-size` / `--max-passes` take what JS `Number` takes for decimal, hex, octal and binary
  integers. Exotic spellings (`Infinity`, separators) are refused.
