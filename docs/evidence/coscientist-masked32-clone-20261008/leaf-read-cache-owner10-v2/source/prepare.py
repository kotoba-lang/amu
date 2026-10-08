from pathlib import Path
import json,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent;L=W/'vector-leaf-straight-read-cache-source-v1-native-controls';MO=W/'vector-masked32-on-clone-observer-source-v3-controls';B=W/'vector-leaf-straight-read-cache-build4-actual-review-v2-controls';F=W/'vector-fuel-scalar-dag-component18-source-v1-width'
def j(p):return json.loads(p.read_text())
def pin(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'bytes':p.stat().st_size,'sha256':h.hexdigest()}
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def fn(s,n):
 start=s.index('(defn- '+n+' ');depth=0;quoted=False;comment=False;esc=False
 for i in range(start,len(s)):
  c=s[i]
  if comment:
   if c=='\n':comment=False
   continue
  if quoted:
   if esc:esc=False
   elif c=='\\':esc=True
   elif c=='"':quoted=False
   continue
  if c==';':comment=True
  elif c=='"':quoted=True
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if depth==0:return s[start:i+1]
 raise AssertionError(n)
assert pin(B/'report.json')['sha256']=='c966b2a260be47ef1f9d1e06cfc3a024a5706f1a1715512983706ef004134b55';br=j(B/'report.json');assert br['status']=='PASS_INDEPENDENT_ACTUAL_LEAF_STRAIGHT_READ_CACHE_COMPILER_BUILD4_IDENTITY_ONLY';on=next(x for x in br['images']if x['arm']=='ON')['native']
# Prospective registration before observer/driver source assembly.
pr={'status':'PROSPECTIVE_LC_GENUINE_OWNER_OBSERVER10_BEFORE_SOURCE_AUTHORING','schema':'LC_OWNER_OBSERVER10/v1','maximumLoaderCalls':10,'stageOrder':['ordinary-md5-compile','ordinary-md5-extract','ordinary-sha-compile','ordinary-sha-extract','observer-compile','observer-extract','observed-md5-compile','observed-md5-extract','observed-sha-compile','observed-sha-extract'],'producer':on['path'],'producerSHA256':on['sha256'],'loader':str(W/'vector-masked32-source-bound-loader-build-plan-v2-native-controls/run-outputs/kexe-loader'),'actualProducerProof':str(B/'report.json'),'actualProducerProofStatus':br['status'],'actualLoaderProof':str(W/'vector-masked32-source-bound-loader-actual-review-v2-width/report.json'),'actualLoaderProofStatus':'PASS_INDEPENDENT_ACTUAL_SOURCE_BOUND_DIAGNOSTIC_LOADER16_BUILD_IDENTITY_ONLY','parentSource':str(L/'unity-lc-on.kotoba'),'parentSourcePinsSHA256':pin(L/'source-pins.json')['sha256'],'rootGOStatus':'ROOT_AUTHORIZED_LC_OWNER_OBSERVER10_COMPILE_ONLY','sourceReviewStatus':'PASS_SOURCE_ONLY_READONLY_LC_OWNER_OBSERVER10','freshOutputRoot':str(D/'run-outputs'),'maximumInputFiles':2048,'maximumInputLogicalBytes':402653184,'nativeBytesMaximum':4194304,'containerBytesMaximum':4194560,'stdoutBytesMaximum':16777216,'stderrBytesMaximum':1048576,'fileHardLimitBytes':67108864,'wallSeconds':1810,'reapSeconds':30,'compileResources':j(F/'preregistration.json')['compileResources'],'noRetry':True,'firstFailureStop':True,'outerExecution':'require_escalated','workloadGuestAuthorized':False,'timingAuthorized':False,'generatedWorkloadExecutionAuthorized':False,'observerCompilerExecutionAuthorized':True,'zeroEligibleOwnerPolicy':'STOP_FIRST_ZERO_OBSERVED_WORKLOAD; retain raw; no synthetic positive SIR or region widening','novelDiagnosticAuthoringException':'Isolated authored readonly diagnostic, no product source mutation; no claimed refactor verify equivalence.','observationScope':'lc-assign once before/after FREC/gn fields/sreg; function prologue and vector-read emitted spans; final full SIR/FREC/CODE/FIX/LIT/LITB/LABEL/EXP tables before/after output layout. Physical x19..21 instruction witnesses remain evidence requiring interpretation, not runtime ABI proof.'}
save('preregistration.json',pr)
helper=(MO/'helpers.kotoba').read_text().split('(defn- mo-call-field ')[0].replace('mo-','lo-').replace('"MO "','"LO "')
helper+='''\n(defn- lo-print [tag :string xs :vector-i64] :i64
 (let [a (io-out tag) b (loop [k 0] (if (>= k (vector-count xs)) 0 (let [p (io-out (string-concat " " (string-from-i64 (vector-at xs k))))] (recur (inc k)))))] (io-out "\\n")))
(defn- lo-assign-record [M :vector-i64 phase :i64 i :i64 f :i64 np :i64] :i64
 (let [a (lo-print "LA" [phase i f np (vector-at M MM-ERR) (vector-at M MM-SIR-N) (vector-at M MM-FN-N) (vector-at M MM-CODE-N) (vector-at M MM-FIX-N)])
       b (loop [k 0] (if (= k 16) 0 (let [p (lo-print "LG" [phase i f k (gn-g M k)])] (recur (inc k)))))
       c (loop [k 0] (if (= k 16) 0 (let [p (lo-print "LF" [phase i f k (gn-fnf M f k)])] (recur (inc k)))))
       d (loop [k 1] (if (> k 7) 0 (let [p (lo-print "LS" [phase i f k (gn-sreg M k)])] (recur (inc k)))))] 0))
'''
(D/'helpers.kotoba').write_text(helper);patches=[]
for source,out in [(L/'41-lc-on.kotoba','41-observer-on.kotoba'),(L/'unity-lc-on.kotoba','unity-observer-on.kotoba')]:
 s=source.read_text();original=s;pp=[]
 # Add readonly helpers before lc-assign. All original delegate definitions copied byte-for-byte.
 old=fn(s,'lc-assign');ren=old.replace('(defn- lc-assign','(defn- lo-base-assign',1);new=helper+'\n'+ren+'''\n(defn- lc-assign [M :vector-i64 i :i64 f :i64 np :i64] :vector-i64
 (let [a (lo-assign-record M 0 i f np) result (lo-base-assign M i f np) b (lo-assign-record result 1 i f np)] result))''';assert s.count(old)==1;s=s.replace(old,new,1);pp.append({'old':old,'new':new})
 for name,wrapper in [('gn-op-fn2','''(defn- gn-op-fn2 [M :vector-i64 i :i64 f :i64 np :i64] :vector-i64
 (let [start (vector-at M MM-CODE-N) result (lo-base-op-fn2 M i f np)
       p (lo-print "LP" [i f start (vector-at result MM-CODE-N) (gn-g result gn-f-fb) (gn-g result gn-f-nsv) (gn-g result gn-f-vmode) (gn-g result gn-f-leaf) (gn-g result gn-f-freg) (gn-g result gn-f-ctx) (vector-at result MM-ERR)])] result))'''),('gn-rt-at','''(defn- gn-rt-at [M :vector-i64 i :i64 t :i64] :vector-i64
 (let [start (vector-at M MM-CODE-N) mode (gn-g M gn-f-vmode) result (lo-base-rt-at M i t)
       p (lo-print "LR" [i t mode start (vector-at result MM-CODE-N) (vector-at result MM-ERR)])] result))''')]:
  old=fn(s,name);ren=old.replace('(defn- '+name,'(defn- lo-base-'+name[3:],1);new=ren+'\n'+wrapper;s=s.replace(old,new,1);pp.append({'old':old,'new':new})
 for name in (['gn-run','out-build']if source.name.startswith('unity')else ['gn-run']):
  old=fn(s,name)
  if name=='gn-run':new=old.replace('(if (= mc-feature 1)', '(lo-snapshot (if (= mc-feature 1)',1)[:-1]+' 3))'
  else:new=old.replace('(out-build2 M1 S)','(lo-snapshot (out-build2 M1 S) 4)',1)
  s=s.replace(old,new,1);pp.append({'old':old,'new':new})
 r=s
 for z in reversed(pp):assert r.count(z['new'])==1;r=r.replace(z['new'],z['old'],1)
 assert r==original;(D/out).write_text(s);patches.append({'path':out,'parent':str(source),'parentSHA256':pin(source)['sha256'],'patches':pp,'exactReverse':True})
