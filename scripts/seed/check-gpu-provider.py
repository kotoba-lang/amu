#!/usr/bin/env python3
"""The GPU provider's protocol core on the fake device (ADR 0371 step 6).

The unit is tools/gpu_provider.kotoba's ns line, the protocol table
(tools/gpu_compute_protocol.kotoba) and the fake device layer
(tools/gpu_device_fake.kotoba), each without its ns line, then the rest of
tools/gpu_provider.kotoba. --compiler (an Amu-produced static compiler from
these sources: S3.elf of selfhost-bootstrap.py, or X2 on x86_64) builds it
with --format platform-linked; it runs on x86_64 Linux with glibc, natively or
under qemu-user. The fake device has no GPU, so this covers what the core
decides: the grant, the artifact table and digests, the handle tables, the
recording state, the provider's refusals (19 on), the session-ending ones,
frames, and the report on fd 4.

Phase "build" (any Linux): the provider, and for the native run a static
guest that uses wire 42 and the static launcher.

Phase "run" (x86_64 Linux with glibc; native or emulated):
* sessions, each a provider process with fd 3 the grant and fd 4 the report:
  every verb with its answer, the refusals from 19 on, the table's refusals
  passed through, a request that is not ASCII, device lost and fence timeout
  (the fake layer's faults; the session ends), a frame longer than one
  runtime value, the buffer and pipeline tables and the dispatch limit at
  their bounds, and answers that cannot be written;
* grants: one well-formed grant, and refusals (another key, a repeated key, no
  wire 42, a missing key, a short digest, a backslash, a timeout of 61,
  trailing bytes, no fd 3): the provider serves nothing and exits 2; a device
  index the layer lacks exits 3;
* on a native kernel also: the provider under the static launcher, answering a
  static guest's wire-42 session (binfmt_misc cannot start a close-on-exec
  memfd, so not under emulation).

Python only orchestrates processes, frames and hashes.
  podman run --platform linux/arm64 ... python3 check-gpu-provider.py build --compiler S3.elf --output OUT
  podman run --platform linux/amd64 (glibc image) ... python3 check-gpu-provider.py run --output OUT
  python3 check-gpu-provider.py all --compiler X2.elf --output OUT   (x86_64 host)
"""
import argparse
import hashlib
import json
import os
import platform
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVIDER, TABLE, FAKE = "tools/gpu_provider.kotoba", "tools/gpu_compute_protocol.kotoba", "tools/gpu_device_fake.kotoba"
NS = re.compile(r"^\d+$")
GUEST = ('(ns g (:export [main]))\n'
         '(defn- gpu [r :string] :string (typed-cap-call 42 :string :string r))\n'
         '(defn main [] :i64\n'
         '  (let [a (gpu "ALLOC 16") w (gpu "WRITE 1 0 0a0b0c") r (gpu "READ 1 0 3") i (gpu "INFO")]\n'
         '    (if (and (string=? a "1") (string=? w "1") (string=? r "0a0b0c") (string=? i "Kotoba fake device|fake|65535|1")) 0 1)))\n')


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def split_ns(path):
    first, rest = (ROOT / path).read_text().split("\n", 1)
    assert first.startswith("(ns ") and first.endswith("))"), (path, first)
    return first, rest


def unit():
    ns, provider = split_ns(PROVIDER)
    return "\n".join([ns, split_ns(TABLE)[1], split_ns(FAKE)[1], provider])


