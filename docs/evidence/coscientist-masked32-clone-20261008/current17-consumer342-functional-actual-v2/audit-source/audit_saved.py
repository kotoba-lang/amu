"""Inert saved-only auditor. No child, FD, thread, kernel or network operations.
Explicit mappings point to already collected regular files. Main creates only a
fresh audit directory. No PASS is produced before all342 saved closures pass.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,stat,sys,copy,struct
SOURCE=Path('/Users/junkawasaki/github/workspaces/codex/current17-consumer-qualify342-source-v2-20261009-dense')
EXPECTED={'source-pins.json':'6a78c235d423736bd170853ce4776db17fa8732f0ea460be307df3d529b3a9e1','input-pins.json':'7454891786ad19795420801d654842dd93e544378707b27fd59c7dcfdcba872f','run.py':'53cc44ac4201ce5d6abe920c6f1cd34de769c40c61522142eca394b868da588f','preregistration.json':'58bbf0aeebcdff725d8bf08d8cf1cdd9c14cf78ef5be77229e0de3398dd5afc4'}
def need(x,m):
 if not x:raise AssertionError(m)
def unique(pairs):
 d={}
 for k,v in pairs:need(k not in d,'duplicate JSON key');d[k]=v
 return d
def digest(b):return hashlib.sha256(b).hexdigest()
def read(p,cap=16777216):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and 0<=s.st_size<=cap,'bounded regular saved file:'+str(p));b=p.read_bytes();z=p.lstat();need((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stable saved bytes');return b
def receipt(p):b=read(p);return dict(path=str(p),bytes=len(b),sha256=digest(b))
def metadata(p):return json.loads(read(p),object_pairs_hook=unique)
def save(p,q):p.write_text(json.dumps(q,indent=2)+'\n')
class Saved:
 def __init__(self,mappings):
  need(type(mappings)is list and mappings,'explicit remote-to-saved mappings');self.maps=[];self.checked={}
  for v in mappings:
   need(set(v)=={'recordedPrefix','savedPrefix'},'exact mapping fields');r=PurePosixPath(v['recordedPrefix']);s=Path(v['savedPrefix']);need(r.is_absolute()and'..'not in r.parts and s.is_absolute()and'..'not in s.parts,'absolute safe mapping');self.maps.append((r,s))
  need(len({str(r)for r,s in self.maps})==len(self.maps),'no ambiguous same-prefix mapping');self.maps.sort(key=lambda z:len(z[0].parts),reverse=True)
 def path(self,p):
  q=PurePosixPath(p);need(q.is_absolute()and'..'not in q.parts,'recorded path grammar')
  for r,s in self.maps:
   try:return s/str(q.relative_to(r))
   except ValueError:pass
  raise AssertionError('unmapped recorded evidence path:'+str(p))
 def raw(self,p,cap=16777216):
  local=self.path(p);b=read(local,cap);self.checked[str(p)]=dict(savedPath=str(local),bytes=len(b),sha256=digest(b));return b
 def pin(self,r,cap=16777216):
  b=self.raw(r['path'],cap);need((len(b),digest(b))==(r['bytes'],r['sha256']),'exact recorded receipt:'+r['path']);return b
 def load(self,p):return json.loads(self.raw(p),object_pairs_hook=unique)
def memory(o,a,rows,out,err,bindings,invocation):
 need(o['semanticQualification']is True and o['sampleReceiptPersistenceQualified']is True,'semantic+durable sampler admission');m=o['memoryAdmissionRecord'];cap=o['capture'];leader=a['pid'];child=next(p for p in bindings if p!=leader)
 for k in ['heldOwnershipQualified','exactHeldChildWait0','acceptedLeaderBirthBound','completePipeEOF','stoppedClosedCapture','withinOriginalDeadline','groupAuthorityRetired','loaderWaitProtocolPinned']:need(m[k]is True,'memory record '+k)
 need(m['initialHeldSamples']==2 and m['otherRefusals']==[]and m['rawTruncated']is False and m['captureErrors']==[]and m['exactDirectChildWait']=='closed0'and m['waitUncertain']is False and m['groupOperationsAfterWait']==m['groupOperationsAfterUncertainty']==0,'record refusal/retirement boundary')
 need(cap['EOF']=={'stdout':True,'stderr':True}and cap['completeRaw']is True and cap['stoppedWriter']is True and cap['semanticDecodeAuthorized']is True and cap['ownershipDecision']=='worker-granted'and cap['errors']==[]and cap['dropped']=={'stdout':0,'stderr':0},'complete stopped capture')
 need(cap['hashes']=={'stdout':a['stdout'],'stderr':a['stderr']}and cap['retained']=={'stdout':len(out),'stderr':len(err)}and cap['observedBytes']==len(out)+len(err),'complete raw capture accounting')
 need(2<=len(rows)<=2048 and len(rows)==a['memorySamples']==o['sampleCount']==m['acceptedSamples']and o['directChildWait']=='closed0'and o['waitUncertain']is False,'exact finite durable sample count')
 last=-1;maximum=0;sampled=set()
 for i,q in enumerate(rows,1):
  need(type(q)is list and len(q)==4 and q[0]==i and type(q[1])is int and last<q[1]<2**64 and q[2]==leader and 1<=len(q[3])<=2,'ordered numeric sample');last=q[1];known={}
  for p,b,f in q[3]:need(all(type(x)is int for x in [p,b,f])and p in bindings and b==bindings[p]and 0<p<2**31 and 0<b<2**64 and 0<=f<2**64 and p not in known,'known unique PID birth footprint');known[p]=b;sampled.add(p)
  need(known.get(leader)==bindings[leader]and(i!=1 or set(known)=={leader})and(i!=2 or set(known)=={leader,child}),'held initial two births');total=sum(v[2]for v in q[3]);need(total<=4294967296,'sampled soft footprint');maximum=max(maximum,total)
 ev=o['controllerEvents'];need(len(ev)<=4096 and ev.count('wait-enter')==1 and ev.count('retire:owned-child-exit-before-reap-ACK')==1,'retire before held child reap');first=next(i for i,x in enumerate(ev)if x.startswith('retire:'));need('group-operation'not in ev[first+1:]and ev.index('wait-enter')>first,'no group operation after retirement/wait')
 failure=m['failure']
 if failure is None:
  need(o['status']=='COMPLETE_HELD_LAUNCH_SEMANTIC_SAMPLED_MEMORY'and o['strictHeldSamplingPolicyPassed']is True and cap['firstFailure']is None and ev.count('group-operation')==len(rows),'strict finite sampler')
 else:
  need(o['status']=='HELD_LAUNCH_SEMANTIC_TERMINATION_GAP'and o['strictHeldSamplingPolicyPassed']is False and m['freshKnownFailureVerified']is True and cap['firstFailure']in [None,'sampling-uncertainty'],'only admitted diagnostic gap')
  need(ev.count('group-operation')==len(rows)+1,'one failed source-bound sample operation');need(failure['typedOrigin']=='fresh-owned-group-api-v1'and failure['contextVersion']=='owned-group-sampling-failure-context-v1'and failure['invocation']==invocation and type(failure['queryOrdinal'])is int and failure['queryOrdinal']>0,'persisted current API origin');pid=failure['pid'];stage=failure['stage'];need(pid in bindings and pid in sampled,'failure previously birth-bound')
  need((stage=='leader-getpgid'and pid==leader)or(stage in {'member-getpgid','member-rusage'}and pid in bindings),'owned fault stage');need((failure['errno']==3 and failure['failureClass']in {'kernel-oserror','kernel-failed-return'})or(failure['errno']==0 and failure['failureClass']=='kernel-observed-exited'and failure['observedBirth']==bindings[pid]and type(failure['observedExit'])is int and failure['observedExit']>0),'explicit owned termination context')
 from integration import classify_memory
 need(o['memoryObservation']==classify_memory(m),'classification exact; gap unavailable not zero');return maximum,failure is None

def audit(go_path,mapping_path,outdir):
 need(not outdir.exists(),'fresh audit destination');outdir.mkdir();sv=Saved(metadata(mapping_path));g=metadata(go_path);gr=receipt(go_path);root=Path(g['taskRoot']);O=str(root/'consumer-qualification-v2-outputs');pr=metadata(SOURCE/'preregistration.json');sp=metadata(SOURCE/'source-pins.json');ip=metadata(SOURCE/'input-pins.json');recordedGO=sv.load(O+'/report.json')['rootGO'];need({k:recordedGO[k]for k in ('bytes','sha256')}=={k:gr[k]for k in ('bytes','sha256')},'saved GO copy identity');sv.pin(recordedGO);gr=recordedGO
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:need(digest(read(SOURCE/n))==g[k]==EXPECTED[n],'frozen source/GO binding')
 for n,r in sp.items():need((len(read(SOURCE/n)),digest(read(SOURCE/n)))==(r['bytes'],r['sha256']),'SOURCE pin');sv.pin(dict(path=str(root/'source/current17-qualification-v2'/n),**r))
 for n,r in ip.items():sv.pin(dict(path=str(root/n),**r))
 sys.dont_write_bytecode=True;sys.path.insert(0,str(SOURCE));import run,prepare,qualification,ownership,header
 need(run.validate_scope(pr,ip)and set(g)==run.GO_KEYS and g['status']==pr['qualifyGOStatus']and g['maximumLoaderCalls']==342 and g['runtimeGuestAuthorized']is True and g['timingAuthorized']is False and g['noRetry']is True and g['C2']is False,'exact independent qualifier GO')
 need(len(g['sourceReviews'])==2 and len({v['path']for v in g['sourceReviews']})==2,'two distinct source reviews')
 for v in g['sourceReviews']:
  q=json.loads(sv.pin(v),object_pairs_hook=unique);need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'exact SOURCE review')
 packet=copy.deepcopy(metadata(SOURCE/'packet.json')['entries']);cproof={};cdescs={};consumers={}
 for row in packet:
  w=row['workload'];row['source']['path']=str(root/'sources/kotoba'/f'{w}.kotoba');sv.pin(row['source'])
  for arm in ['OFF','ON']:
   row[arm]['native']['path']=str(root/'inputs'/w/(arm+'.bin'));row[arm]['container']['path']=str(root/'inputs'/w/(arm+'.kseed'));payload,exports=run.container(sv.pin(row[arm]['container']));need(payload==sv.pin(row[arm]['native'])and(row['symbol'],row[arm]['offset'],1)in exports,'whole own container/export')
 for v in g['C19Proofs']:
  q=json.loads(sv.pin(v),object_pairs_hook=unique);w=q['workload'];row=next(z for z in packet if z['workload']==w);need(w not in cproof and q['status']=='PASS_INDEPENDENT_FRESH_CURRENT19_C_BUILD_SOURCE_IDENTITY_ONLY'and q['symbol']==row['symbol']and q['bridgeABI']=='I64_8ARGS'and q['artifact']['path']==str(root/'C-build-outputs'/w/'c.dylib'),'actual own C proof');sv.pin(q['artifact']);cproof[w]=q;cdescs[w]=v
 need(len(cproof)==19,'all19 C proofs')
 for v in g['consumerProofs']:
  q=json.loads(sv.pin(v),object_pairs_hook=unique);w=q['workload'];row=next(z for z in packet if z['workload']==w);need(w not in consumers and q['status']=='PASS_INDEPENDENT_FRESH_CURRENT17_CONSUMER_BUILD_SOURCE_IDENTITY_ONLY'and q['symbol']==row['symbol']and q['consumerABI']=='ARM_n_calls_warmup_5ARGV_V1','actual own consumer proof');need(q['consumerBuildSourcePinsSHA256']=='514bbfffffb4718e3a175989001ece4e9da39ad3770c6424347ebe252f71a6ba'and q['consumerSourcePinsSHA256']=='a0d2bed0535e7cf2e9fd6d277303ba99ff1664aff83466989a3c124626ff7699'and q['CProof']==cdescs[w],'own build/source/C lineage');need(q['artifact']['path']==str(root/'consumer-build-outputs'/w/'consumer'),'fresh consumer path');sv.pin(q['artifact'])
  need(q['compileArgv']==['/Library/Developer/CommandLineTools/usr/bin/clang','-std=c11','-O2','-DKEXE_OWNERSHIP_DIAGNOSTIC_V3','-I',str(root/'build'/w),str(root/'source/consumer/timing-loader.c'),'-o',q['artifact']['path'],'-lproc'],'exact own compile argv');generated=header.header(row,sv.pin(row['OFF']['native']),sv.pin(row['ON']['native']),sv.pin(cproof[w]['artifact']),cproof[w]);need(q['generatedHeader']['path']==str(root/'build'/w/'timing-packet-generated.h')and sv.pin(q['generatedHeader'])==generated and sv.raw(str(root/'inputs'/w/'C.dylib'))==sv.pin(cproof[w]['artifact']),'whole generated header/C materialization');consumers[w]=q['artifact']
 need(len(consumers)==19,'all19 actual consumer proofs');cases=prepare.qualification_cases(root,packet,consumers)
 expected=dict(pr);expected.update(qualificationSourcePinsSHA256=g['sourcePinsSHA256'],taskRoot=str(root),freshOutputRoot=O,interpreter=g['hostBinding']['interpreter'],cases=cases,environment=pr['environmentBase']|{'TMPDIR':O},maximumLoaderCalls=342,rootGOStatus=pr['qualifyGOStatus'],invocationSealVersion='current17-consumer342-held-v6-invocation/v2')
 rr=sv.load(O+'/runtime-preregistration.json');need(rr==expected,'entire342 runtime registration');regref=dict(path=O+'/runtime-preregistration.json',bytes=len(sv.raw(O+'/runtime-preregistration.json')),sha256=digest(sv.raw(O+'/runtime-preregistration.json')))
 co=sv.load(O+'/report.json');at=sv.load(O+'/attempts.json');results=sv.load(O+'/results.json');gen=sv.load(O+'/generated-pins.json');term=sv.load(O+'/terminal.json');need(term==dict(consumerCalls=342,allChildrenClosed=True,failure=False)and len(at)==len(results)==len(cases)==342,'all342 exact completion');need(co['status']=='COMPLETE_CURRENT17_CONSUMER342_V2_FUNCTIONAL_DIAGNOSTIC_ONLY'and co['consumerCalls']==342 and co['warmupAndBodyCalls']==741 and co['results']==results and co['rootGO']==gr,'whole report binding')
 for k in ['performanceQualified','officialEmbenchQualified','hardPeakQualified','CfuelArenaAvailable','C2']:need(co[k]is False,'no qualification '+k)
 need(set(co['evidence'])=={'runtime-preregistration.json','terminal.json','attempts.json','generated-pins.json','results.json','effective-environment.json'},'six exact valid-last metadata receipts')
 for n,v in co['evidence'].items():need(v['path']==O+'/'+n,'evidence owner');sv.pin(v)
 need(sv.load(O+'/effective-environment.json')==rr['environment']and len(rr['environment'])==17,'entire17 environment');need(set(gen)=={O+'/runtime-preregistration.json'}|{O+'/'+c['label']+'.admission.json'for c in cases},'registration +342 exact seals')
 for p,r in gen.items():sv.pin(dict(path=p,**r))
 proofs=[];details=[];sampletotal=0;strict=0;pids=set()
 for i,(c,a,r)in enumerate(zip(cases,at,results),1):
  base=O+'/'+c['label'];sealpath=base+'.admission.json';sr=gen[sealpath];seal=json.loads(sv.pin(dict(path=sealpath,**sr)),object_pairs_hook=unique);need(sr['bytes']<=4096 and seal==dict(format=rr['invocationSealVersion'],index=i,case=c,runtimeRegistration=regref,rootGO=gr,sourcePinsSHA256=g['sourcePinsSHA256'],preregistrationSHA256=g['preregistrationSHA256']),'whole invocation seal')
  need(a['index']==i and a['label']==c['label']and a['nativeArgv']==c['nativeArgv']and a['environment']==rr['environment']and a['invocation']==sr['sha256'],'attempt case/env/seal');av=a['argv'];need(av[:3]==[rr['interpreter']['path'],str(root/'source/current17-qualification-v2/launch-wrapper.py'),'--journal-fd']and av[3].isdigit()and int(av[3])>=3 and int(av[3])!=4 and av[4:6]==['--admission-sha',sr['sha256']]and av[6]=='--ownership-fd'and av[7].isdigit()and int(av[7])>4 and int(av[7])!=int(av[3]) and av[8:]==['--',*c['nativeArgv']],'exact wrapper fd/argv')
  need(type(a['pid'])is int and a['pid']>0  ,'owned direct Popen PID');need(a['state']=='terminal'and a['returncode']==0 and a['waitEntered']is True and a['waitUncertain']is False and a['signalingAuthorityRetired']is True and a['captureStopAcknowledged']is True and a['ownershipWriterStopAcknowledged']is True and a['watchdogErrors']==[]and a['failure']is None,'stopped writers/sole wait normal closure')
  raws={}
  for key,suf,cap in [('stdout','stdout',8388608),('stderr','stderr',1048576),('limitJournal','limit-journal.jsonl',65536),('memoryJournal','memory-journal.jsonl',8388608),('ownershipJournal','ownership-journal.jsonl',65536)]:raws[key]=sv.pin(dict(path=base+'.'+suf,**a[key]),cap)
  decoded=qualification.parse(raws['stdout'],raws['stderr'],c,c['expected'],0);report=dict(timing=decoded['timing'],observables=decoded['observables'],arena17=decoded['observables'].get('arena17'),result=decoded['observables']['result']);need(a['structuredReportObservation']==report and a['counterObservation']==dict(status='unavailable-C'if c['arm']=='C'else'valid',values=report['arena17']),'whole case decoder/current expected')
  lj=[json.loads(x,object_pairs_hook=unique)for x in raws['limitJournal'].splitlines()];need(len(lj)==6,'six resource rows');ew=lj[0];keys=sorted(rr['environment']);need(ew==dict(stage='environment-admission',suppliedKeyNames=keys,runtimeExtraKeyNames=ew.get('runtimeExtraKeyNames'),missingKeyNames=[],changedExpectedKeyNames=[],nativeExecKeyNames=keys,nativeExecEnvironmentExact=True)and ew['runtimeExtraKeyNames']in [[],['__CF_USER_TEXT_ENCODING']],'named optional metadata/exact17 native env')
  for k,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',30,31)]):
   b,z=lj[1+2*k:3+2*k];need(set(b)=={'index','limit','stage','before','desired'}and b['index']==k+1 and b['limit']==name and b['stage']=='before'and b['desired']==[soft,hard]and type(b['before'])is list and len(b['before'])==2 and all(type(x)is int and (x==9223372036854775807 or x>=y) for x,y in zip(b['before'],[soft,hard]))and z==dict(index=k+1,limit=name,stage='outcome',outcome='installed',readback=[soft,hard]),'exact unchanged nonraising setter')
  need(lj[-1]==dict(stage='exec-ready',argv=c['nativeArgv'],ASSetterRequested=False,CPUGraceHardSeconds=31),'exact consumer exec-ready')
  own=[json.loads(x,object_pairs_hook=unique)for x in raws['ownershipJournal'].splitlines()];bindings={int(k):v for k,v in a['ownershipBindings'].items()};need(len(bindings)==2 and a['pid']in bindings and len(own)==4,'exact held birth pairs/four durable rows');leader=a['pid'];child=next(p for p in bindings if p!=leader);need((leader,bindings[leader])not in pids,'new invocation direct PID birth identity');pids.add((leader,bindings[leader]));nonce=digest((sr['sha256']+gr['sha256']).encode());stages=[(2,1,0,leader),(4,2,child,child),(6,3,child,child),(8,4,child,child)]
  for j,(stage,seq,wirechild,owner)in enumerate(stages):
   wire=ownership.encode(stage,seq,leader,wirechild,bindings[owner],leader,0,bytes.fromhex(gr['sha256']),bytes.fromhex(nonce));z=own[j];common=dict(pid=owner,birth=bindings[owner],GO=gr['sha256'],nonce=nonce,wireSHA256=digest(wire))
   ex=dict(stage='held-birth-admitted',sequence=seq,leader=leader,**common,guestStillHeld=True)if j<2 else dict(stage='loader-child-exit-held',**common,exit=0,unreapedPIDAnchor=True)if j==2 else dict(stage='loader-child-wait',**common,waitStatus=0,noPostReapGroupQueries=True);need(z==ex,'exact source-bound held wire receipt')
  need(a['childWaitReceipt']==dict(pid=child,birth=bindings[child],exit=0,durable=True),'held child wait0');mem=[json.loads(x,object_pairs_hook=unique)for x in raws['memoryJournal'].splitlines()];need(len(raws['memoryJournal'])==a['memoryJournalBytes']and all(len(x)<=4096 for x in raws['memoryJournal'].splitlines()+raws['ownershipJournal'].splitlines()),'bounded journal byte accounting');maximum,isstrict=memory(a['controllerObservation'],a,mem,raws['stdout'],raws['stderr'],bindings,sr['sha256']);strict+=isstrict;sampletotal+=len(mem)
  reconstructed=dict(label=c['label'],case=c,returncode=0,report=report,arena=report['arena17'],rawStdoutSHA256=a['stdout']['sha256'],rawStderrSHA256=a['stderr']['sha256'],memoryObservation=a['controllerObservation']['memoryObservation'],strictHeldSamplingPolicyPassed=isstrict);need(r==reconstructed,'complete saved result identity')
  rawrefs={key:receipt(sv.path(base+'.'+key))for key in ['stdout','stderr']};proofs.append(dict(status='PASS_INDEPENDENT_CURRENT17_CONSUMER_QUALIFICATION_CHILD_CLOSURE_ONLY',index=i,label=c['label'],nativeArgv=c['nativeArgv'],sourcePinsSHA256=g['sourcePinsSHA256'],invocationSHA256=sr['sha256'],directWaitCount=1,reaped=True,returncode=0,heldChildWait0=True,ownershipBirths=bindings,strictHeldSamplingPolicyPassed=isstrict,typedGapUnavailable=not isstrict,stdout=rawrefs['stdout'],stderr=rawrefs['stderr'],sourceBoundAssertionsNotKernelTrace=True));details.append(dict(index=i,label=c['label'],directPID=leader,childPID=child,samples=len(mem),maximumObservedGroupFootprint=maximum,strict=isstrict,observables=decoded['observables']))
 # Only now all342 full closures succeeded: emit independent percase proofs then narrow verifier.
 childdir=outdir/'child-proofs';childdir.mkdir();descs=[]
 for q in proofs:p=childdir/(str(q['index']).zfill(3)+'.json');save(p,q);descs.append(receipt(p))
 from verify_saved import verify_saved
 narrow=verify_saved(outdir,rr,descs);save(outdir/'decoder-report.json',narrow)
 result=dict(status='PASS_INDEPENDENT_SAVED_CURRENT17_CONSUMER342_V2_FINITE_HELD_CLOSURE_RESULT_FUEL_COUNTER_REPEAT_ONLY',sourcePinsSHA256=g['sourcePinsSHA256'],inputPinsSHA256=g['inputPinsSHA256'],preregistrationSHA256=g['preregistrationSHA256'],driverSHA256=g['driverSHA256'],rootGO=gr,mappings=receipt(mapping_path),cases=342,bodyInvocationsIncludingWarmup=741,heldChildWait0=342,directWait0=342,strictSampledCalls=strict,typedTerminationGapCalls=342-strict,finiteSamples=sampletotal,childProofs=descs,decoderReport=receipt(outdir/'decoder-report.json'),calls=details,checkedSavedPins=sv.checked,reviewerRole='HeldV6 lifecycle mechanism author; independent of Dense qualifier/consumer/C author and root once execution. Saved-data audit only.',limitations=['Source-bound correlated journals and assertions, not independent kernel syscall/scheduling trace or universal WNOWAIT/FD/descendant proof.','45 controlled FD ledger excludes dlopen internal/transient peak; no hard memory peak, general process cleanup or zero-gap inference.','Remote interpreter/tool hashes and source read closures are saved source-bound witnesses if bytes are uncollected; no new host API verification.','C answers only: C fuel/arena unavailable. No timing comparison, official Embench, C2, general ABI/compiler/adoption or CID performance qualification.'],newOperationalCalls=0,performanceQualified=False,hardPeakQualified=False,C2=False)
 save(outdir/'report.json',result);return result

def main():
 need(len(sys.argv)==5 and sys.argv[1]=='--audit-closed','explicit saved-closed audit only: GO mappings fresh-output');out=Path(sys.argv[4]);need(out.is_absolute(),'canonical fresh audit output')
 try:q=audit(Path(sys.argv[2]),Path(sys.argv[3]),out);print(json.dumps(dict(status=q['status'],report=receipt(out/'report.json'))))
 except BaseException as e:
  if out.exists()and not(out/'report.json').exists():save(out/'failure.json',dict(status='FAILED_INDEPENDENT_SAVED342_AUDIT_NO_PASS',error=repr(e),newOperationalCalls=0))
  raise
if __name__=='__main__':main()
