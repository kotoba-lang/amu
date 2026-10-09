"""Inert SOURCE. Current OFF/TC original19 functional190 only after exact two reviews and GO."""
from pathlib import Path
import json,hashlib,stat,importlib.util,re,os
D=Path(__file__).resolve().parent

def need(v,m):
 if not v:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def receipt(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=469762048,'bounded regular pin');b=p.read_bytes();s2=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(s2.st_dev,s2.st_ino,s2.st_size,s2.st_mtime_ns),'immutable bytes');return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def pin(p,r):need(receipt(p)=={k:r[k]for k in ['bytes','sha256']},'exact pin:'+str(p));return Path(p)
def save(p,v):
 
 if Path(p).name=='attempts.json':need(all(len(json.dumps(r).encode())<=65536 for r in v),'bounded per-case metadata before publication')
 b=(json.dumps(v,indent=2)+'\n').encode();need(len(b)<=16777216,'bounded valid-last metadata');q=Path(str(p)+'.pending')
 with q.open('wb',buffering=0)as f:
  view=memoryview(b)
  while view:
   n=f.write(view);need(type(n)is int and 0<n<=len(view),'metadata write');view=view[n:]
  os.fsync(f.fileno())
 os.replace(q,p);fd=os.open(str(Path(p).parent),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def container(raw):
 need(0<len(raw)<=4194560,'bounded KSEED');m=re.match(rb'KSEED1 ([1-9][0-9]{0,9}) ([1-9][0-9]{0,2})\n',raw);need(m is not None,'header');cut=raw.find(b'\n\n',m.end());need(cut>=m.end(),'separator');lines=raw[m.end():cut].splitlines();n=int(m[2]);need(1<=n<=128 and len(lines)==n,'exports');exports=[]
 for line in lines:
  q=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]{1,10}) ([0-9]{1,2})',line);need(q is not None,'export line');exports.append((q[1].decode(),int(q[2]),int(q[3])))
 payload=raw[cut+2:];need(0<len(payload)<=4194304 and len(payload)==int(m[1]) and len(set(x[0]for x in exports))==n,'whole payload/unique');need(all(x[1]%4==0 and x[1]+4<=len(payload)and x[2]<=32 for x in exports),'entry ABI');return payload,exports

