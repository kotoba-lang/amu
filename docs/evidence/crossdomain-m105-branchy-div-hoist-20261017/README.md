# T2 branchy/access-free constant-division hoist

This is an unpromoted selfhost compiler experiment from 2026-10-17. It is not
an official Embench timing result and does not establish a speedup.

## Evidence

- `source.patch` is the experimental T2 change against the worktree base.
- `report.json` records the native selfhost G1/G2/G3 fixed point and source
  unity hash; `selfhost-calls.json` records compiler invocations.
- `codegen-comparison.json` and the two disassemblies show new `smulh` fast
  copies in the strings and collections fixtures; guarded `sdiv` sites remain.
- `fixture-exactness.json` records six input/result/fuel checks per fixture.
- `callback-equivalence.json` covers 32 valid UTF-8 code points through the
  string callback slow path.
- `all19-build.json`, `all19-images.json`, and
  `all19-image-comparison.json` record the 19 pinned port builds and show that
  no native image changed relative to the current M105 image set.
- `all19-exactness.json` records the official 19/19 result, fuel, and arena
  accounting pass.
- `exploratory-abba-results.json` preserves the loaded-host measurements.
  `baseline_candidate` stores candidate/baseline time; `candidate_C` stores
  C/candidate time. Both are exploratory because the host load averages were
  114.02 at start and 123.21 at end.

All elapsed values from exactness runs are excluded from performance analysis.
