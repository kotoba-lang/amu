from pathlib import Path
import json,hashlib,sys,ast
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-fuel-scalar-dag-component18-source-v1-width';O=Path(__file__).resolve().parent;ip={}
def j(p):return json.loads(p.read_text())
def pin(p,v=None):
 p=Path(p);assert p.is_file()and not p.is_symlink();h=hashlib.sha256();n=0
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
 z={'bytes':n,'sha256':h.hexdigest()}
 if v is not None:assert z=={k:v[k]for k in ['bytes','sha256']},str(p)
 ip[str(p)]=z;return z
sp=pin(D/'source-pins.json');assert sp['sha256']=='7be013ea72525ce912f0e3c6bd3db91c190a801b5c6a38c72b8ba5addbb6d38c'
for n,v in j(D/'source-pins.json').items():pin(D/n,v)
pr=j(D/'preregistration.json');inputs=j(D/'input-pins.json');assert len(inputs)==pr['exactInputFiles']==1738 and sum(v['bytes']for v in inputs.values())==pr['exactInputLogicalBytes']==369725436 and len(inputs)<=2048 and sum(v['bytes']for v in inputs.values())<=402653184
for p,v in inputs.items():pin(p,v)
for key in ['actualProducerProof','actualLoaderProof']:assert j(Path(pr[key]))['status']==pr[key+'Status']
assert pin(Path(pr['producer']))['sha256']==pr['producerSHA256']=='d3a0e2ffe5887a1b77ace0e0a366dd8bda180f3e9ef2f7067a1e3436f9c3d15a'
parent=Path(pr['parentEmitterSourceDirectory'])/'unity-df-on.kotoba';base=parent.read_text();candidate=(D/'unity-component.kotoba').read_text();helper=(D/'control-helpers.kotoba').read_text()
def definition(s,name):
 start=s.index('(defn- '+name+' ');depth=0;string=False;comment=False;escape=False
 for i in range(start,len(s)):
  c=s[i]
  if comment:
   if c=='\n':comment=False
   continue
  if string:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':string=False
   continue
  if c==';':comment=True
  elif c=='"':string=True
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if depth==0:return s[start:i+1]
 raise AssertionError('unbalanced')
oldcall=definition(base,'gn-op-call');renamed=oldcall.replace('(defn- gn-op-call','(defn- dc-original-call',1);wrapper=definition(candidate,'gn-op-call');assert wrapper=='(defn- gn-op-call [M :vector-i64 i :i64 f :i64 t :i64 n :i64] :vector-i64\n (if (and (dc-enabled) (> (df-admit M i f t n) 0)) (dc-check M i f t n) (dc-original-call M i f t n)))'
r=candidate.replace(helper+'\n'+renamed+'\n'+wrapper,oldcall,1)
mods=[('m1 (mem-alloc m0 (if enlarged newneed oldneed))]','m1 (mem-alloc m0 (if enlarged newneed oldneed))\n       receipt (if (dc-enabled) (dc-print "ALLOC" [b (if enlarged newneed oldneed) (vector-at m1 MM-R0) (vector-at m1 MM-HEAP-TOP) (vector-at m1 MM-R1) (vector-at m1 MM-ERR)]) 0)]'),('(defn- seed-main [] :i64 (drv-main))','(defn- seed-main [] :i64 (if (dc-enabled) (dc-main) (drv-main)))'),('(defn- drv-c5 [M :vector-i64 S :string path :string out :string] :i64\n  (if (= (vector-at M MM-ERR) 0) (drv-c6 (gn-run M) S path out) (drv-fail M path)))','(defn- drv-c5 [M :vector-i64 S :string path :string out :string] :i64\n  (if (dc-enabled) (dc-finish M) (if (= (vector-at M MM-ERR) 0) (drv-c6 (gn-run M) S path out) (drv-fail M path))))')]
patch=j(W/'vector-masked32-shift-orr-native-controls-source-v3-native-controls/mc-diagnostic-return-patch.json');mods.append((patch['old'],patch['new'].replace('sx-enabled','dc-enabled')))
for a,b in reversed(mods):assert r.count(b)==1;r=r.replace(b,a,1)
assert r==base
# Execute only truncated pure source controls, preventing its frozen output write.
s=(D/'source-controls.py').read_text();cut=s.index("(D/'source-controls.json').write_text");ns={'__file__':str(D/'source-controls.py'),'__name__':'source_only_review'};exec(compile(s[:cut],str(D/'source-controls.py'),'exec'),ns)
run=(D/'run.py').read_text();fuel=(W/'vector-fuel-scalar-dag-compiler-build4-plan-v2-width/run.py').read_text()
def ledger(s):
 start=s.index('  op=O/(label+');end=s.index('\n try:\n',start);return s[start:end]
assert ledger(run)==ledger(fuel)
assert "['probe',str(c),str(fixture)]"in run and '(> (io-argc) 2)'in helper and '(io-arg 2)'in helper and pr['expectedCases']==list(range(16))and pr['maximumLoaderCalls']==18
for n in ['run.py','validate.py','assemble.py']:ast.parse((D/n).read_text())
report={'status':'PASS_SOURCE_ONLY_FUEL_DAG_COMPONENT18','sourcePinsSHA256':sp['sha256'],'driverSHA256':pin(D/'run.py')['sha256'],'preregistrationSHA256':pin(D/'preregistration.json')['sha256'],'inputPinsSHA256':pin(D/'input-pins.json')['sha256'],'exactInputFiles':1738,'exactInputLogicalBytes':369725436,'maximumLoaderCalls':18,'twoBuildAndSixteenProbeOnly':True,'parentExactReversalIndependentlyRecomputed':True,'ordinaryPipelineAndSentinelPreserved':True,'ledgerCleanupByteExactReviewedFuelBuild4V2':True,'pureValidRecords':16,'pureRejectedMutants':8,'scope':'Actual df-admit/df-call scalar-state predicate and copied M comparison; diagnostic source no generated CODE execution. Capacity/dirty/shape guard cases compare copied full scalar input. Allocator receipt must match actual owner state before probe.','limitations':['Fixture actual admission and native lexical/type qualification pending; first missing eligible site stops.','M/G equality is source-derived scalar predicate, not independent memory capture or external arena dump.','Fuel0/1/2 model is abstract and 5-word encoding witness only; no executed low-fuel trap or ABI/function equivalence.','Fixed guest pools may refuse copied full-vector diagnostic allocation; no universal allocation theorem.'],'participation':'Reviewer authored separate earlier component/Compute witnesses and LC source; current fuel emitter/component/driver authored by width. This is independent source review, no actual execution approval.','rootGORequired':True,'nativeCompilerSSHCalls':0,'performanceQualified':False,'full19Qualified':False}
for name,z in [('report.json',report),('input-pins.json',ip)]: (O/name).write_text(json.dumps(z,indent=2)+'\n')
(O/'source-pins.json').write_text(json.dumps({p.name:pin(p)for p in sorted(O.iterdir())if p.is_file()and p.name!='source-pins.json'},indent=2)+'\n');print(json.dumps({'report':pin(O/'report.json'),'inputPins':pin(O/'input-pins.json')}))
