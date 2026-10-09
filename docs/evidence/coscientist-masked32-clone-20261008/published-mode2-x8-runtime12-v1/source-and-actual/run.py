"""Inert SOURCE. Published x8 statemate/vector runtime12 only after exact two reviews and GO."""
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

def loader_protocol(pr):
 v=load(pin(pr['loaderSupervisorProtocolView']['path'],pr['loaderSupervisorProtocolView']))
 need(v['status']=='SOURCE_PROTOCOL_VIEW_ONLY_NOT_DYNAMIC_PROCESS_PROOF'and v['OSClosureTraceQualified']is False and v['universalCompilerProof']is False,'conditional loader protocol only')
 need(len(v['pins'])==4,'fixed protocol four owners')
 for r in v['pins']:pin(r['path'],r)
 cs,build,loader,wrapper=v['pins'];bp=load(build['path'])
 need(cs['sha256']=='f44b50995a0e45db4be35244da34dd61538a484c7d5ea2f15f7f5a73d9daa8c3'and build['sha256']=='5f7c433cf349362457887d0bdc01eb31b4e96413de2efe9a83b669675bcd6484'and loader==pr['loaderArtifact']and wrapper['sha256']=='dfd2317a7381e5e6b8c8f5db24e3f46085736295302b7b810cd0278a6289cedf','loader source/build/binary protocol identity')
 need(bp['status']==v['savedBuildProofStatus']=='PASS_INDEPENDENT_ACTUAL_SOURCE_BOUND_DIAGNOSTIC_LOADER16_BUILD_IDENTITY_ONLY'and bp['CSourceSHA256']==cs['sha256']and bp['loader']==loader,'saved loader source-to-binary correspondence')
 lines=Path(cs['path']).read_text().splitlines(keepends=True)
 for span in v['spans']:
  text=''.join(lines[span['start']-1:span['end']]);need(text==span['text']and hashlib.sha256(text.encode()).hexdigest()==span['sha256'],'exact conditional supervisor source spans')
 need(pr['zeroCapabilityGrants']=='-'and len(pr['environment'])==17 and not any(k.startswith('KEXE_CAP_')or k in ['KEXE_SPAWN_ENV','KEXE_SPAWN_PATH_LOOKUP','KEXE_GPU_VULKAN']for k in pr['environment']),'zero brokers source premises')
 return True

