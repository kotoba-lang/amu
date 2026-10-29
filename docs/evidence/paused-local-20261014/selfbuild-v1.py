from pathlib import Path
import hashlib,json,os,subprocess,shutil,sys
assert not sys.flags.optimize
W=Path(__file__).parent;D=W/'selfbuild-v1';D.mkdir(exist_ok=False);art=D/'artifacts';art.mkdir();host=D/'host';host.mkdir();raw=D/'raw';raw.mkdir()
L=W.parent/'embench-pf-twoarg-20261013/protected-host/kexe-loader';source=art/'candidate.kotoba';source.write_bytes((W/'candidate.kotoba').read_bytes());P=host/'G1.bin';shutil.copy2(W/'compiler-only-v1/artifacts/candidate.bin',P)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)==json.loads((W/'compiler-only-v1/report.json').read_text())['nativeSHA256'];pins={p:sha(p)for p in [L,source]}
env={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')};env.update(KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(art),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(art));calls=[];stages=[]
for n in [2,3,4]:
 before=sha(P);k=art/f'G{n}.kseed';b=art/f'G{n}.bin'
 for cmd,args in [('compile',['compile',source,'--target','aarch64-macos','--output',k]),('extract',['extract-native',k,'--symbol','main','--output',b])]:
  z=subprocess.run(list(map(str,[L,P,'0','0','aarch64','35,37,38,39','--',*args])),cwd=art,env=env,capture_output=True,timeout=1800);tag=f'G{n}-{cmd}'
  (raw/(tag+'.stdout')).write_bytes(z.stdout);(raw/(tag+'.stderr')).write_bytes(z.stderr);calls.append(dict(name=tag,exit=z.returncode));(D/'calls.json').write_text(json.dumps(calls,indent=2)+'\n');assert z.returncode==0 and not z.stderr,(tag,z.returncode,z.stdout,z.stderr);assert sha(P)==before and all(sha(p)==h for p,h in pins.items())
 h,payload=k.read_bytes().split(b'\n\n',1);assert payload==b.read_bytes()and h.decode().splitlines()[1:]==['main 0 0'];stages.append(dict(generation=n,nativeSHA256=sha(b),containerSHA256=sha(k),bytes=b.stat().st_size));P=host/f'G{n}.bin';shutil.copy2(b,P)
assert len({r['nativeSHA256']for r in stages})==1 and len({r['containerSHA256']for r in stages})==1
r=dict(status='PASS_CW48_NATIVE_SELFHOST_G2_G3_G4_FIXEDPOINT_NOT_PROGRAM_QUALIFICATION',stages=stages,compilerCalls=6,sourceSHA256=sha(source),adopted=False,performanceMeasured=False);(D/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
