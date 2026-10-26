# Amu user-v3 against current main (2026-10-26)

The user-v2/v3 source stack at `01a98f22ce65c4910c443f17431c684c5c3802f8`
was merged in an isolated worktree with `origin/main`
`57d18c983c449979cf92e592fb24167f26ed09cb`. The main branch's
user-v1 zero-argument refusal and Mac Darwin execution smoke were retained.
The merged tree has 47 canonical modules. An Apple Silicon Mac ran the pinned,
signed native Amu compiler and packager without Linux, JVM, Node or C compiler
execution for this build.

- [Mac root receipt](mac-root.json): F1=F2 compiler container
  `476a5348561679bf49b0c50c20868fa0a5950a8828bde5665457e7499e3b364b`;
  source unity `fabcaef2ae2ac18230580033d38583ca79d0ae93d7b483a50500eb0b1505cb55`.
  The user-v1 effect and parameter refusals passed.
- [User-v3 receipt](mac-user-v3.json): bounded local-model ELF remains
  `331a3ed64c5859bc546a36ce9666e1a1e17e31195caca96407def6f63f5cc7b1`.
- [Mac execution smoke](mac-smoke.json): bounded Darwin I/O and error refusal
  passed on that fixed-point compiler.
- [Mac cross receipt](mac-cross.json): ARM root candidate
  `bc9c295119b597a6de8356d8ad2a1421e94ad514e4aef091150e624dfdbff756`,
  x86 public compiler candidate
  `8d8debe0bbe793ec717853aadd757b28f1a684b17f025f7f7a6020e80df06c49`.

These bytes are pinned in `seed/bootstrap/aarch64-linux-static-root.elf`,
`bin/amu`, and their descriptors. The cross images were produced on Mac and
have not yet executed in native Linux qualification on this merged source.
The earlier full `selfhost-native` run on the pre-merge branch is separate
evidence; its result cannot qualify these merged-source bytes. Native ARM/x86
fixed points, full corpus, controller, public aliases/consumers and exact-head
CI remain open. Guest Itonami agent-loop, release and hardware acceptance are
separate from this compiler build.
