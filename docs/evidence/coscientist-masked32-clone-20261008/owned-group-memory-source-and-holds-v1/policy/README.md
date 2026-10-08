# Portable memory policy proposal: SOURCE HOLD

The accepted historical native compiler harnesses cap output files and guest arenas and delegate CPU/wall limits to the loader. They do not claim a process address-space ceiling. The pinned Darwin loader itself excludes AS installation on Apple platforms, forks a compiler child and supervises it. An outer-PID-only memory observer would therefore miss the actual compiler process.

A fresh policy could retain the exact arena budgets and supervise aggregate resident size and physical footprint for the complete loader process group, refusing above4GiB. This is a different, explicitly soft process-memory contract. It does not establish AS equivalence, private-byte equivalence, or a hard maximum between samples. Unknown extra processes, unavailable API, malformed inventories and incomplete samples must refuse; no fallback or guessed zero.

The loader CPU installer requests soft1800/hard1801. The prior wrapper's hard1800 would obstruct that request. Any fresh policy must explicitly resolve this contract, retaining finite CPU/wall budgets and disclosing the one-second hard-limit grace rather than silently raising the old limit.

CPython3.14 maps an OS EINVAL from setrlimit to the generic current-limit-exceeds-maximum message, so that text does not prove an attempted inherited-hard-limit increase. [Python implementation](https://github.com/python/cpython/blob/v3.14.0/Modules/resource.c). Darwin's resource ABI declares resident size and physical footprint separately. [Apple ABI source](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/resource.h). The local SDK15.5 headers are pinned for exact adapter layout proposals.

No setters, memory API probes, compiler, native producer or SSH calls were executed for this proposal. The failed V2 setter remains unknown; V3 independently identified its own AS failure. Original current source and native8 scope remain unchanged, with no execution GO.
