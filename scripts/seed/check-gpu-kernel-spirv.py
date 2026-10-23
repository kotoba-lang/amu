#!/usr/bin/env python3
"""GPU kernels as SPIR-V from Kotoba, through the loaderless compiler (ADR 0372 steps 1-3).

Suite kir1 (the default): KIR v1 elementwise (4 operators x 2 workgroup
sizes), workgroup reductions (3 x 2), the ADR 0358 workgroup-sweep FMA kernel
(LocalSize 32..1024) and the subgroup reductions (3, GroupNonUniformArithmetic).
Suite kir2 (--suite kir2): the KIR v2 builder (tools/gpu_kernel_kir2.kotoba)
and the kernels written with it (tools/gpu_kernels_v2.kotoba): KIR v1's
elementwise kernel again (4 x 2) and attn_copy_dense. Its receipt is
gpu-kernel-kir2.json; the Kotoba checker must accept glslang's module of the
hand-written attn_copy_dense (refs phase, tools/gpu_kernel_refs/), and phase
"gpu" runs both modules of each kernel through the ADR 0371 provider.

Phase "refs" (a host with glslangValidator): glslang compiles the hand-written
oracle kernels tools/gpu_kernel_refs/*.comp into OUT/refs/ref-*.spv. The
build phase puts them into the scope, and the Kotoba checker must accept
them: a structural check of modules that Amu did not write.

Phase "build" (Linux): one unit is built from the test's ns line, then the
suite's modules (kir1: tools/spirv_encode.kotoba, tools/spirv_check.kotoba and
tools/gpu_kernel_kir1.kotoba) without their ns lines, then the rest of the
suite's test (kir1: tools/gpu_kernel_spirv_test.kotoba), as seed/MANIFEST
units are built. An
Amu-produced static compiler (--compiler: the pinned root or S3.elf) compiles
it with --format static, and the image runs with a writable :fs/app-data scope
(KEXE_CAP_RESOURCES_35) into which it writes the .spv modules. Checked in
both directions:
* the unit: every case passes, and CASES equals the expect calls counted in
  the test source;
* the control (CONTROL 1, one expected refusal made wrong): exactly one fails.
The modules written are hashed into the receipt.

Phase "oracle" (any host with SPIRV-Tools): spirv-val (--target-env
vulkan1.1, i.e. SPIR-V 1.3) and spirv-dis run on every module of a build
output and their results join the receipt. They are test oracles only: the
product route has no C or C++ tool (ADR 0372).

Phase "gpu" (suite kir2, a GPU host only: libvulkan runs there and nowhere
else, owner decision 2026-10-22): each KIR v2 module and glslang's module of
the same source run through the ADR 0371 provider (the provider-vulkan image
of a scripts/seed/check-gpu-provider.py build output, --provider) on the same
inputs. ewise: z = x + y, exact. attn_copy_dense: three shapes (GQA with the
dynamic position; no GQA, P.aux and two rows; d = 320 with T = 256), the
cache rows written by phase 1 compared byte for byte with the expected copy,
the outputs compared with each other byte for byte (the same arithmetic in
the same order) and with an f64 reference of the same math (below 1e-5). The inputs are 24-bit values from a fixed LCG (exact in
f32), and the receipt records their digests.

Python only orchestrates processes and hashes. Examples:
  podman run --platform linux/arm64 -v REPO:REPO -v OUT:OUT python:3.12-alpine \
    python3 REPO/scripts/seed/check-gpu-kernel-spirv.py build \
    --compiler REPO/seed/bootstrap/aarch64-linux-static-root.elf --output OUT
  python3 scripts/seed/check-gpu-kernel-spirv.py oracle --output OUT
(run "refs --output OUT" on the host first.)
  python3 scripts/seed/check-gpu-kernel-spirv.py gpu --suite kir2 --output OUT --provider PROVIDER_OUT
"""
import argparse
import hashlib
import importlib.util
import json
import math
import platform
import re
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENCODE_CHECK = ["tools/spirv_encode.kotoba", "tools/spirv_check.kotoba"]
# modules, test, the receipt, the written modules' prefix and their sizes by
# name part, the control's one failure, and whether glslang refs go in
SUITES = {
    "kir1": dict(modules=[*ENCODE_CHECK, "tools/gpu_kernel_kir1.kotoba"], test="tools/gpu_kernel_spirv_test.kotoba",
                 receipt="gpu-kernel-spirv.json", prefix="kir1-",
                 sizes={"ewise": 1004, "reduce-sum": 1740, "reduce-max": 1748, "reduce-min": 1748, "sweep": 856,
                        "subgroup-sum": 1896, "subgroup-max": 1904, "subgroup-min": 1904},
                 count=23, control="FAIL label inside an open block", refs=True),
    "kir2": dict(modules=[*ENCODE_CHECK, "tools/gpu_kernel_kir2.kotoba", "tools/gpu_kernels_v2.kotoba"],
                 test="tools/gpu_kernel_kir2_test.kotoba", receipt="gpu-kernel-kir2.json", prefix="kir2-",
                 sizes={"ewise": 1096, "attn-copy-dense": 6488}, count=9, control="FAIL attn: variables", refs=True),
}
FUEL = 100000000
EXPECT_CALL = re.compile(r"\(expect ")
REPORT = re.compile(rb"\{:status :(\w+) :result (-?\d+) :fuel \{:initial (\d+) :remaining (\d+)\}\}")


