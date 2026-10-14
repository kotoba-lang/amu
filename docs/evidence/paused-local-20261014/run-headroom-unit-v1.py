from pathlib import Path
import json,hashlib,subprocess,os,re
W=Path(__file__).parent;D=W/'headroom-unit-v1';P=json.loads((D/'PLAN.json').read_text());L=W.parent/'embench-pf-twoarg-20261013/protected-host/kexe-loader';C=W/'compiler-only-v1/artifacts/candidate.bin';S=D/'probe.kotoba';K=D/'probe.kseed';B=D/'probe.bin';(D/'raw').mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S)==P['sourceSHA256'];pins={p:sha(p)for p in [L,C,S]};calls=[]
E={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')};E.update(KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(D),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(D))
for cmd,args in [('compile',['compile',S,'--target','aarch64-macos','--output',K]),('extract',['extract-native',K,'--symbol','probe','--output',B])]:
 z=subprocess.run(list(map(str,[L,C,'0','0','aarch64','35,37,38,39','--',*args])),cwd=D,env=E,capture_output=True,timeout=1800);(D/'raw'/(cmd+'.stdout')).write_bytes(z.stdout);(D/'raw'/(cmd+'.stderr')).write_bytes(z.stderr);calls.append(dict(cmd=cmd,exit=z.returncode));(D/'calls.json').write_text(json.dumps(calls,indent=2)+'\n');assert z.returncode==0 and not z.stderr;assert all(sha(p)==v for p,v in pins.items())
h,b=K.read_bytes().split(b'\n\n',1);assert b==B.read_bytes();exports={n:[int(pc),int(arity)]for n,pc,arity in(l.split()for l in h.decode().splitlines()[1:])};assert exports['probe'][1]==1
E={k:v for k,v in E.items()if not k.startswith('KEXE_')};E.update(KEXE_FUEL='off',KEXE_ARENA_USE='1',KEXE_STRUCTURED_REPORT='1');rows=[]
for i,(remaining,expected)in enumerate(zip(P['remainingWords'],P['expected'])):
 z=subprocess.run(list(map(str,[L,B,exports['probe'][0],'1','aarch64','37',remaining])),cwd=D,env=E,capture_output=True,timeout=60);(D/'raw'/(str(i)+'.stdout')).write_bytes(z.stdout);(D/'raw'/(str(i)+'.stderr')).write_bytes(z.stderr);m=re.search(rb':status :ok :result (-?\d+)',z.stdout);assert z.returncode==0 and m and int(m[1])==expected,(remaining,expected,z.stdout,z.stderr);rows.append(dict(remainingWords=remaining,expected=expected,actual=int(m[1]),exit=z.returncode))
r=dict(status='PASS_ACTUAL_CW_ENTRY_WORK_SOURCE_ALL12_HEADROOM_BOUNDARIES_NATIVE',rows=rows,sourceSHA256=sha(S),compilerSHA256=sha(C),nativeSHA256=sha(B),compilerCalls=2,guestCalls=12,performanceMeasured=False,adopted=False);(D/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
