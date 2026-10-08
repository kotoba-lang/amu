# V3 resource diagnostic design: HOLD

V2 failed closed before returning a process handle, with a generic preexec_fn exception. The saved raw files are empty. The exact failing resource setter is unknown. Current read-only FSIZE, CPU and AS limits all equal Python resource.RLIM_INFINITY; current evidence does not support inherited finite-hard-limit raising as the cause. V2 remains unchanged and is never retried.

The smallest next gate is one ordinary Python child that installs the three mandatory limits in fixed order and records exact per-limit outcomes. It executes no loader or native compiler. Both soft and hard targets are capped at the inherited finite limits and policy budget. Missing AS support remains a failure. A named limit error or readback mismatch stops the diagnostic, preserving the record. No alternative memory policy is selected implicitly.

The one-child diagnostic requires a separately frozen adapter and exact root/independent SOURCE review before installation trials. A successful diagnostic does not authorize native8, which would require another fresh bounded source/preregistration/GO.

Concrete adapter run.py starts exactly one pinned Python diagnostic-child.py, with no preexec_fn. The child fsyncs a bounded journal before emitting each record. Parent retains at most64KiB per raw pipe, supervises10s wall and5s reap, and writes terminal evidence before completion. Installation/readback refusal is a terminal failure with raw evidence, never an equivalence result. The interpreter executable is pinned; platform shared-library/stdlib closure remains outside this narrow diagnostic claim.
