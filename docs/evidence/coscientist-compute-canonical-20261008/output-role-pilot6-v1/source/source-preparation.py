"""Pure source authoring/AST boundary controls; never runs compiler/native/SSH."""
from pathlib import Path
import json,hashlib,re,ast
D=Path(__file__).resolve().parent;W=D.parent;K=W/'vector-compute-current19-query-census-source-v1-controls';B=W/'vector-compute-current19-query-census40-plan-v2-controls'
def pin(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def forms(s):
 depth=0;start=None;string=False;comment=False;esc=False;out=[]
 for i,c in enumerate(s):
  if comment:
   if c=='\n':comment=False
   continue
  if string:
   if esc:esc=False
   elif c=='\\':esc=True
   elif c=='"':string=False
   continue
  if c==';':comment=True;continue
  if c=='"':string=True;continue
  if c in '([{':
   if depth==0:start=i
   depth+=1
  elif c in ')]}':
   depth-=1;assert depth>=0
   if depth==0:out.append((start,i+1,s[start:i+1]))
 assert depth==0 and not string
 return out
def definition(s,name):
 z=[(a,b,t)for a,b,t in forms(s)if re.match(r'\(defn-?\s+'+re.escape(name)+r'\s',t)]
 assert len(z)==1,name;return z[0]
old=(K/'helpers.kotoba').read_text();new=old
a,b,t=definition(new,'cq-edges')
needle='(cq-edges M f (inc e))'
assert t.count(needle)==1
t=t.replace(needle,'(let [detail (if (= (vw-e M e 0) f) (cr-edge M f e) 0)] (+ (if (= (vw-e M e 0) f) 1 0) (cq-edges M f (inc e))))')
new=new[:a]+t+new[b:]
a,b,t=definition(new,'vw-memo-query')
assert t.count('valid (cq-valid M f)')==1
t=t.replace('valid (cq-valid M f)','valid (cq-valid M f) support-before (if valid (vw-f M f 15) 0) poison-before (if valid (vw-f M f 14) 0)')
t=t.replace('edges (if (and valid (cq-valid m f)) (cq-edges m f 0) 0)] m))','result (if (and valid (cq-valid m f)) (cr-result m f) 0)\n       fields (if (and valid (cq-valid m f)) (cr-fields m f 0) 0)\n       edges (if (and valid (cq-valid m f)) (cq-edges m f 0) 0)\n       done (cq-print "CR-END" [f support-before poison-before (if (and valid (cq-valid m f)) 1 0) edges])] m))')
assert '(cq-original-query M f)'in t and 'CR-END'in t
new=new[:a]+t+new[b:]
extra=(D/'extra-helpers.kotoba').read_text();idx=definition(new,'cq-edges')[0];new=new[:idx]+extra+'\n'+new[idx:];(D/'helpers.kotoba').write_text(new)
for name in ('41-census.kotoba','unity-census.kotoba'):
 s=(K/name).read_text();assert s.count(old)==1;n=s.replace(old,new);forms(n)
 (D/name.replace('census','result')).write_text(n)
 assert n.replace(new,old).encode()==(K/name).read_bytes()
for forbidden in ('vw-tick','vw-write','vw-cs','vw-fs','gn-put','gn-gs','vector-assoc!'):
 assert forbidden not in extra
assert definition(new,'vw-memo-query')[2].count('(cq-original-query M f)')==1
save(D/'source-reversal.json',{'exactReverseToFrozenCensusUnityAnd41':True,'additionalDefinitions':['cr-fields','cr-result','cr-edge'],'modifiedObserverDefinitions':['cq-edges','vw-memo-query'],'originalAnalyzerBodiesUnchanged':True,'originalQueryCallsPerWrapper':1,'newMGWrites':0,'newAnalysisTicks':0,'newQuerySkips':0,'sourcePreparation':'AST top-level definition selection and offset-preserving novel observer additions; no product refactor'})
inputs={str(K/'source-pins.json'):pin(K/'source-pins.json'),str(K/'helpers.kotoba'):pin(K/'helpers.kotoba'),str(K/'41-census.kotoba'):pin(K/'41-census.kotoba'),str(K/'unity-census.kotoba'):pin(K/'unity-census.kotoba'),str(B/'source-pins.json'):pin(B/'source-pins.json')}
for p in ('report.json','source-pins.json'):
 q=W/'vector-compute-result-projection-offline-v1-census-review'/p;inputs[str(q)]=pin(q)
save(D/'input-pins.json',inputs)
pr=json.loads((B/'preregistration.json').read_text());pr['schema']='DECLARED_OUTPUT_ROLE_CRC32_SLRE_PILOT6/v1';pr['entries']=[e for e in pr['entries']if e['workload']in ('crc32','slre')]
pr.update(maximumChildCalls=6,compilerBuildCalls=2,workloadCompileExtractCalls=4,rootGOStatus='AUTHORIZE_DECLARED_OUTPUT_ROLE_CRC32_SLRE_PILOT6_ONLY',sourceReviewStatus='PASS_SOURCE_ONLY_DECLARED_OUTPUT_ROLE_PILOT6',freshOutputDirectory=str(D/'run-outputs'),original19Qualified=False,driverCorrectionVersion=1)
pr['censusSourcePinsSHA256']=pin(K/'source-pins.json')['sha256'];pr['sourceOnly']=True;pr['actualCalls']=0;pr['fullResultCIDQualified']=False;pr['outputRoleClosed']=False
save(D/'pilot-preregistration.json',pr)
print('SOURCE prepared; no compiler/native/SSH calls')
