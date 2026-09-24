import os, subprocess
# Compare bit-shift acceptance on tick8 worktree /tmp/amu-tick8 if present, else report
p = '/tmp/amu-tick8'
print('worktree exists:', os.path.isdir(p))
if os.path.isdir(p):
    r = subprocess.run([p + '/bin/amu', 'check', '--jvm-free', '/tmp/q9probe3/p03-bitshift.kotoba'],
                       capture_output=True, text=True, cwd=p, timeout=120)
    print('p03 bitshift rc:', r.returncode)
    print((r.stdout + r.stderr)[:300])
    r2 = subprocess.run([p + '/bin/amu', 'check', '--jvm-free', '/tmp/q9probe3/c13-frag-final.kotoba'],
                        capture_output=True, text=True, cwd=p, timeout=120)
    print('c13 rc:', r2.returncode)
    print((r2.stdout + r2.stderr)[:300])