def pin(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def split_ns(text, name):
    first, rest = text.split("\n", 1)
    assert first.startswith("(ns ") and first.endswith("))") and first.count("(") == first.count(")"), (name, first)
    return first, rest


def units(suite):
    bodies = [split_ns((ROOT / m).read_text(), m)[1] for m in suite["modules"]]
    test_ns, test_body = split_ns((ROOT / suite["test"]).read_text(), suite["test"])
    counted = len(EXPECT_CALL.findall(test_body))
    assert counted > 0 and f"(def CASES {counted})" in test_body, ("CASES must equal the expect calls", counted)
    assert test_body.count("(def CONTROL 0)") == 1
    unit = "\n".join([test_ns, *bodies, test_body])
    return counted, unit, unit.replace("(def CONTROL 0)", "(def CONTROL 1)")


REFS = ROOT / "tools/gpu_kernel_refs"


def refs(output):
    glslang = shutil.which("glslangValidator")
    assert glslang, "glslangValidator is needed for the refs phase (oracle input only)"
    out = output / "refs"
    out.mkdir(parents=True, exist_ok=False)
    rows = {}
    for comp in sorted(REFS.glob("*.comp")):
        spv = out / ("ref-" + comp.stem + ".spv")
        r = subprocess.run([glslang, "-V", "--target-env", "vulkan1.1", str(comp), "-o", str(spv)], capture_output=True, text=True)
        assert r.returncode == 0, (comp.name, r.stdout, r.stderr)
        rows[spv.name] = dict(source=pin(comp), module=pin(spv))
    version = subprocess.run([glslang, "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    (out / "refs.json").write_text(json.dumps(dict(tool=version, host=[platform.system(), platform.machine()], modules=rows,
                                                   note="oracle input only; not part of the product route"), indent=2) + "\n")
    print("REFS", len(rows), "glslang modules", flush=True)


