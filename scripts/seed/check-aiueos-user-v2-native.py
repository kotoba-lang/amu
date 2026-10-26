#!/usr/bin/env python3
"""Observe the bounded AIUEOS user-v2 Goal input ELF contract.

Amu emits the ELF. This observer checks its image and fixed source/refusal
vectors; it does not implement guest behavior or establish CPL3 execution.
"""

import struct


TARGET = "x86_64-aiueos-user-v2"
SOURCE = ("(ns aiueos-user-goal-v2 (:export [main]))\n"
          "(defn main [request :i64 request-bytes :i64] :i64 "
          "(kernel-load-u32 request request-bytes 0))\n")
CONSTANT = ("(ns aiueos-user-goal-v2 (:export [main]))\n"
            "(defn main [request :i64 request-bytes :i64] :i64 42)\n")
REFUSALS = {
    "arity": ("(ns aiueos-user-goal-v2 (:export [main]))\n"
              "(defn main [request :i64] :i64 request)\n", "E7102"),
    "base": ("(ns aiueos-user-goal-v2 (:export [main]))\n"
             "(defn main [request :i64 request-bytes :i64] :i64 "
             "(kernel-load-u32 (+ request 4) request-bytes 0))\n", "E7106"),
    "length": ("(ns aiueos-user-goal-v2 (:export [main]))\n"
               "(defn main [request :i64 request-bytes :i64] :i64 "
               "(kernel-load-u32 request 64 0))\n", "E7106"),
    "effect": ("(ns aiueos-user-goal-v2 (:export [main]))\n"
               "(defn main [request :i64 request-bytes :i64] :i64 "
               "(let [x (typed-cap-call :io/write :string :string \"denied\")] 42))\n", "E7101"),
    "export": ("(ns aiueos-user-goal-v2 (:export [other]))\n"
               "(defn other [request :i64 request-bytes :i64] :i64 42)\n", "E7102"),
    "parameter-type": ("(ns aiueos-user-goal-v2 (:export [main]))\n"
                       "(defn main [request :bool request-bytes :i64] :i64 42)\n", "E7102"),
    "return-type": ("(ns aiueos-user-goal-v2 (:export [main]))\n"
                    "(defn main [request :i64 request-bytes :i64] :bool true)\n", "E7102"),
}


def verify(blob):
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(len(blob) == 8280, "unexpected user-v2 image length")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", blob)
    require(header == (b"\x7fELF\x02\x01\x01" + bytes(9), 2, 62, 1,
                       0x1E1000, 64, 0, 0, 64, 56, 2, 0, 0, 0), "ELF identity")
    rx, rw = (struct.unpack_from("<IIQQQQQQ", blob, 64 + 56 * i) for i in range(2))
    require(rx[:5] == (1, 5, 4096, 0x1E1000, 0x1E1000), "RX segment identity")
    require(80 < rx[5] == rx[6] <= 4096 and rx[7] == 4096, "RX segment bounds")
    require(rw == (1, 6, 8192, 0x1E2000, 0x1E2000, 88, 320, 4096), "RW segment contract")
    require(not any(blob[176:4096]) and not any(blob[4096 + rx[5]:8192]),
            "ELF padding")
    prefix = bytes.fromhex(
        "4c8d0df90f0000498db900010000be40000000e838000000"
        "488905e10f0000f390ebfc")
    require(blob[4096:4096 + len(prefix)] == prefix, "v2 entry and arguments")
    require(blob[4096 + len(prefix):4096 + 48] == bytes([0x90]) * (48 - len(prefix)),
            "entry padding")
    require(blob[4096 + 48:4096 + 60] == bytes.fromhex("b805000000488b7f500f05c3"),
            "syscall trampoline")
    require(blob[4096 + 60:4096 + 80] == bytes([0x90]) * 20, "trampoline padding")
    context = bytearray(88)
    struct.pack_into("<Q", context, 8, 256)
    struct.pack_into("<Q", context, 48, 0x1E1030)
    require(blob[8192:] == context, "v2 image must not bake in Goal or authority")


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    args = parser.parse_args()
    verify(args.elf.read_bytes())
    print("PASS_AIUEOS_USER_V2_ELF_SHAPE")
