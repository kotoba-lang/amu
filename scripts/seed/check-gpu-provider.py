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

Phase "build" (any Linux): the provider on the fake layer and on the Vulkan
layer (tools/gpu_device_vulkan.kotoba; built here, never run here), for the
native run a static guest that uses wire 42 and the static launcher, and two
KIR v1 modules written by a kernel tool image (ADR 0372: z = x + y, and
per-workgroup sums).

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

Phase "gpu" (a GPU host only: the owner decided on 2026-10-22 that libvulkan
runs there and nowhere else): the Vulkan provider on the host's driver. INFO
and DEVCLASS; WRITE, WRITEDEC, READ and ZERO through the staging buffer; MAP of
70 MiB (more than one staging chunk) read back at the chunk edge; z = x + y at
once, in a recording whose second dispatch reads the first's output, in a kept
command buffer submitted and replayed, and with DISPATCHC; per-workgroup sums.
The values are exact in f32, so the answers are compared byte for byte.

Python only orchestrates processes, frames and hashes.
  podman run --platform linux/arm64 ... python3 check-gpu-provider.py build --compiler S3.elf --output OUT
  podman run --platform linux/amd64 (glibc image) ... python3 check-gpu-provider.py run --output OUT
  python3 check-gpu-provider.py all --compiler X2.elf --output OUT   (x86_64 host)
  python3 check-gpu-provider.py gpu --output OUT                      (GPU host, after build)
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
VULKAN = "tools/gpu_device_vulkan.kotoba"
# the KIR v1 modules the GPU phase runs (ADR 0372): z = x + y, and per-workgroup sums
KERNELS = ('(ns gpu-kernels (:export [main]))\n', ["tools/spirv_encode.kotoba", "tools/gpu_kernel_kir1.kotoba"],
           '(defn main [] :i64\n'
           '  (+ (if (= (spv-write (kir1-ewise 1 256) "add.spv") 1004) 0 1)\n'
           '     (if (> (spv-write (kir1-reduce 1 256) "sum.spv") 0) 0 2)))\n')
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


def unit(layer=FAKE):
    ns, provider = split_ns(PROVIDER)
    return "\n".join([ns, split_ns(TABLE)[1], split_ns(layer)[1], provider])


