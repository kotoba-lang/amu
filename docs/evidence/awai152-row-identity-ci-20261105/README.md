# Row identity gate after record-constructor refusal

Amu PR #1824 macOS CI run 41895873289 failed the JUN-733 row gate on
`definition-cids update-sugar`: the compiler returned exit 66, empty stdout
and `DSB:BRIDGE:3:9`, while the gate expected per-definition refusal rows.
The definition bridge explicitly refuses `defrecord` atomically; the existing
closed-dispatch gate already checks that contract. The row gate now requires
the same atomic refusal separately for both update examples and no longer
claims CID equivalence for forms whose identities cannot be emitted.

On local Darwin ARM64 the signed CI-generated compiler from earlier run
41891665699, SHA-256
`703709f8bc10efe3b50ac23e5a80e48655049891bf66b13211745ce9aeb9fe50`,
returned exit 66, empty stdout and `DSB:BRIDGE:3:9` for each of the two current
example sources. A separate scalar definition returned exit 0 and `SCANNED
1/1`, confirming this compiler can produce an identity on that control.
Each process had a three-second CPU cap; no hard memory limit was applied.
The compiler is from a prior CI run, not a rebuilt compiler from this merge.
The full row gate, its compiler mutants and the current head CI have not been
executed by this local check. No governor or deployed workload is qualified.