def source_scope(pr):
 loader_protocol(pr)
 off=load(pin(pr['OFFActualProof']['path'],pr['OFFActualProof']));cp=load(pin(pr['CandidateCompilerActualProof']['path'],pr['CandidateCompilerActualProof']));oracle=load(pin(pr['C95Oracle']['path'],pr['C95Oracle']));ep=load(pin(pr['EmittedAssociationProof']['path'],pr['EmittedAssociationProof']))
 need(off['status']==pr['OFFActualProofStatus']and off['currentBaselineNative']['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'and off['current16BaselineSource']['sha256']=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418','current OFF lineage, no LC substitute')
 need(cp['status']==pr['CandidateCompilerActualProofStatus']and cp['closedCompilerCalls']==6 and cp['stageClobberCertificateQualified']is False and cp['candidateAdoptionQualified']is False and cp['guestRuntimeExecuted']is False,'saved candidate compiler artifact identity only')
 need(ep['status']==pr['EmittedAssociationProofStatus']and ep['qualification']=={'conditionalSavedWordAssociationOnly':True,'fullMachineGPRClobber':False,'actualTypedMode2Admission':False,'fullVectorNonfuelSemantics':False,'guestRuntime':False,'full19Functional':False,'performance':False,'candidateAdoption':False},'word association remains machine certificate HOLD')
 for k in ['subjectReport','subjectFreeze']:need(ep[k]=={j:pr[k][j]for j in ['bytes','sha256']},'exact associated subject');pin(pr[k]['path'],pr[k])
 completion=load(pin(cp['completion']['path'],cp['completion']));need(completion['fixtureSource']==pr['fixtureSource']and completion['unchangedStatemateSource']==pr['statemateEntry']['source']and completion['candidateActualProof']==cp['candidateActualProof'],'compiled source identity')
 matrix=load(pin(pr['canonicalMatrix']['path'],pr['canonicalMatrix']));m=next(e for e in matrix['entries']if e['workload']=='statemate');need(pr['statemateEntry']=={'workload':'statemate','source':{'path':'/Users/junkawasaki/github/wt/amu-seed17/bench/embench/batch-ports/statemate.kotoba','bytes':59847,'sha256':'977d840bc3beee78ff8fcc43fd5c34bdb786b65da494c5926a4745515cc0bf44'},'symbol':'batch','iterations':[0,1,2,17,32]}and m['expectedSourceSha256']==pr['statemateEntry']['source']['sha256']and m['symbol']=='batch'and m['iterations']==[0,1,2,17,32],'unchanged original source/symbol/profiles')
 os=next(e for e in off['joinedOriginal19Images']if e['workload']=='statemate');arts=cp['wholeArtifactsAndOwnExports'];need(pr['images']=={'statemate':{'OFF':os,'ON':arts[2]},'vector-fixture':{'OFF':arts[0],'ON':arts[1]}},'whole four saved artifact owners')
 need(pr['fixtureSource']['sha256']=='aa3feb907fe7533d76b485d8ade164100b8a70e232e750f874a724d91d6562dd','exact synthetic fixture')
 need(oracle['status']==pr['C95OracleStatus']and pr['C5StatemateRows']==[r for r in oracle['rows']if r['workload']=='statemate']and len(pr['C5StatemateRows'])==5,'saved C result-only oracle')
 expected=[]
 from loader_grammar import interpretation
 for work,n in [('statemate',n)for n in [0,1,2,17,32]]+[('vector-fixture',1)]:
  for arm in ['OFF','ON']:
   c=pr['cases'][len(expected)];im=pr['images'][work][arm];symbol='batch'if work=='statemate'else'bench';src=pr['statemateEntry']['source']if work=='statemate'else pr['fixtureSource'];answer=next(r['result']for r in pr['C5StatemateRows']if r['n']==n)if work=='statemate'else 3
   need(c['label']==work+'-'+arm+'-n'+str(n)and c['workload']==work and c['arm']==arm and c['profile']==n and c['symbol']==symbol and c['source']==src and c['expectedResult']==answer and type(c['expectedResult'])is int and c['arity']==1,'fixed source/profile/arm/result')
   need(c['native']==im['native']and c['container']==im['container'],'whole native/container receipt');payload,exports=container(pin(c['container']['path'],c['container']).read_bytes());need(payload==pin(c['native']['path'],c['native']).read_bytes()and (symbol,c['offset'],1)in exports,'actual own export payload/arity')
   need(c['nativeArgv']==[pr['loader'],c['native']['path'],str(c['offset']),'1','aarch64','-',str(n)]and interpretation(c['nativeArgv'])=={'typedI64':[n],'guestArgv':None,'effectiveArgc':7},'runtime typed i64 no -- or compiler guestargv');expected.append(c)
 need(len(expected)==len(pr['cases'])==12 and pr['maximumLoaderCalls']==12 and pr['guestFuelPerCall']==16777216 and len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='16777216'and pr['zeroCapabilityGrants']=='-','12 calls original runtime contract')
 need(pr['guestArenaCaps']=={'pairs':2097152,'string-pool-bytes':65536,'vectors':4096,'vector-items':65536}and pr['environment']=={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':pr['freshOutputRoot'],'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_PAIRS':'2097152','KEXE_VECTOR_ITEMS':'65536','KEXE_CPU_SECONDS':'30','KEXE_WALL_SECONDS':'30','KEXE_FUEL':'16777216','KEXE_ARENA_USE':'1','PYTHONNOUSERSITE':'1','KEXE_STRUCTURED_REPORT':'1','KEXE_RESULT_TYPE':'i64'},'exact original arena and17 environment values')
 need(pr['operationalEnvironment']=={'version':'host-authorized-loader-owned-sandbox-v1','requiresOuterHostEscalation':True,'loaderOwnedSandboxRequired':True,'loaderSandboxWeakeningAuthorized':False,'hostEscalationDeclarationIsNotKernelMeasurement':True}and pr['C2']is False and pr['timingAuthorized']is False and pr['generalCandidateAdoptionQualified']is False and pr['fullClobberCertificateQualified']is False and pr['actualTypedMode2AdmissionObserved']is False,'prospective diagnostic only; general HOLD')
 return True

def go_header(g,pr,O):
 proofKeys=['OFFActualProof','CandidateCompilerActualProof','C95Oracle','C95OracleProof','integrationFixtureProof','EmittedAssociationProof']
 need(set(g)==set(['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews']+proofKeys),'exact GO keys')
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==12 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is True and g['C2']is False and g['outerHostLaunchRequiresEscalation']is True,'exact runtime12 only under declared host profile')
 return proofKeys

def main(goPath):
 import time
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);rows=[];results=[];generated={};ok=False
 proofKeys=go_header(g,pr,O)
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'exact GO identity')
 need(len(g['sourceReviews'])==2 and len(set(r['path']for r in g['sourceReviews']))==2,'two exact distinct reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'exact reviewed SOURCE')
 for k in proofKeys:
  target='qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k;need(g[k]==pr[target],'exact proof identity');pin(g[k]['path'],g[k])
 f=load(g['integrationFixtureProof']['path']);need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','actual component fixture scope')
 for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'qualified unchanged components')
 op=load(pr['C95OracleProof']['path']);need(op['status']==pr['C95OracleProofStatus']and op['oracle']==pr['C95Oracle'],'C oracle result-only scope')
 def guard():
  need(receipt(gp)==gr and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256'],'immutable GO/input registries')
  need(len(ip)==pr['inputFiles']<=256 and sum(r['bytes']for r in ip.values())==pr['inputLogicalBytes']<=33554432,'bounded targeted closure')
  for n,r in sp.items():pin(D/n,r)
  for p,r in ip.items():pin(p,r)
  for p,r in generated.items():pin(p,r)
  source_scope(pr)
 guard();need(not O.exists(),'fresh namespace');O.mkdir();save(O/'attempts.json',rows);save(O/'effective-environment.json',pr['environment']);save(O/'generated-pins.json',generated)
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);deadline=time.monotonic()+820
 try:
  for index,c in enumerate(pr['cases'],1):
   guard();need(time.monotonic()+60<=deadline,'finite original per-call deadlines before new child')
   seal={k:c[k]for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};seal.update(format=pr['invocationSealVersion'],index=index,rootGO=dict(path=str(gp),**gr),sourcePinsSHA256=g['sourcePinsSHA256'],preregistrationSHA256=g['preregistrationSHA256']);p=O/(c['label']+'.admission.json');need(not p.exists(),'fresh single invocation seal');save(p,seal);need(p.stat().st_size<=4096,'bounded seal');p.chmod(0o444);sr=receipt(p);generated[str(p)]=sr;save(O/'generated-pins.json',generated)
   r=mod.call(D,O,pr,c,rows,save,sr['sha256']);results.append(r);save(O/'results.json',results)
   if index%2==0:
    a,b=results[-2:];need(all(a['report'][k]==b['report'][k]for k in ['result','fuelInitial','fuelRemaining','fuelConsumed','arena17']),'paired original result/fuel/17arena parity')
  guard();need(len(rows)==len(results)==12 and all(r['state']=='terminal'and r['returncode']==0 for r in rows),'12 new closed runtime children');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed']and not terminal['failure'],'durable terminal before COMPLETE')
 evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['terminal.json','attempts.json','generated-pins.json','results.json','effective-environment.json']};save(O/'report.json',{'status':'COMPLETE_PUBLISHED_MODE2_X8_STATEMATE_VECTOR_RUNTIME12_DIAGNOSTIC_ONLY','runtimeCalls':12,'statemateOriginalProfiles':[0,1,2,17,32],'statematePairs':5,'vectorFixturePairs':1,'results':results,'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'evidence':evidence,'CandidateCompilerActualProof':g['CandidateCompilerActualProof'],'EmittedAssociationProof':g['EmittedAssociationProof'],'C95Oracle':g['C95Oracle'],'C95FuelArenaAvailable':False,'C95FuelArena':None,'full19FunctionalQualified':False,'generalCandidateAdoptionQualified':False,'fullClobberCertificateQualified':False,'actualTypedMode2AdmissionObserved':False,'performanceQualified':False,'hardPeakQualified':False,'strictPhysicalMemoryQualified':False,'new12StrictSampledPolicyPassed':all(r['strictOldMemoryPolicyPassed']for r in results),'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact root GO');main(sys.argv[1])
