# Seed contract requests

Append one dated line per request: `- 2026-10-02 <module>: <what is wrong or missing in MEMORY-MAP/HEADS/SIR/MANIFEST> -- <the choice you used meanwhile>`.
The contracts owner answers by editing the contract (then `scripts/seed/gen-ns.sh`) and appending `-> done <commit>`.

- 2026-10-02 contracts: (T2) `string-length` = pair_second (72), `typed_cap_call(ctx, wire, kind, kind, req)`, string literal = pair_new(code-relative offset, len) -> done (seed/SIR, from docs/selfhost-seed-t2-t3-20261002.md); 41-a64gen re-checks string-length on non-literal strings.
- 2026-10-02 contracts: OPEN (T3, owner 02-io) stage-0 native-image refuses a computed `:bytes` argument to `typed-cap-call :fs/app-data :bytes :bytes` ("typed values currently require ..."), also for scripts/selfhost-wall/bytes-cap/probe.cljk. Same report: docs/selfhost-seed-t2-t3-20261002.md (fixed in osaho e77ffff; needs a stage-0 rebuild). Fallback in place: `SEED_HEX_STDOUT=1` in scripts/seed/build.sh (hex on stdout, `xxd -r -p`).
- 2026-10-02 contracts: OPEN (T1 defect 1) stable amu-native answers `internal compiler error` on 12/19 ports and on some seed-style constructs (MEMORY-MAP rule L13); seed-0 (build.sh 0) needs the rebuilt image or a JVM stage-0 for step 1.
- 2026-10-02 41-a64gen (stage-0 defect, measured): the stable native amu-native answers 'internal compiler error' on ANY and/or/not (one-line probes: (if (and (>= x 0) (<= h 5)) 1 -1), (or ..), (not ..); the same without and/or/not compiles) -- seed code must use nested if / i64 flags until stage-0 is rebuilt; suggest adding this to MEMORY-MAP rule L13
