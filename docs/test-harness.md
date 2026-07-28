# Official `.kotoba` test harness (T9.3)

## Contract

1. Export zero-arity functions named `test-*` (not `test-handler`).  
2. A test **passes** only when it returns **i64 1**.  
3. Optional `test-handler` for deterministic capability stubs.  
4. Runner executes the **same checked KIR** on JVM oracle, restricted ESM, and Wasm.

## CLI

```bash
clojure -M:run test path/to/tests.kotoba
clojure -M:run test path/to/tests.kotoba --json
```

Human mode prints `kotoba test: P/T passed` and lists failures.
`--json` prints the full report EDN/JSON-friendly map.

## Fixture

`resources/kotoba/test-harness/smoke.kotoba` — add/string smoke tests.

## Related

- `kotoba.compiler.test-profile`
- ADR 0171