save('reversal.json',patches)
# Two whole unmodified sources from canonical original matrix.
matrix=Path('/Users/junkawasaki/github/wt/amu-seed17/bench/embench/comparison-matrix.json');rows=j(matrix)['entries'];entries=[]
for n in ['md5sum','nettle-sha256']:
 e=next(x for x in rows if x['workload']==n);source=Path('/Users/junkawasaki/github/wt/amu-seed17')/e['source'];assert pin(source)['sha256']==e['expectedSourceSha256'];entries.append({'workload':n,'source':dict(path=str(source),**pin(source)),'symbol':e['symbol']})
pr['entries']=entries;pr['observerSource']=str(D/'unity-observer-on.kotoba')
ip={}
def add(p,z=None):
 p=Path(p);v=pin(p)
 if z:assert v=={k:z[k]for k in ('bytes','sha256')}
 if str(p)in ip:assert ip[str(p)]==v
 ip[str(p)]=v
for p,z in j(B/'input-pins.json').items():add(p,z)
for n in ['report.json','input-pins.json']:add(B/n)
for p in L.rglob('*'):
 if p.is_file()and '__pycache__'not in p.parts:add(p)
for n in ['helpers.kotoba','source-pins.json','source-report.json']:add(MO/n)
for n in ['run.py','source-pins.json','preregistration.json']:add(F/n)
add(matrix)
for e in entries:add(e['source']['path'],e['source'])
assert len(ip)<=2048 and sum(v['bytes']for v in ip.values())<=402653184;save('input-pins.json',ip);pr.update(inputPinsSHA256=pin(D/'input-pins.json')['sha256'],exactInputFiles=len(ip),exactInputLogicalBytes=sum(v['bytes']for v in ip.values()));save('preregistration.json',pr)
