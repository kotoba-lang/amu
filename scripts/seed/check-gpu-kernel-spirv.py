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
else, owner decision 2026-10-22), after the oracle phase: every KIR v2 module
runs through the ADR 0371 provider (the provider-vulkan image of a
scripts/seed/check-gpu-provider.py build output, --provider), and where a
glslang module of the same source exists it runs beside it on the same
inputs. The modules must be the bytes the build and refs phases recorded.
* ewise, all eight modules: add, sub and mul exact, div within 3 ulp; the
  two workgroup sizes give the same bytes; add/wg256 gives glslang's bytes.
* attn_copy_dense, three shapes (GQA with the dynamic position; no GQA,
  P.aux and two rows; d = 320 with T = 256): the cache rows written by phase
  1 equal the expected copy, the output bytes equal glslang's module's (the
  same arithmetic in the same order), and both are within 1e-5 of an f64
  reference of the same math.
The inputs are 24-bit values from a fixed LCG (exact in f32), and the
receipt records their digests.

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
EWISE_OPS = ["add", "sub", "mul", "div"]
# nex-ops.comp is one kernel per -DOP (the decode ops that KIR v2 writes,
# tools/gpu_kernels_v2.kotoba kir2-nex-op 1..19 in this order)
NEX_OPS = ["rmsnorm", "l2norm", "gated_rmsnorm", "silu_mul", "conv1d_step", "gate_decay", "gate_decay2", "copy_at",
           "weighted_sum", "add", "add_bias", "f32_matvec", "add_rmsnorm", "pos_incr", "rope_neox", "attn_decode",
           "softmax_topk", "argmax_partial", "argmax_final"]
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
                 sizes={"ewise": 1096, "attn-copy-dense": 6488, **{"kir2-nex-" + op + ".spv": n for op, n in zip(NEX_OPS, [3440, 3468, 3516, 1992, 2660, 2452, 2396, 2140, 2704, 1872, 1968, 3088, 3476, 1652, 3988, 5964, 5356, 3604, 4052])},
                        "kir2-dot-rows.spv": 2448, "kir2-kdot-f32-r1.spv": 28776,
                        "kir2-kdot-f32-r8.spv": 25056, "kir2-kdot-f32-r8-rows4.spv": 25056,
                        "kir2-kdot-f32-r8-rows16.spv": 25072, "kir2-kdot-f32-r8-rows32.spv": 25072},
                 count=34, control="FAIL attn: variables", refs=True),
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
# sources compiled more than once: (name suffix, -D define) per module
REF_VARIANTS = {"nex-ops.comp": [(op, "OP=" + op) for op in NEX_OPS],
                "kdot-f32-r8.comp": [(None, None), ("rows4", "ROWS=4"), ("rows16", "ROWS=16"), ("rows32", "ROWS=32")]}


def refs(output):
    glslang = shutil.which("glslangValidator")
    assert glslang, "glslangValidator is needed for the refs phase (oracle input only)"
    out = output / "refs"
    out.mkdir(parents=True, exist_ok=False)
    rows = {}
    for comp in sorted(REFS.glob("*.comp")):
        for suffix, define in REF_VARIANTS.get(comp.name, [(None, None)]):
            spv = out / ("ref-" + comp.stem + ("-" + suffix if suffix else "") + ".spv")
            r = subprocess.run([glslang, "-V", "--target-env", "vulkan1.1", *(["-D" + define] if define else []), str(comp), "-o", str(spv)],
                               capture_output=True, text=True)
            assert r.returncode == 0, (comp.name, define, r.stdout, r.stderr)
            rows[spv.name] = dict(source=pin(comp), define=define, module=pin(spv))
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
    # a module's size by its name, else by the first key inside its name
    size = lambda n: sizes[n] if n in sizes else next(v for k, v in sizes.items() if k in n)
    assert len(modules) == suite["count"] and all(m["bytes"] == size(n) for n, m in modules.items()), modules
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


