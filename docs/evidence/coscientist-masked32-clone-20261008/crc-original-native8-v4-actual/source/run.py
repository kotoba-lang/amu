"""Inert import. Frozen8 original CRC guest plan; inert until exact reviewed root GO."""
from pathlib import Path
import hashlib,json,os,sys,re,stat,subprocess,signal,time,threading,selectors,importlib.util
D=Path(__file__).resolve().parent;H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):
 p=Path(p);need(p.parent==D/'run-outputs','fixed output namespace')
 b=(json.dumps(v,indent=2)+'\n').encode();need(len(b)<=1048576,'finite metadata receipt')
 temp=p.with_name(p.name+'.new')
 with temp.open('wb',buffering=0)as f:
  view=memoryview(b)
  while view:
   n=f.write(view);need(type(n)is int and 0<n<=len(view),'full metadata write');view=view[n:]
  os.fsync(f.fileno())
 os.replace(temp,p)
 fd=os.open(p.parent,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)

def receipt(p):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink(),'regular nonsymlink');need(0<=s.st_size<=384*1024**2,'bounded file before hash');b=p.read_bytes();s2=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(s2.st_dev,s2.st_ino,s2.st_size,s2.st_mtime_ns),'immutable during hash');return {'bytes':len(b),'sha256':H(b)}
def pin(p,v):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size==v['bytes'],'exact stat before hash');need(receipt(p)=={k:v[k]for k in ['bytes','sha256']},'exact pin');return p
def kseed(b):
 need(0<len(b)<=4194560,'bounded container');m=re.match(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)\n',b);need(m is not None,'KSEED header');end=b.find(b'\n\n',m.end());need(end>=0,'export terminator');rows=b[m.end():end].split(b'\n');need(len(rows)==int(m[2])<=64,'export count');exports=[]
 for row in rows:
  z=row.split(b' ');need(len(z)==3 and re.fullmatch(rb'[A-Za-z_][A-Za-z0-9_.!?/-]*',z[0])and z[1].isdigit()and z[2].isdigit(),'export row');exports.append((z[0].decode(),int(z[1]),int(z[2])))
 payload=b[end+2:];need(0<len(payload)<=4194304 and len(payload)==int(m[1])and len({z[0]for z in exports})==len(exports)and all(0<=off<len(payload)and off%4==0 and ar<=16 for _,off,ar in exports),'whole payload/exports');return payload,exports
FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
PAT=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in FIELDS)+'}\n').encode())
def counters(b):
 m=PAT.fullmatch(b)
 if not m or any(len(x)>20 for x in m.groups()):return {'status':'unavailable-or-invalid','values':None,'entireStderrIsCounterLine':False}
 u=dict(zip(FIELDS,map(int,m.groups())));valid=all(0<=x<2**64 for x in u.values())and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items']and u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
 return {'status':'valid'if valid else'invalid','values':u,'entireStderrIsCounterLine':True}

def emission_guard(ep,xp,ec,pr):
 need(ep['status']==pr['acceptedEmissionProofStatus'] and ep['independent'] is True,'exact repaired emission proof')
 need(ep['wholeObservedUnobservedKSEEDSHA256']==pr['onContainer']['sha256'] and ep['oldBuild8StillFailed'] is True and ep['savedCalls']==7 and ep['completionAbsent'] is True,'saved repair does not complete old build8')
 need(ep['recomputedSelectedEmission']['selectedSite']==220 and ep['recomputedSelectedEmission']['TCEmitterExecuted'] is True and ep['recomputedSelectedEmission']['guestRuntimeQualified'] is False,'selected saved emission only')
 need(xp['status']==pr['acceptedExtractionProofStatus'] and xp['independent'] is True and xp['completion']==pr['actualExtractionCompletion'],'exact separate extraction proof')
 need(xp['acceptedEmissionProof']==pr['actualEmissionProof'] and xp['extractedNative']==pr['onArtifact'] and xp['savedContainer']==pr['onContainer'],'extraction exact repaired lineage and whole artifacts')
 need(xp['oldBuild8StillFailed'] is True and xp['oldCallsRepeated']==0 and xp['freshExtractionCalls']==1 and xp['guestRuntimeQualified'] is False,'fresh one-call identity only; no old repeat')
 need(ec['status']=='COMPLETE_TC_SAVED_OBSERVER_EXTRACT1_IDENTITY_ONLY' and ec['sourcePinsSHA256']==xp['sourcePinsSHA256'] and ec['rootGOSHA256']==xp['rootGOSHA256'],'exact extraction completion source binding')
 need(ec['acceptedEmissionProof']==pr['actualEmissionProof'] and ec['native']==pr['onArtifact'] and ec['savedContainer']==pr['onContainer'] and ec['exports']==xp['exports'],'complete native/container own exports')
 need(ec['oldBuild8StillFailed'] is True and ec['oldCallsRepeated']==0 and ec['freshExtractionCalls']==1 and ec['TCEmitterExecuted'] is False and ec['generatedWorkloadExecuted'] is False,'separate extraction only')

