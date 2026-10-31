#!/usr/bin/env python3
"""The aiueos kernel object route's memory fences (JUN-708, ADR 0401).

kernel-fence-load [], kernel-fence-store [] and kernel-fence-full [] are ids 43..45 of
seed/74-x86_64-aiueos-object.kotoba: lfence (0f ae e8), sfence (0f ae f8) and mfence (0f ae f0), each answering 0, the
bytes kotoba-native machine-ir encodes for :fence-load / :fence-store / :fence-full and that kotoba-compiler/1 emitted
into the rtl8125 driver objects (`0f ae f8` in rtl8125-program.o, `0f ae e8` in rtl8125-rx-poll.o, each followed by
`mov r10d,0`). Compiles with a native Amu compiler and checks (Python stages and observes; it emits nothing):

* sequences: an object exporting fl, fs, ff (one function per fence) carries each of FENCE; xor eax,eax exactly once,
  in that order, and no other 0f ae fence byte sequence;
* in a driver shape: a store, sfence, then a doorbell store into the same 4 KiB window (as rtl8125-tx-submit does), and
  an lfence between two loads (as rtl8125-rx-poll does): the fence lies between the two accesses, in source order;
* opt-in: the 4 KiB width object of check-aiueos-object-windows4k.py, which names no fence, carries no fence bytes and
  keeps its pinned SHA-256; so do the objects that name neither block (the 512-byte and 16 KiB width objects and the
  out-port object, ids 0..34);
* refused, nothing written: each fence called with an argument (E2103).

Not shown here: execution. docs/evidence/windows4k-fence-20261031/ runs the three fences under QEMU.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
FENCES = {"load": "0faee8", "store": "0faef8", "full": "0faef0"}
SOURCE = """(ns fence (:export [fl fs ff]))
(defn fl [] :i64 (kernel-fence-load))
(defn fs [] :i64 (kernel-fence-store))
(defn ff [] :i64 (kernel-fence-full))
"""
DRIVER = """(ns drv (:export [submit poll]))
(defn submit [b :i64 n :i64 v :i64] :i64
  (let [d (kernel-store-u32-4k b n 0 v) f (kernel-fence-store) bell (kernel-store-u8-4k b n 56 64)] (+ d f)))
(defn poll [b :i64 n :i64] :i64
  (let [s (kernel-load-u32-4k b n 0) f (kernel-fence-load) w (kernel-load-u64-4k b n 8)] (+ (+ s f) w)))
"""


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(compiler, output):
    windows16 = load("check-aiueos-object-windows16")
    windows4k = load("check-aiueos-object-windows4k")
    outport = load("check-aiueos-object-outport")
    gate = windows16.gate_module()
    gate.verify_macho(compiler)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {}

    _, obj = windows16.compile_source(gate, compiler, output, "fence", SOURCE)
    text = windows16.text_section(obj).hex()
    found = {name: text.count(code + "31c0") for name, code in FENCES.items()}
    at = [text.find(code + "31c0") for code in FENCES.values()]
    # fl, fs, ff: the bodies lie in source order, so lfence, sfence, mfence in that order (each fence its own name's)
    if found != {"load": 1, "store": 1, "full": 1} or text.count("0fae") != 3 or not at[0] < at[1] < at[2]:
        raise ValueError(f"fence sequences {found} at {at}, 0f ae occurrences {text.count('0fae')}")
    report["fences"] = {"sequences": found, "sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}

    _, obj = windows16.compile_source(gate, compiler, output, "driver", DRIVER)
    raw = windows16.text_section(obj)
    w = [(at, kind_width) for at, kind_width in windows4k.windows(raw, 4096)]
    sf, lf = raw.find(bytes.fromhex(FENCES["store"])), raw.find(bytes.fromhex(FENCES["load"]))
    order = [kw for _, kw in w]
    # the accesses in the order the functions use them (the object places the bodies in source order)
    if order != [("store", 4), ("store", 1), ("load", 4), ("load", 8)] or not (w[0][0] < sf < w[1][0] < w[2][0] < lf < w[3][0]):
        raise ValueError(f"driver: windows {w}, sfence at {sf:#x}, lfence at {lf:#x}")
    report["driver"] = "store; sfence; doorbell store -- load; lfence; load"

    for name, source, digest in (("w4k", windows4k.SOURCE, windows4k.W4K_SHA256),
                                 ("widths", windows16.WIDTHS_SOURCE, windows16.WIDTHS_SHA256),
                                 ("widths16", windows16.SOURCE16, windows4k.WIDTHS16_SHA256),
                                 ("outport", outport.SOURCE, outport.SOURCE_SHA256)):
        _, obj = windows16.compile_source(gate, compiler, output, name, source)
        have = hashlib.sha256(obj.read_bytes()).hexdigest()
        if b"\x0f\xae" in windows16.text_section(obj) or have != digest:
            raise ValueError(f"{name}: an object naming no fence changed ({have}) or carries fence bytes")
        report[f"{name}NoFence"] = have

    for name in FENCES:
        source = f"(ns r (:export [f]))\n(defn f [] :i64 (kernel-fence-{name} 1))\n"
        result, obj = windows16.compile_source(gate, compiler, output, f"{name}-argument", source, expected=1)
        message = (result.stdout + result.stderr).decode(errors="replace")
        if "E2103" not in message or obj.exists():
            raise ValueError(f"fence-{name} with an argument was not refused with E2103 and no output: {message}")
        report[f"{name}-argument"] = "refused E2103"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS_AIUEOS_OBJECT_FENCE " + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(strict=True), args.output.resolve())
