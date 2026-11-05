# f64 -> i64 truncation on the aarch64-linux emitter (JUN-846)

`f64-to-i64-truncating` traps NaN, +-Inf and every |x| >= 2^63 (the reference's behaviour); it no longer saturates through a
bare `fcvtzs`. `seed/80-aarch64-linux.kotoba` (`xa-un`) carries the same double-precision guard as `seed/41-a64gen.kotoba`
(`gn-fl-f64-to-i64`); `scripts/seed/check-a64-f2i.py` pins the guard in the aarch64-linux ELF (compile only, it runs on macOS).

## Execution (one-off, 2026-11-05)

Host: Apple silicon, podman machine `podman-machine-default` (applehv), `--platform linux/arm64`, image `alpine:3`. The ELFs
were compiled by this branch's `seed/bootstrap/aarch64-macos/amu-full-root.macho` with
`compile F.kotoba --target aarch64-linux --output F.elf --format static`; each has `main` returning one conversion.

| program (f64 bits) | value | result |
|---|---|---|
| 9221120237041090560 | quiet NaN | exit 120, `KEXE_TRAP {:kind :signal :signal :SIGTRAP}` |
| 9218868437227405312 | +Inf | exit 120, SIGTRAP |
| 4890909195324358656 | 2^63 | exit 120, SIGTRAP |
| 4614256656552045848 | 3.14159.. | exit 3 (truncated to 3) |
| -4332462841530417152 | -2^63 | exit 0 (INT64_MIN, low byte 0) |

Not run here: the x86_64 routes (the conversion is still refused there, E7101) and the full `seed/float-cases.json` chain.