def main(gopath):
 pending=load(D/'preregistration.json');need(pending['status']=='SOURCE_FROZEN_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4_HOLD' and pending['actualEmissionProof']is not None and pending['onArtifact']is not None,'unresolved draft cannot execute')
 gp=Path(gopath);g=load(gp);gh=receipt(gp);pr=load(D/'preregistration.json')
 sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=D/'run-outputs'
 need(set(g)=={'status','maximumLoaderCalls','outputRoot','outerExecution','noRetry','TCEmitterExecutionAuthorized','generatedWorkloadExecutionAuthorized','timingAuthorized','sha256','sourceReviews','memoryPolicyVersion','integrationFixtureProof'},'no unknown GO fields')
 need(set(g['sha256'])=={'run.py','preregistration.json','source-pins.json','input-pins.json'},'exact GO hashes')
 need(all(set(r)=={'path','bytes','sha256'}for r in g['sourceReviews']),'exact review receipt fields')
 need(g['status']=='ROOT_GO_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4_ONLY' and g['maximumLoaderCalls']==8
      and g['outputRoot']==str(O) and g['outerExecution']=='require_escalated'
      and g['noRetry']is True and g['TCEmitterExecutionAuthorized']is False
      and g['generatedWorkloadExecutionAuthorized']is True and g['timingAuthorized']is False,'exact guest8 GO')
 need(g['memoryPolicyVersion']==pr['memoryPolicyVersion'],'explicit diagnostic memory policy v2')
 for name in ['run.py','preregistration.json','source-pins.json','input-pins.json']:
  need(g['sha256'][name]==receipt(D/name)['sha256'],'specific immutable gate '+name)
 need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'root and independent driver SOURCE reviews')
 need(pr['maximumPythonWrapperStarts']==8 and pr['maximumNativeCompilerChildStarts']==0 and pr['maximumNativeGuestChildStarts']==8 and pr['maximumSimultaneousGroupMembers']==2,'finite exec/fork scope')
 need(pr['producer']['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'
      and pr['baseline41SHA256']=='4ed9b5600505c33013c966d266a977a3d4ccd56ad3cdc425b1805acf390b95f3','explicit audited current producer/source')
 need(ip[pr['producer']['path']]=={k:pr['producer'][k]for k in ['bytes','sha256']}
      and ip[pr['loader']['path']]=={k:pr['loader'][k]for k in ['bytes','sha256']},'producer/loader pins in full declared closure')
 extra={}
 def guard():
  need(receipt(gp)==gh,'immutable GO')
  for name in ['run.py','preregistration.json','source-pins.json','input-pins.json']:
   need(receipt(D/name)['sha256']==g['sha256'][name],'immutable registry/driver')
  need(len(ip)<=pr['maximumInputFiles'] and sum(v['bytes']for v in ip.values())<=pr['maximumInputLogicalBytes'],'closure admission')
  for path,v in ip.items():pin(path,v)
  for name,v in sp.items():pin(D/name,v)
  for path,v in extra.items():pin(path,v)
  for r in g['sourceReviews']:
   q=load(pin(r['path'],r));need(q['status']=='PASS_SOURCE_ONLY_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4'
      and q['sourcePinsSHA256']==g['sha256']['source-pins.json']
      and q['driverSHA256']==g['sha256']['run.py'],'specific reviewed driver')
  pp=load(pr['actualProducerProof']);need(pp['status']==pr['actualProducerProofStatus'],'actual stage0 producer proof')
  need(pp['wholeBaselineNative']=={k:pr['producer'][k]for k in ['bytes','sha256']} and pp['currentProducerBindingQualified']is True and pp['TCEmitterExecuted']is False,'accepted current producer binding; no prior TC claim')
  pc=load(pin(pr['currentProducerCompletion']['path'],pr['currentProducerCompletion']))
  need(pc['status']=='COMPLETE_CURRENT_TYPED_BIND8_READONLY_IDENTITY_ONLY' and pc['images'][0]['native']==pr['producer'] and pc['sourcePinsSHA256']==pp['sourcePinsSHA256'],'current native/source completion')
  pin(pr['currentTypedBinding']['path'],pr['currentTypedBinding']);pin(pr['currentOriginalNative']['path'],pr['currentOriginalNative'])
  ep=load(pin(pr['actualEmissionProof']['path'],pr['actualEmissionProof']))
  xp=load(pin(pr['actualExtractionProof']['path'],pr['actualExtractionProof']))
  ec=load(pin(pr['actualExtractionCompletion']['path'],pr['actualExtractionCompletion']))
  emission_guard(ep,xp,ec,pr)
  old=load(pin(pr['oldBuild8FailureProof']['path'],pr['oldBuild8FailureProof']));need(old['status']=='PASS_INDEPENDENT_SAVED_FAILURE_TC_CURRENT_EMITTED_CALLS7_ONLY' and len(old['savedCalls'])==7,'preserved seven-call failure')
  for field in ['offArtifact','offContainer','onArtifact','onContainer']:pin(pr[field]['path'],pr[field])
  need(pr['offArtifact']==pc['products'][0]['native'] and pr['offContainer']==pc['products'][0]['container'],'actual OFF original CRC identity')
  lp=load(pr['actualLoaderProof']);need(lp['status']==pr['actualLoaderProofStatus']
      and lp['loader']==pr['loader'],'actual existing loader identity')
  fq=load(pin(pr['qualifiedMemoryFixtureProof']['path'],pr['qualifiedMemoryFixtureProof']))
  need(fq['status']==pr['qualifiedMemoryFixtureProofStatus']and fq['acceptedSamples']==8 and fq['memberCounts']==[1,1,2,2,2,2,1,1]and fq['normalClosureEstablishedForFixedFixture']is True and fq['hardMemoryCapEstablished']is False and fq['native8Authorized']is False,'accepted limited fixed fixture only')
  fc=load(pin(pr['qualifiedMemoryFixtureCompletion']['path'],pr['qualifiedMemoryFixtureCompletion']));need(fc['status']=='COMPLETE_OWNED_GROUP_MEMORY_ADAPTER_QUALIFICATION_ONLY','exact fixture completion')
 guard()
 fp=g['integrationFixtureProof'];need(set(fp)=={'path','bytes','sha256'},'exact integrated fixture receipt')
 fixture=load(pin(fp['path'],fp));need(fixture['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','qualified limited transfer/controller fixture required')
 need(fixture['captureSHA256']==sp['capture.py']['sha256'] and fixture['integrationSHA256']==sp['integration.py']['sha256'] and fixture['controllerSHA256']==sp['controller.py']['sha256'],'fixture exact current component bindings')
 extra[fp['path']]={k:fp[k]for k in ['bytes','sha256']}
 guard();need(pr['qualifiedMemoryFixtureProof']is not None,'accepted actual fixture proof required')
 fq=load(pin(pr['qualifiedMemoryFixtureProof']['path'],pr['qualifiedMemoryFixtureProof']));need(fq['status']==pr['qualifiedMemoryFixtureProofStatus'],'accepted exact actual memory fixture')
 spec=importlib.util.spec_from_file_location('pinned_memory_adapter',D/'adapter.py');memoryModule=importlib.util.module_from_spec(spec);spec.loader.exec_module(memoryModule)
 guard();need(not O.exists(),'fresh no retry output');O.mkdir();rows=[];images=[];ok=False
 env=dict(pr['environment']);need(len(env)==17 and 'KEXE_COMMAND'not in env and 'KEXE_CAP_RESOURCES_35'not in env and env['KEXE_STRUCTURED_REPORT']=='1'and env['KEXE_RESULT_TYPE']=='i64'and env['KEXE_FUEL']=='1000000','exact guest17 no filesystem grant')
 save(O/'effective-environment.json',env);save(O/'attempts.json',rows)
 def capture(path,maximum):
  path=Path(path);need(path.is_file()and not path.is_symlink()and 0<path.stat().st_size<=maximum,'artifact bound')
  extra[str(path)]=receipt(path);save(O/'generated-pins.json',extra);return dict(path=str(path),**extra[str(path)])
 def call(label,nativeArgv,producer):
  guard()
  c=next(c for c in pr['cases']if c['label']==label);need(nativeArgv==c['nativeArgv'] and producer==nativeArgv[1],'exact frozen guest argv')
  spec=importlib.util.spec_from_file_location('pinned_native_call',D/'native-call.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module.call(D,O,pr,c,rows,save)
 try:
  rb=(D/'validate-runtime.py').read_bytes();need(H(rb)==sp['validate-runtime.py']['sha256'],'exact runtime decoder source')
  rn={'__file__':str(D/'validate-runtime.py'),'__name__':'pinned_runtime_decoder'};exec(compile(rb,str(D/'validate-runtime.py'),'exec'),rn)
  globals()['parse_report']=rn['parse_report'];globals()['observe_report']=rn['observe_report']
  # Resolve exports from each accepted complete container; never reuse OFF offsets for ON.
  for arm,field in [('OFF','offContainer'),('ON','onContainer')]:
   payload,exports=kseed(Path(pr[field]['path']).read_bytes());native=pr['offArtifact']if arm=='OFF'else pr['onArtifact']
   need(Path(native['path']).read_bytes()==payload,'whole native equals its complete container payload')
   for c in pr['cases']:
    if c['arm']==arm:need([(off,ar)for sym,off,ar in exports if sym==c['symbol']]==[(c['offset'],1)],'actual symbol offset/arity for own arm')
  results=[]
  for c in pr['cases']:
   prod=pr['offArtifact']if c['arm']=='OFF'else pr['onArtifact']
   result=call(c['label'],c['nativeArgv'],prod['path']);results.append(result)
   save(O/'guest-results.json',results);capture(O/'guest-results.json',1048576)
   if c['arm']=='ON':
    off,on=results[-2:];need(off['case']['arm']=='OFF' and off['case']['symbol']==on['case']['symbol'] and off['case']['argument']==on['case']['argument'],'adjacent exact paired case')
    need(off['report']==on['report'] and off['rawStdoutSHA256']==on['rawStdoutSHA256'] and off['rawStderrSHA256']==on['rawStderrSHA256'] and off['arena']==on['arena'] and off['returncode']==on['returncode']==0,'exact OFF/ON result/fuel/heap arenas/rawstream/normalexit')
  need(len(rows)==8 and len(results)==8 and all(r['state']=='terminal'for r in rows),'all eight guests closed')
  completion={'status':'COMPLETE_CURRENT_ORIGINAL_TC_GUEST8_CAPTURE_SEMANTIC_DIAGNOSTIC_ONLY','currentProducer':pr['producer'],'OFF':pr['offArtifact'],'ON':pr['onArtifact'],'actualEmissionProof':pr['actualEmissionProof'],'actualExtractionProof':pr['actualExtractionProof'],'actualExtractionCompletion':pr['actualExtractionCompletion'],'oldBuild8FailureProof':pr['oldBuild8FailureProof'],'sourcePinsSHA256':g['sha256']['source-pins.json'],'rootGOSHA256':gh['sha256'],'pairedCases':4,'selectedSiteGuestReach':'source-bound checksum via prefix-crc positive stop and bench1; selected physical site220 required by prior audited emission','generatedWorkloadExecuted':True,'fuelTrapStressQualified':False,'full256CandidateReachQualified':False,'prefixSentinelQualified':False,'fallbackAndFADDRQualified':False,'capsRollbackQualified':False,'fixedPointQualified':False,'original19Qualified':False,'performanceQualified':False,'OSStackLimitProof':False,'hardMemoryCapEstablished':False}
  completion['strictOldMemoryPolicyPassed']=all(r['strictOldMemoryPolicyPassed']for r in results)
  completion['memoryPolicyVersion']=pr['memoryPolicyVersion']
  completion['memoryObservations']=[r['memoryObservation']for r in results]
  completion['nativeControllerFixtureProof']=fp
  ok=True
 except BaseException as ex:
  save(O/'failure.json',{'status':'FAIL_FIRST_FAILURE_NO_RETRY','exception':repr(ex),'attemptedCalls':len(rows)});raise
 finally:
  save(O/'terminal.json',{'attemptedCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok,'noRetry':True})
 if ok:
  need(len(rows)==8 and all(r['state']=='terminal'for r in rows),'valid-last all eight closed')
  completion['terminal']=capture(O/'terminal.json',1048576)
  completion['attempts']=dict(path=str(O/'attempts.json'),**receipt(O/'attempts.json'))
  completion['generatedPins']=dict(path=str(O/'generated-pins.json'),**receipt(O/'generated-pins.json'))
  guard();save(O/'completion.json',completion)
if __name__=='__main__':need(len(sys.argv)==2,'exact reviewed root GO required');main(sys.argv[1])
