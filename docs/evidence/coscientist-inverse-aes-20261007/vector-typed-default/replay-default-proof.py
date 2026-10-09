"""Stdlib offline evidence replay; executes no native/compiler/network/timing."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,re
D=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest()
f=D/'default-proof.manifest.json';assert sha(f.read_bytes())=='1dec5a65b7bdf55b1abb589bebc50a0a93f9f59429de89686179ca7beff48835'
m=json.loads(f.read_text());a=D/m['archive'];assert a.stat().st_size==m['archiveBytes']<=5242880 and sha(a.read_bytes())==m['archiveSHA256']
assert len(m['paths'])<=2000 and m['uncompressedSelectedBytes']<=67108864
objects={}
with tarfile.open(a,'r:gz')as tf:
 for t in tf.getmembers():
  assert t.isfile() and re.fullmatch(r'objects/[0-9a-f]{64}',t.name) and t.size<=67108864
  b=tf.extractfile(t).read();h=t.name[8:];assert sha(b)==h and h not in objects;objects[h]=b
assert len(objects)==m['objects'] and sum(map(len,objects.values()))==m['uncompressedSelectedBytes']
files={}
for n,r in m['paths'].items():
 p=PurePosixPath(n);assert not p.is_absolute() and '..'not in p.parts
 b=objects[r['sha256']];assert len(b)==r['bytes'];files[n]=b
J=lambda n:json.loads(files[n]);T=lambda n:files[n].decode()
# Complete own input inventories, not unselected external inventory claims.
verified=0
for folder in ['native','initial','ports']:
 for n,r in J(folder+'/input-pins.json').items():
  b=files[folder+'/'+n];assert sha(b)==r['sha256'] and len(b)==r['bytes'];verified+=1
assert sha(files['source/unity-vector-analysis-default.kotoba'])=='aab2b95c9c6064fde2ca206a4ec736c92d4a67704aa477de4e84cda3c37abfb3'
assert files['source/unity-vector-analysis-default.kotoba']==files['native/unity.kotoba']==files['initial/unity.kotoba']
assert T('native/unity.kotoba').count('(def vw-feature 0)')==1 and '(def vw-feature 1)'not in T('native/unity.kotoba')
assert sha(files['native/seed-0.bin'])=='3ad29932428206a84a8c571a8089a793d0dcf95d167c23cbcbb43effdba2a346'
assert J('native/disabled-syntax-correction-preregistration.json')['sourceVariant']=='DEFAULT-OFF only'
assert J('native/permission-recovery-preregistration.json')['sameSourceAndNativeInputs']
old=J('initial/attempts.json');assert len(old)==1 and old[0]['state']=='terminal'and old[0]['returncode']==125
assert files['initial/seed-1-compile.stdout']==b'' and b'sandbox initialization failed'in files['initial/seed-1-compile.stderr']
assert J('initial/build-terminal.json')['failure']
rows=J('native/attempts.json');assert len(rows)==8;gens=[]
for g in range(1,5):
 for z,stage in enumerate(['compile','extract']):
  r=rows[(g-1)*2+z];assert r['generation']==g and r['stage']==stage and r['returncode']==0 and r['state']=='terminal'
  cmd=r['argv'];root=cmd[0].rsplit('/',1)[0]
  assert cmd[:7]==[root+'/kexe-loader',root+f'/seed-{g-1}.bin','0','0','aarch64','35,37,38,39','--']
  expected=['compile',root+'/unity.kotoba','--target','aarch64-macos','--output',root+f'/seed-{g}.kseed']if stage=='compile'else['extract-native',root+f'/seed-{g}.kseed','--symbol','main','--output',root+f'/seed-{g}.bin']
  assert cmd[7:]==expected
  assert files[f'native/seed-{g}-{stage}.stderr']==b'' and b':ok true'in files[f'native/seed-{g}-{stage}.stdout']
 b=files[f'native/seed-{g}.bin'];kb=files[f'native/seed-{g}.kseed'];h=re.match(rb'KSEED1 (\d+) 1\nmain 0 0\n\n',kb)
 assert h and int(h[1])==len(b)==918120 and kb[h.end():]==b
 assert T(f'native/seed-{g}.offset')=='0\n' and sha(b)=='3893f7073bfee306f1f1d5502180b4187747f2fc2c38a58f0888121e2ea687e2'
 gens.append({'generation':g,'bytes':len(b),'sha256':sha(b),'offset':0})
assert gens==J('native/fixed-point.json')['generations']
assert all(gens[i]=={k:v for k,v in J('independent/report.json')['generations'][i].items()if k in gens[i]}for i in range(4))
assert J('native/build-terminal.json')['processes']==8 and not J('native/build-terminal.json')['failure']
assert files['ports/seed.bin']==files['native/seed-4.bin']
matrix=J('ports/comparison-matrix.json')['entries'];ref={r['workload']:r for r in J('ports/baseline19.json')};images=J('ports/images.json');attempts=J('ports/attempts.json')
assert len(matrix)==len(ref)==len(images)==19 and len(attempts)==38
for i,e in enumerate(matrix):
 name=e['workload'];r=images[i];assert r['workload']==name and r['chargedBaselineExact'];b=files['ports/ports/'+name+'/native.bin'];kb=files['ports/ports/'+name+'/image.kseed']
 h,payload=kb.split(b'\n\n',1);parts=h.splitlines();top=parts[0].split();assert top[0]==b'KSEED1' and int(top[1])==len(b)and int(top[2])==len(parts)-1 and payload==b
 exports={p.split()[0].decode():tuple(map(int,p.split()[1:]))for p in parts[1:]};assert len(exports)==len(parts)-1 and e['symbol']in exports
 off,arity=exports[e['symbol']];assert off==r['offset']==ref[name]['offset'] and arity==1
 assert b==files['baseline/'+name+'.bin'] and T('baseline/'+name+'.offset')==T('ports/ports/'+name+'/native.offset')==str(off)+'\n'
 assert len(b)==r['bytes']==ref[name]['bytes'] and sha(b)==r['nativeSha256']==ref[name]['nativeSha256']
 assert sha(files['ports/sources/'+name+'.kotoba'])==r['sourceSha256']==ref[name]['sourceSha256']
 for z,stage in enumerate(['compile','extract']):
  r=attempts[i*2+z];assert r['workload']==name and r['stage']==stage and r['state']=='terminal' and r['returncode']==0
  cmd=r['argv'];root=cmd[0].rsplit('/',1)[0];out=root+'/ports/'+name
  assert cmd[:7]==[root+'/kexe-loader',root+'/seed.bin','0','0','aarch64','35,37,38,39','--']
  expected=['compile',root+'/sources/'+name+'.kotoba','--target','aarch64-macos','--output',out+'/image.kseed']if stage=='compile'else['extract-native',out+'/image.kseed','--symbol',e['symbol'],'--output',out+'/native.bin']
  assert cmd[7:]==expected and files['ports/ports/'+name+'/'+stage+'.stderr']==b'' and b':ok true'in files['ports/ports/'+name+'/'+stage+'.stdout']
r=J('ports/report.json');assert r['all19ChargedBaselineExact'] and r['compilerProcesses']==38 and r['guestBenchmarkExecutions']==0 and not r['timing']
assert not J('ports/terminal.json')['failure'] and J('ports/terminal.json')['images']==19
print(json.dumps({'status':'PASS copied3file DEFAULT-OFF native evidence','selectedPaths':len(files),'verifiedInputInventoryEntries':verified,'nativeCompilerGenerations':4,'all19ByteExact':True,'actualSuccessfulCompilerEntries':46,'retainedPreentrySandboxRefusals':1,'totalLoaderInvocations':47,'readerNativeNetworkSolverTiming':0,'ONAnalysisQualification':False,'wholeMResourcePerformanceProductQualification':False}))
