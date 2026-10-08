from pathlib import Path
import json,hashlib,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-table-decision-collapse-tc-emitted-build8-source-v1-20261008';OLD=W/'crc-table-decision-collapse-native-component-v4-portable-env-20261008'
H=lambda b:hashlib.sha256(b).hexdigest()
sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text());fr=json.loads((D/'freeze.json').read_text())
counts=[]
for reg,relative in [(sp,True),(ip,False)]:
 total=0
 for n,pin in reg.items():
  p=D/n if relative else Path(n);b=p.read_bytes();assert len(b)==pin['bytes']and H(b)==pin['sha256'],str(p);total+=len(b)
 counts.append([len(reg),total])
for key,n in [('sourcePinsSHA256','source-pins.json'),('inputPinsSHA256','input-pins.json'),('preregistrationSHA256','preregistration.json'),('driverSHA256','run.py')]:assert fr[key]==H((D/n).read_bytes())
assert counts==[[18,2382308],[1911,382399845]]
assert H((D/'source-pins.json').read_bytes())=='32b8830c7a03cae3d8b2fd33a7e98ca86db8f8826fb19e32edf4cc19703d41fa'
assert H((D/'run.py').read_bytes())=='c6349d2b4c0fb3a3ac717fd833e2475f674fccaa54671751025ee03c32721804'
a=json.loads((D/'source-assembly.json').read_text());mods=a['modules'];parts={m:Path(p['path']).read_text()for m,p in zip(mods,a['modulePins'])};assert H(('\n'.join(parts[m]for m in mods)+'\n').encode())=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418'
parts['seed/41-a64gen.kotoba']=(D/'41-a64gen-candidate.kotoba').read_text();assert ('\n'.join(parts[m]for m in mods)+'\n').encode()==(D/'unity-candidate.kotoba').read_bytes()
p=parts['seed/41-a64gen.kotoba'];assert p.count('(defn- tc-call [')==p.count('(defn- gn-op-call [')==p.count('(defn- gn-call-generic [')==1
p=p.replace('(defn- tc-call [','(defn- fo-original-tc-call [',1).replace('(defn- gn-op-call [',(D/'observer-helpers.kotoba').read_text()+'\n'+(D/'observer-tc-call.kotoba').read_text()+'\n(defn- fo-original-call [',1).replace('(defn- gn-call-generic [','(defn- gn-op-call [M :vector-i64 i :i64 f :i64 t :i64 n :i64] :vector-i64 (fo-call M i f t n))\n(defn- gn-call-generic [',1);parts['seed/41-a64gen.kotoba']=p
parts['seed/50-out.kotoba']=parts['seed/50-out.kotoba'].replace('(defn- out-build [','(defn- fo-original-build [',1)+'\n(defn- out-build [M :vector-i64 S :string] :vector-i64\n (let [result (fo-original-build M S) w (if (fo-enabled) (fo-final result) 0)] result))\n'
parts['seed/90-drv.kotoba']=parts['seed/90-drv.kotoba'].replace('(defn- drv-c5 [','(defn- fo-original-c5 [',1)+'\n(defn- drv-c5 [M :vector-i64 S :string path :string out :string] :i64\n (let [w (if (fo-enabled) (fo-pre M) 0)] (fo-original-c5 M S path out)))\n'
assert ('\n'.join(parts[m]for m in mods)+'\n').encode()==(D/'unity-emitter-observer.kotoba').read_bytes()
for n in ['adapter.py','launch-wrapper.py','observer-helpers.kotoba']:assert (D/n).read_bytes()==(OLD/n).read_bytes(),n
new=(D/'run.py').read_text();old=(OLD/'run.py').read_text();assert new[new.index(' def call('):new.index(' def build(')]==old[old.index(' def call('):old.index(' def build(')]
assert (D/'validate.py').read_text().split('# New bounded emitted gate.')[0]==(OLD/'validate.py').read_text()+'\n'
ns={'__file__':str(D/'source-controls.py'),'__name__':'independent_pure_source_controls'};prefix=(D/'source-controls.py').read_text().split("q={'status'")[0];exec(compile(prefix,str(D/'source-controls.py'),'exec'),ns)
assert len(ns['controls'])==16
pr=json.loads((D/'preregistration.json').read_text());proof=json.loads(Path(pr['actualProducerProof']).read_text());assert proof['status']==pr['actualProducerProofStatus'];assert len(pr['environment'])==17
print(json.dumps({'status':'PASS_PURE_INDEPENDENT_CHECKS','counts':counts,'assemblyExact':True,'transportExactV4':True,'preservedTypedValidatorExact':True,'syntheticMutantsRefused':len(ns['controls']),'operationalCalls':0}))