def nex_cases():
    """The nex_ops gate: per case the op, Meta, bindings 1..6 (inputs, and the
    writable ones' initial bytes), the workgroups, and an optional check of the
    outputs (bindings -> bytes) answering the largest error (0 when exact)."""
    def meta(n=0, rows=0, aux=0, aux2=0, eps=0.0, scale=0.0, p0=0.0, p1=0.0):
        return struct.pack("<4I4f", n, rows, aux, aux2, eps, scale, p0, p1)

    def bufs(**kw):
        out = {b: bytes(16) for b in range(1, 7)}
        for k, v in kw.items():
            out["_abcosi".index(k)] = v if isinstance(v, bytes) else f32(v)
        return out

    def near(got, want):
        return max(abs(g - w) for g, w in zip(from_f32(got), want))

    def rms(a, w, n, rows, stride, eps):
        out = []
        for r in range(rows):
            x = a[r * stride:r * stride + n]
            inv = 1.0 / math.sqrt(sum(v * v for v in x) / n + eps)
            out += [x[i] * inv * w[i] for i in range(n)]
        return out

    cases = []
    a, w = lcg(3 * 2100, 11), lcg(2048, 12)
    cases.append(dict(name="rmsnorm stride", op="rmsnorm", meta=meta(n=2048, aux=2100, eps=1e-6),
                      bufs=bufs(a=a, b=w, o=bytes(4 * 3 * 2048)), groups=(3, 1, 1),
                      check=lambda o, a=a, w=w: near(o[4], rms(a, w, 2048, 3, 2100, 1e-6))))
    a2 = lcg(2 * 1024, 13)
    cases.append(dict(name="rmsnorm contiguous", op="rmsnorm", meta=meta(n=1024, eps=1e-5),
                      bufs=bufs(a=a2, b=w[:1024], o=bytes(4 * 2 * 1024)), groups=(2, 1, 1),
                      check=lambda o, a=a2, w=w: near(o[4], rms(a, w, 1024, 2, 1024, 1e-5))))
    for sc in (0.0, 0.5):
        cases.append(dict(name=f"l2norm scale {sc}", op="l2norm", meta=meta(n=128, aux2=64, eps=1e-6, scale=sc),
                          bufs=bufs(a=lcg(64 + 4 * 128, 14), o=bytes(4 * 4 * 128)), groups=(4, 1, 1)))
    cases.append(dict(name="gated_rmsnorm", op="gated_rmsnorm", meta=meta(n=128, eps=1e-6),
                      bufs=bufs(a=lcg(512, 15), b=lcg(128, 16), c=lcg(512, 17), o=bytes(2048)), groups=(4, 1, 1)))
    cases.append(dict(name="silu_mul", op="silu_mul", meta=meta(n=1000),
                      bufs=bufs(a=lcg(1000, 18), b=lcg(1000, 19), o=bytes(4000)), groups=(4, 1, 1)))
    cases.append(dict(name="conv1d_step", op="conv1d_step", meta=meta(n=500),
                      bufs=bufs(a=lcg(500, 20), b=lcg(2000, 21), s=lcg(1500, 22), o=bytes(2000)), groups=(2, 1, 1)))
    # softplus takes both arms: a[h] + b[h] > 20 for the first four heads;
    # rows, aux (o's offset) and aux2 (a's offset) all differ
    big = [25.0] * 4 + lcg(104, 23)
    cases.append(dict(name="gate_decay", op="gate_decay", meta=meta(rows=48, aux=50, aux2=60),
                      bufs=bufs(a=big, b=lcg(48, 24), c=lcg(48, 25), o=bytes(4 * 98)), groups=(1, 1, 1)))
    cases.append(dict(name="gate_decay2", op="gate_decay2", meta=meta(rows=48, aux=52),
                      bufs=bufs(a=big[:48], b=lcg(48, 24), c=lcg(48, 25), s=lcg(48, 26), o=bytes(4 * 100)), groups=(1, 1, 1)))
    x = lcg(512, 27)
    cases.append(dict(name="copy_at dynamic", op="copy_at", meta=meta(n=512, aux2=512, p1=1.0),
                      bufs=bufs(a=x, o=bytes(4 * 8 * 512), i=struct.pack("<4I", 3, 0, 0, 0)), groups=(2, 1, 1),
                      check=lambda o, x=x: 0 if o[4] == bytes(4 * 3 * 512) + f32(x) + bytes(4 * 4 * 512) else 1))
    cases.append(dict(name="copy_at static", op="copy_at", meta=meta(n=512, aux2=1024),
                      bufs=bufs(a=x, o=bytes(4 * 8 * 512), i=struct.pack("<4I", 3, 0, 0, 0)), groups=(2, 1, 1),
                      check=lambda o, x=x: 0 if o[4] == bytes(4 * 1024) + f32(x) + bytes(4 * 5 * 512) else 1))
    cases.append(dict(name="weighted_sum", op="weighted_sum", meta=meta(n=300, aux=8),
                      bufs=bufs(a=lcg(16 * 300, 28), b=lcg(16, 29), c=lcg(600, 30), s=lcg(2, 31), o=bytes(2400)), groups=(2, 2, 1)))
    y1, y2 = lcg(1000, 32), lcg(1000, 33)
    cases.append(dict(name="add", op="add", meta=meta(n=1000), bufs=bufs(a=y1, b=y2, o=bytes(4000)), groups=(4, 1, 1),
                      check=lambda o, y1=y1, y2=y2: 0 if o[4] == f32([u + v for u, v in zip(y1, y2)]) else 1))
    cases.append(dict(name="add_bias", op="add_bias", meta=meta(n=1000, aux=100), bufs=bufs(a=y1, b=y2[:100], o=bytes(4000)),
                      groups=(4, 1, 1), check=lambda o, y1=y1, y2=y2: 0 if o[4] == f32([y1[i] + y2[i % 100] for i in range(1000)]) else 1))
    m, v = lcg(64 * 1024, 34), lcg(2 * 1024, 35)
    cases.append(dict(name="f32_matvec", op="f32_matvec", meta=meta(n=1024, rows=64), bufs=bufs(a=m, b=v, o=bytes(4 * 128)),
                      groups=(64, 2, 1),
                      check=lambda o, m=m, v=v: near(o[4], [sum(m[r * 1024 + i] * v[y * 1024 + i] for i in range(1024))
                                                            for y in range(2) for r in range(64)])))
    cases.append(dict(name="add_rmsnorm", op="add_rmsnorm", meta=meta(n=2048, eps=1e-6),
                      bufs=bufs(a=lcg(4096, 36), b=lcg(4096, 37), c=lcg(2048, 38), o=bytes(4 * 4096), s=bytes(4 * 4096)),
                      groups=(2, 1, 1)))
    cases.append(dict(name="pos_incr", op="pos_incr", meta=meta(), bufs=bufs(i=struct.pack("<4I", 5, 7, 0, 0)), groups=(1, 1, 1),
                      check=lambda o: 0 if o[6] == struct.pack("<4I", 6, 7, 0, 0) else 1))
    # rope: NEOX pairs at the dynamic position with a rotated part and a
    # copied tail; NORMAL pairs at P.aux2, two heads per token, with
    # rope_freqs divisors (P.eps != 0)
    cases.append(dict(name="rope_neox neox", op="rope_neox", meta=meta(n=128, aux=64, scale=10000.0, p1=1.0),
                      bufs=bufs(a=lcg(512, 39), o=bytes(2048), i=struct.pack("<4I", 7, 0, 0, 0)), groups=(4, 1, 1)))
    cases.append(dict(name="rope_neox normal", op="rope_neox", meta=meta(n=64, rows=2, aux=64, aux2=5, eps=1.0, scale=500000.0, p0=1.0),
                      bufs=bufs(a=lcg(256, 40), b=[1.0 + 0.125 * k for k in range(32)], o=bytes(1024)), groups=(4, 1, 1)))
    # NEOX at the dynamic position with two heads per token, rope_freqs and a
    # copied tail; NORMAL with a copied tail
    cases.append(dict(name="rope_neox neox dynamic rows freqs", op="rope_neox",
                      meta=meta(n=128, rows=2, aux=64, eps=1.0, scale=10000.0, p1=1.0),
                      bufs=bufs(a=lcg(512, 120), b=[1.0 + 0.0625 * k for k in range(32)], o=bytes(2048), i=struct.pack("<4I", 9, 0, 0, 0)),
                      groups=(4, 1, 1)))
    cases.append(dict(name="rope_neox normal tail", op="rope_neox", meta=meta(n=128, aux=96, aux2=3, scale=10000.0, p0=1.0),
                      bufs=bufs(a=lcg(512, 121), o=bytes(2048)), groups=(4, 1, 1)))
    # attn_decode: the interleaved output gate at the dynamic position (T =
    # 38, GQA); dense (p0 != 0, s a stub) with P.aux and two rows
    cases.append(dict(name="attn_decode gated", op="attn_decode", meta=meta(n=64, rows=8, aux2=2, eps=-1.0, scale=0.125, p1=1.0),
                      bufs=bufs(a=lcg(512, 41), b=lcg(64 * 2 * 64, 42), c=lcg(64 * 2 * 64, 43), o=bytes(2048), s=lcg(1024, 44),
                                i=struct.pack("<4I", 37, 0, 0, 0)), groups=(8, 1, 1)))
    # the interleaved gate on two rows (T = 38, 39); the plain gate (eps >= 0,
    # p0 == 0: s[qoff + h d + i]) with P.aux and two rows
    cases.append(dict(name="attn_decode gated two rows", op="attn_decode", meta=meta(n=64, rows=8, aux2=2, eps=-1.0, scale=0.125, p1=1.0),
                      bufs=bufs(a=lcg(1024, 122), b=lcg(64 * 2 * 64, 42), c=lcg(64 * 2 * 64, 43), o=bytes(4096), s=lcg(2048, 123),
                                i=struct.pack("<4I", 37, 0, 0, 0)), groups=(8, 2, 1)))
    cases.append(dict(name="attn_decode plain gate", op="attn_decode", meta=meta(n=64, rows=4, aux=10, aux2=4, eps=1e-6, scale=0.125),
                      bufs=bufs(a=lcg(512, 124), b=lcg(16 * 4 * 64, 125), c=lcg(16 * 4 * 64, 126), o=bytes(2048), s=lcg(512, 127)),
                      groups=(4, 2, 1)))
    cases.append(dict(name="attn_decode dense", op="attn_decode", meta=meta(n=128, rows=4, aux=40, aux2=4, eps=1e-6, scale=0.088, p0=1.0),
                      bufs=bufs(a=lcg(2 * 4 * 128, 45), b=lcg(48 * 4 * 128, 46), c=lcg(48 * 4 * 128, 47), o=bytes(4 * 1024)),
                      groups=(4, 2, 1)))
    # softmax_topk: 2 tokens over 128 experts, top 8, scaled
    logits = lcg(256, 48)

    def topk(o, k=8, n=128, scale=2.5):
        ids, out = struct.unpack("<16I", o[6][:64]), from_f32(o[4][:64])
        err = 0.0
        for r in range(2):
            x = logits[r * n:(r + 1) * n]
            m = max(x)
            e = [math.exp(v - m) for v in x]
            p = [v / sum(e) for v in e]
            pick = sorted(range(n), key=lambda j: (-p[j], j))[:k]
            if list(ids[r * k:(r + 1) * k]) != pick:
                return 1.0
            w = sum(p[j] for j in pick)
            err = max(err, max(abs(out[r * k + q] - p[pick[q]] / w * scale) for q in range(k)))
        return err
    cases.append(dict(name="softmax_topk", op="softmax_topk", meta=meta(n=128, aux=8, scale=2.5),
                      bufs=bufs(a=logits, o=bytes(64), i=bytes(64)), groups=(2, 1, 1), check=topk))
    # k = 4 over n = 200 (fewer experts than invocations)
    logits2 = lcg(400, 128)

    def topk4(o):
        ids, out = struct.unpack("<8I", o[6][:32]), from_f32(o[4][:32])
        err = 0.0
        for r in range(2):
            x = logits2[r * 200:(r + 1) * 200]
            e = [math.exp(v - max(x)) for v in x]
            p = [v / sum(e) for v in e]
            pick = sorted(range(200), key=lambda j: (-p[j], j))[:4]
            if list(ids[r * 4:(r + 1) * 4]) != pick:
                return 1.0
            err = max(err, max(abs(out[r * 4 + q] - p[pick[q]] / sum(p[j] for j in pick)) for q in range(4)))
        return err
    cases.append(dict(name="softmax_topk k4 n200", op="softmax_topk", meta=meta(n=200, aux=4, scale=1.0),
                      bufs=bufs(a=logits2, o=bytes(32), i=bytes(32)), groups=(2, 1, 1), check=topk4))
    # argmax: three partials over 10000 logits with ties at the maximum inside
    # a workgroup and across them (the lower index wins), then the final pick
    # (a tie between partials too) into the token buffer
    lg = lcg(10000, 49)
    lg[123] = lg[200] = lg[5000] = lg[9000] = 2.0

    def partial(o):
        want_v, want_i = [], []
        for w in range(3):
            seg = range(w * 4096, min(w * 4096 + 4096, 10000))
            j = min(seg, key=lambda q: (-lg[q], q))
            want_v.append(lg[j])
            want_i.append(j)
        return 0 if o[5][:12] == f32(want_v) and struct.unpack("<3I", o[6][:12]) == tuple(want_i) else 1
    cases.append(dict(name="argmax_partial", op="argmax_partial", meta=meta(n=10000),
                      bufs=bufs(a=lg, s=bytes(16), i=bytes(16)), groups=(3, 1, 1), check=partial))
    # the token-buffer guard at its boundary: pos + 1 == aux2 writes b[5];
    # inside the prompt (aux2 = 6) and with a static position nothing is written
    for label, aux2, p1, want_b in (("at the prompt's end", 5, 1.0, bytes(20) + struct.pack("<I", 4200) + bytes(8)),
                                    ("inside the prompt", 6, 1.0, bytes(32)), ("static position", 2, 0.0, bytes(32))):
        cases.append(dict(name="argmax_final " + label, op="argmax_final", meta=meta(aux=3, aux2=aux2, p1=p1),
                          bufs=bufs(b=bytes(32), c=struct.pack("<I", 4) + bytes(12), o=bytes(16), s=f32([0.5, 0.9, 0.9, 0.0]),
                                    i=struct.pack("<4I", 10, 4200, 9000, 0)), groups=(1, 1, 1),
                          check=lambda o, want_b=want_b: 0 if (struct.unpack("<4I", o[6]) == (10, 4200, 9000, 4200)
                                                               and o[2] == want_b) else 1))
    cases.append(dict(name="argmax_final", op="argmax_final", meta=meta(aux=3, aux2=2, p1=1.0),
                      bufs=bufs(b=bytes(32), c=struct.pack("<I", 4) + bytes(12), o=bytes(16), s=f32([0.5, 0.9, 0.9, 0.0]),
                                i=struct.pack("<4I", 10, 4200, 9000, 0)), groups=(1, 1, 1),
                      check=lambda o: 0 if (struct.unpack("<4I", o[6]) == (10, 4200, 9000, 4200) and o[4][:4] == f32([0.9])
                                            and o[2] == bytes(20) + struct.pack("<I", 4200) + bytes(8)) else 1))
    return cases


