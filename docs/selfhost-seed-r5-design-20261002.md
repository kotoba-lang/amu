# Seed rung R5: modules and effects (design, 2026-10-03)

Owner: agent R5D (design and tests only; R5 module sources start when R4 lands). Inputs: `docs/selfhost-seed-design-20261002.md`
(rung table, section 1.4), `src/kotoba/compiler/project.cljk` + `project_files.cljk` (the reference project route), ADRs 0358,
0360, 0362, 0363, kotoba-lang `lang/state-ability.edn`, `lang/local-state.edn`, `lang/conformance/manifest.edn` (commit 919232de),
`docs/selfhost-minimal-reach-20261002.md` (R6: 126 modules). Everything marked *measured* was run on this tree on 2026-10-03
(host load average 45-80 during the runs); *est.* marks estimates.

## 0. Summary

| question | answer |
|---|---|
| What R5 adds | `ns` with `:require` (`:as`, `:refer`), qualified calls, `(:export ..)` / `{:kotoba/export ..}` / implicit exports, `#?` / `#?@` reader conditionals, `@x`; local state (`atom swap! reset! deref`); the state ability (`defhandler perform handle with resume`) and `(handle body (catch ..))`; namespace `:capabilities`, effect ceilings `{:effects #{..}}` and the compile-time capability policy (`--policy`); multi-module projects with the reference linker's rules |
| Linking model | **Per-module compile against dependency interfaces, then an image link of machine code** (section 3). Not a source-level unity: the big compiler (126 modules, about 0.95M tokens with host arms, *measured*) does not fit one heap `M` (8,388,608 words; 131,072 tokens per module region), while its largest module (machine_ir, about 107k tokens) does. The same module object format serves an in-process loop (default) and process-per-module + `seed link` (R6) |
| Semantics anchor | Stage-0's project route analyses each module **alone against import stubs** and then compiles the linked unit. The seed keeps the first half exactly (per-module analysis against interfaces, ADR 0363 abort propagation, the same refusals and bounds) and replaces the second half (re-analysing the linked text) by linking code. No language meaning depends on the second half (section 2.2) |
| State lowering | **Imperative**: a handler's state is a frame slot; `perform` = one call to the handler clause, which returns (value in x0, next state in x1); a stateful function specialised per handler takes the state as parameter 0 and returns (value x0, state x1). Equivalent to the reference's state-passing rewrite because evaluation is strict left to right and handlers are pure and tail-resumptive (section 5.4). Local atoms are hidden frame slots (no SIR change) |
| SIR/ABI additions | 2 opcodes (`RES2 t`, `RET2 t`), 1 fixup kind (`FX-EXT`, a `bl` to an imported function), FN kind `FK-IMPORT`, a per-FN side table, an image buffer vector `I` outside `M`, the module object container `KSEEDO1`; the executable container `KSEED1` is unchanged (section 6) |
| Gate | 20 conformance entries (23 source files) of `namespace_priority/ entry_extensions/ state/ local-state/ reader_target/` + their 16 pinned negatives + 41 feature cases = **77 cases** in `seed/tests/r5/` with stage-0 oracle values (section 8). Stage-0 *measured*: all 20 conformance values equal the manifest's `:kotoba` value |
| Baseline (*measured*) | the R3 seed (`cbae36dc`) passes 37 of 77: the 5 `entry_extensions` programs (15/20/25/35/45) and 32 refusals, all for the wrong reason (0 of 16 pinned texts) |
| Size (est.) | about 2.6-3.4k new seed lines (section 9); 6-9 agent-days with 4 owners after R4 lands |

## 1. Scope: the gate programs

The rung table names `namespace_priority/`, `entry_extensions/`, `state/`, `local-state/`, `reader_target/` with "23". The count
is 23 **source files**: 20 runnable entries plus the three `demo/util.*` modules of `namespace_priority/src`. The manifest also
pins 16 negatives in these directories by exact message (`state/negative` 11, `local-state/negative` 5); they are part of the gate.

