#!/usr/bin/env python3
# Bootstrap-only diagnostic authoring; canonical product/benchmark source is unchanged.
from pathlib import Path
import argparse,os,subprocess,re,json,hashlib,struct
p=argparse.ArgumentParser(description='Bootstrap-only native cumulative-phase diagnostic, never a replacement Embench workload.')
p.add_argument('repo',type=Path);p.add_argument('output',type=Path);p.add_argument('seed',type=Path);p.add_argument('loader',type=Path);p.add_argument('canonical_native',type=Path);p.add_argument('runner',type=Path)
options=p.parse_args();r=options.repo.resolve();w=options.output.resolve();seed=options.seed.resolve();loader=options.loader.resolve()
assert not w.exists(), 'Refusing to overwrite diagnostic evidence'
w.mkdir(parents=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

s=(r/'bench/embench/picojpeg-full.kotoba').read_text().replace('(:export [bench repeated-state bounds-probe])','(:export [bench repeated-state bounds-probe phase-init phase-coefficients])',1)
s+='''\n;; Diagnostic cumulative phases, not replacement benchmark workloads.
(defn- phase-repeat [v :vector-i64 n :i64 i :i64 coefficient :bool] :vector-i64
  (if (= i n) v
      (let [a (reset-init v 1400) b (if coefficient (coefficient-state a 169) (stages a 3))]
        (phase-repeat b n (inc i) coefficient))))
(defn phase-init [n :i64] :i64
  (let [v (phase-repeat (vector-alloc 4096) n 0 false)] (if (= (vector-at v 1520) 0) 1 0)))
(defn phase-coefficients [n :i64] :i64
  (let [v (phase-repeat (vector-alloc 4096) n 0 true)] (if (= (vector-at v 1520) 1) 1 0)))
''';src=w/'picojpeg-phases.kotoba';src.write_text(s);env=dict(os.environ,KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(r)+':/private/tmp',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',KEXE_STRING_POOL='268435456',KEXE_VECTORS='65536',KEXE_PAIRS='16777216',KEXE_VECTOR_ITEMS='134217728');symbols=['bench','phase-init','phase-coefficients'];offsets={}
for label,args in [('compile',['compile',str(src),'--target','aarch64-macos','--output',str(w/'image.kseed')])]+[(x,['extract-native',str(w/'image.kseed'),'--symbol',x,'--output',str(w/'native.bin')]) for x in symbols]:
 p=subprocess.run([str(loader),str(seed),'0','0','aarch64','35,37,38,39','--',*args],env=env,capture_output=True,text=True);(w/(label+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,(label,p.stdout,p.stderr)
 if label!='compile':offsets[label]=int(re.search(r':offset (\d+)',p.stdout).group(1))
base=options.canonical_native.resolve();a=base.read_bytes();b=(w/'native.bin').read_bytes();delta=len(b)-len(a)
def target(i,word):
 v=word&0x3ffffff
 if v&(1<<25):v-=1<<26
 return i+4*v
changed=[i for i in range(0,len(a),4) if a[i:i+4]!=b[i:i+4]]
# Added functions precede compiler-synthesized runtime adapters. Verify every
# changed shared instruction is BL to the byte-identical relocated adapter.
first=changed[0];word=struct.unpack_from('<I',a,first)[0];assert word&0xfc000000==0x94000000
boundary=target(first,word);assert boundary>first and a[boundary:]==b[boundary+delta:]
relocations=[]
for i in range(0,boundary,4):
 x=struct.unpack_from('<I',a,i)[0];y=struct.unpack_from('<I',b,i)[0]
 if x!=y:
  assert x&0xfc000000==y&0xfc000000==0x94000000
  ta=target(i,x);tb=target(i,y);assert boundary<=ta<len(a) and tb==ta+delta
  relocations.append({'offset':i,'oldTarget':ta,'newTarget':tb})
assert len(relocations)==3
(w/'canonical-relocation-proof.json').write_text(json.dumps({'sharedInstructionBytes':boundary,'runtimeAdapterBytes':len(a)-boundary,'adapterRelocation':delta,'verifiedBLRelocations':relocations,'otherSharedInstructionsByteIdentical':True,'adapterBytesIdentical':True},indent=2)+'\n')
runner=options.runner.resolve();checks=[]
for symbol in symbols:
 for n in [1,2,8,32]:
  p=subprocess.run([str(runner),'raw',str(w/'native.bin'),str(offsets[symbol]),'aarch64',str(n),'1','0','16777216'],capture_output=True,text=True);assert p.returncode==0,(symbol,n,p.stderr);x=json.loads(p.stdout);assert x['result']==1,(symbol,n,x);checks.append({'symbol':symbol,'n':n,'fuel':x['contextFuelConsumed']})
manifest={'format':'amu.native-cumulative-phase-manifest/v1','sourceSha256':sha(src),'canonicalSourceSha256':sha(r/'bench/embench/picojpeg-full.kotoba'),'compilerSha256':sha(seed),'nativeSha256':sha(w/'native.bin'),'runnerSha256':sha(runner),'canonicalSharedInstructionsIdenticalExceptVerifiedAdapterRelocations':True,'canonicalMachineBytes':base.stat().st_size,'offsets':offsets,'iterationsPerCall':32,'checks':checks,'purpose':'diagnostic cumulative phases, no reduced workload benchmark claim','officialEmbenchScore':False}
(w/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2),flush=True)
