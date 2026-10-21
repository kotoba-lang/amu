#!/usr/bin/env python3
"""Independent native source controls: original oracle, exact fuel and all arena counters."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FIELDS={'pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selfbuild-output',type=Path,required=True);a=ap.parse_args();out=a.selfbuild_output.resolve();host=out/'host';w=out/'artifacts/certified-call-controls';w.mkdir(exist_ok=False)
 fixture=ROOT/'seed/tests/certified-scalar-calls';structure=json.loads((fixture/'native-structure.json').read_text());cases=json.loads((fixture/'cases.json').read_text());assert len(cases)==54
 assert sha(fixture/'controls.kotoba')==structure['sourceSHA256'] and sha(fixture/'cases.json')==structure['casesSHA256']
 source=w/'controls.kotoba';shutil.copy2(fixture/'controls.kotoba',source);loader=host/'kexe-loader';producers={}
 for tag,src in [('OFF',ROOT/'docs/evidence/certified-scalar-calls-20261013/previous-lookup-bootstrap.bin'),('ON',out/'artifacts/G2.bin')]:
  dst=host/('certified-'+tag+'-producer.bin');shutil.copy2(src,dst);producers[tag]=dst
 assert sha(producers['OFF'])=='09ee805e5f0feef246922026023e75d7d92e4531245466c9827883ff5baf9f62'
 assert sha(producers['ON'])==json.loads((ROOT/'seed/adoption-20261017.json').read_text())['nativeImageSHA256']
 pins={p:sha(p)for p in [loader,source,*producers.values()]};env={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')};env.update(KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(w),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(w));calls=[]
 def run(argv,name,e):
  z=subprocess.run(list(map(str,argv)),cwd=w,env=e,capture_output=True,timeout=1800);(w/(name+'.stdout')).write_bytes(z.stdout);(w/(name+'.stderr')).write_bytes(z.stderr);calls.append(dict(name=name,exit=z.returncode));(w/'calls.json').write_text(json.dumps(calls,indent=2)+'\n');assert z.returncode==0 and all(sha(p)==h for p,h in pins.items()),name;return z.stdout,z.stderr
 arms={}
 for tag,producer in producers.items():
  container=w/(tag+'.kseed');native=w/(tag+'.bin');prefix=[loader,producer,'0','0','aarch64','35,37,38,39','--']
  for command,tail in [('compile',[source,'--target','aarch64-macos','--output',container]),('extract-native',[container,'--symbol','pure-chain','--output',native])]:
   _,stderr=run(prefix+[command,*tail],tag+'-'+command,env);assert not stderr
  head,payload=container.read_bytes().split(b'\n\n',1);lines=head.decode().splitlines();ex={n:[int(p),int(a)]for n,p,a in map(str.split,lines[1:])};assert lines[0]==f'KSEED1 {len(payload)} {len(ex)}' and payload==native.read_bytes()
  assert dict(bytes=len(payload),sha256=sha(native),exports=ex)==structure[tag];arms[tag]=(native,ex)
 guest={k:v for k,v in env.items()if not k.startswith('KEXE_')};guest.update(KEXE_ARENA_USE='1',KEXE_STRUCTURED_REPORT='1',KEXE_FUEL='100000',KEXE_CPU_SECONDS='60',KEXE_WALL_SECONDS='60')
 for i,c in enumerate(cases):
  pair=[]
  for tag,(native,ex)in arms.items():
   offset,arity=ex[c['symbol']];assert arity==1;o,e=run([loader,native,str(offset),'1','aarch64','37',str(c['x'])],f'{i:02d}-{tag}',guest);m=re.search(rb':status :ok :result (-?\d+)',o);assert m and int(m.group(1))==c['result'];f=re.search(rb':fuel\s+\{\s*:initial\s+(\d+)\s+:remaining\s+(\d+)\s*\}',o);assert f and int(f.group(1))==100000 and 0<=int(f.group(2))<=100000
   lines=re.findall(rb'^KEXE_ARENA_USE.*$',e,re.M);assert len(lines)==1;arena={k.decode():int(v)for k,v in re.findall(rb':([a-z-]+) (\d+)',lines[0])};assert set(arena)==FIELDS and all(v>=0 for v in arena.values());pair.append((o,e))
  assert pair[0]==pair[1],('EXACT_RAW_FUEL_ARENA_MISMATCH',i)
 report=dict(status='PASS_CERTIFIED_SCALAR_CALL_54_FULL64_EXACT_RAW_FUEL_ALL17_PAIRS',pairs=54,guestCalls=108,compilerCalls=4,compilerImageSHA256=sha(producers['ON']),performanceMeasurement=False);(host/'certified-call-controls-report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