def build(compiler, output):
    assert platform.system() == "Linux", "run on Linux"
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    calls, images = [], {}
    for name, source, fmt in (("provider-fake", unit(), "platform-linked"), ("guest", GUEST, "static"),
                              ("launcher", (ROOT / "tools/static_launcher.kotoba").read_text(), "launcher")):
        src, out = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        z = subprocess.run([str(producer), "compile", str(src), "--target", "x86_64-linux", "--output", str(out), "--format", fmt],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}, capture_output=True, timeout=900)
        calls.append(dict(name=name, format=fmt, exit=z.returncode, stdout=z.stdout.decode(errors="replace").strip()))
        assert z.returncode == 0 and not z.stderr and b":ok true" in z.stdout, (name, z.returncode, z.stderr[-400:])
        out.chmod(0o755)
        images[name] = str(out.relative_to(output))
    assert ":libvulkan false" in calls[0]["stdout"], calls[0]
    report = dict(status="PASS_GPU_PROVIDER_BUILD", compiler=pin(compiler), host=[platform.system(), platform.machine(), platform.release()],
                  sources={p: pin(ROOT / p) for p in (PROVIDER, TABLE, FAKE)}, images=images, calls=calls, cCompilerOrLoader=False)
    (output / "gpu-provider.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(images), "images", flush=True)


def native_kernel():
    try:
        info = Path("/proc/cpuinfo").read_text()
    except OSError:
        return False
    return "GenuineIntel" in info or "AuthenticAMD" in info


def chain(n, tag):
    out = b""
    while len(out) < n:
        out += hashlib.sha256(out[-32:] + tag).digest()
    return out[:n]


def frame(b):
    return struct.pack("<I", len(b)) + b


class Session:
    """A provider process: fd 0 requests, fd 1 answers, fd 3 the grant, fd 4 the report."""

    def __init__(self, img, raw, name, grant, with_grant=True):
        self.name, self.raw = name, raw
        gpath = raw / (name + ".grant.edn")
        gpath.write_bytes(grant)
        self.rep_r, rep_w = os.pipe()
        redirect = '3<"$1" 4>&"$2"' if with_grant else '3<&- 4>&"$2"'
        self.p = subprocess.Popen(["/bin/sh", "-c", f'exec "$0" {redirect}', str(img), str(gpath), str(rep_w)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env={"PATH": "/usr/bin:/bin"}, pass_fds=(rep_w,), cwd=raw)
        os.close(rep_w)
        self.log = []

    def ask(self, request):
        self.p.stdin.write(frame(request if isinstance(request, bytes) else request.encode()))
        self.p.stdin.flush()
        return self.answer(request)

    def answer(self, request):
        h = self.p.stdout.read(4)
        if len(h) < 4:
            self.log.append([str(request), None])
            return None
        n = struct.unpack("<I", h)[0]
        a = self.p.stdout.read(n).decode()
        self.log.append([request.decode(errors="replace")[:120] if isinstance(request, bytes) else request[:120], a[:200]])
        return a

    def close(self, want):
        try:
            self.p.stdin.close()
        except BrokenPipeError:
            pass
        rest = self.p.stdout.read()
        err = self.p.stderr.read()
        code = self.p.wait(timeout=120)
        rep = b""
        while True:
            b = os.read(self.rep_r, 65536)
            if not b:
                break
            rep += b
        os.close(self.rep_r)
        (self.raw / (self.name + ".report")).write_bytes(rep)
        (self.raw / (self.name + ".stderr")).write_bytes(err)
        assert code == want and not rest, (self.name, code, rest[:200], err[-300:])
        line = rep.decode()
        assert line.startswith("{:provider :kotoba.gpu-provider/v1 :device \"fake\" ") and line.endswith("}\n") and line.count("\n") == 1, line
        return line


def expect(s, request, want):
    got = s.ask(request)
    ok = bool(want.match(got)) if hasattr(want, "match") else got == want
    assert got is not None and ok, (s.name, request if isinstance(request, str) else request[:80], got, want)
    return got


def grant(artifacts, cap=1000000, extra=""):
    rows = " ".join(f'{{:path "{p}" :sha256 "{h}" :kind :{k}}}' for p, h, k in artifacts)
    return f"{{:wires #{{42}} :artifacts [{rows}] :device-bytes {cap}{extra}}}\n".encode()


def run(output):
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "run phase: x86_64 Linux"
    report = json.loads((output / "gpu-provider.json").read_text())
    img = {k: output / v for k, v in report["images"].items()}
    raw = output / "run"
    raw.mkdir(exist_ok=False)
    model, spv = chain(300000, b"model"), struct.pack("<5I", 0x07230203, 0x00010000, 0, 1, 0)
    files = {"model.bin": model, "bad.bin": chain(1000, b"bad"), "k.spv": spv, "notspv.spv": b"\0" * 20, "odd.spv": spv + b"\0\0"}
    for n, b in files.items():
        (raw / n).write_bytes(b)
    sha = {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}
    arts = [("model.bin", sha["model.bin"], "model"), ("bad.bin", sha["model.bin"], "model"), ("k.spv", sha["k.spv"], "spirv"),
            ("notspv.spv", sha["notspv.spv"], "spirv"), ("odd.spv", sha["odd.spv"], "spirv"), ("missing.spv", sha["k.spv"], "spirv")]
    rows = {}

    # every verb, and the refusals the provider decides
    s = Session(img["provider-fake"], raw, "verbs", grant(arts, cap=4096))
    for req, want in [
            ("INFO", "Kotoba fake device|fake|65535|1"), ("DEVCLASS", "other"),
            ("ALLOC 64", "1"), ("ALLOC 32", "2"), ("WRITE 1 0 00ff10", "1"), ("READ 1 0 3", "00ff10"),
            ("WRITEDEC 2 4 1,2,4294967295", "3"), ("READ 2 0 16", "00000000" "01000000" "02000000" "ffffffff"),
            ("READ 2 30 4", "!gpu/past-buffer READ past the buffer"), ("WRITE 2 31 0000", "!gpu/past-buffer WRITE past the buffer"),
            ("WRITEDEC 2 30 1", "!gpu/past-buffer WRITEDEC past the buffer"),
            ("WRITE 9 0 00", "!gpu/no-such-buffer WRITE: no such buffer"), ("ZERO 1", "1"), ("READ 1 0 3", "000000"),
            ("FREE 1", "1"), ("FREE 1", "!gpu/no-such-buffer FREE: no such buffer"), ("ALLOC 16", "1"),
            ("ALLOC 5000", "!gpu/device-bytes-cap ALLOC: over the granted device bytes"),
            ("MAP model.bin 100 1000", "3"), ("READ 3 0 1000", model[100:1100].hex()),
            ("MAP model.bin 299999 2", "!gpu/past-buffer MAP past the buffer"),
            ("MAP model.bin 0 4000", "!gpu/device-bytes-cap MAP: over the granted device bytes"),
            ("MAP nothere.bin 0 1", "!gpu/artifact-not-granted MAP: path is not in the granted artifact table"),
            ("MAP bad.bin 0 10", "!gpu/artifact-digest-mismatch MAP: artifact digest does not match the grant"),
            ("MAP bad.bin 0 10", "!gpu/artifact-digest-mismatch MAP: artifact digest does not match the grant"),
            ("MAP k.spv 0 4", "!gpu/artifact-not-granted MAP: path is not in the granted artifact table"),
            ("PIPELINE k.spv 2", "1"), ("PIPELINE notspv.spv 1", "!gpu/not-spirv PIPELINE: not a SPIR-V module"),
            ("PIPELINE odd.spv 1", "!gpu/not-spirv PIPELINE: not a SPIR-V module"),
            ("PIPELINE missing.spv 1", "!gpu/artifact-not-granted PIPELINE: path is not in the granted artifact table"),
            ("PIPELINE model.bin 1", "!gpu/artifact-not-granted PIPELINE: path is not in the granted artifact table"),
            ("DISPATCH 1 1 1 1 2 3", NS), ("DISPATCH 1 1 1 1 2", "!gpu/binding-mismatch DISPATCH: handle count != pipeline bindings"),
            ("DISPATCH 2 1 1 1 2 3", "!gpu/no-such-pipeline DISPATCH: no such pipeline"),
            ("DISPATCHC 1 1 1 1 2 9", "!gpu/no-such-buffer DISPATCHC: no such buffer"),
            ("BEGIN", "1"), ("DISPATCH 1 4 1 1 2 3", "1"), ("DISPATCHC 1 4 1 1 3 2", "1"),
            ("MAP model.bin 0 1", "!gpu/while-recording MAP while recording (BEGIN open): finish with SUBMIT first"),
            ("SUBMIT", NS), ("SUBMIT", "!gpu/not-recording SUBMIT without BEGIN"),
            ("BEGINK 0", "1"), ("SUBMIT", "!gpu/kept-without-dispatch SUBMIT: kept command buffer holds no dispatch"),
            ("BEGINK 0", "1"), ("DISPATCH 1 1 1 1 2 3", "1"), ("SUBMIT", NS),
            ("FREE 2", "!gpu/buffer-bound-in-kept FREE: buffer is bound in a kept command buffer (DROP it first)"),
            ("FREE 1", "1"), ("REPLAY 0", NS), ("BEGINK 0", "!gpu/slot-kept BEGINK: slot is kept (DROP it first)"),
            ("REPLAY 1", "!gpu/slot-empty REPLAY: slot holds no kept command buffer"),
            ("DROP 1", "!gpu/slot-empty DROP: slot holds no kept command buffer"),
            ("DROP 0", "1"), ("REPLAY 0", "!gpu/slot-empty REPLAY: slot holds no kept command buffer"), ("FREE 2", "1"),
            ("ALLOC 0", "!gpu/zero-length ALLOC <bytes>"), ("", "!gpu/empty-request empty request"),
            ("INFO extra", "!gpu/arity INFO"),
            ("INFO é", "!gpu/unknown-verb unknown :gpu/compute request")]:
        expect(s, req, want)
    line = s.close(0)
    assert f":served {len(s.log)} " in line and " :end :eof " in line, line
    rows["verbs"] = dict(requests=len(s.log), refused=int(re.search(r":refused (\d+)", line)[1]), report=line.strip(), log=s.log)

    # faults that end the session
    for name, x, code in (("device-lost", 4294967295, "!gpu/device-lost device lost; the provider ends the session"),
                          ("fence-timeout", 4294967294, "!gpu/fence-timeout fence timeout; the provider ends the session")):
        s = Session(img["provider-fake"], raw, name, grant(arts))
        expect(s, "ALLOC 16", "1")
        expect(s, "PIPELINE k.spv 1", "1")
        expect(s, f"DISPATCH 1 {x} 1 1 1", code)
        assert s.answer("after") is None
        line = s.close(1)
        assert f" :end :{name} " in line, line
        rows[name] = dict(report=line.strip(), log=s.log)
    s = Session(img["provider-fake"], raw, "request-too-long", grant(arts))
    s.p.stdin.write(struct.pack("<I", 8388609))
    s.p.stdin.flush()
    assert s.answer("frame of 8388609 bytes") == "!gpu/request-too-long request longer than one runtime value"
    line = s.close(1)
    assert " :end :request-too-long " in line, line
    rows["request-too-long"] = dict(report=line.strip())
    s = Session(img["provider-fake"], raw, "answers-closed", grant(arts))
    s.p.stdout.close()
    s.p.stdin.write(frame(b"INFO"))
    s.p.stdin.flush()
    s.p.stdout = open(os.devnull, "rb")
    line = s.close(1)
    assert " :end :answers-not-written " in line, line
    rows["answers-closed"] = dict(report=line.strip())

    # the tables and the dispatch limit at their bounds
    s = Session(img["provider-fake"], raw, "bounds", grant(arts))
    for h in range(1, 4096):
        expect(s, "ALLOC 1", str(h))
    expect(s, "ALLOC 1", "!gpu/buffer-table-full buffer table full (4096)")
    for p in range(1, 128):
        expect(s, "PIPELINE k.spv 1", str(p))
    expect(s, "PIPELINE k.spv 1", "!gpu/pipeline-table-full pipeline table full")
    expect(s, "BEGIN", "1")
    for _ in range(2048):
        expect(s, "DISPATCHC 1 1 1 1 1", "1")
    expect(s, "DISPATCHC 1 1 1 1 1", "!gpu/dispatch-limit more than 2048 dispatches in one command buffer")
    expect(s, "SUBMIT", NS)
    line = s.close(0)
    rows["bounds"] = dict(requests=len(s.log), report=line.strip())

    # grants
    good = (b'  {:wires #{37 42}, :artifacts [{:kind :model :sha256 "' + sha["model.bin"].encode() + b'" :path "model.bin"}]\n'
            b' :device-bytes 2000 :submit-timeout-seconds 5 :device 0}  \n')
    s = Session(img["provider-fake"], raw, "grant-good", good)
    expect(s, "MAP model.bin 0 2000", "1")
    expect(s, "ALLOC 1", "!gpu/device-bytes-cap ALLOC: over the granted device bytes")
    line = s.close(0)
    rows["grant-good"] = dict(report=line.strip())
    refused = {
        "another-key": grant([], extra=" :color 1"), "repeated-key": grant([], extra=" :device-bytes 5"),
        "no-wire-42": b"{:wires #{37} :artifacts [] :device-bytes 0}", "missing-key": b"{:wires #{42} :artifacts []}",
        "short-digest": grant([("model.bin", sha["model.bin"][:63], "model")]),
        "backslash": grant([("mo\\del.bin", sha["model.bin"], "model")]),
        "timeout-61": grant([], extra=" :submit-timeout-seconds 61"), "trailing": grant([]) + b"x",
        "unknown-kind": grant([("model.bin", sha["model.bin"], "wasm")]), "empty": b"",
    }
    for name, g in refused.items():
        s = Session(img["provider-fake"], raw, "grant-" + name, g)
        line = s.close(2)
        assert " :served 0 " in line and " :end :grant-refused :grant-error-at " in line, (name, line)
        rows["grant-" + name] = dict(report=line.strip())
    s = Session(img["provider-fake"], raw, "grant-no-fd-3", grant([]), with_grant=False)
    line = s.close(2)
    assert " :end :grant-refused " in line, line
    rows["grant-no-fd-3"] = dict(report=line.strip())
    s = Session(img["provider-fake"], raw, "no-device", grant([], extra=" :device 1"))
    line = s.close(3)
    assert " :end :no-device " in line, line
    rows["no-device"] = dict(report=line.strip())
    digest = pin(img["provider-fake"])["sha256"]
    assert f':image "{digest}"' in rows["verbs"]["report"], ("the report's image digest", digest)

    native = native_kernel()
    if native:
        g = raw / "launcher.grant.edn"
        g.write_bytes(grant(arts))
        z = subprocess.run([str(img["launcher"]), "10", "37,38,39,42", str(g), str(img["provider-fake"]), "--", str(img["guest"])],
                           env={"PATH": "/usr/bin:/bin"}, capture_output=True, timeout=120)
        (raw / "launcher.stdout").write_bytes(z.stdout)
        (raw / "launcher.stderr").write_bytes(z.stderr)
        line = z.stdout[z.stdout.rindex(b"{:receipt "):].decode()
        assert z.returncode == 0 and ":verdict :ok" in line and ":result 0 " in line and ":end :eof" in line, (z.returncode, line, z.stderr[-300:])
        rows["under-the-launcher"] = dict(exit=z.returncode, receipt=line.strip())
    report["run"] = dict(host=[platform.system(), platform.machine(), platform.release()], nativeKernel=native, rows=rows,
                         notRun=[] if native else ["the provider under the static launcher: binfmt_misc cannot start a close-on-exec memfd image (native kernels only)"])
    report["status"] = "PASS_GPU_PROVIDER_FAKE_DEVICE"
    (output / "gpu-provider.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], "native" if native else "emulated", len(rows), "sessions", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("phase", nargs="?", choices=["build", "run", "all"], default="all")
    parser.add_argument("--compiler", type=Path, help="build: an Amu-produced static compiler from these sources")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.phase in ("build", "all"):
        assert args.compiler, "--compiler is required to build"
        build(args.compiler.resolve(), args.output.resolve())
    if args.phase in ("run", "all"):
        run(args.output.resolve())
