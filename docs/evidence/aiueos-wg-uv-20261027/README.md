# WG and boot intrinsic UV-context admission

The previous draft compiler selected the 147456-byte ValueRuntime arena for a
kernel-v1 source that called GOP, Browser and native-font intrinsics but no
direct `kernel-value-enable-user`. Those intrinsics call `uv-require` and need
the 2359296-byte user-context arena. The `native full selfhost` ARM job in run
40470276142 failed at the typed desktop-region admission step because the
image had LV magic `0x324c5652`, not UV magic `0x334c5652`.

`seed/95-aiueos-user-context.kotoba` now treats intrinsic IDs from `UV-FIRST`
through `KM-INTR-N` as user-context users. This includes WG, boot-payload and
user-slot calls. The exact former failing source compiled with the signed Mac
F2 compiler into a kernel-v1 image with RW extent `0x240000` and UV magic;
all six region-forgery controls still refused `E7106`.

Mac native evidence, produced with the complete 48-module source:

- Source unity: `6eefc165d8590078a4752035ceb60fcca74d2fb5679485245110d706ea71cdad`.
- Compiler F1=F2 container: `9f42f23caf7abbbfe26b32f1ad151a09fbd7b2b79d4afa331db500a564d70c0e`.
- Signed Mac F2: `a50e174f681ab7e4413d9226a351c835ba3948b6762d0ee59dd22bc0b7feba36`.
- Canonical Mac user-target gate: `PASS_MAC_NATIVE_USER_TARGET_SELFHOST`.
- Canonical Mac cross gate: `MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED`.
- Checked-in ARM root: `d7331314fd028c5ef3325c078797e2739fa329581065f69a521d663962120473`.
- Checked-in x86 compiler: `6f6d6931975cee3c930bd806c25aee455012f97c7b9a3fac4e97500cba414265`.

Local gate receipts are under
`workspaces/codex/jun444-wg-uv-20261027/canonical-mac-gate/`,
`workspaces/codex/jun444-wg-uv-20261027/canonical-cross-gate/` and
`workspaces/codex/jun444-wg-uv-20261027/desktop-regions-mac/`.
The Linux candidates have not been independently executed or qualified on
their native ISAs at this revision. This is not an AIUEOS guest, Itonami turn,
release or physical-hardware qualification.
