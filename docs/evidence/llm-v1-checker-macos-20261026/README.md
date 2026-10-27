# Native Amu llm-v1 checker boundary (2026-10-26)

The canonical `resources/kotoba/lang/capability-kits/llm-v1.edn` names wire 11,
its five-field request record, and a result variant with nested completion,
usage and error records. This change makes the Mac-native selfhost compiler's
`check` command recognize only that exact nominal type shape. A different
request field type, nested usage field type, or result name fails E2115.

The compiler still has no native structured request/result transport for wire
11. `compile` explicitly fails E3004 before lower can emit a wire-0/kind-0
call. Both `aarch64-macos` and `x86_64-aiueos-user-v3` are covered. No guest
ELF or LLM provider is qualified by this checker gate.

## Local native evidence

- A pinned signed Mac Amu compiler (`5635e728fc49e8d0c7ca3685b5c22ac72bd2d85fae3799a0af45204b8e5f0755`)
  compiled the 47-module `seed/FULL-MANIFEST` unity source with SHA-256
  `11f5c88ac7f7dfd6a11964e22bedb605e07ce2d2099e8965efe81b8943d49f41`.
- The resulting compiler container SHA-256 was
  `55375042523dece49fa830e1c9676808ec96fae21c65dd96573863f97e1f6658`.
  The generated signed Mac image SHA-256 was
  `d86bee40d15a4dae6abf1bd9254e0742c9829575723b83cc0b945deee5f7e030`.
  Recompiling the same unity source with that generated image produced a
  byte-identical container (F3→F4).
- [checker-receipt.json](checker-receipt.json) records two positive checks
  (inline schemas and `[:ref ...]`), three near-miss refusals, and four
  code-generation refusals with no output artifacts. Run
  `python3 scripts/seed/native_build_queue.py -- python3 scripts/seed/check_llm_v1_checker_macos.py --image <signed-image> --expected-image-sha256 <sha256> --output <fresh-directory>`
  to repeat the checker gate.
- An unchanged Mac UTF-8 sample compiled with both the prior pinned compiler
  and the new image to the same 737-byte kseed container,
  SHA-256 `682ab427170c444bd1550384024ed5c988df96edfa520d68795502028c8ef5b5`.

The older `check_macos_fs2_bc.py` gate embeds the prior compiler's exact Linux
artifact size and digest. It reported `compile mismatch` with the new image;
that pinned diagnostic was not used as a regression verdict. The direct Mac
sample comparison above checks an unaffected source without those stale pins.
