# ADR 0168: T1.4 pure-native-v1 pilot

- Status: Accepted
- Date: 2026-07-28
- WBS: T1.4

## Decision

1. Resource `resources/kotoba/lang-conformance/native-pilot-manifest.edn`  
2. Runner `kotoba.compiler.lang-native-conformance` — signed kexe + loader  
3. Host ISA only (`:x86_64-kotoba-v1` or `:aarch64-kotoba-v1`)  
4. The manifest is the counted source of truth for the bounded native cases.
5. Soft-skip if tender-native absent; CI `:test` alias includes tender-native  

## Follow-up: context ABI v3 (2026-08-04)

ADR 0212 expands the pilot to 16 cases and adds real signed-kexe execution for
immutable `vector-i64` and `vector-f64` values. The compiler, native backends,
verifier, and POSIX/Windows loaders agree on context ABI v3; the manifest count
test prevents a new case from silently escaping the runner.

## Related

- T6.1 standalone (kexe secondary path)  
- native-aot-baseline
