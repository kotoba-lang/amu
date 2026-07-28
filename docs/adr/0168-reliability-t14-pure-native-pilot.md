# ADR 0168: T1.4 pure-native-v1 pilot

- Status: Accepted
- Date: 2026-07-28
- WBS: T1.4

## Decision

1. Resource `resources/kotoba/lang-conformance/native-pilot-manifest.edn`  
2. Runner `kotoba.compiler.lang-native-conformance` — signed kexe + loader  
3. Host ISA only (`:x86_64-kotoba-v1` or `:aarch64-kotoba-v1`)  
4. 5 pure cases: i64 arith, nested arith, string-length, concat+length, if  
5. Soft-skip if tender-native absent; CI `:test` alias includes tender-native  

## Related

- T6.1 standalone (kexe secondary path)  
- native-aot-baseline