def build(compiler, output):
    assert platform.system() == "Linux", "run on Linux"
    output.mkdir(parents=True, exist_ok=False)
    art = output / "artifacts"
    art.mkdir()
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)
    calls, images = [], {}
    host = {"aarch64": "aarch64-linux", "arm64": "aarch64-linux", "x86_64": "x86_64-linux", "AMD64": "x86_64-linux"}[platform.machine()]
    kernels = KERNELS[0] + "\n".join(split_ns(p)[1] for p in KERNELS[1]) + "\n" + KERNELS[2]
    for name, source, fmt, tgt in (("provider-fake", unit(), "platform-linked", "x86_64-linux"), ("guest", GUEST, "static", "x86_64-linux"),
                                   ("launcher", (ROOT / "tools/static_launcher.kotoba").read_text(), "launcher", "x86_64-linux"),
                                   ("provider-vulkan", unit(VULKAN), "platform-linked", "x86_64-linux"),
                                   ("kernels", kernels, "static", host)):
        src, out = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        z = subprocess.run([str(producer), "compile", str(src), "--target", tgt, "--output", str(out), "--format", fmt],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}, capture_output=True, timeout=900)
        calls.append(dict(name=name, format=fmt, exit=z.returncode, stdout=z.stdout.decode(errors="replace").strip()))
        assert z.returncode == 0 and not z.stderr and b":ok true" in z.stdout, (name, z.returncode, z.stderr[-400:])
        out.chmod(0o755)
        images[name] = str(out.relative_to(output))
    assert ":libvulkan false" in calls[0]["stdout"] and ":libvulkan true" in calls[3]["stdout"], calls
    # the modules, written by the kernel tool into its :fs/app-data scope
    kdir = output / "kernels"
    kdir.mkdir()
    z = subprocess.run([str(output / images["kernels"])], cwd=kdir, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(kdir)},
                       capture_output=True, timeout=300)
    assert z.returncode == 0 and (kdir / "add.spv").exists() and (kdir / "sum.spv").exists(), (z.returncode, z.stderr[-300:])
    report = dict(status="PASS_GPU_PROVIDER_BUILD", compiler=pin(compiler), host=[platform.system(), platform.machine(), platform.release()],
                  sources={p: pin(ROOT / p) for p in (PROVIDER, TABLE, FAKE, VULKAN, *KERNELS[1])}, images=images,
                  modules={n: pin(kdir / n) for n in ("add.spv", "sum.spv")}, calls=calls, cCompilerOrLoader=False)
    (output / "gpu-provider.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(images), "images", flush=True)


def native_kernel():
    try:
        info = Path("/proc/cpuinfo").read_text()
    except OSError:
        return False
    return "GenuineIntel" in info or "AuthenticAMD" in info


def chain(n, tag):
    out, last = bytearray(), b""
    while len(out) < n:
        last = hashlib.sha256(last + tag).digest()
        out += last
    return bytes(out[:n])


def frame(b):
    return struct.pack("<I", len(b)) + b


class Session:
    """A provider process: fd 0 requests, fd 1 answers, fd 3 the grant, fd 4 the report."""

    def __init__(self, img, raw, name, grant, with_grant=True, device="fake"):
        self.name, self.raw, self.device = name, raw, device
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
        assert line.startswith("{:provider :kotoba.gpu-provider/v1 :device ") and line.endswith("}\n") and line.count("\n") == 1, line
        assert self.device is None or line.startswith(f'{{:provider :kotoba.gpu-provider/v1 :device "{self.device}" '), line
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
    assert f":served {len(s.log)} " in line and " :end :eof " in line and ' :needed ["libc.so.6"] ' in line, line
    rows["verbs"] = dict(requests=len(s.log), refused=int(re.search(r":refused (\d+)", line)[1]), report=line.strip(), log=s.log)

    # ordinary device errors: refused, and the session goes on
    s = Session(img["provider-fake"], raw, "device-error", grant(arts, cap=1 << 40))
    for req, want in [("ALLOC 4294967293", "!gpu/device-error ALLOC: device error"), ("ALLOC 16", "1"), ("PIPELINE k.spv 1", "1"),
                      ("BEGIN", "1"), ("DISPATCH 1 4294967293 1 1 1", "!gpu/device-error DISPATCH: device error"),
                      ("DISPATCH 1 1 1 1 1", "1"), ("SUBMIT", NS), ("DISPATCH 1 4294967293 1 1 1", "!gpu/device-error DISPATCH: device error"),
                      ("INFO", "Kotoba fake device|fake|65535|1")]:
        expect(s, req, want)
    line = s.close(0)
    assert " :refused 3 " in line and " :end :eof " in line, line
    rows["device-error"] = dict(report=line.strip(), log=s.log)

    # an artifact changed after its verification: MAP checks each piece it
    # reads and refuses; PIPELINE keeps using the module bytes it verified
    for n in ("model.bin", "k.spv"):
        (raw / ("changed-" + n)).write_bytes((raw / n).read_bytes())
    changed = [("changed-model.bin", sha["model.bin"], "model"), ("changed-k.spv", sha["k.spv"], "spirv")]
    s = Session(img["provider-fake"], raw, "artifact-changed", grant(changed))
    expect(s, "MAP changed-model.bin 0 1000", "1")
    expect(s, "PIPELINE changed-k.spv 1", "1")
    with open(raw / "changed-model.bin", "r+b") as f:
        f.seek(200000)
        f.write(b"\xff" * 16)
    with open(raw / "changed-k.spv", "r+b") as f:
        f.write(b"\0" * 20)
    # one 1 MiB piece holds the whole file: the change refuses any range of it
    expect(s, "MAP changed-model.bin 199000 2000", "!gpu/artifact-digest-mismatch MAP: artifact digest does not match the grant")
    expect(s, "MAP changed-model.bin 0 1000", "!gpu/artifact-digest-mismatch MAP: artifact digest does not match the grant")
    expect(s, "PIPELINE changed-k.spv 1", "2")
    line = s.close(0)
    rows["artifact-changed"] = dict(report=line.strip(), log=s.log)

    # truncated frames: not a clean end
    for name, data in (("truncated-header", b"\x04\x00"), ("truncated-payload", struct.pack("<I", 10) + b"INF")):
        s = Session(img["provider-fake"], raw, name, grant(arts))
        s.p.stdin.write(data)
        s.p.stdin.flush()
        line = s.close(1)
        assert " :end :truncated-request " in line, (name, line)
        rows[name] = dict(report=line.strip())

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


def f32(values):
    return struct.pack(f"<{len(values)}f", *values)


def gpu(output):
    """GPU hosts only (owner decision 2026-10-22): the Vulkan layer on the host's driver."""
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "gpu phase: x86_64 Linux with a Vulkan driver"
    report = json.loads((output / "gpu-provider.json").read_text())
    img = output / report["images"]["provider-vulkan"]
    raw = output / "gpu"
    raw.mkdir(exist_ok=False)
    model = chain(70 * 1024 * 1024 + 123, b"model")
    files = {"model.bin": model, "add.spv": (output / "kernels" / "add.spv").read_bytes(), "sum.spv": (output / "kernels" / "sum.spv").read_bytes()}
    for n, b in files.items():
        (raw / n).write_bytes(b)
    sha = {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}
    g = grant([("model.bin", sha["model.bin"], "model"), ("add.spv", sha["add.spv"], "spirv"), ("sum.spv", sha["sum.spv"], "spirv")],
              cap=1 << 30)
    s = Session(img, raw, "gpu", g, device=None)
    rows = {}
    info = expect(s, "INFO", re.compile(r"[^|]+\|\d+\.\d+\.\d+\|\d+\|[01]"))
    devclass = expect(s, "DEVCLASS", re.compile(r"discrete|integrated|virtual|cpu|other"))
    rows["info"], rows["devclass"] = info, devclass
    # transfers through the staging buffer
    data = chain(4096, b"data")
    expect(s, "ALLOC 4096", "1")
    expect(s, "WRITE 1 0 " + data.hex(), "1")
    expect(s, "READ 1 0 4096", data.hex())
    expect(s, "READ 1 100 7", data[100:107].hex())
    expect(s, "WRITEDEC 1 8 1,2,3", "3")
    expect(s, "READ 1 8 12", "010000000200000003000000")
    expect(s, "ZERO 1", "1")
    expect(s, "READ 1 0 16", "00" * 16)
    # MAP of 70 MiB: more than one staging chunk (64 MiB)
    t0 = __import__("time").monotonic()
    expect(s, f"MAP model.bin 0 {len(model)}", "2")
    rows["map-70MiB-seconds"] = round(__import__("time").monotonic() - t0, 3)
    for off in (0, 64 * 1024 * 1024 - 2048, len(model) - 4096):
        expect(s, f"READ 2 {off} 4096", model[off:off + 4096].hex())
    # z = x + y over n = 1000 (values exact in f32)
    n = 1000
    x, y = [i * 0.5 for i in range(n)], [float(n - i) for i in range(n)]
    for h in ("3", "4", "5"):
        expect(s, f"ALLOC {4 * n}", h)
    expect(s, "ALLOC 4", "6")
    expect(s, "WRITE 3 0 " + f32(x).hex(), "1")
    expect(s, "WRITE 4 0 " + f32(y).hex(), "1")
    expect(s, f"WRITEDEC 6 0 {n}", "1")
    expect(s, "PIPELINE add.spv 4", "1")
    ns = [int(expect(s, "DISPATCH 1 4 1 1 3 4 5 6", NS))]
    expect(s, f"READ 5 0 {4 * n}", f32([a + b for a, b in zip(x, y)]).hex())
    # a recording: the second dispatch reads the first's z (barrier between)
    expect(s, "ZERO 5", "1")
    expect(s, "BEGIN", "1")
    expect(s, "DISPATCH 1 4 1 1 3 4 5 6", "1")
    expect(s, "DISPATCH 1 4 1 1 5 4 5 6", "1")
    ns.append(int(expect(s, "SUBMIT", NS)))
    expect(s, f"READ 5 0 {4 * n}", f32([a + 2 * b for a, b in zip(x, y)]).hex())
    # a kept command buffer, submitted and replayed
    expect(s, "BEGINK 0", "1")
    expect(s, "DISPATCH 1 4 1 1 5 4 5 6", "1")
    ns.append(int(expect(s, "SUBMIT", NS)))
    ns.append(int(expect(s, "REPLAY 0", NS)))
    expect(s, f"READ 5 0 {4 * n}", f32([a + 4 * b for a, b in zip(x, y)]).hex())
    expect(s, "DROP 0", "1")
    # two independent dispatches (DISPATCHC: no barrier)
    expect(s, "BEGIN", "1")
    expect(s, "DISPATCHC 1 4 1 1 3 4 5 6", "1")
    expect(s, "DISPATCHC 1 4 1 1 3 3 1 6", "1")
    ns.append(int(expect(s, "SUBMIT", NS)))
    expect(s, f"READ 5 0 {4 * n}", f32([a + b for a, b in zip(x, y)]).hex())
    expect(s, f"READ 1 0 {4 * n}", f32([2 * a for a in x]).hex())
    # per-workgroup sums of 1..1000 (exact in f32)
    ints = [float(i + 1) for i in range(n)]
    expect(s, f"ALLOC {4 * n}", "7")
    expect(s, "ALLOC 16", "8")
    expect(s, "WRITE 7 0 " + f32(ints).hex(), "1")
    expect(s, "PIPELINE sum.spv 3", "2")
    ns.append(int(expect(s, "DISPATCH 2 4 1 1 7 8 6", NS)))
    expect(s, "READ 8 0 16", f32([sum(ints[k:k + 256]) for k in range(0, n, 256)]).hex())
    # unaligned bytes (copies are widened to 4-byte spans) and ZERO of a
    # buffer whose size is not a multiple of 4
    expect(s, "ALLOC 3", "9")
    expect(s, "WRITE 9 0 a1b2c3", "1")
    expect(s, "WRITE 9 1 abcd", "1")
    expect(s, "READ 9 0 3", "a1abcd")
    expect(s, "READ 9 2 1", "cd")
    expect(s, "ZERO 9", "1")
    expect(s, "READ 9 0 3", "000000")
    expect(s, "WRITE 1 4093 010203", "1")
    expect(s, "READ 1 4092 4", "00010203")
    # a workgroup count over the device's limit is a device error, and the
    # session goes on
    expect(s, "DISPATCH 1 4 4294967295 1 3 4 5 6", "!gpu/device-error DISPATCH: device error")
    expect(s, "INFO", info)
    line = s.close(0)
    name = info.split("|")[0]
    assert f':device "{name}" ' in line and " :end :eof " in line, (line, name)
    rows.update(report=line.strip(), submitNanoseconds=ns, requests=len(s.log))
    report["gpu"] = dict(host=[platform.system(), platform.machine(), platform.release()], node=platform.node(), rows=rows, log=s.log[:8])
    report["status"] = "PASS_GPU_PROVIDER_VULKAN"
    (output / "gpu-provider.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], info, devclass, len(s.log), "requests", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("phase", nargs="?", choices=["build", "run", "all", "gpu"], default="all")
    parser.add_argument("--compiler", type=Path, help="build: an Amu-produced static compiler from these sources")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.phase in ("build", "all"):
        assert args.compiler, "--compiler is required to build"
        build(args.compiler.resolve(), args.output.resolve())
    if args.phase in ("run", "all"):
        run(args.output.resolve())
    if args.phase == "gpu":
        gpu(args.output.resolve())
