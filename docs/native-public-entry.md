# Current Amu selfhost native entry

The public `bin/amu` is a 8,790,528-byte static Linux x86_64 ELF,
SHA-256 `68f1f3db2c185428055005e3052c6458637c64d7a4004481def85aae585979f1`, built from the complete29 source of amu#1535 (JUN-354: an ungranted
wire is refused by name) on main 6deb9969. Both relative aliases resolve to that same image. The native ARM root is
`f70486914adb760dc35817a9fbd9064c6247af5e198fa644523bb494bd0ce07a`. Its native qualification (x86_64 F1=F2=F3, controller, aliases) is the exact-head PR CI and is recorded as pending in `native-product.json` until then. Before amu#1535 the image was
`23e714db082b2db65208cfc573ad682c399a4228fb1e04041f420ea50d9d65c0` (source `f382a939ec3b0c750393d04a8efaaa1f5e3bd30c`) and the root `c95b844146ae31e9…`. Every adopted18 core module is retained. Complete
ARM containers F1=F2=F3, packed F2=F3 and independent canonical Pw agree;
actual native x86 F1=F2=F3 reproduce the public image. Static capacities are
TOK786432/MM-WORDS29,491,200/LitB1MiB/OUT12MiB, heap1765120 words unchanged.

## Actual current-source verification

The changed native runner `80b757e13799761061c8d13e328d52f325b57e726e736b6e2c73337be56865bf` ran
all19 Embench correctness workloads, MIR normal/all6 large/whole-large,
GMIR8,31 runtime/resource cases,17 pin refusals and E2104 afresh. All33 MIR
files/3roots and12 GMIR files/2roots retain exact source locks, fuel and
grants. Whole-MIR exits with tracked use0 and155,688,217 scope releases.
The final compiler reproduces all27 executed containers and exact runner
and C0. New independent C0 `267911f9cdea95d9d3868d342d590c8591349e5622ff1400c549f25da4ffef83` reproduces complete18
core container `086f85dbc21ab94098a9ca1f356ce8430741797467c0c586a5c6b97553dffd06`, matching warm3 and locked
unity. No comparative performance score was measured.

Source locks use a private native frame and one nonblocking/no-follow FD,
regular-file metadata,1MiB maximum, complete read/EOF and close. Directory,
FIFO,socket,symlink,oversized,empty,malformed and missing inputs refuse
E6015. Unicode and old-separator filenames preserve positive compiled
bytes. Direct core/current ARM F/current x86 public3aliases cover150
positive/refusal observations. The public check requires current complete
proof, all3 actual native F images and current full unity; mutable matching
descriptors alone cannot qualify an unrelated or stale product.

The fresh Kotoba native controller `39a500374e27d3a04404573cbf455eef56b2dbb6aa473279e3cd75cae9a1263a` ran
both mandatory roles,24 result/exit/fuel cases,18 refusals and parent-death
child cleanup. The report matches its physical positive gate receipt and
the controller/gate ledger and image identities. Python only stages/hashes
and observes processes; the Amu/Kotoba native controller owns the verdict.
Current clock/entropy controls include ENOSYS refusal; ARM durable/sleep9
and launcher30 pass. Historical x86 provider/exec-trace observations keep
their source35 scope; they are not relabeled as current execution.

Evidence: `docs/evidence/native-cdci-20261023/current-scope.json`.
Artifact qualification used exact candidate native CI run40003789973. Terminal
exact-final-head PR CI, expected-head merge, terminal exact-main CI and
tree/pin/alias/mode readback, archive-first owned cleanup remain separate
completion gates recorded in the PR and internal task record.

## Remaining broader contracts

Engine-neutral defaults, full CLI verb/target compatibility,module/package
locks,resolver/Definition CID,profile/seal,historical full assertion and
general FS fault/race parity remain separate. The earlier RANGE out-of-file
generic SIGILL observation remains open and is not named-refusal parity.
Unsupported paths retain named refusals. Platform-linked providers and live
cutover are not covered. There is no old language host,C compiler,loader,
runtime or emulation fallback in this qualified native route.
