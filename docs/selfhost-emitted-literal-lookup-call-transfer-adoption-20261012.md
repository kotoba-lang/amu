# Native selfhost emitted literal lookup call transfer — 2026-10-12

The compiler reuses an already emitted dense byte lookup directly at eligible call sites. This generic rule requires a completed typed owner, the exact emitted prefix and literal fixup, and equality of every literal byte with its SIR value. It preserves full-width unsigned bounds/default behavior, caller preparation/restoration, and all existing fuel, trap, and publication operations. Seven SGlib calls use the certified lookup. The guest image grows 224 bytes and reuses the same 100-byte literal pool.

The local comparison measured 43,790.039 ns/body before and 43,509.766 ns/body after: a 0.640039% reduction. C measured 8,650.391 ns/body; this candidate is still 5.0298 times slower in this comparison. This is one coarse timing trio, unconfirmed and not an official Embench score. The small positive point is retained under the requested fast-cycle policy; there were no precision repeats.

Validation passed source controls (134 refusals, 2,264 full-width traces), four native compiler calls, saved machine translation audit, and byte-identical native images and containers across G2/G3/G4. All original 19 workloads were generated/extracted in 38 calls. SGlib alone changed; the other 18 native images and containers are byte-identical. The 95-profile record has five fresh SGlib executions and 90 exact-image reused results. Result, fuel, and all 17 arena counters match. Independent source, machine, and final saved-evidence reviews passed.

This is a local source adoption on parent e4b28f9782b8f2d613c89a928f2ae18e2eca50ce. Bootstrap reports and seed binaries remain exact. Normal Git hooks are used. No network publication is part of this adoption.

ADR 0357 exception: this is a novel optimization algorithm with a new exact typed-owner/literal certificate and call-edge emitter, rather than a repeated textual refactor. No applicable AST refactor rule exists. The hand edit is confined to seed/41-a64gen.kotoba and was validated with a full inverse, the other 15 unchanged modules, source falsifiers, emitted-machine audit, and native selfhost qualification.

Root proof bundle: /Users/junkawasaki/github/workspaces/codex/current-emitted-literal-lookup-call-transfer-adoption-root-v1-20261012/report.json
