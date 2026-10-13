"""abab3.py OUT.jsonl BASEROOT CANDROOT ROUNDS DIVISOR [workloads] -- alternating base/candidate; CPU time via RUSAGE_CHILDREN.
Each run executes LSF*8192/DIVISOR bodies. Receipts (fuel, verify) must match between arms."""
import sys,json,subprocess,os,re,resource,time
out,broot,croot,rounds,div=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5]); W=json.load(open('workloads.json'))
sel=sys.argv[6:] or [e['workload'] for e in W]
env=dict(os.environ,KEXE_FUEL='34359738368',KEXE_STRUCTURED_REPORT='1',KEXE_ARENA_USE='1',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800')
def run(t,n,e):
    x=dict(env)
    if n=='aha-mont64': x.update(KEXE_VECTORS='67108864',KEXE_VECTOR_ITEMS='134217728')
    if n=='qrduino': x.update(KEXE_PAIRS='65536')
    if n=='slre': x.update(KEXE_PAIRS='8388608')
    r0=resource.getrusage(resource.RUSAGE_CHILDREN)
    p=subprocess.run([t,str(max(1,e['LSF']*8192//div))],capture_output=True,text=True,env=x)
    r1=resource.getrusage(resource.RUSAGE_CHILDREN)
    m=re.search(r'\{"schema".*\}',p.stdout); r=json.loads(m[0]) if m else None
    return dict(rc=p.returncode,receipt=r,cpu=(r1.ru_utime-r0.ru_utime)+(r1.ru_stime-r0.ru_stime),load=os.getloadavg()[0])
with open(out,'a') as f:
    for k in range(rounds):
        for e in W:
            n=e['workload']
            if n not in sel: continue
            arms=[('base',f'{broot}/{n}/timer'),('cand',f'{croot}/{n}/timer')]
            if k%2: arms.reverse()
            for arm,t in arms:
                r=run(t,n,e); r.update(workload=n,arm=arm,round=k); f.write(json.dumps(r)+'\n'); f.flush()