def build(compiler, output, target, suite, seccomp_if_available=False):
    assert platform.system() == "Linux", "run the build phase on Linux"
    refs_dir = output / "refs"
    assert not suite["refs"] or (refs_dir / "refs.json").exists(), "run the refs phase first (on a host with glslangValidator)"
    art = output / "artifacts"
    art.mkdir(exist_ok=False)
    counted, unit, control = units(suite)
    producer = art / "compiler.elf"
    producer.write_bytes(compiler.read_bytes())
    producer.chmod(0o755)

    def build_and_run(name, source, scope):
        scope.mkdir()
        for ref in refs_dir.glob("ref-*.spv"):
            shutil.copy(ref, scope / ref.name)
        src, elf = art / (name + ".kotoba"), art / (name + ".elf")
        src.write_text(source)
        c = subprocess.run([str(producer), "compile", str(src), "--target", target, "--output", str(elf), "--format", "static"],
                           cwd=art, env={"PATH": "/usr/bin:/bin", "KEXE_CAP_RESOURCES_35": str(art)}, capture_output=True, timeout=600)
        (art / (name + ".compile.stderr")).write_bytes(c.stderr)
        assert c.returncode == 0 and not c.stderr and b":ok true" in c.stdout, (name, c.returncode, c.stderr[-400:])
        elf.chmod(0o700)
        x = subprocess.run([str(elf)], cwd=scope,
                           env={"PATH": "/usr/bin:/bin", "KEXE_STRUCTURED_REPORT": "1", "KEXE_FUEL": str(FUEL),
                                "KEXE_CAP_RESOURCES_35": str(scope), **({"KEXE_SECCOMP": "if-available"} if seccomp_if_available else {})},
                           capture_output=True, timeout=300)
        (art / (name + ".run.stdout")).write_bytes(x.stdout)
        (art / (name + ".run.stderr")).write_bytes(x.stderr)
        assert x.returncode == 0 and not x.stderr, (name, x.returncode, x.stderr[-400:])
        lines = x.stdout.decode().splitlines()
        report = REPORT.search(x.stdout)
        assert report and report.group(1) == b"ok", (name, x.stdout[-400:])
        cases = [int(l.split()[1]) for l in lines if l.startswith("CASES ")]
        failed = [int(l.split()[1]) for l in lines if l.startswith("FAILED ")]
        fails = [l for l in lines if l.startswith("FAIL ")]
        assert len(cases) == 1 and len(failed) == 1, (name, lines[-5:])
        return dict(name=name, source=pin(src), image=pin(elf), result=int(report.group(2)),
                    fuelUsed=int(report.group(3)) - int(report.group(4)), cases=cases[0], failed=failed[0],
                    failLines=fails), cases[0], failed[0], fails

    spv = output / "spv"
    u, cases, failed, fails = build_and_run("kernel-test", unit, spv)
    assert cases == counted and failed == 0 and not fails, u
    k, cases, failed, fails = build_and_run("kernel-control", control, output / "spv-control")
    assert cases == counted and failed == 1 and len(fails) == 1 and fails[0].startswith(suite["control"]), fails
    modules = {p.name: pin(p) for p in sorted(spv.glob(suite["prefix"] + "*.spv"))}
    sizes = suite["sizes"]
    assert len(modules) == suite["count"] and all(m["bytes"] == next(v for k, v in sizes.items() if k in n) for n, m in modules.items()), modules
    report = dict(status="PASS_GPU_KERNEL_SPIRV_BUILD", suite=suite["name"], target=target, compiler=pin(compiler),
                  host=[platform.system(), platform.machine(), platform.release()],
                  imageSeccomp="if-available" if seccomp_if_available else "required",
                  sources={p: pin(ROOT / p) for p in [*suite["modules"], suite["test"]]}, casesCounted=counted, runs=[u, k],
                  modules=modules, cCompilerOrLoader=False)
    if suite["refs"]:
        report["glslangReferences"] = json.loads((refs_dir / "refs.json").read_text())
    (output / suite["receipt"]).write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], target, counted, "cases", len(modules), "modules", flush=True)


