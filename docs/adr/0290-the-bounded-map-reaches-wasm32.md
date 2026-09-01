# ADR 0290: The bounded map reaches wasm32, and the conformance case that needed it passes

- Status: accepted
- Date: 2026-09-01

## Decision

`lang/conformance/manifest.edn` in `kotoba-lang/kotoba-lang` declares
`:bounded-control-match-and-pure-desugar` with
`:required-backends #{:kir :wasm32-kotoba-v1}` and `:expect {:kotoba 21}`. Its
fixture, `control/match_desugar.kotoba`, joins a `loop`/`recur` sum to a
`match` over a bare `{:value 9}` literal through a `defdesugar`.

KIR ran it. wasm32 refused it. The case is now in this repository's
dual-backend pilot and passes on both.

## What the refusal actually was

Not `match`. Measured 2026-09-01 against this repository at `27d82d8`, through
the JDK-free `bin/amu` path, `compile --target wasm32`:

| program | exit | message | `:operation` |
|---|---|---|---|
| `(defn main [] (match 5 0 100 5 200 :else 300))` | 0 | — | — |
| `(defn main [] (get {:value 9} :value))` | 70 | `typed Wasm operation is not qualified` | `map-get` |
| `(defn main [] (match {:value 9} {:value n} n :else 0))` | 70 | `unsupported typed Wasm expression` | `map-new` |
| the fixture | 70 | `unsupported typed Wasm expression` | `map-new` |

Row one is the control: `match` with no map in it compiles, and the artifact
answers `200n`. The cause is the BOUNDED `:map` value type — what a bare map
literal desugars to.

Rows two and three are **two distinct refusal sites**, not one message
reported twice, and closing either alone left the other standing:

- `map-get` reached `kotoba.wasm.core`'s `emit*` fallthrough: it is neither an
  emitter case nor a function in the module.
- `map-new` reached `kotoba.wasm.typed/infer-type`: a `let` needs the STATIC
  type of its init, and there was no inference case. Row three has a `let`
  because that is what `match` lowers its scrutinee to; row two has none.

So which message a program got depended on whether it bound the map to a
local, not on anything about maps.

## Why nothing had noticed

Every map fixture already in this pilot writes `typed-map-*` explicitly
(`values/typed_map_kit.kotoba`, `values/typed_map_dissoc_kit.kotoba`), which is
the canonical parametric map and has been emitted since the typed value ABI
landed. `kotoba-wasm`'s own suite contained no `map-new` at all. A bare map
literal had never been asked of this backend.

## Change

- `kotoba-lang/kotoba-wasm` `cc23ea3` (ADR 0048 there) adds
  `kotoba.wasm.typed/lower-bounded-maps`, which rewrites `map-new` /
  `map-get` / `map-assoc` and the `:map` signature type onto
  `[:map :keyword :i64]` and the canonical `typed-map-*` operations, over the
  whole module, before signatures, the descriptor table, the literal table,
  inference or emission see it. The bounded map already IS that descriptor:
  `kotoba.compiler.frontend` checks every key as `:keyword` and every value as
  `:i64`, so no source can spell anything else into it. No new map
  representation was added.
- This repository advances its `kotoba-wasm` pin to `cc23ea3`, regenerates
  `deps-lock.edn`, and adds the authority's case to
  `resources/kotoba/lang-conformance/pilot-manifest.edn` with its fixture
  copied verbatim.

## Evidence

`clojure -M:conformance`: **62 / 62 passed (57 pure-product, 5 portable)**, up
from 61 / 61 (56 / 5). The new case is
`:bounded-control-match-and-pure-desugar`, and it passes on `:kir` AND on
`:wasm32-kotoba-v1` — the runner executes the wasm artifact through
`runtime/browser-host.mjs` on Node and compares the scalar it returns to
`:expect`.

`clojure -M:conformance --write-golden` added exactly one row and changed no
existing digest: the lowering is a no-op for every module without a bounded
map, and the 61 pre-existing cases prove it byte for byte. The new row is
`:kir-sha256 a43416af…`, `:wasm-sha256 ef5e8fc8…`, 2193 wasm bytes.

Directly, outside the runner: the three previously-refused programs emit and,
instantiated through `runtime/browser-host.mjs`, `main()` answers `9`, `9` and
`21` — the same values `kotoba.kir/execute` answers for the same modules.

## What is still not carried

`kotoba.kir.value/map-entry-limit` admits **128** entries for the bounded map
on the KIR oracle. The typed value runtime rejects a **32nd**
(`browser-host.mjs`: `typed map entry budget exceeded`). A bounded map literal
over 31 entries is now refused at compile time by name — `bounded map exceeds
the typed map entry budget` — rather than emitted into a module that traps.

**wasm32 carries the bounded map up to 31 entries.** 32..128 are admitted by
the frontend and by KIR and refused by the backend. That gap is recorded, not
closed; closing it would mean changing the typed value domain and every host
that implements it.

Nothing was measured for `wasm32-browser-kotoba-v1`, `wasm32-wasi-kotoba-v1`,
the Component path, a browser engine, or the native backends. The authority's
`:map-literal` entry claims `:implementation #{:compiler :kotoba-wasm
:kotoba-cljs}`; only the `:kotoba-wasm` half of that claim was tested here.
