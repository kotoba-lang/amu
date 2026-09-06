import os, hashlib, subprocess

repo = '/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu'
out = []
def h(p):
    if os.path.exists(p):
        return hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
    return 'MISSING'

# bench source digests (compare to probe1: kernels.c 2847a8e6f3e93204, kernel.kotoba a704c3f17d524a8e)
out.append('kernel.kotoba sha ' + h(os.path.join(repo,'bench/runtime-comparison/kernel.kotoba')))
out.append('kernels.c     sha ' + h(os.path.join(repo,'bench/runtime-comparison/kernels.c')))

# H-C2 staged artifacts
for p in ['/private/tmp/hc2_amu_kernel.bin', '/private/tmp/hc2_amu.kexe',
          '/private/tmp/hc2_clang.dylib', '/private/tmp/hc2_kexe_bench',
          '/private/tmp/jb_imod_control_preflight']:
    if os.path.exists(p):
        out.append('EXISTS %s size=%d sha=%s' % (p, os.path.getsize(p), h(p)))
    else:
        out.append('MISSING %s' % p)

# amu binary present?
amu = subprocess.run(['/bin/ls','-la', os.path.join(repo,'bin/amu')],
                     capture_output=True, text=True).stdout
out.append('bin/amu: ' + amu.replace('\n',' | '))
open('/private/tmp/hc2_preflight_verify.txt','w').write('\n'.join(out))
print('WROTE')