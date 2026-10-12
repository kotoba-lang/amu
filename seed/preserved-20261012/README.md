# Safety-fixed preservation source — 2026-10-12

This is the 16-module compiler adopted on the paused preservation branch
`3eace60393ac711da7f243d72cca813cbe911fef` (source `f86c2a6f0`), integrated as an
independent closure. It does **not** overwrite current main's optimizer, public
CLI, production loader, dependencies or other source migrations. Fifteen modules
remain byte-identical. The driver takes main's explicit-policy E2170 refusal,
and applies that same gate to single-file and project `check` before `ok`.

Until a structured policy parser is qualified, every explicit policy is refused:
empty allow, deny/comment tokens, legitimate grants, malformed or missing files.
This is a fail-closed refusal, not implementation of general policy semantics.
The normal policy-free compile path remains supported.

`adoption.json` pins the new source and safety-fixed native bootstrap. The C
trusted bootstrap loader is the same frozen loader as main's adopted compiler;
the public `tools/kexe_loader.c` and its fuzz fingerprint remain the current-main
pair. Do not reuse the obsolete fuzz pin from the historical branch.

```sh
python3 scripts/seed/build-adopted.py --receipt seed/preserved-20261012/adoption.json --verify-only
python3 scripts/seed/build-adopted.py --receipt seed/preserved-20261012/adoption.json --output /Users/junkawasaki/github/workspaces/codex/preserved-selfbuild-new
```

Qualification in `integration.json`: three generations of byte-identical native
images and containers; 34 policy refusals across compile/check and source-path
routes (nonzero exit 1, E2170, no artifact); policy-free execution result 42;
19 complete native images equal the historical qualified artifacts. This is
correctness maintenance, not fresh Embench execution timing. Historical timings
and mixed 10-fresh/85-reused functional evidence remain in the archive.

The goal remains **paused and unmet**. No performance search, tuning or timing was
performed. New native images are safety-fixed images; old timings must not be
relabelled as measurements of these images. Restart instructions and raw evidence
are in `docs/evidence/native-selfhost-paused-20261012/`.

Explicit `--policy` without a following value is also refused with E2170, never interpreted as policy-free.

Trusted bootstrap loaderはABI v11に対応する凍結fuzz targetを使い、公開loaderは現行ABI v12 targetを使う。両方のsource pin、全reach counter、既存Linux coverage floorを検査する。初回のv12 targetによる未到達はharnessの不整合で、失敗ログを残して適合targetで再検証した。