| dir | entries | manifest `:kotoba` | stage-0 native (*measured*, `seed/tests/r5/r5.oracle`) | needs in the seed |
|---|---|---|---|---|
| reader_target | branching, default_fallback, splicing | 51, 107, 3 | 51, 107, 3 (main renamed, see below) | `#?`, `#?@` at top level and in a call; `:kotoba` and `:default` features |
| namespace_priority | main.cljk (+ `src/demo/util.{kotoba,cljc.cljk,clj.cljk}`), fn `run` | 101 | 101 (`--source-path src --unpinned`) | `:require [demo.util :as u]`, `u/bump`, `#?(:kotoba (:export [run]))` in the ns form, path resolution `demo.util -> demo/util.kotoba` |
| entry_extensions | main.kotoba, .cljk, .clj.cljk, .cljc.cljk, .cljs.cljk | 15, 20, -, 35, - | 15, 20, 25, 35, 45 | nothing new (the entry's extension does not matter); the R3 seed already passes all 5 |
| local-state | counter_in_a_let, atom_through_an_if, swap_with_extra_arguments | 42, 15, 42 | 42, 15, 42 | `atom swap! reset! deref @` |
| state | counter, inline_operations, nested_handlers, two_state_types, loop_accumulator, handler_logic, branch_join, ceiling_declares_state | 42, 42, 2110, 10, 5050, 77004, 114021006, 42 | identical | `defhandler perform handle with resume`, specialisation per handler, `{:effects #{:state}}`, `(ns x {:kotoba/export [main]})` |

Stage-0 adaptation, recorded per line in `r5.oracle`: stage-0 refuses a native `main` with parameters ("main must take zero
arguments"), and then a file without an `ns` ("entryless library requires an explicit non-empty namespace export list"). The
oracle compiles a copy with `main` renamed `oracle-main` (and `(ns oracle (:export [oracle-main]))` prepended when there is no
`ns`) and calls it with the manifest's arguments. The seed already admits `main [x]` as an exported arity-1 function and is run
on the verbatim files.

## 2. Reference semantics the seed must reproduce

### 2.1 The project route of stage-0 (project.cljk, project_files.cljk)

1. **Discovery** (`project_files`): namespace `a.b-c` -> relative path `a/b_c` + extension, extensions tried in the order
   `.kotoba .cljk .cljc` inside one root; across roots exactly one `.kotoba` wins over `.cljk/.cljc` twins, anything else is
   "namespace resolves from multiple explicit source paths". A `.clj.cljk` / `.cljs.cljk` file is never a module candidate.
   The file found must declare the required name ("resolved path namespace does not match requirement"). A multi-module
   compile needs `--unpinned` or a module lock ("a multi-module compile needs pinned inputs").
2. **Header** (`module-info`): exactly one `ns`; `(ns NAME DOCSTRING? ATTR-MAP? CLAUSE*)`; the attr-map keys
   `:kotoba/export :kotoba/capabilities :kotoba/schemas :kotoba/params` are the clauses `(:export ..)` etc.; admitted clauses:
   one `:export`, one `:capabilities`, one `:schemas`, one `:params`, any number of `:require`, `:refer-clojure` (validated and
   dropped); `:import :use :require-macros ..` are refused by name. Require specs: `[ns :as a]`, `[ns :refer [f ..]]`,
   `[ns :as a :refer [..]]`, `[ns :as a :with {..}]` (templates); duplicate alias, duplicate namespace, a referred name defined
   locally or referred twice are refused. With no `:export`, the public `defn`s in source order are the exports (ADR 0353
   floor 1); a module whose every function is private and that has no `:export` is refused ("project module X exports
   nothing ..."). Only **functions** are exported: a `def` is not an import ("export does not name a declared function").
3. **Order**: depth-first from the root, each require in clause order, dependency analysed before its importer (post-order);
   cycle on the namespace -> "cyclic module dependency rejected"; bounds checked on the way (2.3).
4. **Per-module analysis** (`analyze-module`): the module is analysed **alone**, its qualified calls `a/f` rewritten to import
   stubs `kotoba_import__i` whose signature is the dependency's interface (clauses by arity, param types, result,
   effects). **ADR 0363**: an aborting export is stubbed with its authored result T and a body that throws E, so the importer
   infers `:abort` with E at every call exactly as for its own function; a qualified call that is not an export is "qualified
   call is not an admitted exported import: a/f" (a `defn-` included); a qualified name that is neither an alias nor a
   registered capability operation is "named operation zz/f is not a registered capability".
5. **Link** (`link-source`): every analysed function is renamed `kotoba_module__<m>__<i>` (loop helpers keep
   `__kotoba_loop_<m*10^6+i>`), calls are renamed, closure dispatchers `__kotoba_invoke$arityN` are routed by lambda-id ranges
   `(m*16384, (m+1)*16384]`, the root's exports become wrapper `defn`s, `:schemas` are merged (a name defined differently by two
   modules is refused), and the resulting single source unit is compiled once more.

### 2.2 Why linking machine code is faithful

The second compile of step 5 re-derives what step 4 established per module (types, effects, abort lowering); the renaming makes
private names disjoint. Its observable additions are only whole-program **bounds** (2.3) and the dispatcher routing. The seed keeps
both at link time. Two points need care and are pinned by tests: (a) abort across modules (`feat/p10` = 11005, `feat/n09`
refused "unhandled abort at export boundary; catch it with try: main", both stage-0-measured); (b) a stateful function or a
handler never crosses a module boundary: a stateful export is refused in its own module (`feat/n10`, "unhandled ability :state at
export boundary ...: bump") and `(with l/cell 0)` is refused (`feat/n16`, "handle installs one handler with one initial state:
(handle body (with handler init))"). So state needs no interface support.

### 2.3 Bounds (ADR 0358, 0360, 0362; project.cljk constants)

| bound | value | where the seed checks it |
|---|---|---|
| modules | 256 | discovery |
| dependency depth | 64 (root = 1) | discovery (*measured*: a 64-deep chain passes stage-0's linker and is refused only later by its verifier, `feat/p20`; 66 deep is refused "project dependency depth exceeds limit", `feat/n15`) |
| dependency edges | 256 | discovery |
| project source bytes | 8 MiB total | discovery (sum of file lengths) |
| functions (linked, incl. dispatchers and wrappers) | 16,384 | link (sum of per-module FN counts + synthesised) |
| exports (interface clauses of all modules) | 1,024 | link |
| expression nodes / literals | 2^22 each, whole project | link (sum of per-module counts; the seed counts its own nodes, so a program at the edge may be refused earlier, never later, than stage-0) |
| string literal bytes | 1 MiB whole project | link |
| one definition's source | 1 MiB | per module (the defn's byte span) |
| string / bytes value | 8 MiB (ADR 0362) | loader; also caps the seed's own output write (risk R3, section 10) |
| template parameters | 8 | R5 refuses `(:params ..)` / `:with` by name (templates are R6, 2 of the 126 files use `:kotoba/params`) |

Seed capacity limits stay per module and are refused by their own E-codes (TOK 131,072, NODE 131,072, SYM 65,536, FN 8,192,
SIR 262,144, CODE 524,288 words), so a module that overflows names itself.

### 2.4 Reader conditionals (*measured* on stage-0)

Features: `:kotoba` and `:default` match, every other keyword does not. The **first** clause whose feature matches wins
(`#?(:default 5 :kotoba 1)` reads 5: `feat/p21` = 15). A conditional with no matching clause reads as **nothing**, at top level,
as an argument and as a splice (`feat/p22` = 3). `#?@(.. [a b])` splices the items into the enclosing list (`splicing.cljk` = 3).
A conditional may stand anywhere a form may, including inside `ns` (`namespace_priority`, `feat/p16` = 11, the unselected
require is never resolved). For R6 the important property is that **unselected arms are not Kotoba**: the 126 modules carry
8,827 `#?(` and 629 `#?@(` (*measured* grep) whose `:clj`/`:cljs` arms hold host syntax (`#"re"`, `#js`, `^Type`, `.method`).
So the seed reads a conditional with a **lenient skipper** for unselected arms (balanced delimiters, strings, char literals,
comments, `#"..."`; no token classification) and the normal reader for the selected one.

## 3. The linking model (decision)

### 3.1 Measurements that decide it

| quantity | value | source |
|---|---|---|
| seed unity (R3) | 431,715 bytes, 9,477 lines, about 81k tokens / 65k nodes (crude tokenizer, `seed/tests/r5` session) | *measured* |
| seed self-compile, R3 seed | 0.14 s real, RSS 81.6 MB, 62 pairs, 4 vectors, 9,378,440 vector items, heap 76.1 MB (`KEXE_ARENA_USE=1`, load 60) | *measured* |
| big compiler, 126 modules (`/private/tmp/reach-minimal.txt`) | 7.11 MB, 136k lines, about 950k tokens / 728k nodes **with** host arms | *measured* (same tokenizer) |
| its largest modules | machine_ir 107k tokens, desugar 86k, infer 68k, mir 56k, analyze 51k | *measured* |
| `M` | 8,388,608 words; TOK 131,072 x 4 words; NODE 131,072 x 8 words | seed/MEMORY-MAP |

A source-level unity of the big compiler needs about 12 words per token for tokens and nodes alone, so 6-11M words before SIR
and code (est.; the Kotoba reading is smaller than the with-host-arms count, by an unmeasured factor): more than `M`, and the
token region would have to grow 4-7x. Per module, the largest file fits the current regions (107k < 131,072 tokens, before arm
selection). Pairs are not the constraint (62 per self-compile).

### 3.2 Options

| option | memory | reuse | semantic fit | verdict |
|---|---|---|---|---|
| A. source-level unity (read every module, rename, compile one unit; what stage-0 does after step 4) | whole project in one `M`: fails at R6 (3.1) | simple for small projects | renaming must touch every binding position of the grammar | **rejected** (it is how the seed itself is still built from MANIFEST, unchanged) |
| B. per-module compile against interfaces, in one process, `M` reset between modules, code appended to an image buffer, link at the end | bounded by the largest module + the link table | the whole pipeline unchanged per module; link = patch `bl` and literal offsets | exactly step 4 of the reference; step 5's bounds and dispatchers at link | **adopt (default)** |
| C. B with one process per module (`--emit-module` writes a `KSEEDO1` object) and `seed link` | bounded per process; parallel | same object format as B | identical | **adopt for R6**; gate: B and C give byte-identical images |

### 3.3 The pipeline of `seed compile <entry> [--source-path D ..] [--unpinned] [--policy P] --output X`

1. **Discover** (driver, new module `60-proj`): read the entry, lex+read its `ns` form only, resolve requires (2.1.1), recurse;
   produce the module order (2.1.3) in a LINK table; check modules/depth/edges/source bytes. Without `--source-path` a file with
   `:require` is refused like stage-0 ("required module X is missing from the explicit source paths").
2. **Per module, in order**: `mem-reset` (zero exactly the filled prefix of every region and the HEAP up to its top, so the
   "fresh words are zero" rule of 01-mem holds; LINK and `I` survive); compile the module with its dependencies' interfaces
   loaded as `FK-IMPORT` functions; append its code+pool blob to `I` at an 8-byte aligned base; record its relocations, its
   exports (interface) and its counts in LINK.
3. **Link**: resolve every `FX-EXT` `bl` (imm26, target = the importee's entry in `I`), add each module's base to its literal
   relocations (`FX-LIT32` movz/movk values are code-start-relative), emit the closure dispatchers (R4) as code after the last
   module, build the export table from the **root's** exports with their source names, check the whole-program bounds, write
   `KSEED1` (unchanged format) and print `{:ok true .. :capabilities #{..}}`.

Determinism: module order is a function of the sources; private names never meet; no hash order reaches `I`. Separate mode
(C): `seed compile --emit-module NS --source-path .. --output m.kso` runs steps 1 and 2 for one module (interfaces read from
the dependencies' `.kso` files, which must exist), `seed link root.kso --source-path .. --output X` runs step 3.

## 4. Names, exports, requires (20-names, 21-check)

- Qualified symbol `a/f`: 20-names splits at the last `/`; `a` must be an alias of this module's requires; `f` must be an
  export of that module (interface lookup) -> an `FK-IMPORT` FN record (one per imported clause used); else the reference
  texts of 2.1.4. A referred name resolves to the same import record. Locals shadow referred names as usual; a referred name that
  collides with a definition is refused at the header.
- An `FK-IMPORT` behaves in 21-check like a local `defn` whose signature is already known (param types, result type, SF-ABORT
  error type): that is ADR 0363 without stubs. A call to an aborting import makes the caller abort with E; `try` catches it.
- Interface record (per exported clause): source name, arity, param types, result type, error type or 0, effect set
  (capability wires; `:state` cannot occur, 2.2). Types are stored **canonically** (a type string such as `[:result :i64
  :string]`), because composite-type indices (CT) and record identity symbols are per module; the importer re-interns them.
  Record types travel with their schema (keyword name + field list); a name defined differently by two modules is refused at
  link ("modules declare the same schema name with different definitions").
- Exports: `(:export [..])`, `{:kotoba/export [..]}` (also after a docstring), `#?(:kotoba (:export ..))` (resolved by the
  reader), implicit = public defns (R1 already has FF-EXPORT 2). Exportability at the **root** keeps R1's rule (params i64,
  result i64/bool) because the runner calls the image; a library export may have any admitted signature (it is linked, not
  called from outside).
- Constants (`def`) are not exported (reference). Consequence for the seed's own rung proof: each namespace carries the
  generated constants it uses (gen-ns.sh writes a per-namespace constant block, section 7).

## 5. Effects

### 5.1 Reader-level forms (10-lex, 11-read)

`#?(`, `#?@(` (selection at read time, 2.4), `@x` -> `(deref x)`, namespaced symbols and keywords (`u/bump`, `:state/get`,
`:kotoba/export`). A malformed conditional (odd number of forms, a non-keyword feature) is refused by name.

### 5.2 Local state (lang/local-state.edn slice 1)

Elaboration in 21-check, no SIR change: `(let [a (atom init)] ..)` allocates a **hidden frame slot** (R3 already allocates hidden
slots); `(swap! a f x ..)` = `slot := (f slot x ..)` with value the new content (arguments read the old value, left to right);
`(reset! a v)` = `slot := v`; `(deref a)` / `@a` = the slot. The cell's type is init's type; every rebinding must have it. A
branch whose arms write the cell needs no copies: arms write the same slot, the join is the slot. The **refusals are kept exactly**
(they are the language's, pinned with `=`): escape (passed, returned, stored, captured by `fn`, read or written inside
`loop/recur/doseq/dotimes`, named in another function, shadowed), atom position, not-a-cell, position (`and or some-> cond-> condp
match ->`), cell type, effectful branch (an arm that writes a cell and calls a capability), `cond` without `:else`, arity. Texts:
`lang/local-state.edn :refusals` (section 7.4).

### 5.3 The state ability: front end

- `defhandler NAME DOC? [:state S] (get [s] body) (put [s v] body)`: a top-level definition (HANDLER record in HEAP: name, S,
  the two clause FNs). Checks with the reference texts: exactly `get` and `put` once each, clause params `[state]` /
  `[state value]`, every tail of a clause body is exactly one `(resume value next)` and `resume` appears nowhere else, value and
  next state typed S, the clause bodies are pure (no capability call, no perform).
- `(perform :state/get)` / `(perform :state/put v)`; `(perform :cap/op args)` for a catalogued capability is the capability
  call (typed-cap-call of that wire).
- `(handle body (with h init))`: `h` must name a handler of this module (texts "handle names no handler: h", "handle installs one
  handler with one initial state: ..."); `(handle body (catch e h))` = `try`.
- Effect rows: a function that performs `:state` (or calls one that does) outside every `handle` body is **stateful**; computed
  as a fixpoint over the module's call graph. A stateful export (or `main`) is refused ("unhandled ability :state at export
  boundary; handle it with (handle body (with handler init)): f"). Declared ceilings `{:effects #{..}}` (in the result position or
  after it) must contain the inferred set ("inferred effects exceed declared effect ceiling for f: #{:state}"). Refused by name
  as in slice 1: perform inside `fn`, a stateful function as a value, throw/try inside a stateful function or a handle body, a
  stateful function that aborts, an aborting call inside a handle body.
- **Specialisation**: worklist over pairs (f, h) reached from a `handle` with handler h; an FN record per pair (side table:
  origin FN, handler). 21-check types each specialisation at S; two pairs with the same S share the node tree (only 30-lower's
  calls differ); a pair whose S differs from every earlier one gets a node clone (R1 already appends NODE records). Bound:
  pairs <= functions x handlers in the module, refused above FN-CAP by the existing E-code.

### 5.4 The state ability: lowering, and why it is equivalent

The reference rewrites a specialisation to state-passing source: `f_h(s, args) -> [:record retN [[:value T] [:state S]]]`,
get/put as calls to split clause functions, and copies or join functions at branches. The seed lowers the same thing
imperatively:

| construct | SIR (slot σ = the current handler's state slot) |
|---|---|
| `(handle body (with h init))` | `[init -> t] LSET σnew t`; push (σnew, h); `[body -> t]`; pop |
| `(perform :state/get)` | `LGET t σ`; `CALL h.get t 1`; `RES2 t+1`; `LSET σ t+1` (value in t) |
| `(perform :state/put v)` | `LGET t σ`; `[v -> t+1]`; `CALL h.put t 2`; `RES2 t+1`; `LSET σ t+1` |
| call of stateful g under h | `LGET t σ`; args at t+1..; `CALL g_h t n+1`; `RES2 t+1`; `LSET σ t+1` |
| body of `f_h` | σ = parameter slot 0; every `RET t` becomes `LGET t+1 σ; RET2 t` |
| clause `(get [s] .. (resume v n))` | a function of (s) / (s v) whose tails are `[v -> t] [n -> t+1] RET2 t` |

Equivalence: the reference threads the state through the specialised body in evaluation order (strict, left to right; `let`
sequential; `if` evaluates the test then one arm); the imperative slot is read and written at exactly those points, so each read
sees the value the threaded version would pass. Branch joins need no copy: both arms update the one slot. A loop keeps σ in its
frame slot (recur does not touch it), which is the reference's "a stateful loop stays a loop". Handlers are pure and resume once
in tail position, so calling the clause once and taking (value, next state) from x0/x1 is the reference's two calls
`h-get-value`/`h-get-state` folded into one. Nested handles shadow by the lexical (σ, h) stack. Cost: no allocation per stateful
call (stage-0 allocates a pair per non-tail stateful call and its verifier could not re-derive 400 calls, `feat/p13b`; the seed
must answer 79,800 and 12,497,500 for 5,000 calls, `feat/p13`). Stateful functions keep the 5-register argument limit
**including** the state (a stateful function with 5 user parameters is refused by name until stack arguments exist, KIR request
of 2026-10-02).

### 5.5 Capability policy

1. Catalogue: `perform :ns/op` and friendly `ns/op` calls map to wires by a generated table (HEADS `:cap-catalog`, from
   `lang/capability-catalog.edn`); R5 carries the wires the seed already lowers (35, 37, 38, 39) plus `:clock/now` for the tests;
   R6 extends the table to what the 126 modules use (grep at R6 start). Unknown -> "named operation X is not a registered
   capability".
2. Namespace declaration: when the module declares `:capabilities` (clause or attr-map), every capability it uses must be in
   it ("cap-call uses a capability not declared in namespace :capabilities: #{..}", `feat/n12`); absent clause = no check
   (reference: nil vs empty set differ).
3. Compile policy: `--policy P` (`{:allow #{[:cap/call N] ..}}`, the stage-0 file shape): the linked program's required set must
   be allowed ("capability policy denies required effects; missing grants #{..} (required #{..}, allowed #{..})", `feat/n13`).
   Without `--policy` the seed does not check (R0-R3 behaviour) and prints the required set in its `{:ok ..}` line; the build
   scripts pass `--policy` for the seed's own build (wires 35, 37, 38, 39 = SEED_GRANT).
4. A handler clause must not use a capability ("handler h is not pure: its put clause performs #{:clock/now}; ..."),
   checked before the namespace check.

## 6. SIR, ABI and container additions

| item | definition | owner |
|---|---|---|
| `OP-RES2 t` (next free opcode after R4) | `t := x1` of the CALL immediately before it (no instruction between; 41-a64gen emits `mov` of x1 first) | SIR / 30-lower / 41-a64gen |
| `OP-RET2 t` | return temp t in x0 and temp t+1 in x1 | same |
| stateful convention | `f_h(state, a1..a4)`; result value x0, next state x1; handler clause fns `(s)` / `(s v)` -> (x0, x1); x1 is caller-saved, so RES2 must follow the call directly | 41-a64gen |
| `FK-IMPORT` (FN kind 4) | FN record of an imported clause; FF-NODE = LINK interface index; no SIR; calls to it emit `bl` with `FX-EXT` | 20-names / 41-a64gen |
| `FX-EXT` (fixup kind 6) | `bl` imm26 to LINK import target; resolved by the linker (unresolved in a `.kso`) | 41/42 |
| FN side table FN2 (HEAP, MM-FN-CAP x 8 words) | FF2-ORIGIN (specialised from), FF2-HANDLER, FF2-STATEFUL, FF2-IMPORT, FF2-LAMBDA-BASE, 3 spare | 20-names / 21-check |
| LINK region | top 262,144 words of HEAP (`MM-LINK-BASE = MM-HEAP-END - 262144`), never reset; `mem-alloc` stops below it | 01-mem / 60-proj |
| image buffer `I` | a second `:vector-i64`, one byte per item, up to the 8 MiB bytes-value bound; written by the linker; replaces OUT (1 MiB cap) for every output | 60-proj / 50-out |
| `KSEEDO1` object | text header `KSEEDO1 <code-len> <n-exports> <n-imports> <n-relocs>`, lines `E <name> <offset> <arity> <type> <err> <effects>`, `I <ns>/<name> <arity>`, `R <kind> <offset> <arg>`, `S <schema>`, a blank line, then code+pool | 50-out |
| `KSEED1` executable | unchanged (the runner's format); exports = root exports by source name | 50-out |
| lambda ids | `module-index * 16384 + local id` (reference-compatible); the linker emits one global `__kotoba_invoke$arityN` per arity that range-tests `pair-first` and tail-calls the module's local dispatcher (project.cljk `project-dispatchers`) | 60-proj, after R4 |
| CLI | `--source-path` (repeatable), `--unpinned` (required with source paths; `--module-lock` refused by name), `--policy`, `--emit-module NS`, `link` | 90-drv |

No other SIR change: local atoms, exports, qualified calls and reader conditionals are front-end work; abort across modules is the
R3 lowering.

## 7. Contract deltas (requests; the contracts owner applies them)

1. **HEADS**: heads `atom swap! reset! deref perform handle with resume catch-in-handle` (expression forms), top-level
   `defhandler`; ns clause keywords `:require :as :refer :export :capabilities :schemas :refer-clojure :with :params`; keyword
   codes for `:kotoba :default :state/get :state/put :state :effects :kotoba/export :kotoba/capabilities :kotoba/schemas
   :kotoba/params`; RES class `RES-IMPORT` is not needed (RES-FN on an FK-IMPORT record); `:cap-catalog` table.
2. **SIR**: OP-RES2, OP-RET2, FX-EXT, the stateful convention, the LIT32 relocation rule (code-start-relative values + module
   base), and that RES2 must directly follow CALL.
3. **MEMORY-MAP**: LINK region and `mem-alloc` bound, FN2 side table, `mem-reset` (01-mem) with its zeroing rule, the image
   buffer `I`, FK-IMPORT, the HANDLER block, the cell (atom) slots as hidden slots in 21-check's state, MM cells for module index
   and lambda base, write rights for 60-proj.
4. **MANIFEST**: new module `60-proj` (prefix `pj-`) after `50-out` (discovery, per-module loop, link); 90-drv gains the CLI
   flags. For the rung proof the seed source is split into namespaces (section 9), so MANIFEST gains a namespace column and
   gen-ns.sh writes one constant block per namespace (only the constants it uses; `def`s are not importable).
5. **Errors** (new E-codes, texts = the reference's so `neg/` can be compared with `=`; placeholders in braces):

| code (proposed) | text |
|---|---|
| E2140 | `atom \`{name}\` escapes its let scope (atom slice 1 admits swap!/reset!/deref in straight-line code of the binding function only)` |
| E2141 | `atom must be the init expression of a let binding (atom slice 1 admits swap!/reset!/deref in straight-line code of the binding function only)` |
| E2142 | `{op} expects a let-bound atom cell as its first argument; got \`{name}\` (atom slice 1)` |
| E2143 | `swap!/reset! is not admitted inside \`{head}\` (atom slice 1 admits them in let, do, if, when, cond and case only)` |
| E2144 | `atom \`{name}\` is {t}; this rebinding is {t2} (atom slice 1 requires one type per cell)` |
| E2145 / E2146 / E2147 | effectful branch, cond without :else, shadow (local-state.edn :refusals) |
| E2150 | `unhandled ability :state at export boundary; handle it with (handle body (with handler init)): {name}` |
| E2151 | `handler {h} resumes state/{op} with {t}, but state/{op} returns {s} in a [:state {s}] handler` (+ the next-state variant) |
| E2152 | `handler {h} does not match the :state ability: {detail}` (both shapes) |
| E2153 | `handler {h} is not pure: its {op} clause performs {set}; a handler for the pure ability :state must be pure` |
| E2154 | `inferred effects exceed declared effect ceiling for {name}: {set}` |
| E2155 | `handler {h} clause {op} must end every branch in exactly one (resume value state) in tail position` |
| E2156 | state position (fn literal, lazy thunk, stateful function as a value): three texts of state-ability.edn |
| E2157 | state and abort (three texts) |
| E2158 | `handle names no handler: {h}` / handle shape / perform arity |
| E2160-E2175 | the linker and header texts of 2.1 (`cyclic module dependency rejected`, `required module {ns} is missing from the explicit source paths`, `duplicate import alias`, `qualified call is not an admitted exported import: {name}`, `project module requires exactly one namespace`, `namespace clause {k} is not admitted: ..`, `resolved path namespace does not match requirement`, `project module {ns} exports nothing: ..`, `named operation {name} is not a registered capability`, `project dependency depth exceeds limit`, edges/modules/functions/exports/nodes/literals bounds, referred-name texts) |
| E2176 / E2177 | `cap-call uses a capability not declared in namespace :capabilities: {set}`; `capability policy denies required effects; missing grants {set} (required {set}, allowed {set})` |
| E1006 | `malformed reader conditional` (seed text; stage-0's reader text to be recorded at implementation) |

A `{set}` prints as the reference prints it (`#{:clock/now}`, sorted); 90-drv needs a printer for keyword sets.

## 8. Conformance gate and tests (`seed/tests/r5/`, owner R5D)

| file | content |
|---|---|
| `conf/` | the 23 source files, verbatim (kotoba-lang 919232de), in their directories |
| `neg/` | the 16 pinned negatives, verbatim, renamed `<dir>-<name>.kotoba` |
| `feat/` (generated by `gen-feat.py`) | 41 feature cases: 25 positives (require/as/refer, private isolation, diamond, implicit and attr-map exports, loop helper and string signature across modules, ADR 0363 import abort, multi-arity export, stateful loop of 5,000 and 400 calls, string atom, cond writes, `#?` in ns, extension priority, `.cljk` fallback, `my-lib -> my_lib`, depth 64, `#?` first-match and no-match, handle/catch, deref long form, one function under two handlers) and 16 negatives (cycle, missing module, duplicate alias, private call, unknown export, two ns, `:use`, ns/path mismatch, unhandled imported abort, stateful export, module exporting nothing, undeclared capability, policy denial, unknown qualified name, depth 66, imported handler) |
| `cases.tsv`, `feat-cases.tsv` | label, entry, source path, function, arguments, manifest value or pinned text |
| `oracle-r5.sh` | stage-0 verdicts -> `r5.oracle` (77 lines; 2 stage-0 slots, nice; about 6 s) |
| `r5.oracle` | *measured*: 41 values (20/20 conformance = manifest, 21 feature positives), 32 negatives refused with stage-0's text, 4 feature positives refused by stage-0 for its own reasons |
| `r5.spec` | values for those 4: `p13` 12497500, `p13b` 79800, `p20` 63 (stage-0 verifier: "native artifact oracle inconclusive"), `p23` 705 (stage-0 native: "unsupported effect" for handle/catch, while try across modules runs: `p10`) |
| `check-r5.sh [seed.bin [off]]` | the gate (every compile with `--policy {:allow #{}}`, as the oracle): positives equal; negatives refused with one `seed: E..` line; the 16 `neg/` texts equal to the manifest (TEXT-OK) |
| `baseline-r3.txt` | the R3 seed's run: PASS 37 FAIL 40, TEXT-OK 0 |

R5 acceptance (scripted, after R4): `check-r5.sh` exit 0 (77/77 and 16/16 TEXT-OK); every previous gate (`gates.sh --rung
r4`); fixed point on the **project route** (seed-1 == seed-2 when the seed is built from its namespaces); in-process (B) and
separate (C) images byte-identical on all 77 cases and on the seed itself; G5 on `seed compile` of a 3-module project; the
golden `refusal-r5.txt` (GATES) records the seed's texts for `feat/n*`, whose texts are not pinned by kotoba-lang.

## 9. Work plan after R4 (est.)

| unit | owner | lines (est.) | depends on |
|---|---|---|---|
| 10-lex/11-read: `#?`, `#?@`, lenient skipper, `@`, qualified symbols/keywords | mid | 250-350 | contracts |
| 20-names: ns header (all clauses, attr-map), aliases, refer, qualified resolution, FK-IMPORT, FN2 | strong | 500-650 | interface format |
| 21-check: imports as known signatures, local state, state ability (rows, specialisation, handler checks), ceilings, capability declaration | strong | 900-1,200 | 20-names |
| 30-lower: hidden cell slots, σ stack, RES2/RET2, specialised FNs | mid-strong | 250-350 | 21-check |
| 41-a64gen/42-layout: RES2, RET2, FX-EXT, relocatable blobs | strong | 120-200 | SIR |
| 01-mem `mem-reset`, LINK; 50-out KSEEDO1, image buffer | mid | 200-300 | MEMORY-MAP |
| 60-proj (discovery, loop, link, bounds, dispatchers) + 90-drv CLI | strong | 450-600 | all |
| rung proof: seed split into namespaces (front, lower, back, drv) + gen-ns per namespace | contracts | 150 + edits | 60-proj |

Total about 2.6-3.4k lines; critical path 20-names -> 21-check -> 60-proj -> rung proof, about 6-9 agent-days (est., R1-R3 rate).

## 10. Risks, each with a cheap test

| # | assumption | cheap test | if it fails |
|---|---|---|---|
| R1 | the largest R6 module fits one `M` after arm selection (107k tokens with host arms vs 131,072) | when the lenient skipper lands: token count of machine_ir/desugar/infer through 10-lex with `KEXE_ARENA_USE=1` (30 min) | widen TOK/NODE by relayout (HEAP shrinks), or split machine_ir (R6 owner) |
| R2 | per-module analysis + code link admits exactly the programs stage-0's link admits | `check-r5.sh` feat/ cases + `abort-diff`-style differential over 10 two-module projects generated from the KIR corpus (1 h) | add the missing link-time check found |
| R3 | the R6 image fits the 8 MiB bytes-value bound and the loader's vector budget (M 8.39M + I up to 8.39M items vs `KEXE_VECTOR_ITEMS` 16,777,216 in seed_run) | compile the seed itself through the project route and extrapolate code bytes per source byte to 126 modules (seed: 330,584 bytes from 431,715 source bytes) | raise SEED_VECTOR_ITEMS, pack I 8 bytes per item and convert per chunk, or let the loader read two segments |
| R4 | imperative state lowering equals the reference on every slice-1 program | the 8 conformance + 5 feat state programs; plus 50 random programs over get/put/if/let/loop under 2 handlers, compared with stage-0 where stage-0's verifier answers (1 h) | fall back to the reference's state-passing rewrite with pairs (no RES2/RET2) |
| R5 | `mem-reset` restores "fresh = zero" for every module's state | unit: compile module X alone vs after module Y; byte-identical blob (15 min) | zero the whole regions (cost: 6.4M words per module, est. 5-10 ms) |
| R6 | constants per namespace keep the seed's code identical in behaviour | G1/G2/G4 on the namespace-split seed | keep the seed a unity and prove R5 with a separate multi-module test program only |
| R7 | stage-0 stays a usable oracle for R5 programs | measured: 4 of 41 feature positives already need `r5.spec` (verifier re-derivation, handle/catch); conformance 20/20 fine | widen `r5.spec` with hand-derived values, as R3 did (28 of 54) |
