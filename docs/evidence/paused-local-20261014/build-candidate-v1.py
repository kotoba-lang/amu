from pathlib import Path
import hashlib,json,os,subprocess,sys
assert not sys.flags.optimize
W=Path(__file__).parent;D=W/'compiler-only-v1';D.mkdir(exist_ok=False);art=D/'artifacts';art.mkdir();raw=D/'raw';raw.mkdir()
L=W.parent/'embench-pf-twoarg-20261013/protected-host/kexe-loader'
P=W.parent/'seed-copy-chain-forward-20261014/compiler-only-v1/artifacts/candidate.bin'
source=art/'candidate.kotoba';source.write_bytes((W/'candidate.kotoba').read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)=='0139f2cb69b6a4166262c1851d7bfb0802715a2ba705ca2139dd015541791df7'
assert sha(source)==json.loads((W/'candidate-source-receipt.json').read_text())['candidateUnitySHA256']
pins={p:sha(p)for p in [L,P,source]};env={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')};env.update(KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(art),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(art));calls=[]
for name,args in [('compile',['compile',source,'--target','aarch64-macos','--output',art/'candidate.kseed']),('extract',['extract-native',art/'candidate.kseed','--symbol','main','--output',art/'candidate.bin'])]:
 argv=[L,P,'0','0','aarch64','35,37,38,39','--',*args]
 z=subprocess.run(list(map(str,argv)),cwd=art,env=env,capture_output=True,timeout=1800)
 (raw/(name+'.stdout')).write_bytes(z.stdout);(raw/(name+'.stderr')).write_bytes(z.stderr);calls.append(dict(name=name,exit=z.returncode));(D/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
 assert z.returncode==0 and not z.stderr,(name,z.returncode,z.stdout,z.stderr)
 assert all(sha(p)==h for p,h in pins.items()),'Input mutation'
head,payload=(art/'candidate.kseed').read_bytes().split(b'\n\n',1);assert payload==(art/'candidate.bin').read_bytes();assert head.decode().splitlines()[1:]==['main 0 0']
r=dict(status='PASS_NATIVE_CANDIDATE_TWO_TOOLS_NOT_SELFHOST_FIXEDPOINT_OR_PROGRAM_QUALIFICATION',sourceSHA256=sha(source),nativeSHA256=sha(art/'candidate.bin'),containerSHA256=sha(art/'candidate.kseed'),compilerCalls=2,adopted=False,performanceMeasured=False);(D/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
