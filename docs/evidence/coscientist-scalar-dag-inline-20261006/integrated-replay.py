"""Offline retained-data replay. Standard library only; no guest/compiler/solver."""
from pathlib import Path
import json,hashlib,tarfile,tempfile,re,struct,importlib.util,collections
D=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text());man=load(D/'archive-manifest.json');archive=D/man['archive']['file'];assert sha(archive)==man['archive']['sha256'] and archive.stat().st_size==man['archive']['bytes'];T=Path(tempfile.mkdtemp(prefix='amu-integrated-offline-'))
with tarfile.open(archive) as t:t.extractall(T,filter='data')
P=T/'integrated-proof';assert sha(P/'payload-pins.json')==man['pins']['sha256'];pins=load(P/'payload-pins.json');assert len(pins)==man['pins']['count']
for n,v in pins.items():assert sha(P/n)==v['sha256'] and (P/n).stat().st_size==v['bytes'],n
F=load(P/'new/source-fixedpoint.json');assert F['commit']=='44bfaa28ccb70252bf763e20de5321ced848f0e4';assert sha(P/'measured/seed-4.bin')==F['seedSha256'];assert (P/'new/source/seed/41-a64gen.kotoba').read_bytes()==(P/'measured/41.kotoba').read_bytes()
for rel,h in F['committedDependencyContentPins'].items():assert sha(P/'new/source'/rel)==h
for rel,h in F['inputContentPins'].items():assert sha(P/'new/inputs'/rel)==h
for g in [1,2,3]:
 r=F['generations'][g-1]
 for rel,h in r['objects'].items():assert sha(P/f'new/g{g}/o'/rel)==h
 for rel,h in r['frontend'].items():assert sha(P/f'new/front{g}'/rel)==h
 assert len(r['objects'])==162 and len(r['frontend'])==117
 for name,v in r['artifacts'].items():assert sha(P/f'new/g{g}'/name)==v['sha256'] and (P/f'new/g{g}'/name).stat().st_size==v['bytes']
 if g>1:
  for name in r['objects']:assert (P/f'new/g{g}/o'/name).read_bytes()==(P/'new/g1/o'/name).read_bytes()
  for name in r['frontend']:assert (P/f'new/front{g}'/name).read_bytes()==(P/'new/front1'/name).read_bytes()
  for name in r['artifacts']:assert (P/f'new/g{g}'/name).read_bytes()==(P/'new/g1'/name).read_bytes()
for e in load(P/'new/comparison-matrix.json')['entries']:
 name=e['workload'];assert sha(P/'new/batch-source'/e['source'])==e['expectedSourceSha256'];assert (P/'new/ports'/name/'native.bin').read_bytes()==(P/'measured/ports'/name/'native.bin').read_bytes();b=next(x for x in load(P/'measured/ports-build.json')['entries'] if x['workload']==name);off=int(re.search(r':offset (\d+)',(P/'new/ports'/name/'extract.log').read_text())[1]);assert off==b['offset']
 for stage in ['compile','extract']:assert ':ok true' in (P/'new/ports'/name/(stage+'.log')).read_text()
 assert (P/'new/ports'/name/'check.log').read_text().startswith('ok ')
# Only precisely documented source roots and relocated report IDs normalize.
newroot='/private/tmp/amu-scalar-dag-inline-integrated-20261006/committed-source';priorroot='/private/tmp/amu-stable-vector-cfg-integrated-20261006/committed-source';oldroot='/Users/junkawasaki/github/wt/amu-seed17'
def norm(s):return s.replace(newroot+'/bench/embench/ports','/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports').replace(priorroot+'/bench/embench/ports','/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports').replace(newroot,oldroot).replace(priorroot,oldroot)
def identity(s):return s.replace('bench.embench.ports.','embench.ports.')
def lines(p):return p.read_text().splitlines()
def first(d,pre):return next((norm(l.strip()).replace('\t',' ') for l in ((d/(pre+'.out')).read_text()+'\n'+(d/(pre+'.err')).read_text()).splitlines() if l.startswith('ok ') or l.startswith('error: ')), '')
dirs={identity(p.name):p for p in (P/'new-main/run').iterdir()};dirs.update({identity(p.name):p for p in (P/'new-supplement/run').glob('*')});assert len(dirs)==391
sourceMap=load(P/'corpus-source-map.json');assert len(sourceMap)==391
for v in sourceMap.values():assert sha(P/v['path'])==v['sha256']
combined={}
for name,count in [('check.tsv',391),('compile.tsv',391),('exports.tsv',891)]:
 r=[identity(l) for l in lines(P/'new-supplement'/name)]+[identity(l) for l in lines(P/'new-main'/name)];assert len(r)==count
 if name=='check.tsv':
  rr=[]
  for l in r:
   f=l.split('\t');d=dirs[f[0]];f[2]=first(d,'s0c')[:200];f[4]=first(d,'ac')[:200];rr.append('\t'.join(f))
  r=rr
 assert [norm(l) for l in r]==[norm(x) for x in lines(P/'old'/name)]==lines(P/'new-final'/name),name;combined[name]=r
