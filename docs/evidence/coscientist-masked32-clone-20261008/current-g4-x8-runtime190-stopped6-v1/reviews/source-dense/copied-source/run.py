"""Inert SOURCE. Current G4 x8 original19 runtime190 only after exact two reviews and GO."""
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
 off=load(pin(pr['OFFActualProof']['path'],pr['OFFActualProof']));actual=load(pin(pr['G4Original19ActualProof']['path'],pr['G4Original19ActualProof']));fp=load(pin(pr['FixedpointActualProof']['path'],pr['FixedpointActualProof']));oracle=load(pin(pr['C95Oracle']['path'],pr['C95Oracle']))
 need(off['status']==pr['OFFActualProofStatus']and off['currentBaselineNative']['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'and off['current16BaselineSource']['sha256']=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418','current OFF lineage')
 need(actual['status']==pr['G4Original19ActualProofStatus']and actual['closedCompilerCalls']==38 and actual['sourcePinsSHA256']=='099f52dbbbd0a09bdb9bec665287785fc7bd42074f98c9410659d230cefe068b','independent saved current G4 original19 artifact proof')
 completion=load(pin(pr['G4Original19Completion']['path'],pr['G4Original19Completion']));need(actual['completion']==pr['G4Original19Completion'],'exact independently checked compile38 completion')
 need(fp['status']==pr['FixedpointActualProofStatus']and fp['G2G3G4WholeNativeEqual']is True and fp['G2G3G4WholeContainerEqual']is True,'exact ownfixedpoint')
 g4=pr['G4Producer'];need(g4['native']['sha256']=='6b410b003a428a40098bdd330539ccf3fef5fdd6d8e9bad23758f941b347462d'and g4['container']['sha256']=='3ebef5afb6b2b7cd826499722dbbbc250c8e71ed54afc893f5124ee8d6f952da','G4 fixedpoint hashes')
 need(next(x for x in fp['wholeArtifactsAndOwnExports']if x['generation']==4)['native']==g4['native']and next(x for x in fp['wholeArtifactsAndOwnExports']if x['generation']==4)['container']==g4['container'],'specific G4 artifacts from current fixedpoint');payload,exports=container(pin(g4['container']['path'],g4['container']).read_bytes());need(payload==pin(g4['native']['path'],g4['native']).read_bytes()and exports==[('main',0,0)],'whole G4 producer main0')
 need(completion['status']=='COMPLETE_PUBLISHED_MODE2_X8_G4_ORIGINAL19_COMPILE38_ARTIFACTS_ONLY'and completion['currentG4Native']==g4['native']and completion['currentG4Container']==g4['container']and completion['closedCompilerCalls']==38 and completion['original19Images']==pr['imagesON'],'all19 assembled with exact current G4')
 matrix=load(pin(pr['canonicalMatrix']['path'],pr['canonicalMatrix']));need(matrix['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'and len(matrix['entries'])==len(pr['entries'])==len(pr['imagesON'])==19,'original19 matrix')
 need(pr['imagesOFF']==off['joinedOriginal19Images'],'actual current OFF full19 identity');need(oracle['status']==pr['C95OracleStatus']and len(oracle['rows'])==95,'saved result-only C oracle')
 expected=[]
 from loader_grammar import interpretation
 for entry,mat in zip(pr['entries'],matrix['entries']):
  need(entry['workload']==mat['workload']and entry['source']['sha256']==mat['expectedSourceSha256']and entry['source']['path'].endswith('/'+mat['source'])and entry['symbol']==mat['symbol']and entry['iterations']==mat['iterations'],'unchanged original source/symbol/profiles')
  work=entry['workload'];ims={arm:next(x for x in pr['images'+arm]if x['workload']==work)for arm in ['OFF','ON']}
  for arm,im in ims.items():
   need(im['source']==entry['source']and im['iterations']==entry['iterations'],'image owner current source/profiles');offset=im['offset']if arm=='OFF'else im['selectedExport'][1];payload,exports=container(pin(im['container']['path'],im['container']).read_bytes());need(payload==pin(im['native']['path'],im['native']).read_bytes()and (entry['symbol'],offset,1)in exports,'own full image/export')
  for n in entry['iterations']:
   answers=[r for r in oracle['rows']if r['workload']==work and r['n']==n];need(len(answers)==1 and answers[0]['sourceSHA256']==entry['source']['sha256']and answers[0]['symbol']==entry['symbol'],'source-bound saved C result only');answer=answers[0]['result']
   for arm in ['OFF','ON']:
    c=pr['cases'][len(expected)];im=ims[arm];offset=im['offset']if arm=='OFF'else im['selectedExport'][1];need(c==dict(label=work+'-'+arm+'-n'+str(n),workload=work,arm=arm,profile=n,symbol=entry['symbol'],offset=offset,arity=1,native=im['native'],container=im['container'],source=entry['source'],expectedResult=answer,nativeArgv=[pr['loader'],im['native']['path'],str(offset),'1','aarch64','-',str(n)]),'exact190 original case order')
    need(interpretation(c['nativeArgv'])==dict(typedI64=[n],guestArgv=None,effectiveArgc=7),'typed runtime no separator');expected.append(c)
 need(len(expected)==len(pr['cases'])==pr['maximumLoaderCalls']==190 and pr['guestFuelPerCall']==16777216,'190 original runtime calls/fuel')
 need(pr['guestArenaCaps']=={'pairs':2097152,'string-pool-bytes':65536,'vectors':4096,'vector-items':65536}and pr['environment']=={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':pr['freshOutputRoot'],'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_PAIRS':'2097152','KEXE_VECTOR_ITEMS':'65536','KEXE_CPU_SECONDS':'30','KEXE_WALL_SECONDS':'30','KEXE_FUEL':'16777216','KEXE_ARENA_USE':'1','PYTHONNOUSERSITE':'1','KEXE_STRUCTURED_REPORT':'1','KEXE_RESULT_TYPE':'i64'},'unchanged all17 env/caps')
 need(pr['operationalEnvironment']=={'version':'host-authorized-loader-owned-sandbox-v1','requiresOuterHostEscalation':True,'loaderOwnedSandboxRequired':True,'loaderSandboxWeakeningAuthorized':False,'hostEscalationDeclarationIsNotKernelMeasurement':True}and pr['C2']is False and pr['timingAuthorized']is False and pr['generalCandidateAdoptionQualified']is False and pr['fullClobberCertificateQualified']is False and pr['actualTypedMode2AdmissionObserved']is False,'diagnostic only/general HOLD')
 return True

def go_header(g,pr,O):
 proofKeys=['OFFActualProof','G4Original19ActualProof','C95Oracle','C95OracleProof','integrationFixtureProof','FixedpointActualProof']
 need(set(g)==set(['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews']+proofKeys),'exact GO keys')
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==190 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is True and g['C2']is False and g['outerHostLaunchRequiresEscalation']is True,'exact runtime190 only under declared host profile')
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
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);deadline=time.monotonic()+12000
 try:
  for index,c in enumerate(pr['cases'],1):
   guard();need(time.monotonic()+60<=deadline,'finite original per-call deadlines before new child')
   seal={k:c[k]for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};seal.update(format=pr['invocationSealVersion'],index=index,rootGO=dict(path=str(gp),**gr),sourcePinsSHA256=g['sourcePinsSHA256'],preregistrationSHA256=g['preregistrationSHA256']);p=O/(c['label']+'.admission.json');need(not p.exists(),'fresh single invocation seal');save(p,seal);need(p.stat().st_size<=4096,'bounded seal');p.chmod(0o444);sr=receipt(p);generated[str(p)]=sr;save(O/'generated-pins.json',generated)
   r=mod.call(D,O,pr,c,rows,save,sr['sha256']);results.append(r);save(O/'results.json',results)
   if index%2==0:
    a,b=results[-2:];need(all(a['report'][k]==b['report'][k]for k in ['result','fuelInitial','fuelRemaining','fuelConsumed','arena17']),'paired original result/fuel/17arena parity')
  guard();need(len(rows)==len(results)==190 and all(r['state']=='terminal'and r['returncode']==0 for r in rows),'190 new closed runtime children');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed']and not terminal['failure'],'durable terminal before COMPLETE')
 evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['terminal.json','attempts.json','generated-pins.json','results.json','effective-environment.json']};save(O/'report.json',{'status':'COMPLETE_CURRENT_G4_X8_ORIGINAL19_RUNTIME190_DIAGNOSTIC_ONLY','runtimeCalls':190,'originalWorkloads':19,'pairedProfiles':95,'results':results,'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'evidence':evidence,'G4Original19ActualProof':g['G4Original19ActualProof'],'FixedpointActualProof':g['FixedpointActualProof'],'C95Oracle':g['C95Oracle'],'C95FuelArenaAvailable':False,'C95FuelArena':None,'full19FunctionalAdmissionPassed':True,'generalCandidateAdoptionQualified':False,'fullClobberCertificateQualified':False,'actualTypedMode2AdmissionObserved':False,'performanceQualified':False,'hardPeakQualified':False,'strictPhysicalMemoryQualified':False,'all190StrictSampledPolicyPassed':all(r['strictOldMemoryPolicyPassed']for r in results),'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact root GO');main(sys.argv[1])
