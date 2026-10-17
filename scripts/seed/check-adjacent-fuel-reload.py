from pathlib import Path
import json,hashlib,subprocess,os,importlib.util,re
ROOT=Path(__file__).resolve().parents[2]
# Static single-feature audits (native-gate) compare against AUDITED, the adopted compiler at which they were established
# and last held; the same-algorithm m104 adoption replaced it. Every behavioural pair runs on the current adopted compiler (ON).
AUDITED=ROOT/'docs/evidence/same-algo-m104-20261015/previous-bootstrap.bin';AUDITED_SHA256='87efe842dc0389f0ba7d476fcf034f6820483632df61fad53b474a2297e3e345'
import argparse,shutil
ap=argparse.ArgumentParser();ap.add_argument('--selfbuild-output',type=Path,required=True);arg=ap.parse_args();O=arg.selfbuild_output.resolve();E=ROOT/'docs/evidence/adjacent-fuel-reload-20261014';F=ROOT/'seed/tests/adjacent-fuel-reload';D=O/'artifacts/adjacent-fuel-reload-controls';D.mkdir(exist_ok=False);A=D/'artifacts';A.mkdir();raw=D/'raw';raw.mkdir();S=A/'controls.kotoba';shutil.copy2(F/'controls.kotoba',S)
L=O/'host/kexe-loader';P={'OFF':E/'previous-bootstrap.bin','ON':O/'artifacts/G2.bin','AUDITED':AUDITED}
def pin(p):p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
assert pin(P['OFF'])['sha256']=='87d29d354142b3391abd475211ddd6a677c4e1f18ea0c74c72ffa450cf16eb56';assert pin(P['AUDITED'])['sha256']==AUDITED_SHA256;assert pin(P['ON'])['sha256']==json.loads((ROOT/'seed/adoption-20261018.json').read_text())['nativeImageSHA256']
pins={p:pin(p)for p in [L,S,F/'cases.json',E/'native-gate.py',E/'native-utils.py',E/'source-pool.py',E/'trusted-loader-abi.c',*P.values()]};calls=[]
env={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')};env.update(KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(A),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(A))
def call(tag,args,e):
 z=subprocess.run(list(map(str,args)),cwd=D,env=e,capture_output=True,timeout=1800);(raw/(tag+'.stdout')).write_bytes(z.stdout);(raw/(tag+'.stderr')).write_bytes(z.stderr);calls.append(dict(tag=tag,exit=z.returncode));(D/'calls.json').write_text(json.dumps(calls,indent=2)+'\n');assert all(pin(p)==v for p,v in pins.items());return z.returncode,z.stdout,z.stderr
arms={}
for tag,p in P.items():
 k=A/(tag+'.kseed');b=A/(tag+'.bin');base=[L,p,'0','0','aarch64','35,37,38,39','--']
 for name,args in [('compile',['compile',S,'--target','aarch64-macos','--output',k]),('extract',['extract-native',k,'--symbol','run','--output',b])]:
  code,_,err=call(tag+'-'+name,base+args,env);assert code==0 and not err
 h,payload=k.read_bytes().split(b'\n\n',1);assert payload==b.read_bytes();ex={n:[int(o),int(a)]for n,o,a in map(str.split,h.decode().splitlines()[1:])};assert all(a==1 for _,a in ex.values());arms[tag]=dict(native=pin(b),container=pin(k),source=pin(S),exports=ex)
spec=importlib.util.spec_from_file_location('fuel_physical',E/'native-gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);audited=arms.pop('AUDITED');proof=m.audit(arms['OFF'],audited);(D/'physical-proof.json').write_text(json.dumps(proof,indent=2)+'\n');assert proof['changed'] and len(proof['sites'])>=1,'No generic changed site: save before guests'
cases=json.loads((F/'cases.json').read_text())['cases'];assert len(cases)==365
(D/'cases.json').write_text(json.dumps(dict(cases=cases),indent=2)+'\n');guest={k:v for k,v in env.items()if not k.startswith('KEXE_')};guest.update(KEXE_ARENA_USE='1',KEXE_STRUCTURED_REPORT='1',KEXE_CPU_SECONDS='60',KEXE_WALL_SECONDS='60',TMPDIR=str(A));rows=[]
for i,c in enumerate(cases):
 pair=[];guest['KEXE_FUEL']=str(c['fuel'])
 for tag,a in arms.items():
  off,arity=a['exports'][c['symbol']];code,o,e=call(f'{i}-{tag}',[L,a['native']['path'],off,arity,'aarch64','37',c['x']],guest)
  if b':status :ok'in o:
   value=re.search(rb':result (-?\d+)',o);assert code==0 and value and int(value[1])==c['result']
  else:assert code==120 and b':status :trap :exit 120'in o and b':SIGTRAP'in e and b'budget/fuel'in e and c['fuel']<=64 and re.search(rb':remaining 0\}',o)
  fuel=re.search(rb':fuel \{:initial (\d+) :remaining (\d+)\}',o);assert fuel and int(fuel[1])==c['fuel']and 0<=int(fuel[2])<=c['fuel']and len(re.findall(rb':[a-z-]+ \d+',e))==17
  pair.append((code,o,e))
 assert pair[0]==pair[1],('ADJACENT_CHARGE_RAW_PARITY',c);rows.append(dict(**c,exit=pair[0][0]))
(O/'host/adjacent-fuel-reload-controls-report.json').write_text(json.dumps(dict(status='PASS_ADJACENT_FRAMED_CONTROLS_RAW_FUEL1_64_MAX53_ALL17',pairs=len(rows),guestCalls=len(rows)*2,compilerCalls=6,changedSites=len(proof['sites']),rows=rows,adopted=False,staticAuditCompiler=AUDITED_SHA256,performanceMeasured=False),indent=2)+'\n');print('PASS_ADJACENT_FRAMED_CONTROLS',len(rows),'pairs',len(proof['sites']),'sites')
