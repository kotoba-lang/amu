#!/usr/bin/env python3
"""Generate f32 ewise-compute SPIR-V kernels with a fixed LocalSize each.

The kernel is deliberately compute-shaped (256 fused multiply-adds per thread,
result written to an SSBO) so a workgroup-size sweep measures scheduling and
SIMD-group effects rather than memory copy. Workgroup size is the ONLY thing
that differs between the generated files.

Usage: python3 gen-wg-shaders.py <outdir>   (needs glslangValidator on PATH)
"""
import subprocess
import sys
from pathlib import Path

TEMPLATE = """#version 450
layout(local_size_x = {n}) in;
layout(set = 0, binding = 0) buffer O {{ float outp[]; }};
void main() {{
  uint gid = gl_GlobalInvocationID.x;
  float x = float(gid) + 1.0;
  for (int k = 0; k < 256; k++) {{ x = fma(x, 1.0000001, 1.0000001); }}
  outp[gid] = x;
}}
"""

SIZES = [32, 64, 128, 256, 512, 1024]


def main():
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    for n in SIZES:
        src = outdir / f"wg{n}.comp"
        spv = outdir / f"wg{n}.spv"
        src.write_text(TEMPLATE.format(n=n))
        subprocess.run(["glslangValidator", "-V", "-S", "comp", str(src), "-o", str(spv)], check=True)
        print(spv.name, spv.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
