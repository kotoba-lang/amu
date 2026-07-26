# ADR 0023 — one-source portable Kotoba tests

- Status: Implemented
- Date: 2026-07-25

## Decision

Kotoba tests are ordinary exported, zero-arity definitions named `test-*`.
They pass by returning Kotoba `i64` value `1`. The compiler command

```sh
clojure -M:run test path/to/module.kotoba
```

checks the source once, assigns a content ID to the selected KIR test
definition, and executes that same KIR through the JVM oracle, restricted ESM,
and Wasm. Expectations live only in the `.kotoba` module; target runners may
adapt values and traps, but must not restate the assertions.

If the module has no `main`, the test harness adds a zero-effect `main`
lifecycle stub before the single checked KIR is produced. This satisfies the
admitted Wasm host contract without adding a target-specific expectation.

An optional exported `test-handler(cap-id, value)` is a deterministic mock
ability handler written in Kotoba. Every target connects its capability ABI to
that same handler. This makes effect programs portable without pretending that
real network, filesystem, clocks, credentials, or process isolation can be
implemented inside the guest.

## Rationale

This follows Unison's useful property that tests are normal, content-addressed
program terms, while retaining Clojure's cross-target source portability.
Target execution remains plural because JVM, JavaScript, and Wasm are distinct
machines; semantic test authorship is singular.

## Trusted boundary

Pure policy and deterministic effect decisions should be Kotoba. Physical I/O,
resource metering, last-boundary provider validation, and sandbox enforcement
remain a small host TCB. Host adapters retain only binding-level smoke tests.
