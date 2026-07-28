# ADR 0170: T9.2 check + pure-product profile; T3.4 human diagnostics

- Status: Accepted
- Date: 2026-07-28
- WBS: T9.2 / T3.4

## Decision

1. `kotoba check <file> [--profile pure-product] [--json]`  
2. `check-source` accepts `:language-profile` without poisoning capability admission  
3. Default CLI mode: human `error: <code> at <file>:<line>:<col>: <msg>`  
4. `--json` keeps `kotoba.cli-error/v1` / `kotoba.check/v1` envelopes  

## Related

- T2.1 pure-product admission, T3.1 error codes
