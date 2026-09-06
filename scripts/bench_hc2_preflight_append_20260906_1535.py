path = '/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md'
entry = (
    " | 2026-09-06 15:34 JST bench tick preflight (load-robust, no timing): "
    "H-C2 A/B artifacts verified intact for the next quiet window - "
    "bench/runtime-comparison sources unchanged (kernels.c sha256 "
    "2847a8e6f3e93204, kernel.kotoba a704c3f17d524a8e); staged "
    "hc2_amu_kernel.bin (1100B), hc2_clang.dylib (17216B), hc2_kexe_bench "
    "(35840B), hc2_amu.kexe (7110B) all present; J-B preflight binary "
    "/private/tmp/jb_imod_control_preflight (50504B) still staged."
)
txt = open(path).read()
lines = txt.splitlines()
target = None
for i, l in enumerate(lines):
    if l.startswith('| H-C2 | the remaining ~4.4% vs Clang'):
        target = i
        break
if target is None:
    raise SystemExit('H-C2 row not found')
lines[target] = lines[target] + entry
open(path, 'w').write('\n'.join(lines) + '\n')
print('preflight note appended')