# Mac selfhost user-v3 root and bounded cross check (2026-10-26)

The [Mac root receipt](mac-root.json) rebuilt all 47 canonical Kotoba modules
from the repository bootstrap compiler to an F1=F2 native Amu compiler. The
source unity SHA-256 is
`728f4fed3a6735696e92d6cfb8945fef7d4c8d5361c155d47e3ccead487c6dc3`;
the fixed compiler container SHA-256 is
`0b0d1229881d8746fbe305798c80cfd4e55eaaf64d18d72fddcc27803c1e074f`.
The [user-v3 gate](mac-user-v3.json) reproduced its ELF byte for byte,
checked the 16-byte-aligned syscall trampoline and refused that operation in
the v2 target. The ELF SHA-256 is
`331a3ed64c5859bc546a36ce9666e1a1e17e31195caca96407def6f63f5cc7b1`.

The [Mac cross record](mac-cross.json) binds the ARM root at
`2264537598cb8c09fdbbe805fc24ecc20b500743c02663a6ccdcdc09cbcc2714`
and the x86 public compiler at
`ebc2a164799a950e52958f78d107d731d2f8ab0e9c9aa17ae81e39588528d51f`.
The exact source, fixed container and both ELF digests matched the
[CI Mac producer](https://github.com/kotoba-lang/amu/actions/runs/40259071903).
The same run's native ARM and x86 jobs each executed two further generations
and reported `PASS_MAC_CROSS_NATIVE_FIXED_POINT` with those ELF digests.
Linux was an independent verifier of Mac-produced bytes, not a build input
for AIUEOS or the user-v3 ELF.

Those bytes are pinned in the repository ARM root and public `bin/amu` as
current-source candidates. `check-native-identities.py` passed against the
new pins. The native full corpus, controller, public consumer and terminal
exact-head CI remain separate requirements; these bounded fixed-point checks
do not qualify a release, a physical machine or an Itonami agent loop.
