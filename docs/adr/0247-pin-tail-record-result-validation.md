# ADR 0247: Pin tail-position record result validation

Status: accepted

Amu advances `kotoba-native` to
`dd7fe0cf8972ef20bcc24894b7c7aaf9d086c1a6`. The aggregate ABI remains v6;
the change narrows record result-schema validation to records that can actually
escape in tail position. A differently shaped record constructed only as a
local intermediate no longer causes a false boundary rejection.

The matching verifier remains pinned at
`e2c0e3f49bd7828cd187aee6a90ba5e6f2474149` because the sealed ABI contract,
recursive depth bound, and re-emission rules are unchanged.

The complete consumer closure must still pass the aggregate contract tests,
JDK-free scalar and recursive-record execution through the real W^X loader,
and the recursive-record plus entryless-library Windows profile checks. No
legacy production fallback or held operation is widened by this pin advance.
