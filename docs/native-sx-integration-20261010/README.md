# SX native SOURCE integration evidence

This record supports the local source integration of the frozen cumulative SX SOURCE into the separate worktree based on `833487fcd03a14708f09823b4cfca974089f9227`. Root reconstructed the destination full16 source: it is byte-identical to the verified frozen unity. This integration reuses the recorded native evidence by exact source identity; it does not claim a newly executed repository build or a product binary release.

## Exact source boundary

Only `seed/40-a64enc.kotoba` and `seed/41-a64gen.kotoba` differ from the base commit. All other 14 registered modules are byte-identical. The encoder grows 12,913→13,205 bytes and adds the guarded signed post-index pair-store encoder (`enc-stp-post`, canonical base/data overlap refusal, SP exemption). The generator grows 124,486→228,114 bytes: it contains the cumulative retained semantic optimizer stack, including the reviewed fuel/typed-runtime ledger work, scalar/boolean and bounded table/reduction/copy specializations, charged associative wrapper, table-prefix preservation and finally generic unsigned-shift/low-mask extraction. It is not an SX-only patch; import the exact reviewed cumulative bytes rather than reconstructing selected edits.

Frozen generator SHA256: `c1572fd58becb7d1fb5bbb004d6e7a22bd374c9568ca805c59064ae23018b118` (228,114 bytes). Frozen encoder SHA256: `6d390b592c95ab26dd43138b3519c33a4a8ae26526151dcfa7135bb1b9fe7ab0` (13,205 bytes).

The full16 SOURCE is reconstructed in registered order by joining the 16 module byte streams with a newline and appending a final newline. This draft independently reproduced exact unity content: 1,159,711 bytes, SHA256 `546d9f676e585be7e1826ca465e609273d948ac8f862930a376a8db96f0d7044`. The accompanying evidence index records every module's base/current digest. Root repeated this reconstruction in the destination worktree and obtained the exact unity hash above. The bootstrap-boundary inventory is byte-identical before and after; git diff --check passes.

## One-off hand-edit exception

`AGENTS.md` requires AST refactor tooling for mechanical changes and permits hand edits when no existing rule covers the change, with the reason recorded in the commit message. These additions implement new semantic emitter/matcher and encoding contracts: typed admission, operand/register protection, original fuel and trap fallback, literal/branch fixups and instruction generation. They are not a namespace move, rename or repeated same-shape mechanical refactor. The recorded exception applies to this cumulative backend feature integration only. No AST plan/apply/verify execution is claimed. Copying the exact frozen two-module result does not authorize unrelated hand transformations.

Suggested commit-message note: “One-off backend semantic-feature exception: existing AST refactor rules do not implement the new guarded A64 emitter/encoder contracts. Import exact reviewed cumulative SOURCE; retain all 14 unrelated modules byte-for-byte.”

## Saved native evidence and limits

- Native fixedpoint: root-owned six-call execution closed with exit 0 (`42bf61`, session 18875). Whole G2/G3/G4 native payloads are equal at 961,640 bytes, SHA256 `0ab4687eeb55dd9ed177e9ae56b73fdb64f6812b330aa9dde74585faa273914a`; containers are equal at 961,666 bytes, SHA256 `b31547cd22e02b735661bcdb48d7c84372790c50636883c38f62c0feb00e691a`. The report requires G2/G3/G4 equality; G1 equality is not a prerequisite.
- Original19 selected95: saved mixed composition reports 90 exact-image reused profiles plus five fresh AES profiles. It binds the new stable compiler, original19 artifact completion, reuse classification, prior selected95 and the fresh AES root closure/raw review. This establishes the recorded selected functional observables through composition, not 95 fresh executions. Fresh AES closed exit 0. The composition is a saved Dense artifact, not an independent claim made by this document.
- SX boundary20: root-owned exit-0 closure (`a37c6c`, session 50099) records 20 closed starts and 10 whole paired reports equal. Cases include measured fuel budgets 1/2/3 and seven additional full64 shift/mask selectors. Public charged entry evidence and normal consumed fuel 2 were measured; helper SIR fuel classification was not invented from source syntax.
- AES exploration7: root-owned exit-0 closure (`2b07f6`, session 43337), three full observable pairs equal. The short reset/ABI/validation-inclusive comparison was an exploratory signal (~7% shorter than its immediate prefix baseline). It is not a pure-kernel clock, official score, calibrated full19 C comparison or physical-memory qualification. C≥ and performance adoption remain unresolved.

All exact receipt paths, sizes and hashes are in `evidence-index.json`. Closed root receipts and their referenced completion hashes were checked while preparing this draft. This work launches no compiler, guest, network or repository mutation. Frozen failed scopes and dropped experimental cache/four-lane branches remain outside this integration.
