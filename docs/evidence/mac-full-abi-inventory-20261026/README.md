# Full Amu Mac candidate: remaining direct ABI and capability boundary

This is a static inventory of the pinned full compiler `main` and the
diagnostic Mach-O image built by the Kotoba packager. The
[machine-readable receipt](receipt.json) records SHA-256 digests, every
direct callback call site, the callback setup stores found in the image,
direct arena pointer loads, and every direct typed-capability call shape.

The full raw `main` references 14 distinct direct runtime callbacks. The
diagnostic image has a context setup store for ten of them. These four
callback slots still have no setup store:

| Context offset | Callback | Call sites in pinned full `main` |
| ---: | --- | ---: |
| 160 | `vector_conj` | 14 |
| 184 | `vector_assoc` | 2 |
| 216 | `string_index_of` | 16 |
| 240 | `string_compare` | 4 |

The six direct arena pointer fields at offsets 288–328 have setup stores.
The full `main` has nine direct typed calls: wire 35 has string/string once,
bytes/bytes twice, and string/bytes once; wires 37, 38, and 39 account for
the other five. In the signed Mac execution recorded by the
[bytes and UTF-8 runtime probe](../mac-bytes-utf8-runtime-20261026/README.md),
`check` reaches wire 35 and traps before file I/O. Wire 35 is therefore the
first observed execution boundary. Its FS2 provider must enforce a declared
app-data root, bounded requests and responses, no-follow path handling, and
the existing refusal rules. The four pure callbacks remain required for the
whole compiler even if wire 35 is repaired first.

Reproduce this inventory using the exact pinned raw and image artifacts:

```sh
python3 scripts/seed/inventory-macos-full-abi.py \
  --raw /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025/full-compiler-main.raw \
  --image /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025/utf8-full.macho \
  --output /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025/mac-full-abi-inventory-repeat.json
```

The scanner recognizes the direct `ldr x16, [x0, #slot]; blr x16` pattern
and candidate context setup stores. It does not prove callback behavior,
indirect calls, code-path reachability, FS2 confinement, complete `check` or
`compile`, Mac F1=F2=F3 self-rebuild, or Linux-free image production. A later
image needs its own complete runtime inventory and signed process tests.
