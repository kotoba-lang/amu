# DMA contracts engineering evidence

The full37 engineering compiler admits the complete locked15-module kernel,
reproduces its ELF byte for byte and packages it through the native PCI v6
EFI route. All18 adopted core inputs remain byte-identical to the prior
full37 baseline. This is not a replacement for full self-rebuild, all24
runtime checks, actual native x86/controller execution or public pin adoption.

The retained16-module functional probe executes the actual RX snapshot code
in QEMU TCG. Ten receipt words and the complete final snapshot are read back
independently through QMP. They cover all four2048-byte buffers, short-packet
zeroing, and invalid index/size/overlap preservation. Fuel923580 is an
observation with a bounded functional gate, not an exact fuel-parity claim.

The valid-image negative control also returns42 but has no DMA receipt. The
observer rejects it and emits no PASS receipt. Existing exact-fuel modes
retain their defaults. Complete kernel boot, live ABI, GPT media,
desktop/input and physical NIC qualification remain open.

`index.json` binds the compiler, exact source unity, artifacts and receipts.
The producer is engineering ARM native; QEMU is guest emulation. No JVM,
Node, GraalVM, C compiler or C loader was used for this route.
