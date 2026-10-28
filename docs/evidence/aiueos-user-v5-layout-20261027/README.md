# AIUEOS user-v5 layout candidate

This draft-branch evidence concerns the Amu compiler and bounded payload
artifact. It does not qualify an AIUEOS guest, a typed LLM kit call, an agent
turn, a release, or physical hardware.

- Source commit: `1af8110a3a69c4e88be2fe34c128dfc3cf237e8e` (module changes;
  later descriptor changes leave the 48-module source bytes unchanged).
- FULL-MANIFEST unity: 3,504,276 bytes, SHA-256
  `aa1d418e1c4d95b960f58d75cc46937b6ac3db596d24b45a43df2e0a4b1cf924`.
- Signed Mac Amu F1=F2 container: SHA-256
  `bd147ad9285af834c7b849700b7e26f9ff4f8edb3c899195c8017f0bd161c7f3`.
  Local root-gate receipt:
  `workspaces/codex/jun450-v5-rootpin-20261027/mac-aiueos-user-target.json`.
- User-v5 ELF: RX `0x420000`, RW `0x421000`, 256 KiB reserved;
  payload slot v4 checks the ELF shape. The entry still receives the legacy
  64-byte input. `eb-dual-layout?` rejects slot v4 until a matching guest
  loader and typed request/result ABI exist.
- Local native layout gate:
  `workspaces/codex/jun450-v5-workflow-mode-20261027/mac-aiueos-user-v5-layout.json`.
  It checks the candidate ELF/slot, v2/v3/v4 legacy artifacts, and changed
  entry/RW/extent, slot-version mix-up, and declared LLM-kit refusals.
- [GitHub Actions run 40453725264](https://github.com/kotoba-lang/amu/actions/runs/40453725264):
  Mac root and independent native ARM/x86 cross fixed-point jobs passed.
  Mac-generated ARM and x86 compiler candidate SHA-256 values are
  `e46456282e73786782d6160fefdf62d5eecf289b903cd6538ece9e641efdb17d`
  and `d115cde2c4d7a5a09c4a66cccfb47d423563866d3a70f6a0aa9061c94005c421`.

The complete native corpus and public product gates for the newly pinned
images still require exact-head CI. The scorecard and release gates are
separate. No Linux, JVM, Node, or C compiler was used to build or execute the
AIUEOS guest in this evidence; the Linux jobs independently verified compiler
artifacts generated on Mac.