# Independently rederive checker classification using full actual outputs.
def okparts(s):
 m=re.match(r'ok profile=(\S+) effects=#\{(.*?)\} exports=\[(.*?)\]',s);return None if not m else (m[1],tuple(sorted(m[2].split())),m[3].split())
def msg(s):
 m=re.match(r'error: \S+ at .*?: (.*)$',s) or re.match(r'error: \S+: (.*)$',s);s=m[1] if m else s;return re.sub(r'#\{([^{}]*)\}',lambda x:'#{'+' '.join(sorted(re.findall(r'\[[^\]]*\]|\S+',x[1])))+'}',s)
for l in combined['check.tsv']:
 id,c0,_,c1,_,expected=l.split('\t');d=dirs[id];a=first(d,'s0c');b=first(d,'ac')
 if c1=='69':cls='STUB'
 elif not b:cls='AMU-TRAP'
 elif a.startswith('ok') and b.startswith('ok'):cls='SAME-OK' if okparts(a)==okparts(b) else 'OK-DIFF'
 elif a.startswith('error') and b.startswith('error'):cls='SAME-REFUSE' if msg(a)==msg(b) else 'REFUSE-DIFF'
 elif a.startswith('ok'):cls='AMU-REFUSES'
 else:cls='AMU-ACCEPTS'
 if cls in ['SAME-OK','SAME-REFUSE'] and c0!=c1:cls+='-RC'
 assert cls==expected,(id,cls,expected)
