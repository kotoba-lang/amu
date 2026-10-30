#!/usr/bin/env python3
"""A kernel window access above its tier's maximum is refused at compile time (JUN-483).

The kernel memory intrinsics trap at run time (ud2) when their size operand is above the
tier maximum: 512 for the plain forms, 4096 for -4k, 16384 for -16k, 65536 for -64k
(seed/86 km-maximum). When that size is a literal, km-check now refuses the call with
E7108 naming the intrinsic, the size and the maximum, instead of compiling a function
that can only reach its ud2. Compiles with a native Amu compiler on the aiueos object
route, over the object's own .bss / .high_bss arrays (whose literal extent is known):

* object route (seed/74): the plain and 16 KiB windows at exactly their maximum compile; at
  twice the maximum they are refused (E7108 with the intrinsic's name, the size and the
  maximum; nothing written), loads and stores, u8 to u64;
* not exercised here: the kernel-image route (seed/86 km-check, all four tiers including
  -4k and -64k), whose source-locked multi-module compile needs the Linux producers of
  check-aiueos-owned-page-native.py;
* unchanged: E7106 for a length that is not the region's own, and an object without
  arrays is byte-identical to check-aiueos-object-exports.py's pinned one-export object.

A size tied to a parameter keeps the run-time check; this gate does not change that.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source(array, size, call):
    return f"(ns t (:export [f]))\n(defn- {array}-addr-0-{size} [] :i64 0)\n(defn f [i :i64 v :i64] :i64 {call})\n"


# object route (seed/74 xk-check): its windows have the plain and 16 KiB tiers; (intrinsic, maximum, array section)
TIERS = [("kernel-store-u8", 512, "bss"), ("kernel-load-u8", 512, "bss"), ("kernel-load-u32", 512, "bss"),
         ("kernel-store-u64", 512, "bss"),
         ("kernel-store-u16-16k", 16384, "highbss"), ("kernel-load-u8-16k", 16384, "highbss"),
         ("kernel-load-u32-16k", 16384, "highbss")]

def call(intrinsic, array, size):
    base = f"({array}-addr-0-{size})"
    return f"({intrinsic} {base} {size} i v)" if "store" in intrinsic else f"({intrinsic} {base} {size} i)"


def main(compiler, output):
    exports = load("check-aiueos-object-exports")
    gate = exports.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}
    for intrinsic, maximum, array in TIERS:
        slug = intrinsic.replace("kernel-", "")
        _, ok = exports.compile_object(gate, compiler, output, f"{slug}-at-max", source(array, maximum, call(intrinsic, array, maximum)))
        if not ok.exists():
            raise ValueError(f"{intrinsic} at its maximum {maximum}: no object")
        over = maximum * 2
        result, bad = exports.compile_object(gate, compiler, output, f"{slug}-over", source(array, over, call(intrinsic, array, over)), expected=1)
        text = (result.stdout + result.stderr).decode(errors="replace")
        want = f"E7108 {intrinsic} size {over} is above its tier maximum {maximum}"
        if bad.exists() or want not in text:
            raise ValueError(f"{intrinsic} size {over}: want '{want}' and no output, got {text[-300:]!r}")
        report[intrinsic] = {"atMaximum": maximum, "refused": over}
    result, bad = exports.compile_object(gate, compiler, output, "wrong-literal",
                                         source("bss", 64, "(kernel-load-u8 (bss-addr-0-64) 128 i)"), expected=1)
    if bad.exists() or "E7106" not in (result.stdout + result.stderr).decode(errors="replace"):
        raise ValueError("a length other than the region's own is no longer E7106")
    report["wrongLiteral"] = "refused E7106"
    _, one = exports.compile_object(gate, compiler, output, "one", exports.ONE_SOURCE)
    if hashlib.sha256(one.read_bytes()).hexdigest() != exports.ONE_SHA256:
        raise ValueError("an object without arrays changed its bytes")
    report["withoutArrays"] = "byte-identical"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_KERNEL_TIER_MAXIMUM " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
