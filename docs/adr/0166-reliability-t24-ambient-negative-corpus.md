# ADR 0166: T2.4 ambient negative corpus on compiler frontend

- Status: Accepted
- Date: 2026-07-28
- WBS: T2.4

## Context

Grade A malicious-source corpus (`kotoba-lang` `lang/malicious-source/*`) is the
normative **policy evaluator** corpus. T2.4 also requires the **compiler** to
always reject ambient guest forms (eval/require/atom/interop/…) so security
regressions cannot silently re-admit them.

## Decision

1. Always-on test: `kotoba.compiler.ambient-negative-corpus-test`  
2. Stable codes (T3.1):  
   - `:kotoba.error/ambient-forbidden` — forbidden-heads / interop  
   - `:kotoba.error/max-parameters` — arity > 5  
   - `:kotoba.error/top-level-form` — non ns/def/defn top level  
3. Cross-link pure-product ambient + cap-call/doseq gates (T2.1)

## Related

- `docs/grade-a-malicious-source-corpus.md` (kotoba-lang)  
- WBS T2.4 / T3.1 / T5.4 (max-parameters kept at 5)
