# ADR-0400 -- literal output ports for the aiueos object route (JUN-600)

- Status: **implemented** (seed/74, `scripts/seed/check-aiueos-object-outport.py`).
- Date: 2026-10-31
- Tracking: JUN-600 (owner decision 2026-10-31: "Yes, add an allowlist").
- Amends: ADR 0399, which left the port-write side open. Follows ADR 0373 (ids 4..5).

## Context

ADR 0399 made `kernel-in-u32` take only the literal port 0xcfc. The write side, `kernel-out-u8` and `kernel-out-u32`
(ids 4 and 5, ADR 0373), still took any port, a parameter or computed one included. So the object route could read one
port and write all 65536. The owner decided to give the write side a literal allowlist taken from the kernel's real
callers, as in-u32 has.

## Inventory (kotoba main c1f446a3)

Every kernel object under `lib/kotoba.aiueos/os/aiueos/kotoba/*.kotoba` that calls an output stub, all on the native
route. Every port is a literal. No object passes a port as a parameter or computes one.

| object | stub | ports | value | C caller |
|---|---|---|---|---|
| `pic-disable` | out-u8 | 0x20, 0xa0 (ICW1), 0x21, 0xa1 (ICW2..4, OCW1), 0x80 (io_wait, ten times) | literals, and the vector bases `master-base` / `slave-base` | `kernel/main.c` and `multiboot/main.c`: `kotoba_aiueos_pic_disable(0xe0, 0xe8)` |
| `pci-config-write` | out-u32 | 0xcf8 (address), 0xcfc (data) | computed address word, the caller's data word | `kernel/pci.c` |
| `pci-config-read` | out-u32 | 0xcf8 (address) | computed address word | `kernel/pci.c` |

`pic-disable`'s parameters are the vector bases that ICW2 writes, not ports. Its ports were literals already. So no
object needed porting. The open JUN-708 branches (kotoba#1129, #1130) add objects that write no port.

The serial (0x3f8..), debug console (0xe9), QEMU exit (0xf4) and reset (0xcf9) ports are written by C (`main.c`'s
`debug_byte` / `qemu_exit`, `ioapic.c`, `pci.c`) and by `os/aiueos/native/*.kotoba`. The native sources compile on the
locked kernel-project route (seed/85..87), whose port intrinsics are seed/86's and are outside this ADR. No object on
this route writes those ports, so they are not listed.

## Decision

`xk-check` reads the port operand's writer, as it does for in-u32. The port must be an integer literal (`OP-CONST`,
0 <= v < 2^32) in the stub's own list. A parameter, a let-bound or computed value, a value chosen by a branch, or any
other literal is refused with E7107, and nothing is written.

| port | width | why it is listed |
|---|---|---|
| 0x20 | out-u8 | master 8259 command port: pic-disable's ICW1 |
| 0x21 | out-u8 | master 8259 data port: pic-disable's ICW2 (vector base), ICW3, ICW4 and the OCW1 mask |
| 0xa0 | out-u8 | slave 8259 command port: pic-disable's ICW1 |
| 0xa1 | out-u8 | slave 8259 data port: pic-disable's ICW2, ICW3, ICW4 and the OCW1 mask |
| 0x80 | out-u8 | the POST port, written as the io_wait delay after each 8259 write |
| 0xcf8 | out-u32 | PCI configuration address port: pci-config-read and pci-config-write |
| 0xcfc | out-u32 | PCI configuration data port: pci-config-write |

The lists are per width. out-u8 to 0xcf8 and out-u32 to 0x20 are refused: no caller does either.

The value stays a run-time operand and is not bounded. It is the payload, and what a device accepts is the device's
rule. pic-disable checks its own vector bases before any write.

### Code and pinned objects

The rule only adds refusals. The stub bytes are unchanged, so every admitted source compiles to the bytes it had. The
locked kernel-project route (seed/87 calls `xk-check` with only ids 0..3 mapped) and the user route (ids 0..1) are not
affected. The plain image artifact (`--artifact image`) shares `xk-check` and gets the same lists.

### Landing order

Nothing in kotoba needs porting, and every pinned object already writes only listed literal ports. So amu lands
first, alone, and kotoba needs no change and no pin bump. An older kotoba root compiles the same sources to the same
bytes.

## Evidence

- `scripts/seed/check-aiueos-object-outport.py` (wired into mac-selfhost-aiueos.yml):
  - One object writes every listed port in pic-disable's and pci-config's shapes: seven out-u8 and three out-u32
    sequences. Its SHA-256 equals what main's root (amu fe7b5b1c) emitted for the same source.
  - The image artifact compiles a listed port and refuses 0x3f8 (E7107).
  - It refuses with E7107, for each width: unlisted literals (out-u8 0x3f8, 0xe9, 0x22, 0xcf9; out-u32 0xcfd, 0xcf9,
    0xf4), the other width's port, a parameter port, a computed port, a let-bound literal and a port chosen by a branch.
  - It refuses with E2103 each stub with one or three arguments.
  - On main's root the same gate fails: the unlisted image port compiles.
- All other object gates in mac-selfhost-aiueos.yml pass on the new root.
- On the new root, all 123 of kotoba main c1f446a3's native-route objects recompile byte-identical. So do the 123 and
  125 on the open JUN-708 branches #1129 and #1130.
