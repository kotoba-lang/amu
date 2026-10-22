# ADR 0363 — An imported aborting function passes its abort on

- Date: 2026-10-02
- Status: Accepted (language rule; analysis `docs/selfhost-efficiency-analysis-20261002.md` item C4, which gates A2,
  the linked frontend differential).
- Amends: `kotoba.compiler.project` `stub-form` (the import stub an importing module is analysed against), and the
  linker's filtering of stub functions.
- Related: `docs/selfhost-frontend-typemodel-design.md` (where the porters recorded the gap and its workarounds).

## Rule

A call to a function imported from another module of the project types and propagates exactly like a call to a
function of the same module. If the imported function can abort with error type E, the call has the authored result
type T, the calling function aborts with E, and a `try` / `catch` of E in the importing module catches it.

## Context

The frontend lowers a function that can `throw` (or that calls one that can) to `:effects #{:abort}` with the result
`[:result T E]`. Within a module, a call to such a function is woven into the caller's lowering (a `result-match-of`
that re-raises the error). Across modules, the linker analyses the importing module against an import STUB built from
the dependency's interface. The stub was a plain function declared to return the lowered `[:result T E]` (body:
`(result-ok-of ...)`), with no `:abort`. So the call typed as a value of `[:result T E]`:

| call shape in the importing module | before |
|---|---|
| tail position, `let` init | `expression type mismatch: expected i64, got [:result :i64 :string]` |
| an `if` branch | `if branches must have the same value type` |
| inside `try` | `try body and catch handler must have the same value type: [:result :i64 :string] and i64` |
| a discarded `let` statement | type-checked, and the error was silently dropped at run time |

Inside one module the same code checks and propagates. The compiler's own ports carried module-local copies of every
aborting helper they imported because of this (`type-valid!` for `validate-value-type!`, `require-k`,
`ae-let-body`, `ae-if-parts`, `dispatcher-name-for`, and error builders exported instead of throwing functions).

## Decision

The stub of an aborting export (`:abort` in its effects, result `[:result T E]`, no callable result contract) is
declared with the authored result T, and its body throws a value of E:

```clojure
(defn- kotoba_import__0 [x :i64] :i64 (throw ""))          ; E = :string
(defn- kotoba_import__1 [s :string] :string (throw (kotoba_import__1__abort_error)))
(defn- kotoba_import__1__abort_error [] [:ref :lib/err] (kotoba_import__1__abort_error))  ; E has no literal
```

The importing module's frontend then infers `:abort` with error type E at every call, exactly as it does for a
function of its own. The stub is analysed, never linked. Each call is rewritten to the dependency's linked
function, whose lowered result is the same `[:result T E]` the importing module's lowering now expects. The error
helper (only for an E with no closed literal) is analysed with the stub and removed with it. A multi-arity export
gets one clause per arity, and each clause aborts or not as its own analysis says. Two arities that throw different
unclosed error types are refused by name (`aborting import arities throw different unclosed error types`).

## Evidence

`test/kotoba/compiler/project_abort_import_test.cljk` (nbb, 21 assertions) links a library that exports
`need-pos!` (E = `:string`), `need-name!` (E = `[:ref :lib/err]`), a two-arity `need-small!` and a plain function,
into a root that calls them in tail, `if`-branch, `let`-init, discarded-statement and `try` positions. Every export
links. On the reference interpreter the dependency's error reaches the root's export (the discarded statement
included), and the root's own `try` catches `:string` and `[:ref :lib/err]` errors. With the previous
`project.cljk` the same test is refused at link time (`try body and catch handler must have the same value type`).
`project_test`, `project_template_test` and `project_loop_helper_test` fail the same 8 assertions under nbb with and
without the change (pre-existing, unrelated).

Repro of the gap on the native checker (before; the checker binary predates this change): `abx.use-tail`,
`use-if` and `use-let` were refused as in the table, while `use-stmt` and the single-module `local` were OK.

## Consequences

- Modules may import aborting helpers instead of carrying local copies. Removing the copies is left to each port's
  owner, guarded by that port's differential.
- The native-image checker (bootstrap reference) needs a rebuild to pick this up (requested in
  `/private/tmp/rebuild-request.txt`).