def oracle(output, suite):
    receipt_path = output / suite["receipt"]
    report = json.loads(receipt_path.read_text())
    val, dis = shutil.which("spirv-val"), shutil.which("spirv-dis")
    assert val and dis, "spirv-val and spirv-dis are needed for the oracle phase"
    version = subprocess.run([val, "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    rows = {}
    for name, expected in report["modules"].items():
        path = output / "spv" / name
        assert pin(path) == expected, (name, "module changed since the build")
        v = subprocess.run([val, "--target-env", "vulkan1.1", str(path)], capture_output=True, text=True)
        d = subprocess.run([dis, "--raw-id", str(path)], capture_output=True, text=True)
        (output / (name + ".dis")).write_text(d.stdout)
        assert v.returncode == 0 and not v.stdout.strip() and not v.stderr.strip(), (name, v.stdout, v.stderr)
        assert d.returncode == 0 and "OpEntryPoint GLCompute" in d.stdout, (name, d.stderr)
        rows[name] = dict(spirvVal="valid (vulkan1.1)", disassembledSHA256=hashlib.sha256(d.stdout.encode()).hexdigest())
    report["oracle"] = dict(tool=version, host=[platform.system(), platform.machine()], modules=rows,
                            note="test oracle only; not part of the product route")
    report["status"] = "PASS_GPU_KERNEL_SPIRV_BUILD_AND_ORACLE"
    receipt_path.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(rows), "modules valid", flush=True)


def provider_driver():
    """check-gpu-provider.py's Session, grant and expect: the provider's protocol driver."""
    spec = importlib.util.spec_from_file_location("check_gpu_provider", ROOT / "scripts/seed/check-gpu-provider.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def lcg(n, seed):
    """n values in [-1, 1) with 24 significant bits (exact in f32) from a fixed LCG."""
    out, x = [], seed
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        out.append((x >> 40) / float(1 << 23) - 1.0)
    return out


def f32(values):
    return struct.pack(f"<{len(values)}f", *values)


def from_f32(b):
    return list(struct.unpack(f"<{len(b) // 4}f", b))


def attn_reference(c, a, kc, vc, dk, dv):
    """attn_copy_dense in f64: the cache after phase 1, and o."""
    d, H, KVH, Y, pos = c["d"], c["heads"], c["kvHeads"], c["rows"], c["pos"]
    group = H // KVH
    kc, vc = list(kc), list(vc)
    for h in range(0, H, group):
        hkv, coff = h // group, pos * KVH * d + (h // group) * d
        kc[coff:coff + d], vc[coff:coff + d] = dk[hkv * d:hkv * d + d], dv[hkv * d:hkv * d + d]
    o = [0.0] * (Y * H * d)
    for row in range(Y):
        T = (pos + 1 if c["p1"] != 0 else c["aux"]) + row
        for h in range(H):
            hkv, q = h // group, row * H * d + h * d
            krow = [dk[hkv * d:hkv * d + d] if t == pos else kc[(t * KVH + hkv) * d:(t * KVH + hkv) * d + d] for t in range(T)]
            vrow = [dv[hkv * d:hkv * d + d] if t == pos else vc[(t * KVH + hkv) * d:(t * KVH + hkv) * d + d] for t in range(T)]
            sc = [c["scale"] * sum(a[q + i] * krow[t][i] for i in range(d)) for t in range(T)]
            m = max(sc)
            e = [math.exp(x - m) for x in sc]
            den = sum(e)
            for i in range(d):
                o[q + i] = sum(e[t] / den * vrow[t][i] for t in range(T))
    return kc, vc, o


# attn_copy_dense shapes: GQA (4 query heads per kv head) at the dynamic
# position; no GQA with P.aux and two rows (row 1 sees one more position);
# d = 320 (two i per invocation) with T = 256, the kernel's largest
ATTN_SHAPES = [
    dict(name="gqa-dynamic", d=64, heads=8, kvHeads=2, rows=1, p1=1.0, aux=0, pos=37, maxpos=64),
    dict(name="aux-two-rows", d=128, heads=8, kvHeads=8, rows=2, p1=0.0, aux=200, pos=199, maxpos=256),
    dict(name="d320-t256", d=320, heads=4, kvHeads=1, rows=1, p1=1.0, aux=0, pos=255, maxpos=256),
]


def gpu(output, suite, provider_out):
    assert suite["name"] == "kir2", "the gpu phase is suite kir2's"
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "gpu phase: x86_64 Linux with a Vulkan driver"
    cgp = provider_driver()
    receipt_path = output / suite["receipt"]
    report = json.loads(receipt_path.read_text())
    preport = json.loads((provider_out / "gpu-provider.json").read_text())
    img = provider_out / preport["images"]["provider-vulkan"]
    raw = output / "gpu"
    raw.mkdir(exist_ok=False)
    files = {"v2-attn.spv": output / "spv" / "kir2-attn-copy-dense.spv", "ref-attn.spv": output / "refs" / "ref-attn-copy-dense.spv",
             "v2-add.spv": output / "spv" / "kir2-ewise-add-wg256.spv", "ref-add.spv": output / "refs" / "ref-ewise-add.spv"}
    for n, f in files.items():
        shutil.copy(f, raw / n)
    assert pin(raw / "v2-attn.spv") == report["modules"]["kir2-attn-copy-dense.spv"], "module changed since the build"
    g = cgp.grant([(n, pin(raw / n)["sha256"], "spirv") for n in files], cap=1 << 28)
    s = cgp.Session(img, raw, "kir2-gpu", g, device=None)
    info = cgp.expect(s, "INFO", re.compile(r"[^|]+\|\d+\.\d+\.\d+\|\d+\|[01]"))
    handles = [0]

    def alloc(nbytes):
        handles[0] += 1
        cgp.expect(s, f"ALLOC {nbytes}", str(handles[0]))
        return handles[0]

    def write(h, b):
        cgp.expect(s, f"WRITE {h} 0 {b.hex()}", "1")

    def read(h, nbytes):
        return bytes.fromhex(cgp.expect(s, f"READ {h} 0 {nbytes}", re.compile(r"^[0-9a-f]*$")))

    pipes = {}
    for k, n in enumerate(["ref-add.spv", "v2-add.spv", "ref-attn.spv", "v2-attn.spv"]):
        cgp.expect(s, f"PIPELINE {n} {4 if 'add' in n else 8}", str(k + 1))
        pipes[n] = k + 1
    rows = {}
    # ewise: z = x + y over n = 1000, exact in f32
    n = 1000
    x, y = lcg(n, 1), lcg(n, 2)
    bx, by, bz, bn = alloc(4 * n), alloc(4 * n), alloc(4 * n), alloc(4)
    for h, b in ((bx, f32(x)), (by, f32(y)), (bn, struct.pack("<I", n))):
        write(h, b)
    # packing rounds the f64 sum once: the f32 sum
    want = f32([a + b for a, b in zip(x, y)])
    for m in ("ref-add.spv", "v2-add.spv"):
        cgp.expect(s, f"ZERO {bz}", "1")
        cgp.expect(s, f"DISPATCH {pipes[m]} 4 1 1 {bx} {by} {bz} {bn}", re.compile(r"^\d+$"))
        assert read(bz, 4 * n) == want, (m, "z = x + y")
    rows["ewise-add"] = dict(n=n, exact=True, modules=["ref-add.spv", "v2-add.spv"])
    # attn_copy_dense
    for c in ATTN_SHAPES:
        d, H, KVH, Y = c["d"], c["heads"], c["kvHeads"], c["rows"]
        c = dict(c, scale=1.0 / math.sqrt(d))
        a, dk, dv = lcg(Y * H * d, 3), lcg(KVH * d, 4), lcg(KVH * d, 5)
        kc0, vc0 = lcg(c["maxpos"] * KVH * d, 6), lcg(c["maxpos"] * KVH * d, 7)
        meta = struct.pack("<4I4f", d, H, c["aux"], KVH, 1e-6, c["scale"], 1.0, c["p1"])
        kc_want, vc_want, o_ref = attn_reference(c, a, kc0, vc0, dk, dv)
        bufs = [alloc(len(meta)), alloc(4 * len(a)), alloc(4 * len(kc0)), alloc(4 * len(vc0)), alloc(4 * Y * H * d),
                alloc(4 * len(dv)), alloc(4 * len(dk)), alloc(4)]
        outs = {}
        for m in ("ref-attn.spv", "v2-attn.spv"):
            for h, b in zip(bufs, [meta, f32(a), f32(kc0), f32(vc0), bytes(4 * Y * H * d), f32(dv), f32(dk), struct.pack("<I", c["pos"])]):
                write(h, b)
            cgp.expect(s, f"DISPATCH {pipes[m]} {H} {Y} 1 " + " ".join(map(str, bufs)), re.compile(r"^\d+$"))
            kc, vc, o = read(bufs[2], 4 * len(kc0)), read(bufs[3], 4 * len(vc0)), read(bufs[4], 4 * Y * H * d)
            assert kc == f32(kc_want) and vc == f32(vc_want), (m, c["name"], "the cache after phase 1")
            err = max(abs(u - v) for u, v in zip(from_f32(o), o_ref))
            assert err < 1e-5, (m, c["name"], "o against the f64 reference", err)
            outs[m] = dict(o=o, maxAbsErrVsF64=err)
        # the same arithmetic in the same order: the driver gives the same bits
        diff = sum(1 for u, v in zip(from_f32(outs["ref-attn.spv"]["o"]), from_f32(outs["v2-attn.spv"]["o"])) if u != v)
        assert diff == 0, (c["name"], diff, "outputs differ from glslang's module")
        rows["attn-copy-dense " + c["name"]] = dict(
            shape={k: c[k] for k in ("d", "heads", "kvHeads", "rows", "p1", "aux", "pos", "maxpos")},
            T=[(c["pos"] + 1 if c["p1"] != 0 else c["aux"]) + r for r in range(Y)],
            inputsSHA256=hashlib.sha256(meta + f32(a) + f32(kc0) + f32(vc0) + f32(dv) + f32(dk)).hexdigest(),
            cacheRowsExact=True, outputsIdentical=True,
            maxAbsErrVsF64={m: outs[m]["maxAbsErrVsF64"] for m in outs},
            outputSHA256={m: hashlib.sha256(outs[m]["o"]).hexdigest() for m in outs})
    line = s.close(0)
    rows["confinement"] = cgp.confined(line, True)
    report["gpu"] = dict(host=[platform.system(), platform.machine(), platform.release()], node=platform.node(), info=info,
                         provider=dict(image=pin(img), source=preport.get("sources")), modules={n: pin(raw / n) for n in files},
                         rows=rows, report=line.strip(), requests=len(s.log),
                         note="glslang's modules are oracle inputs; the f64 reference is Python, test-time only")
    report["status"] = "PASS_GPU_KERNEL_KIR2_GPU"
    receipt_path.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], info, len(rows), "rows", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("phase", choices=["refs", "build", "oracle", "gpu"])
    parser.add_argument("--provider", type=Path, help="gpu: a check-gpu-provider.py build output (its provider-vulkan image)")
    parser.add_argument("--compiler", type=Path, help="build: an Amu-produced static compiler (the pinned root or S3.elf)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["aarch64-linux", "x86_64-linux"], default="aarch64-linux")
    parser.add_argument("--suite", choices=sorted(SUITES), default="kir1")
    parser.add_argument("--seccomp-if-available", action="store_true",
                        help="build: run the tool image with KEXE_SECCOMP=if-available (qemu-user has no seccomp); recorded")
    args = parser.parse_args()
    suite = dict(SUITES[args.suite], name=args.suite)
    if args.phase == "refs":
        refs(args.output.resolve())
    elif args.phase == "build":
        assert args.compiler, "--compiler is required for the build phase"
        build(args.compiler.resolve(), args.output.resolve(), args.target, suite, args.seccomp_if_available)
    elif args.phase == "gpu":
        assert args.provider, "--provider is required for the gpu phase"
        gpu(args.output.resolve(), suite, args.provider.resolve())
    else:
        oracle(args.output.resolve(), suite)
