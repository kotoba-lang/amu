# Native selfhost bounded byte-tree lookup adoption

The native seed compiler replaces a closed, typed i64-to-i64 threshold tree with an immutable byte table when all leaves are bytes, positive thresholds are bounded by 4095, tree depth is at most 12, and the complete owned function is pure and uncharged. Signed negative and high inputs return the original outside defaults before any table read. The original function/register, label ownership, trap, effect, code/fixup/literal budget and epilogue contracts remain admission conditions. No function name or benchmark-specific table enters the production matcher.

The token-table prerequisite expands 393216 records to 524288, shifts the 14 following table bases and heap boundaries by 524288 words, and increases MM-WORDS together with MM-HEAP-END. Compiler model allocation grows 4 MiB; heap usable capacity, guest ABI, guest fuel and loader budgets remain unchanged. The earlier raw-source token-fit claim was withdrawn: drv-run appends ck-r6b-lib before lexing. Failed V2/V3 receipts remain immutable.

Current0276 baseline versus the new G4:

| Workload | OFF ns/body | ON ns/body | C ns/body | exploratory reduction | ON/C |
|---|---:|---:|---:|---:|---:|
| PicoJPEG |121920.41015625|119973.14453125|19727.05078125|1.597161314%|6.081656395|
| QRduino |180495.60546875|172865.234375|38450.1953125|4.227455330%|4.495822010|

Each timing row is one C/OFF/ON trio at n32, calls64, warm1, using BATCH_ABI_RESET_VALIDATION_V1. They are unconfirmed exploratory points, not official Embench scores; no precision repeats occurred. These ratios do not establish the full 19 C target.

PicoJPEG image59412→50924 bytes: one570-byte payload replaces the complete old9120-byte owner. QRduino image33272→25712 bytes: two256-byte payloads replace two4096-byte owners. Whole-image audits account for all removed trees, actual source-derived 14-word prefixes, retained control/ADR/noncontrol instructions, original literal references/pools, and every export.

The same full 16 source rebuilt G2/G3/G4 with byte-identical native images and containers. All 19 unchanged original benchmark sources compiled/extracted successfully (38 calls). Only PicoJPEG and QRduino changed; the other 17 whole native images, containers and exports are identical. Selected95 explicitly combines 10 fresh canonical profiles (0/1/2/17/32 for each changed workload, full result/fuel/arena observations) and 85 exact-identity reused rows. Independent source, machine, stopped-call and final qualification reviews accompany the root receipts. Bootstrap boundary counts and tracked bootstrap seed files must remain unchanged after adoption.

ADR0357 hand-edit exception: a new bounded threshold-tree lowering and atomic internal resource-layout change have no applicable existing AST refactor rule. The full 16 inverse proves only the two owned modules differ, and other 14 are byte-exact. This is an optimizer algorithm and invariant-preserving layout change, not a repeated rename/form port.

Local qualification evidence: /Users/junkawasaki/github/workspaces/codex/bounded-balanced-byte-tree-continuation-root-v4-20261012/cycle.json. Source freeze10099e8f; fixed-point native00ae06cc and container47f60249; primary and QR stopped comparisons73653fe4/9716bf06. Product adoption is local; no network operation is part of this cycle.