def source_scope(pr,off,tc,oracle):
 need(off['status']==pr['OFFActualProofStatus'] and tc['status']==pr['TCActualProofStatus'] and oracle['status']==pr['C95OracleStatus'],'saved proof scope')
 need(off['joinedOriginal19ArtifactWholePayloadIdentity']is True,'OFF nineteen whole artifact proof')
 need(off['currentBaselineNative']['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'and off['current16BaselineSource']['sha256']=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418','current baseline lineage')
 need(tc['G0Native']['sha256']=='5cda246fec1d653b5ff044a56491069874f7a0b58da87785887c369573ccec8c'and tc['current16OwnSource']['sha256']=='94fe39401f5f0a1120b12b2d17bf000d14a54c9c68e1f8976b8b0ced8794f199','current TC lineage')
 for v in [off['currentBaselineNative'],off['currentBaselineContainer'],off['current16BaselineSource'],tc['G0Native'],tc['G0Container'],tc['current16OwnSource']]:pin(v['path'],v)
 need(tc['joinedOriginal19ArtifactWholePayloadIdentity']is True and tc['G0G1G2G3WholeNativeEqual']is True and tc['G0G1G2G3WholeContainerEqual']is True,'TC current own-source fixedpoint lineage')
 matrix=load(pr['canonicalMatrix']);need(len(matrix['entries'])==19 and matrix['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70','original19 source matrix')
 need(len(pr['entries'])==19 and len(oracle['rows'])==95 and len(pr['cases'])==190,'finite original matrix')
 om={r['workload']:r for r in off['joinedOriginal19Images']};tm={r['workload']:r for r in tc['joinedOriginal19Images']};need(len(om)==len(tm)==19,'whole nineteen both arms')
 expected=[]
 for e,m in zip(pr['entries'],matrix['entries']):
  need(e['workload']==m['workload']and e['symbol']==m['symbol']and e['iterations']==m['iterations']and e['source']['sha256']==m['expectedSourceSha256'],'unchanged workload/profile/symbol')
  for n in e['iterations']:
   oo=[r for r in oracle['rows']if r['workload']==e['workload']and r['n']==n];need(len(oo)==1 and oo[0]['sourceSHA256']==e['source']['sha256']and oo[0]['symbol']==e['symbol']and type(oo[0]['result'])is int and oo[0]['result']in [0,1],'C95 exact source/profile Boolean')
   for arm,images in [('OFF',om),('TC',tm)]:
    image=images[e['workload']];c=pr['cases'][len(expected)];need(c['workload']==e['workload']and c['arm']==arm and c['profile']==n and type(c['expectedResult'])is int and c['expectedResult']==oo[0]['result']and c['source']==e['source']and c['symbol']==e['symbol']and c['arity']==1,'exact adjacent OFF/TC profile')
    need(c['native']==image['native']and c['container']==image['container']and c['offset']==image['offset'],'whole saved own artifact binding')
    payload,exports=container(pin(c['container']['path'],c['container']).read_bytes());need(payload==pin(c['native']['path'],c['native']).read_bytes()and (c['symbol'],c['offset'],1)in exports,'own whole payload/export')
    need(c['nativeArgv']==[pr['loader'],c['native']['path'],str(c['offset']),'1','aarch64','-',str(n)],'precise runtime argv no compiler/C calls');expected.append(c)
 from loader_grammar import interpretation
 need(all(interpretation(c['nativeArgv'])['typedI64']==[c['profile']]for c in expected),'source-bound i64 arguments, not guest argv')
 need(len(expected)==190 and len(pr['environment'])==17 and pr['C2']is False and pr['guestFuelPerCall']==16777216,'fixed190 original fuel')
 return True

def main(goPath):
 import time
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);rows=[];results=[];generated={};ok=False
 proofKeys=['OFFActualProof','TCActualProof','C95Oracle','C95OracleProof','integrationFixtureProof','retainedV2Failure','retainedV2FailureProof']
 need(set(g)==set(['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews']+proofKeys),'exact GO keys')
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==190 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is True and g['C2']is False,'exact functional190 only')
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'GO identity')
 need(len(g['sourceReviews'])==2 and len(set(r['path']for r in g['sourceReviews']))==2,'two exact reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'specific reviewed SOURCE')
 need(g['retainedV2Failure']==pr['retainedV2Failure'],'preserve exact V2 failure')
 for r in pr['retainedV2Failure'].values():pin(r['path'],r)
 need(g['retainedV2FailureProof']==pr['retainedV2FailureProof'],'exact independent V2 failure proof');v2proof=load(pin(g['retainedV2FailureProof']['path'],g['retainedV2FailureProof']));need(v2proof['status']==pr['retainedV2FailureProofStatus'],'V2 only failure scope')
 v2t=load(pr['retainedV2Failure']['terminal.json']['path']);v2a=load(pr['retainedV2Failure']['attempts.json']['path']);need(v2t=={'loaderCalls':1,'allChildrenClosed':True,'failure':True}and len(v2a)==1 and v2a[0]['returncode']==2,'V2 remains failed; no replay of prior closed invocation')
 for k in proofKeys:
  if k in ['retainedV2Failure','retainedV2FailureProof']:continue
  target='qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k;need(g[k]==pr[target],'fixed proof identity');pin(g[k]['path'],g[k])
 f=load(g['integrationFixtureProof']['path']);need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','actual fixture scope')
 for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'unchanged qualified components')
 op=load(pr['C95OracleProof']['path']);need(op['status']==pr['C95OracleProofStatus']and op['oracle']==pr['C95Oracle'],'C95 saved result-only scope')
 def guard():
  need(receipt(gp)==gr and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256'],'immutable registries')
  need(len(ip)==pr['inputFiles']<=4096 and sum(r['bytes']for r in ip.values())==pr['inputLogicalBytes']<=469762048,'finite full input closure')
  for n,r in sp.items():pin(D/n,r)
  for p,r in ip.items():pin(p,r)
  for p,r in generated.items():pin(p,r)
  source_scope(pr,load(pr['OFFActualProof']['path']),load(pr['TCActualProof']['path']),load(pr['C95Oracle']['path']))
 guard();need(not O.exists(),'fresh output namespace');O.mkdir();save(O/'attempts.json',rows);save(O/'effective-environment.json',pr['environment']);save(O/'generated-pins.json',generated)
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);campaignDeadline=time.monotonic()+9300
 try:
  for index,c in enumerate(pr['cases'],1):
   guard();need(time.monotonic()+60<=campaignDeadline,'finite campaign deadline before new child')
   seal={k:c[k]for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};seal.update(format=pr['invocationSealVersion'],index=index,rootGO=dict(path=str(gp),**gr),sourcePinsSHA256=g['sourcePinsSHA256'],preregistrationSHA256=g['preregistrationSHA256'])
   sealPath=O/(c['label']+'.admission.json');need(not sealPath.exists(),'one exact call seal');save(sealPath,seal);need(sealPath.stat().st_size<=4096,'bounded seal');sealPath.chmod(0o444);sr=receipt(sealPath);generated[str(sealPath)]=sr;save(O/'generated-pins.json',generated)
   r=mod.call(D,O,pr,c,rows,save,sr['sha256']);need(len(json.dumps(rows[-1]).encode())<=65536,'bounded per-case metadata');results.append(r);save(O/'results.json',results)
   if index%2==0:
    a,b=results[-2:];need(all(a['report'][k]==b['report'][k]for k in ['result','fuelInitial','fuelRemaining','fuelConsumed','arena17']),'OFF/TC Boolean fuel seventeen arenas equal')
  guard();need(len(rows)==len(results)==190 and all(r['state']=='terminal'and r['returncode']==0 for r in rows),'190 complete runtime children');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed']is True and terminal['failure']is False,'durable valid-last terminal')
 evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['terminal.json','attempts.json','generated-pins.json','results.json','effective-environment.json']}
 save(O/'report.json',{'status':'COMPLETE_CURRENT_OFF_TC_ORIGINAL19_FUNCTIONAL190_SAVED_C95_RESULT_ONLY','runtimeCalls':190,'profiles':95,'results':results,'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'evidence':evidence,'C95Oracle':g['C95Oracle'],'C95FuelArenaAvailable':False,'C95FuelArena':None,'performanceQualified':False,'hardPeakQualified':False,'strictPhysicalMemoryQualified':all(r['strictOldMemoryPolicyPassed']for r in results),'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact GO');main(sys.argv[1])
