# Darwin diagnostic FS2 D: distinguish lookup errors

The diagnostic D/A dispatcher now returns `0` for D only when Darwin `openat`
reports ENOENT. Successful opens still return `1`; other open errors return
`?`. A requests retain the previous failure behavior. Because D opens the
path with scoped no-follow flags, `?` can include a symlink or other path that
cannot safely be opened; it does not mean the path is absent. This changes
D's diagnostic response contract for errors. Callers which collapse all
non-`1` responses to absent remain unsafe and must be audited separately.

On one local Darwin ARM64 Mac, the new source was compiled using the native
bootstrap and diagnostic packager below. A real-file fixture saw `1` for a
readable file and directory, `0` for missing paths, and `?` for an unreadable
file, inaccessible parent and a symlink. The old packager returned `0` for the
three error cases. OS-level permission denial was checked separately and all
fixture permissions were restored. Both versions read an ordinary file with A.

A second fixture composed the actual Murakumo bridge request/head checks with
stubbed CID, JSON, save, head and archive authority. Against a parent made
inaccessible, the old provider produced `bridge/request-ready` and
`bridge/head-ready`; the new provider produced `bridge/request-unknown` for
both. This is not an integrated signed turn or cursor update. A separate
regression checked D, A, O, U, E, I, H, M and L operations, and the FIFO
fixture exercised byte writes, rename, synchronization and held-lock refusal.
One eight-process race completed with eight sequentially admitted tickets; it
does not establish ordering or contention fairness.

The 188 Kotoba instruction words match the independent assembly derivation;
the packager consumes Kotoba source, not that assembly. Sources and observers
here are test-only and contain task-specific temporary paths. The exact source
SHA-256 was `8a17f1914f52615b8058b76c7fdb1134bcebb410ab709ec2ad586b47e2f89dad`;
the signed candidate packager was
`4114499dc10bd321070a221f88847b8708565f7d80e87c4ed84b28e599e3c41e`;
the signed new and old probe images were respectively
`87a45d5646258b7bc389f25c268a8265635a05ffeef8b4b4fc9190afaf747ab3` and
`9587b44e85741ae5e477a96d4fe897581455e416e649b263ce318445c755a6c6`.
The signed new bridge and head fixtures were
`dd141b670dd41d0031d0484d893bb5c242cacd9dbcdbd112be6a8edffd96f1b7` and
`628db0a9b2b452550c5a4e246d5a9227765a69ee8d8761c165e90a9547fee2f4`.
The bootstrap compiler and old diagnostic packager were respectively
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6` and
`f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d`.

This is a partial diagnostic runtime on one host. It is not release runtime,
full FS2 conformance, all-error coverage, crash durability, race safety, a
complete checkpoint, or an autonomous bot. Caller compatibility, Linux and
other Macs remain unqualified; path ownership and race protection are still
required.
