# Official `.kotoba` test harness (T9.3)

## Contract

1. Export zero-arity functions named `test-*` (not `test-handler`).  
2. A test **passes** only when it returns **i64 1**.  
3. Optional `test-handler` for deterministic capability stubs.  
4. Runner executes the **same checked KIR** on JVM oracle, restricted ESM, and Wasm.

## CLI

```bash
amu test path/to/tests.kotoba
amu test path/to/tests.kotoba --json
amu test path/to/tests.kotoba --fuel 5000000   # per-test budget (ADR 0349)
```

Human mode prints `kotoba test: P/T passed` and lists failures.
`--json` prints the full report EDN/JSON-friendly map.

Every test runs on its own instance on the js and wasm probes, so the fuel
budget (`--fuel`, default 512) is per test. The interpreter target traps
self-recursion deeper than 100 frames whatever the budget (reported as
`fuel-exhausted`); write such walks as `loop`.

## Fixture

`resources/kotoba/test-harness/smoke.kotoba` — add/string smoke tests.

## Related

- `kotoba.compiler.test-profile`
- ADR 0171
