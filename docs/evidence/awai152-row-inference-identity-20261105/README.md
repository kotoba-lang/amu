# Row-inference identity gate after atomic record refusal

Amu #1824 macOS CI run `41900050636` passed the JUN-733 row-inference native
corpus and its eight listed refusal checks, then failed the annotated identity
case: the gate expected per-definition `REFUSED:unbridged-source` rows but
the compiler returned exit 66, empty stdout and `DSB:BRIDGE:3:9`. Both the
annotated and inferred-row examples contain `defrecord`; the current definition
bridge refuses its unbridged constructor atomically. The gate now requires
exit 66, empty stdout and `DSB:BRIDGE:3:` for each example. It makes no claim
that their CIDs match.

On local Darwin ARM64, the signed compiler from prior CI run 41891665699,
SHA-256 `703709f8bc10efe3b50ac23e5a80e48655049891bf66b13211745ce9aeb9fe50`,
returned the expected atomic refusal for both examples. A separate scalar
definition produced a CID and `SCANNED 1/1`. Native child processes had a
three-second CPU limit and no hard memory cap. This was not the current CI
compiler or the full row-inference mutant gate; both still require current-head
CI. It does not qualify a resource governor or an inference workload.
