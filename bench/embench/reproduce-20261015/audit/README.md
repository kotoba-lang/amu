# Kernel audit of the m93 compiler (be7f0ce3)

The certified kernels of the compiler that produced the published 15 October 2026 round are being audited against the
"same algorithm only" kernel scope policy (see the package README, section "Kernel scope"). The audit tables will be added
to this directory when they are complete (one row per kernel: workload, source function(s), class same-algorithm /
substitution / unsure, reason, the policy item that applies, the commit that introduced it, and whether a same-algorithm
version is possible).

Whatever the audit finds, the rest of this package keeps reproducing the published round exactly as measured. After adding
files here, regenerate `SHA256SUMS` with `python3 tools/make_sums.py`.
