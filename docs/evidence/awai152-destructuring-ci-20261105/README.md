# Destructuring CI update after record defaults

Amu PR #1824 CI run 41891665699 (head `d43d31068590b76ea587177ee235d414efecdcf3`,
merge base `5d2776bd77d8ad835fabed8280a30b5f1f21ecd5`) passed the JUN-728
keyword-map mutant controls, then failed JUN-729 because the old
`or-on-record` case expected E2104 but the compiler accepted it. The merged
main source explicitly supports defaulted record lookups. The stale refusal is
replaced by a corpus assertion that a present record key takes its actual
value instead of the default. A missing destructuring key remains a separate
E2111 refusal; it is not claimed to be supported by destructuring.

`verify.py` checked the modified corpus and compiled and ran it natively on
Darwin ARM64. It also checked the missing-key E2111 refusal. The compiler was
the CI-produced, strictly signature-verified artifact retrieved from that run's
`mac-aiueos-user-root` provenance, SHA-256
`703709f8bc10efe3b50ac23e5a80e48655049891bf66b13211745ce9aeb9fe50`,
matching the compiler hash reported by that run. The diagnostic FS2 packager
SHA-256 was
`f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d`.
Corpus SHA-256:
`473ff9b0078df2c54449b5ca9da656c55e19294dabeab4501baacd5dae16388e`.
The processes had a three-second CPU cap and no hard memory cap. The two
existing destructuring mutant source anchors were also found exactly once in
that merge base. The full destructuring CI gate and mutants still need to run
on the new PR head. The diagnostic script uses local temporary artifact paths;
it is not an operational command or governor qualification.