# kdot_f32_r1's tensor types: type -> bytes per 256 values (block_bytes_of);
# kdot_f32_r8 has all but BF16 (30), PQ2_0 (142) and PTQ1_0 (143)
KDOT_TYPES = {12: 144, 13: 176, 14: 210, 23: 136, 8: 272, 2: 144, 1: 512, 30: 512, 142: 68, 143: 56, 3: 160, 6: 176, 7: 192}
KDOT_BLOCK32 = (8, 2, 1, 30, 3, 6, 7)


def kdot_weights(tt, n, seed):
    """n bytes of weights for tensor type tt: F16 and BF16 halves of 24-bit
    values; the other types random bytes, with every 2-byte-aligned half whose
    f16 or bf16 exponent is all ones defused (bit 14 cleared), so scales stay
    finite."""
    if tt == 1:
        return struct.pack(f"<{n // 2}e", *lcg(n // 2, seed))
    if tt == 30:
        return b"".join(struct.pack("<f", v)[2:] for v in lcg(n // 2, seed))
    raw = bytearray(hashlib.shake_256(b"kdot%d-%d" % (tt, seed)).digest(n))
    for k in range(0, n - 1, 2):
        h = raw[k] | raw[k + 1] << 8
        if (h & 0x7C00) == 0x7C00 or (h & 0x7F80) == 0x7F80:
            raw[k + 1] &= 0xBF
    return bytes(raw)


def kdot_ref(tt, w, x, rows, cols, row_bytes, experts, in_rows):
    """kdot in f64 for F16, BF16 and Q8_0: o[pos rows + r] for each position,
    with its expert's rows and its input row."""
    want = []
    for pos, (ex, xr) in enumerate(zip(experts, in_rows)):
        for r in range(rows):
            base = (ex * rows + r) * row_bytes
            if tt == 1:
                vals = struct.unpack(f"<{cols}e", w[base:base + 2 * cols])
            elif tt == 30:
                vals = [struct.unpack("<f", bytes(2) + w[base + 2 * k:base + 2 * k + 2])[0] for k in range(cols)]
            else:
                vals = []
                for blk in range(cols // 32):
                    o0 = base + blk * 34
                    d = struct.unpack("<e", w[o0:o0 + 2])[0]
                    vals += [d * q for q in struct.unpack("<32b", w[o0 + 2:o0 + 34])]
            want.append(sum(v * x[xr * cols + k] for k, v in enumerate(vals)))
    return want


def kdot_cases():
    """kdot_f32_r1 per tensor type: 8 rows, two positions on experts 1 and 0
    (so expert and position differ) reading their own input rows
    (input_per_expert 1), one workgroup past the rows and one position past
    the positions; for the 32-value types a column count that is not a
    multiple of 256 (the tail group is skipped). Then the input-row paths: a
    prefill MoE (pad0 = 2 positions per input row, pad1 = 1 row offset) and a
    shared input (input_per_expert 0, pad1 = 1). F16, BF16 and Q8_0 also
    against an f64 dequant."""
    cases = []

    def case(name, tt, positions, experts, ipe, pad0, pad1, xrows, seed):
        bb, b32 = KDOT_TYPES[tt], tt in KDOT_BLOCK32
        rows, cols = 8, (480 if b32 else 512)
        row_bytes = ((cols + 31) // 32) * (bb // 8) if b32 else (cols // 256) * bb
        wbytes = 2 * rows * row_bytes
        w = kdot_weights(tt, wbytes + (-wbytes % 4) + 4, seed)
        x = lcg(xrows * cols, 51)
        in_rows = [((p // pad0 if pad0 > 1 else p) if ipe == 1 else 0) + pad1 for p in range(positions)]
        meta = struct.pack("<8I", rows, cols, tt, positions, ipe, pad0, pad1, 0)
        check = None
        if tt in (1, 30, 8):
            def check(o, args=(tt, w, x, rows, cols, row_bytes, experts[:positions], in_rows)):
                return max(abs(g - v) / max(1.0, abs(v)) for g, v in zip(from_f32(o), kdot_ref(*args)))
        # experts has one entry past the positions: main reads expert_ids[position] before its guard
        cases.append(dict(name=name, tt=tt, meta=meta, w=w, x=f32(x), e=struct.pack(f"<{len(experts)}I", *experts),
                          o=bytes(4 * positions * rows), groups=(rows + 1, positions + 1, 1), check=check))
    for tt in KDOT_TYPES:
        case(f"kdot type {tt}", tt, 2, [1, 0, 0], 1, 0, 0, 2, 50 + tt)
    case("kdot type 12 prefill MoE", 12, 4, [1, 0, 1, 0, 0], 1, 2, 1, 3, 140)
    case("kdot type 8 shared input", 8, 2, [0, 1, 0], 0, 0, 1, 2, 141)
    return cases


def kdot_r8_cases(R, types):
    """kdot_f32_r8 with R rows per workgroup: 22 rows (the last workgroup
    partial for R = 4, 8 and 16) or 40 (R = 32: 8 rows in the last of two),
    one workgroup past them, two positions on experts 1 and 0, and one
    position past them."""
    cases = []
    for tt in types:
        bb, b32 = KDOT_TYPES[tt], tt in KDOT_BLOCK32
        rows, cols, positions = (40 if R == 32 else 22), (480 if b32 else 512), 2
        row_bytes = ((cols + 31) // 32) * (bb // 8) if b32 else (cols // 256) * bb
        wbytes = 2 * rows * row_bytes
        cases.append(dict(name=f"kdot r8 rows {R} type {tt}", tt=tt, R=R, meta=struct.pack("<8I", rows, cols, tt, positions, 1, 0, 0, 0),
                          w=kdot_weights(tt, wbytes + (-wbytes % 4) + 4, 60 + tt), x=f32(lcg(positions * cols, 61)),
                          e=struct.pack("<3I", 1, 0, 0), o=bytes(4 * positions * rows), groups=(-(-rows // R) + 1, positions + 1, 1)))
    return cases


KDOT_R8_TYPES = [tt for tt in KDOT_TYPES if tt not in (30, 142, 143)]


def gpu(output, suite, provider_out):
    assert suite["name"] == "kir2", "the gpu phase is suite kir2's"
    assert platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"), "gpu phase: x86_64 Linux with a Vulkan driver"
    cgp = provider_driver()
    receipt_path = output / suite["receipt"]
    report = json.loads(receipt_path.read_text())
    # after the oracle phase only: every module the GPU runs passed spirv-val
    assert report["status"] == "PASS_GPU_KERNEL_SPIRV_BUILD_AND_ORACLE" and "oracle" in report, ("run the oracle phase first", report["status"])
    preport = json.loads((provider_out / "gpu-provider.json").read_text())
    img = provider_out / preport["images"]["provider-vulkan"]
    raw = output / "gpu"
    raw.mkdir(exist_ok=False)
    v2 = {"v2-attn.spv": "kir2-attn-copy-dense.spv",
          **{f"v2-{o}-wg{wg}.spv": f"kir2-ewise-{o}-wg{wg}.spv" for o in EWISE_OPS for wg in (64, 256)},
          **{f"v2-nex-{op}.spv": f"kir2-nex-{op}.spv" for op in NEX_OPS},
          "v2-dot.spv": "kir2-dot-rows.spv", "v2-kdot.spv": "kir2-kdot-f32-r1.spv",
          "v2-kdot8.spv": "kir2-kdot-f32-r8.spv", "v2-kdot4.spv": "kir2-kdot-f32-r8-rows4.spv",
          "v2-kdot16.spv": "kir2-kdot-f32-r8-rows16.spv", "v2-kdot32.spv": "kir2-kdot-f32-r8-rows32.spv"}
    refs = {"ref-attn.spv": "ref-attn-copy-dense.spv", "ref-add.spv": "ref-ewise-add.spv",
            **{f"ref-nex-{op}.spv": f"ref-nex-ops-{op}.spv" for op in NEX_OPS},
            "ref-dot.spv": "ref-dot-rows.spv", "ref-kdot.spv": "ref-kdot-f32-r1.spv",
            "ref-kdot8.spv": "ref-kdot-f32-r8.spv", "ref-kdot4.spv": "ref-kdot-f32-r8-rows4.spv",
            "ref-kdot16.spv": "ref-kdot-f32-r8-rows16.spv", "ref-kdot32.spv": "ref-kdot-f32-r8-rows32.spv"}
    files = {**{n: output / "spv" / m for n, m in v2.items()}, **{n: output / "refs" / m for n, m in refs.items()}}
    for n, f in files.items():
        shutil.copy(f, raw / n)
    # the bytes that run are the ones the build wrote and the oracle checked
    # (KIR v2), and the ones the refs phase recorded (glslang)
    for n, m in v2.items():
        assert pin(raw / n) == report["modules"][m], (m, "changed since the build")
    for n, m in refs.items():
        assert pin(raw / n) == report["glslangReferences"]["modules"][m]["module"], (m, "changed since the refs phase")
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
    for k, n in enumerate(["ref-add.spv", *[f"v2-{o}-wg{wg}.spv" for o in EWISE_OPS for wg in (64, 256)], "ref-attn.spv", "v2-attn.spv",
                           *[f"{w}-nex-{op}.spv" for op in NEX_OPS for w in ("ref", "v2")],
                           "ref-dot.spv", "v2-dot.spv", "ref-kdot.spv", "v2-kdot.spv",
                           "ref-kdot8.spv", "v2-kdot8.spv", "ref-kdot4.spv", "v2-kdot4.spv",
                           "ref-kdot16.spv", "v2-kdot16.spv", "ref-kdot32.spv", "v2-kdot32.spv"]):
        nb = 7 if "-nex-" in n else 5 if "kdot" in n else 8 if "attn" in n else 4
        cgp.expect(s, f"PIPELINE {n} {nb}", str(k + 1))
        pipes[n] = k + 1
    rows = {}
    # ewise, all eight modules over n = 1000 (y kept away from 0 for div).
    # add, sub and mul are exact in f32 (packing rounds the f64 result once);
    # div is within 3 ulp (Vulkan allows OpFDiv 2.5 ulp). Each operator's two
    # workgroup sizes give the same bytes, and add/wg256 those of glslang's
    # module of tools/gpu_kernel_refs/ewise-add.comp.
    n = 1000
    # y as the f32 the device reads: the expectations use the same values
    x, y = lcg(n, 1), from_f32(f32([v + (1.5 if v >= 0 else -1.5) for v in lcg(n, 2)]))
    bx, by, bz, bn = alloc(4 * n), alloc(4 * n), alloc(4 * n), alloc(4)
    for h, b in ((bx, f32(x)), (by, f32(y)), (bn, struct.pack("<I", n))):
        write(h, b)
    fn = {"add": lambda a, b: a + b, "sub": lambda a, b: a - b, "mul": lambda a, b: a * b, "div": lambda a, b: a / b}

    def ulps(got, want):
        g, w = struct.unpack(f"<{n}i", got), struct.unpack(f"<{n}i", want)
        return max(abs(u - v) for u, v in zip(g, w))

    def ewise(m, wg):
        cgp.expect(s, f"ZERO {bz}", "1")
        cgp.expect(s, f"DISPATCH {pipes[m]} {(n + wg - 1) // wg} 1 1 {bx} {by} {bz} {bn}", re.compile(r"^\d+$"))
        return read(bz, 4 * n)
    for o in EWISE_OPS:
        want = f32([fn[o](a, b) for a, b in zip(x, y)])
        z64, z256 = ewise(f"v2-{o}-wg64.spv", 64), ewise(f"v2-{o}-wg256.spv", 256)
        assert z64 == z256, (o, "the workgroup sizes differ")
        err = ulps(z256, want)
        assert (err == 0) if o != "div" else (err <= 3), (o, err, "ulp")
        rows["ewise " + o] = dict(n=n, workgroups=[64, 256], ulpVsF32=err, outputSHA256=hashlib.sha256(z256).hexdigest())
        if o == "add":
            assert ewise("ref-add.spv", 256) == z256, "add differs from glslang's module"
            rows["ewise add"]["identicalToGlslang"] = True
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
        # the same arithmetic in the same order: the driver gives the same bytes
        assert outs["ref-attn.spv"]["o"] == outs["v2-attn.spv"]["o"], (c["name"], "outputs differ from glslang's module")
        rows["attn-copy-dense " + c["name"]] = dict(
            shape={k: c[k] for k in ("d", "heads", "kvHeads", "rows", "p1", "aux", "pos", "maxpos")},
            T=[(c["pos"] + 1 if c["p1"] != 0 else c["aux"]) + r for r in range(Y)],
            inputsSHA256=hashlib.sha256(meta + f32(a) + f32(kc0) + f32(vc0) + f32(dv) + f32(dk)).hexdigest(),
            cacheRowsExact=True, outputsIdentical=True,
            maxAbsErrVsF64={m: outs[m]["maxAbsErrVsF64"] for m in outs},
            outputSHA256={m: hashlib.sha256(outs[m]["o"]).hexdigest() for m in outs})
    # the nex_ops decode set: every writable binding byte-identical between
    # glslang's -DOP module and the KIR v2 module, and the case's check
    for c in nex_cases():
        hs = [alloc(len(c["meta"]))] + [alloc(len(c["bufs"][b])) for b in range(1, 7)]
        outs = {}
        for m in (f"ref-nex-{c['op']}.spv", f"v2-nex-{c['op']}.spv"):
            for h, b in zip(hs, [c["meta"]] + [c["bufs"][b] for b in range(1, 7)]):
                write(h, b)
            cgp.expect(s, f"DISPATCH {pipes[m]} {c['groups'][0]} {c['groups'][1]} {c['groups'][2]} " + " ".join(map(str, hs)),
                       re.compile(r"^\d+$"))
            outs[m] = {b: read(hs[b], len(c["bufs"][b])) for b in (2, 4, 5, 6)}
        ref, v2 = outs.values()
        assert ref == v2, (c["name"], [b for b in ref if ref[b] != v2[b]], "differs from glslang's module")
        err = c["check"](v2) if "check" in c else None
        assert err is None or err < 1e-4, (c["name"], err)
        rows["nex " + c["name"]] = dict(op=c["op"], groups=list(c["groups"]), identical=True, check=err,
                                         inputsSHA256=hashlib.sha256(c["meta"] + b"".join(c["bufs"][b] for b in range(1, 7))).hexdigest(),
                                         outputSHA256=hashlib.sha256(b"".join(v2[b] for b in (2, 4, 5, 6))).hexdigest())
    # dot_rows: 64 rows of 1000, two workgroups past the rows (they return)
    wm, xv = lcg(64 * 1000, 52), lcg(1000, 53)
    dh = [alloc(8), alloc(4 * len(wm)), alloc(4000), alloc(4 * 64)]
    douts = {}
    for m in ("ref-dot.spv", "v2-dot.spv"):
        for h, b in zip(dh, [struct.pack("<2I", 64, 1000), f32(wm), f32(xv), bytes(256)]):
            write(h, b)
        cgp.expect(s, f"DISPATCH {pipes[m]} 66 1 1 " + " ".join(map(str, dh)), re.compile(r"^\d+$"))
        douts[m] = read(dh[3], 256)
    assert douts["ref-dot.spv"] == douts["v2-dot.spv"], "dot_rows differs from glslang's module"
    derr = max(abs(g - sum(wm[r * 1000 + k] * xv[k] for k in range(1000))) for r, g in enumerate(from_f32(douts["v2-dot.spv"])))
    assert derr < 1e-4, ("dot_rows against f64", derr)
    rows["dot_rows"] = dict(rows=64, cols=1000, groups=[66, 1, 1], identical=True, maxAbsErrVsF64=derr,
                            outputSHA256=hashlib.sha256(douts["v2-dot.spv"]).hexdigest())
    # kdot_f32_r1, every tensor type; kdot_f32_r8, every r8 type with 8 rows
    # per workgroup and two with 4
    for c in kdot_cases() + kdot_r8_cases(8, KDOT_R8_TYPES) + kdot_r8_cases(4, [12, 8]) + kdot_r8_cases(16, [12]) + kdot_r8_cases(32, [2]):
        kh = [alloc(32), alloc(len(c["w"])), alloc(len(c["x"])), alloc(len(c["o"])), alloc(len(c["e"]))]
        kouts = {}
        pair = {None: ("ref-kdot.spv", "v2-kdot.spv"), 8: ("ref-kdot8.spv", "v2-kdot8.spv"), 4: ("ref-kdot4.spv", "v2-kdot4.spv"),
                16: ("ref-kdot16.spv", "v2-kdot16.spv"), 32: ("ref-kdot32.spv", "v2-kdot32.spv")}[c.get("R")]
        for m in pair:
            for h, b in zip(kh, [c["meta"], c["w"], c["x"], c["o"], c["e"]]):
                write(h, b)
            cgp.expect(s, f"DISPATCH {pipes[m]} {c['groups'][0]} {c['groups'][1]} 1 " + " ".join(map(str, kh)), re.compile(r"^\d+$"))
            kouts[m] = read(kh[3], len(c["o"]))
        ref, v2 = (kouts[m] for m in pair)
        assert ref == v2, (c["name"], "differs from glslang's module")
        out = from_f32(v2)
        assert all(math.isfinite(v) for v in out) and any(v != 0.0 for v in out), (c["name"], "outputs not finite or all zero")
        err = c["check"](v2) if c.get("check") else None
        assert err is None or err < 1e-4, (c["name"], err)
        rows[c["name"]] = dict(tensorType=c["tt"], groups=list(c["groups"]), identical=True, maxRelErrVsF64=err,
                               inputsSHA256=hashlib.sha256(c["meta"] + c["w"] + c["x"] + c["e"]).hexdigest(),
                               outputSHA256=hashlib.sha256(v2).hexdigest())
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