# Reconstruct export SAME/DIFF/TIMEOUT and missing actual export.
sp=importlib.util.spec_from_file_location('kexe',P/'helpers/kexe_check.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
counts={}
for l in combined['exports.tsv']:
 f=l.split('\t');id,symbol,expected=f[:3];d=dirs[id]
 if expected=='MISSING':
  body=m.parse((d/'a.kexe').read_text());assert m.get(m.get(body,m.Kw(':exports')),m.Sym(symbol)) is None;continue
 if expected=='NOT-RUN':continue
 a=(d/('0.'+symbol+'.out')).read_bytes();b=(d/('1.'+symbol+'.out')).read_bytes();s0=(d/('0.'+symbol+'.st')).read_text().rstrip('\n');s1=(d/('1.'+symbol+'.st')).read_text().rstrip('\n');assert [s0,s1]==f[3:]
 cls='TIMEOUT' if any(x in s0+s1 for x in ['SIGALRM','SIGXCPU']) else 'SAME' if a==b and s0.split(' ')[0]==s1.split(' ')[0] else 'DIFF';assert cls==expected;counts.setdefault(id,collections.Counter())[cls]+=1
sp=importlib.util.spec_from_file_location('kexe',P/'helpers/kexe_check.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
full=raw=images=sourcepins=0;nativeChanges=[];exportLayoutChanges=[]
for id,d in dirs.items():
 old=P/'old/run'/id
 for n in ['ac.out','ac.err']:assert norm((d/n).read_text())==norm((old/n).read_text());full+=1
 for n in old.glob('1.*'):
  if n.suffix in ['.out','.st']:assert (d/n.name).read_bytes()==n.read_bytes();raw+=1
 if (old/'a.kexe').exists():
  a=m.parse((d/'a.kexe').read_text());b=m.parse((old/'a.kexe').read_text());aa=bytes(m.get(a,m.Kw(':code')));bb=bytes(m.get(b,m.Kw(':code')));xa=m.get(a,m.Kw(':exports'));xb=m.get(b,m.Kw(':exports'));sig=lambda xs:[(symbol,[(key,value) for key,value in fields if key not in [m.Kw(':offset'),m.Kw(':length')]]) for symbol,fields in xs];assert sig(xa)==sig(xb);images+=1
  if aa!=bb:nativeChanges.append(id)
  if xa!=xb:exportLayoutChanges.append(id)
  h=re.search(r':source-sha256 "([a-f0-9]{64})"',(old/'a.kexe.provenance.edn').read_text())[1];assert h==sourceMap[id]['sha256'];assert h==re.search(r':source-sha256 "([a-f0-9]{64})"',(d/'a.kexe.provenance.edn').read_text())[1];sourcepins+=1
# Recompute compile classes from retained oracle-cache acceptance, actual exit/seal and export outcomes.
for l in combined['compile.tsv']:
 f=l.split('\t');id,s0,c1,expected=f[:4];d=dirs[id];h=sourceMap[id]['sha256'][:16];assert ('ok' if (P/'oracle-cache'/(h+'.kexe')).exists() else 'refuse')==s0
 if c1=='69':cls='STUB'
 elif int(c1) not in [0,65,64]:cls='AMU-TRAP'
 elif s0=='refuse':cls='AMU-ACCEPTS' if c1=='0' else 'BOTH-REFUSE'
 elif c1!='0':cls='AMU-REFUSES'
 else:
  assert (d/'a.kexe').exists() and ':ok true' in (d/'ap.out').read_text();body=m.parse((d/'a.kexe').read_text());stored=m.get(body,m.Kw(':sha256'));sealbody=m.d_wrap([(k,v) for k,v in body if k!=m.Kw(':sha256')]);assert stored[1]==hashlib.sha256(m.pr(m.canonical(sealbody)).encode()).hexdigest()
  cc=counts.get(id,{});missing=sum(x.split('\t')[0]==id and x.split('\t')[2]=='MISSING' for x in combined['exports.tsv']);cls='BOTH-OK-DIFF' if cc.get('DIFF',0) or missing else 'BEHAVIOUR-SAME' if sum(cc.values()) else 'BOTH-OK-NORUN'
 assert cls==expected,(id,cls,expected)
assert (full,raw,images,sourcepins)==(782,1780,330,330)
refactor=load(P/'new/refactor-proof.json');assert refactor['pairs']==12 and all(r['old']==r['new'] for r in refactor['rows']);
for row in refactor['rows']:
 for arm in ['old','new']:
  for name,h in row[arm]['files'].items():assert sha(P/'new/refactor'/str(row['case'])/arm/name)==h
assert set(nativeChanges)==set(load(P/'new-final/report.json')['changedNativeImages'])
out={'refactorPairs':12,'status':'PASS portable independent integrated retained-byte/classification replay','includedPins':len(pins),'fullOriginalPinSet':load(P/'selection.json')['fullPinCount'],'selectedOmissions':load(P/'selection.json')['omissions'],'generations':[1,2,3],'objectCount':162,'frontendCount':117,'nativeCommandContainerAndObjectEqualitiesRecomputed':True,'original19MeasuredCodeAndOffsetsEqual':True,'check391':True,'compile391':True,'exports891':True,'executableExportRows':890,'exportCounts':dict(collections.Counter(l.split('\t')[2] for l in combined['exports.tsv'])),'preexistingMissingRows':[l for l in combined['exports.tsv'] if l.split('\t')[2]=='MISSING'],'checkerClassificationsRecomputed':391,'compileClassificationsRecomputed':391,'exportClassificationsRecomputed':891,'fullCheckerPairs':391,'nativeOutStatusFilesExact':1780,'nativeImagesVerified':330,'nativeCodeChangesRecorded':nativeChanges,'exportLayoutChangesRecorded':exportLayoutChanges,'nativeExportSignaturesPreserved':330,'oldAndNewSourceProvenanceVerified':330,'pathNormalizationOnly':True,'freshNativeExecutions':0,'freshSolverExecutions':0,'timingExcluded':True,'performanceOrFull100Claim':False}
(D/'replay.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
