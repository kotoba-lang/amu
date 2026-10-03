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
- `src/amu/refactor_partition.kotoba` and `src/amu/refactor_split.kotoba`: partition and split. The --names and
  --partition files are read with the cst twin. String labels and module names are supported; any other spelling is
  a declared stub.
- `src/amu/refactor_plan.kotoba`: plan and apply. This covers rewrite-file, file-report, sum-summaries, core's
  summarize, and the write-through-tmp-and-rename of apply.
- `src/amu/edn.kotoba`: cljs `pr-str`, byte for byte. That covers array-map insertion order versus PersistentHashMap
  HAMT order (cljs murmur3 hashes) and string escapes.
- The library: kotoba-lang `lang/compat/kotoba/compiler/refactor/*.kotoba` guest twins (branch
  `agent/refactor-cst-twin`). PORT/INTEGRATE wrote cst, edit, diff and prelude. REFAC wrote graph, rules,
  cljs-order, finding, core, rules.{destructure,letdestructure,kwcallback,lowerloops,reject,dynvars}, partition,
  extract and verify.

## Status (the sub-commands)

| sub-command | Kotoba route | differential |
|---|---|---|
| (argument layer, every sub-command) | real | `seed/tests/refactor/cases-args.txt` |
| list-rules | real | same |
| graph (full, --summary, --out) | real | `cases-graph.txt`, `cases-graph-src.txt` (every amu src/**/*.cljk) |
| plan, apply (rules a b c d e f, `all`, every flag) | real | `cases-plan.txt`, `cases-plan-src.txt`, `cases-dynvars.txt`, `cases-apply.txt` (scripts/seed/refactor/apply-cases.sh) |
| partition (full, --summary, --out, --modules, --driver) | real | `cases-partition.txt` |
| split | real | `cases-split.txt` (scripts/seed/refactor/split-cases.sh: the answer and every written file) |
| verify | arguments are real; the run is a STUB | it needs wire 20 (spawn), which the image never holds. The comparison twin is real: `scripts/seed/refactor/verify-diff.sh`, 5/5 |

Measured 2026-10-04 with seed r6k ab9f8236 (test entry 95fe7b34), all SAME: args 31/31, graph 20/20, graph-src
109/109, plan 18/18, plan-src 128/128 (every amu src file plus 12 kotoba-sema frontend files with `plan all`, and the
flag cases), apply 36/36, verify twin 5/5. Test entry f90868a7: partition 19/19, split 10/10, args 31/31. Earlier, with seed r6j 4b2498ec: graph SAME on 3 kotoba-sema frontend files
of 347-603 KB. The whole amu.main with the delegate compiles to 963,738 B of code. That image gives
list-rules SAME and graph 20/20 SAME, and `compile` still works (crc32 port).

Measured 2026-10-04 with seed r6k ab9f8236 and test entry e3b13046, using `scripts/seed/refactor/all.sh` (bin/amu as
oracle). Every suite has 0 DIFFER: args 31/31, graph 20/20, plan 18/18, partition 19/19, dynvars 44/44, graph-src
109/109, plan-src 128/128, apply 40/40, split 10/10, verify twin 5/5. Only verify's process runs remain a stub.

Whole image (`scripts/seed/refactor/build-image.sh`): the default r6k seed stops at E5001 (output buffer full). A large-M
r6k seed (fixed point 9d776226, KEXE_ARENA_USE=1) gives 1,428,096 B of code.

Reproduce:

```
source scripts/seed/refactor/lib.sh
rf_compile seed/tests/refactor/entry.kotoba build/refac/t1/rf seed/amu-main/src <kotoba-lang>/lang/compat
zsh scripts/seed/refactor/diff.sh build/refac/t1/rf seed/tests/refactor/cases-graph-src.txt build/refac/d3
```

## Known differences (declared)

- `apply` writes through wire 35 WRITE_SEP. The loader refuses content that holds the token `WRITE_SEP` itself, as
  nbb's refactor_cli.cljk does (single-occurrence rule). Such a file cannot be applied, and failed writes are not
  reported as `:refactor/write-failed`.
- A missing `--partition` file is refused as `:refactor/unreadable` with the message "cannot read P: no such file".
  nbb's message is node's error text instead.
- `--observable-from` is read only by rule c, and the Kotoba route does not read it.

- Paths: bin/amu resolves relative paths against the caller's cwd. The Kotoba dispatcher takes paths as given, so
  resolving them is the launcher's job.
- A path outside the loader's KEXE_CAP_RESOURCES_35/34 scope TRAPS (SIGILL). nbb would instead answer "no such
  file" for it.
- Offsets are UTF-8 bytes in the twins and UTF-16 units on the host. They agree on ASCII text.
- cljs `sort` of strings uses UTF-16 order, the twins use byte order. These differ only between astral characters
  and characters in U+E000..U+FFFF.
- `--modules` / `--stack-size` / `--max-passes` take what JS `Number` takes for decimal, hex, octal and binary
  integers. Exotic spellings (`Infinity`, separators) are refused.
