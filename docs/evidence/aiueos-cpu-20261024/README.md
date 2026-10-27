# Native CPU primitive candidate

The native ARM compiler fixed point and24 existing cases pass. Both native
generations emit identical kernel/EFI bytes for the CPU fixture. On the
pinned QEMU q35/max guest it returns42/fuel999999, checking all four CPUID
results, CR0/3/4 reads and same-value writes/readback, CS, TSC/pause, CLI,
invlpg, and MSR reads/writes. The FS-base test writes a value with a nonzero
high32 half, reads it back exactly, and restores its prior value. STI/HLT
are emitted only when called and are not exercised by this fixture.

The complete15-module kernel remains unchanged and locked. It now reaches
the region-provenance refusal rather than an unknown CPUID operation, and
writes no image. Transitive region requirements, ISR/live runtime and the
remaining integration gates are still open. These guest observations do
not qualify a native x86 compiler successor or public-product adoption.
