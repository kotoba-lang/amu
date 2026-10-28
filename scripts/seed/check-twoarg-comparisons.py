# Ported after the C loader was removed (scripts/seed/RETIRED.md): --selfbuild-output is now the output
# directory of scripts/seed/selfhost-bootstrap.py; payloads run through its C-free aarch64 runner
# (R-aarch64.elf) and ON is its adopted fixed-point image (G3.bin). Run on arm64 Linux.
"""Independent old-main/current native comparison, exact result/fuel/all17 controls."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
assert not sys.flags.optimize
import argparse
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--selfbuild-output',type=Path,required=True);args=ap.parse_args();out=args.selfbuild_output.resolve();(out/'artifacts').mkdir(exist_ok=True);(out/'host').mkdir(exist_ok=True);W=out/'artifacts/twoarg-comparison-boundaries';W.mkdir(exist_ok=False)
art=W/'artifacts';art.mkdir();raw=W/'raw';raw.mkdir()
loader=out/'R-aarch64.elf'
producers={'OFF':ROOT/'docs/evidence/pf-twoarg-v7-20261013/previous-certified-calls-bootstrap.bin','ON':out/'G3.bin'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((ROOT/'seed/adoption-20261022.json').read_text()) # the receipt's loader-source pin is historical: that source was removed
assert loader.is_file() # the C-free runner, pinned below for immutability
assert sha(producers['OFF'])=='446af9f37538cc37e57cb6133ab8ee2a3400cb001dccfd9e34d5da8e1909f76a'
assert sha(producers['ON'])==json.loads((ROOT/'seed/adoption-20261022.json').read_text())['nativeImageSHA256']
fixture=ROOT/'seed/tests/twoarg-comparison-boundaries';meta=json.loads((fixture/'cases.json').read_text());specs=meta['specs'];source=art/'controls.kotoba';source.write_bytes((fixture/'controls.kotoba').read_bytes());assert sha(source)==meta['sourceSHA256'];pins={p:sha(p)for p in [loader,source,*producers.values()]}
env={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')};env.update(KEXE_COMMAND='1',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(art),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(art))
calls=[]
def run(argv,name,e):
 z=subprocess.run(list(map(str,argv)),cwd=art,env=e,capture_output=True,timeout=1800)
 (raw/(name+'.stdout')).write_bytes(z.stdout);(raw/(name+'.stderr')).write_bytes(z.stderr)
 calls.append({'name':name,'exit':z.returncode,'stdoutSHA256':hashlib.sha256(z.stdout).hexdigest(),'stderrSHA256':hashlib.sha256(z.stderr).hexdigest()});(W/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
 assert all(sha(p)==h for p,h in pins.items()),'Input mutation'
 return z.returncode,z.stdout,z.stderr
arms={}
for tag,p in producers.items():
 container=art/(tag+'.kseed');native=art/(tag+'.bin');prefix=[loader,p,'0','0','aarch64','35,37,38,39','--']
 for cmd,args in [('compile',[source,'--target','aarch64-macos','--output',container]),('extract-native',[container,'--symbol','run-0','--output',native])]:
  rc,o,e=run(prefix+[cmd,*args],tag+'-'+cmd,env);assert rc==0 and not e,(tag,cmd,rc,o,e)
 h,b=container.read_bytes().split(b'\n\n',1);ls=h.decode().splitlines();ex={n:[int(p),int(a)]for n,p,a in map(str.split,ls[1:])};assert ls[0]==f'KSEED1 {len(b)} {len(ex)}'and b==native.read_bytes();assert set(ex)=={z['symbol']for z in specs};arms[tag]=(native,ex)
guest={k:v for k,v in env.items()if not k.startswith('KEXE_')};guest.update(KEXE_ARENA_USE='1',KEXE_STRUCTURED_REPORT='1',KEXE_CPU_SECONDS='60',KEXE_WALL_SECONDS='60')
fields={'pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'}
def compare(op,x,k):return {'=':x==k,'<':x<k,'>':x>k,'<=':x<=k,'>=':x>=k}[op]
pairs=0
for j,z in enumerate(specs):
 for n in [0,1,4,17]:
  expected=sum((7 if compare(z['op'],[0,3,8,11][i%4],z['k'])else 11)+40*i for i in range(n))
  for fuel in [1,6,31,100000]:
   guest['KEXE_FUEL']=str(fuel);pair=[]
   for tag,(native,ex)in arms.items():
    offset,arity=ex[z['symbol']];assert arity==1
    rc,o,e=run([loader,native,str(offset),'1','aarch64','37',str(n)],f'{j}-{n}-{fuel}-{tag}',guest);pair.append((rc,o,e));f=re.search(rb':fuel\s+\{\s*:initial\s+(\d+)\s+:remaining\s+(\d+)\s*\}',o);assert f and int(f.group(1))==fuel and 0<=int(f.group(2))<=fuel
    a=re.findall(rb'^KEXE_ARENA_USE.*$',e,re.M);assert len(a)==1;vals={k.decode():int(v)for k,v in re.findall(rb':([a-z-]+) (\d+)',a[0])};assert set(vals)==fields and all(v>=0 for v in vals.values())
    if fuel==100000:assert rc==0,('Expected positive high-fuel result',z,n,rc,o,e)
    if rc==0:
     m=re.search(rb':status :ok :result (-?\d+)',o);assert m and int(m.group(1))==expected
    else:assert b':status :exhausted'in o or b':budget/fuel'in o or b':status :trap'in o
   assert pair[0]==pair[1],('Exact raw mismatch',z,n,fuel);pairs+=1
assert pairs==480 and len(calls)==964
r={'status':'PASS_COMPARISON_FIVE_OPERATORS_SIGNED_IMMEDIATE_BOUNDARIES_480_EXACT_PAIRS','pairs':pairs,'guestCalls':960,'compilerCalls':4,'sourceSHA256':sha(source),'images':{tag:sha(a[0])for tag,a in arms.items()},'specs':specs,'adopted':False,'performanceMeasured':False,'physicalRecipeAudit':'Separate root v3/v7 whole-word/reference proof covers exact 20 copy removals and 10 out-of-range refusals'}
(W/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
