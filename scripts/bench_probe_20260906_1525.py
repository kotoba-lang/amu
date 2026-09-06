import os, subprocess, time, json, traceback

out = {}
try:
    out['tmp_listing'] = subprocess.run(['/bin/ls','-la','/private/tmp/'],
                                        capture_output=True, text=True).stdout
except Exception as e:
    out['tmp_listing'] = traceback.format_exc()

samples = []
try:
    t0 = time.time()
    for i in range(6):
        r = subprocess.run(['/usr/bin/sysctl','-n','vm.loadavg'],
                           capture_output=True, text=True)
        samples.append(r.stdout.strip())
        time.sleep(2)
    out['samples'] = samples
    out['elapsed_s'] = round(time.time()-t0, 1)
except Exception as e:
    out['samples_error'] = traceback.format_exc()

# load-robust static checks
try:
    import hashlib
    for p in ['bench/runtime-comparison/kernels.c',
              'bench/runtime-comparison/kernel.kotoba']:
        full = os.path.join('/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu', p)
        if os.path.exists(full):
            out['sha_' + p] = hashlib.sha256(open(full,'rb').read()).hexdigest()[:16]
        else:
            out['exists_' + p] = os.path.exists(full)
except Exception as e:
    out['sha_error'] = traceback.format_exc()

outpath = '/private/tmp/bench_probe_out.txt'
with open(outpath, 'w') as f:
    f.write(json.dumps(out, indent=2))
print('WROTE', outpath, 'exit-clean')