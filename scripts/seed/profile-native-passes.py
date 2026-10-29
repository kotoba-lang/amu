#!/usr/bin/env python3
"""Native pass/proof diagnostics for the Co-Scientist experiment loop.

Only stage source-marker edits, invoke an admitted native producer and observe
processes. The instrumented compiler is never an adopted compiler or a native
verdict authority. Its emitted workload must match an independent frozen
artifact; marker timings are for hypothesis selection, not speedup claims.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import struct
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PASSES = ["lx-run", "rd-run", "nm-run", "ck-run-h", "lw-run", "gn-run", "gn-loop", "ly-run", "out-build"]
X86_PASSES = ["xs-build", "xg-code", "xr-pool"]
PROOFS = ["gn-op-fn", "gn-op-call", "qi-admit", "pi-admit", "ti-admit", "rp-admit", "rc-admit",
          "gn-call-wrapper", "gn-clamp", "gn-scalar-mask", "gn-affine-reader", "mr-reader", "di-admit",
          "tc-admit", "tb-admit", "aw-admit", "gn-mask-writer", "gn-chain-mode", "gn-chain-target",
          "gp-shape", "gn-small-label", "gn-small-tail", "gn-small-end", "jdag-owner", "ccf-admit",
          "ccf-code", "ccf-fixes", "ccf-labels", "ccf-functions", "ccf-label-source", "ccf-owner", "ccf-end"]
# Immutable previously qualified workload, not the source of the probe.
INPUT_REVISION = "4abac3fd612de050fd7f7a4635deb80ca9a0cb73"
WORKLOADS = {
    "core": dict(sourceSHA256="026d87a058f4f8b7006e2f09ea26d3713633cf3b4585329d818caab1280bc79d",
                 artifactSHA256="6ad407c211c16efb425f4fa4761b0421e6e180211e4d6c28b8d6fb4bf35e0070"),
    "label-x86": dict(sourceSHA256="daa88291555eb738df9d0dd36a1a498d69d550eff89f97931318c20627fb5a8b",
                      artifactSHA256="378fd3cd99fcd9951654612e2df4e2b055d00bf6c068c1b4eeec325325712591"),
}


def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def manifest(path, read):
    return [p for p in read(path).decode().splitlines() if p and not p.startswith("#")]


def instrument(text, name):
    pattern = r"^\(defn- " + re.escape(name) + r" \[([^]]*)\] :(i64|bool|vector-i64)"
    matches = list(re.finditer(pattern, text, re.M))
    assert len(matches) == 1, (name, "source anchor drift")
    match = matches[0]
    start = match.start()
    depth, quoted, escaped, comment = 0, False, False, False
    end = None
    for i in range(start, len(text)):
        c = text[i]
        if comment:
            if c == "\n":
                comment = False
        elif quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
        elif c == ";":
            comment = True
        elif c == '"':
            quoted = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    assert end is not None, name
    args = match[1]
    names = re.findall(r"([\w-]+) :(?:vector-i64|string|i64|bool)", args)
    assert len(names) * 2 == len(args.split()), (name, args)
    inner = "diagnostic-original-" + name
    # Recursive calls stay inside the original body, so a recursive traversal
    # generates one outer span rather than one marker per instruction.
    body = text[start:end].replace("(defn- " + name + " ", "(defn- " + inner + " ", 1)
    body = body.replace("(" + name + " ", "(" + inner + " ")
    wrapper = ("(defn- " + name + " [" + args + "] :" + match[2] + "\n"
               '  (let [begin (io-err "B ' + name + '\\n")\n'
               "        result (" + inner + " " + " ".join(names) + ")\n"
               '        end (io-err "E ' + name + '\\n")] result))\n')
    return text[:start] + body + "\n" + wrapper + text[end:]


def main(out, closure, workload, detail, seconds, workload_file=None):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    machine = 183 if platform.machine() == "aarch64" else 62
    assert struct.unpack_from("<H", Path("/proc/self/exe").read_bytes(), 18)[0] == machine
    producer = ROOT / ("seed/bootstrap/aarch64-linux-static-root.elf" if machine == 183 else "bin/amu-linux-x86_64")
    assert struct.unpack_from("<H", producer.read_bytes(), 18)[0] == machine
    assert closure == "full" or workload == "core", "x86 workload requires the full compiler"
    out.mkdir(parents=True, exist_ok=False)
    read = lambda p: (ROOT / p).read_bytes()

    def frozen(path):
        return subprocess.run(["git", "show", INPUT_REVISION + ":" + path], cwd=ROOT,
                              capture_output=True, check=True).stdout

    paths = manifest("seed/FULL-MANIFEST" if closure == "full" else "seed/CORE-STATIC-MANIFEST", read)
    original = b"".join(read(p) + b"\n" for p in paths).decode()
    functions = PASSES + (X86_PASSES if closure == "full" else []) + (PROOFS if detail == "proofs" else [])
    text = original
    for name in functions:
        text = instrument(text, name)
    source = out / "probe.kotoba"
    source.write_text(text)
    if workload_file:
        raw = workload_file.read_bytes()
    elif workload == "core":
        input_paths = manifest("seed/MANIFEST", frozen)
        raw = b"".join(frozen(p) + b"\n" for p in input_paths)
    else:
        input_paths = manifest("seed/CORE-STATIC-MANIFEST", frozen)[:-1]
        raw = b"".join(frozen(p) + b"\n" for p in input_paths) + frozen("seed/tests/native-label-index.kotoba")
    src = out / "workload.kotoba"
    src.write_bytes(raw)
    expected = WORKLOADS[workload]
    assert pin(src)["sha256"] == expected["sourceSHA256"], "frozen workload drift"
    target = "aarch64-linux" if machine == 183 else "x86_64-linux"
    image = out / "probe.elf"
    env = dict(PATH="/nonexistent", KEXE_STACK_BYTES="8388608", KEXE_CAP_RESOURCES_35=str(out))
    print(json.dumps(dict(phase="BUILDING_PROBE", closure=closure, workload=workload, detail=detail,
                          source=pin(source), nativeVerdictAuthority=False)), flush=True)
    start = time.monotonic()
    build = subprocess.run([str(producer), "compile", str(source), "--target", target,
                            "--output", str(image), "--format", "static"],
                           cwd=out, env=env, capture_output=True, timeout=900)
    (out / "build.stdout").write_bytes(build.stdout)
    (out / "build.stderr").write_bytes(build.stderr)
    assert build.returncode == 0 and not build.stderr, (build.returncode, build.stderr[-1000:])
    image.chmod(0o755)
    print(json.dumps(dict(phase="RUNNING_DIAGNOSTIC", compiler=pin(image), source=pin(src))), flush=True)
    report = dict(schema="amu.native-pass-diagnostic.v1", nativeVerdictAuthority=False,
                  qualificationReplacement=False, performanceQualified=False,
                  host=[platform.system(), platform.machine(), platform.release()], loadStart=os.getloadavg(),
                  closure=closure, detail=detail, workload=workload, workloadRevision=INPUT_REVISION,
                  sourceBindings={p: pin(ROOT / p) for p in paths}, source=pin(src),
                  producer=pin(producer), instrumentedSource=pin(source), compiler=pin(image),
                  buildSeconds=time.monotonic() - start, status="RUNNING", events=0, totals={}, stack=[])
    output = out / ("workload.kseed" if workload == "core" else "workload.elf")
    argv = [str(image), "compile", str(src), "--target",
            "aarch64-macos" if workload == "core" else "x86_64-linux", "--output", str(output)]
    if workload == "core":
        lock = out / "workload.ksl"
        lock.write_text(f"KSL1\nentry {src}\nfile {pin(src)['sha256']} {src}\n")
        argv += ["--source-lock", str(lock), "--source-lock-sha256", pin(lock)["sha256"]]
    else:
        argv += ["--format", "static"]
    start = time.monotonic()
    with (out / "compile.stdout").open("wb") as stdout:
        proc = subprocess.Popen(argv, cwd=out, env=env, stdout=stdout, stderr=subprocess.PIPE)
        timer = threading.Timer(seconds, proc.terminate)
        timer.start()
        stack, totals, last, errors = [], {}, start, []
        with (out / "events.jsonl").open("w") as raw_events:
            for raw_event in proc.stderr:
                now = time.monotonic()
                line = raw_event.decode().strip()
                raw_events.write(json.dumps([now - start, line]) + "\n")
                if stack:
                    totals[stack[-1][0]]["exclusiveSeconds"] += now - last
                if line.startswith("B "):
                    name = line[2:]
                    stack.append((name, now))
                    row = totals.setdefault(name, dict(exclusiveSeconds=0, inclusiveSeconds=0, calls=0))
                    row["calls"] += 1
                elif line.startswith("E "):
                    name = line[2:]
                    assert stack and stack[-1][0] == name, (name, stack[-5:])
                    _, began = stack.pop()
                    totals[name]["inclusiveSeconds"] += now - began
                else:
                    errors.append(line)
                last = now
                report["events"] += 1
                report.update(seconds=now - start, totals=totals, stack=[n for n, _ in stack])
                if detail == "passes" or report["events"] % 256 == 0:
                    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
        code = proc.wait()
        timer.cancel()
    artifact = pin(output) if output.exists() else None
    report.update(exit=code, seconds=time.monotonic() - start, totals=totals, stack=[n for n, _ in stack],
                  openSpans=[dict(name=n, seconds=time.monotonic() - began) for n, began in stack],
                  errors=errors, artifact=artifact, loadEnd=os.getloadavg(),
                  outputParity=bool(artifact and artifact["sha256"] == expected["artifactSHA256"]),
                  status="COMPLETED_DIAGNOSTIC" if code == 0 else "INCOMPLETE_DIAGNOSTIC")
    (out / "observations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "seconds", "outputParity", "totals", "openSpans")}), flush=True)
    assert code == 0 and not errors and report["outputParity"] and not stack, "incomplete diagnostic or output differs from baseline"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--closure", choices=["core", "full"], default="full")
    p.add_argument("--workload", choices=WORKLOADS, default="core")
    p.add_argument("--detail", choices=["passes", "proofs"], default="passes")
    p.add_argument("--seconds", type=int, default=600)
    p.add_argument("--workload-file", type=Path, help="pre-staged frozen bytes, still checked against the immutable source digest")
    a = p.parse_args()
    assert 1 <= a.seconds <= 900
    main(a.output.resolve(), a.closure, a.workload, a.detail, a.seconds,
         a.workload_file and a.workload_file.resolve())
