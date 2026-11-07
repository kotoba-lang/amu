# ADR 0411: The pure heads lower in seed/20-names (JUN-950)

- Date: 2026-11-07
- Status: Accepted
- Implements: part of stage S1 in kotoba-lang `docs/adr/ADR-target-portable-canonical-form.md`
- Spelling authority: kotoba-lang `lang/pure-form.edn`

## Context

The accepted pure form writes a definition as `(def inc1 (lam [n :i64] :i64 (+ n 1)))`.
The native frontend refused `lam`, `app` and `ref` with E2101, while the pure library
sources in `kotoba-lang/kotoba` already spell about 1,300 calls `(app (ref f) ..)`.

Those three names are also ordinary names in production source. `app` is a parameter
and a let binding in several modules, so reserving them would change working programs.

## Decision

`nm-pure-norm` in `seed/20-names.kotoba` rewrites the tree before any name is registered:

| Pure spelling | Lowered to |
|---|---|
| `(def NAME (lam [x T ..] R BODY))` | `(defn NAME [x T ..] R BODY)` |
| `(lam [x ..] BODY)` | `(fn [x ..] BODY)` |
| `(ref NAME)` | `NAME` |
| `(app NAME a ..)` | `(NAME a ..)` |
| `(app COMPUTED a ..)` | `(invoke COMPUTED a ..)` |

- The names are not reserved. A module that defines or binds a spelling, as a top-level
  name or inside a vector, keeps its own meaning for that spelling.
- E2184 refuses a `lam` with other than one body, or a top-level `lam` without every
  parameter and its result annotated.
- `(ref "bafy..")` stays E2101. Reading a definition by CID is separate work.
- No head code, checker path, lowering or emitter changes.

`(app (ref f) ..)` and `(ref f)` are admitted because existing sources use them.
`lang/pure-form.edn` does not keep them after conversion, and whether to keep them is
recorded as an open question on JUN-950.

## Evidence

`scripts/seed/check-pure-forms.py`, on the Mac fixed point of this tree:

- The corpus builds and exits 0, and `bin/amu run` prints 0.
- 15 refusals are checked by code, and 5 modules keep their own meaning of a name.
- Pure and surface spellings print the same Definition CIDs, with a differing control
  for each group, including `loop` against a tail-recursive `def`.
- 5 mutant compilers each fail in the named way.

One-time comparison against the previous root compiler on 2026-11-07, over 159 sources
(`lang/conformance` and `seed/tests`) and 4 targets: 172 artifacts byte-identical,
464 refusals identical, 0 changed.

## Not established

- `(app (lam ..) a)` runs, but `definition-cids` reports `REFUSED:unbridged-source`, so
  the corpus pair `:let-fn-vs-beta-redex` remains unmet.
- Of the 10 library files using `(app (ref ..))`, 1 now checks alone. The others stop at
  other gaps: missing `--source-path` modules, type mismatches and two-argument `record-get`.
- `.kotoba` still admits sugar, and no source has been converted.
- Native records, protocols and multi-arity spellings from `lang/pure-form.edn` are unchanged.
