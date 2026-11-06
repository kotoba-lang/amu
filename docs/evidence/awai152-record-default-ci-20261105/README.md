# Record defaults in the JUN-734 gate

Amu PR #1824 macOS CI run 41893306351 (head `3064aafae6a1d1dc2cac76a109eaa73f8c503338`,
merge base `5d2776bd77d8ad835fabed8280a30b5f1f21ecd5`) passed the earlier
keyword-map and destructuring gates but failed when the JUN-734 gate expected
record keyword defaults to be refused. The merged main's JUN-733 logic permits
such defaults. The obsolete two refusals are replaced with four native corpus
assertions: present and missing keys on a named record and on a literal record.
A type-incompatible default on a present record field remains an E2104 refusal.

The updated corpus passed native `check`, compilation and execution with the
CI-produced, strictly signature-verified compiler SHA-256
`703709f8bc10efe3b50ac23e5a80e48655049891bf66b13211745ce9aeb9fe50`;
the E2104 negative was checked too. The diagnostic FS2 packager SHA-256 was
`f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d`.
The corpus SHA-256 was
`22410ad05d4c513f69800855f4a959b54c76ad703565a29cbaa7534fb7c35829`;
`verify.py` SHA-256 was
`1758881ec1435e89e9f81ad348d70c331d91fd5ef05be2f2055e8d4040aa2a46`.
The source anchors for all six existing JUN-734 mutants each matched once in
the CI merge base; their actual execution and the full gate await new-head CI.
These are low-load local diagnostics with a three-second CPU cap, not a native
governor, production host or a release qualification. The test script uses
local CI-artifact paths and is not a deployment command.
