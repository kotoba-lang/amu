"""Inert SOURCE. Compose10 original NS runtime10 only after exact two reviews and GO."""
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
 off=load(pin(pr['OFFActualProof']['path'],pr['OFFActualProof']));on=load(pin(pr['ONActualProof']['path'],pr['ONActualProof']));oracle=load(pin(pr['C95Oracle']['path'],pr['C95Oracle']))
 need(off['status']==pr['OFFActualProofStatus'] and off['joinedOriginal19ArtifactWholePayloadIdentity']is True,'saved current OFF whole19 identity')
 need(off['currentBaselineNative']['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'and off['current16BaselineSource']['sha256']=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418','current OFF lineage')
 need(on['status']==pr['ONActualProofStatus']and on['closedCompilerCalls']==4 and on['qualification']['actualOriginalNS492WordEmission']is True and on['qualification']['benchmarkGuest']is False and on['qualification']['productAdoption']is False,'ON four compiler calls code only')
 completion=load(pin(pr['ONCompletion']['path'],pr['ONCompletion']));need(on['completion']==pr['ONCompletion']and completion['status']=='COMPLETE_HFT_COMPOSE511_BOUND_HOIST_BUILD_EXTRACT_ORIGINAL_NS_NATIVE4_V1_CODE_ONLY','exact accepted code completion')
 np=load(pin(pr['native4Source']['path'],pr['native4Source']));cert=load(pin(pr['emissionCertificate']['path'],pr['emissionCertificate']));need(on['preregistrationSHA256']==pr['native4Source']['sha256']and on['prospectiveCertificate']==cert,'candidate source and emission association')
 need(np['entries'][0]['source']==pr['entries'][0]['source']and cert['sourceFNCount']==267 and cert['originalDiskDefns']==265 and cert['nullSentinel']==cert['implicitRemDefns']==1 and np['expandedOriginalSource']['bytes']==30443,'original body plus primary implicit rem and sentinel')
 need(on['wholeArtifactsAndOwnExports'][0]==pr['candidateCompiler']and np['sourceCandidate']==pr['candidateSource'],'specific compiled candidate source/wholeproducer binding')
 prior=load(pin(pr['qualifiedPriorRuntime10Proof']['path'],pr['qualifiedPriorRuntime10Proof']));need(prior['sourcePinsSHA256']==pr['qualifiedPriorRuntime10SourcePins']['sha256']and prior['runtimeCalls']==10,'qualified previous runtime10 scope')
 matrix=load(pr['canonicalMatrix']);m=next(e for e in matrix['entries']if e['workload']=='nsichneu');e=pr['entries'][0]
 need(len(pr['entries'])==1 and len(matrix['entries'])==19 and matrix['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'and e['workload']==m['workload']and e['symbol']==m['symbol']=='batch'and e['iterations']==m['iterations']==[0,1,2,17,32]and e['source']['sha256']==m['expectedSourceSha256'],'original five profiles/source/symbol')
 need(oracle['status']==pr['C95OracleStatus']and len(oracle['rows'])==95 and pr['C5Rows']==[r for r in oracle['rows']if r['workload']=='nsichneu']and len(pr['C5Rows'])==5,'C result-only oracle')
 need(pr['images']['OFF']==next(r for r in off['joinedOriginal19Images']if r['workload']=='nsichneu')and pr['images']['ON']==on['wholeArtifactsAndOwnExports'][1],'whole OFF/ON artifact owners')
 before=pin(pr['images']['OFF']['native']['path'],pr['images']['OFF']['native']).read_bytes();after=pin(pr['images']['ON']['native']['path'],pr['images']['ON']['native']).read_bytes();need(len(before)==len(after)==cert['expectedWholeNativeBytes'],'same code count')
 diffs=[{'wordIndex':1+i//4,'physicalByteOffset':i,'before':int.from_bytes(before[i:i+4],'little'),'after':int.from_bytes(after[i:i+4],'little')}for i in range(0,len(before),4)if before[i:i+4]!=after[i:i+4]]
 need(diffs==cert['changes']==on['actualFullNativeWordDifferences']and len(diffs)==492 and hashlib.sha256(after).hexdigest()==cert['expectedWholeNativeSHA256'],'exact492 actual words all other bytes equal')
 need(len(pr['cases'])==10,'no extra cases')
 from loader_grammar import interpretation
 for index,c in enumerate(pr['cases']):
  n=[0,1,2,17,32][index//2];arm=['OFF','ON'][index%2];im=pr['images'][arm];answer=next(r for r in pr['C5Rows']if r['n']==n)
  need(c['label']=='nsichneu-'+arm+'-n'+str(n)and c['workload']=='nsichneu'and c['arm']==arm and c['profile']==n and type(c['profile'])is int and c['source']==e['source']and c['symbol']=='batch'and c['expectedResult']==answer['result']and type(c['expectedResult'])is int and answer['sourceSHA256']==e['source']['sha256']and answer['symbol']=='batch','source/profile/result order')
  need(c['native']==im['native']and c['container']==im['container']and c['offset']==36440 and c['arity']==1,'fixed saved batch ABI')
  payload,exports=container(pin(c['container']['path'],c['container']).read_bytes());need(payload==pin(c['native']['path'],c['native']).read_bytes()and ('batch',36440,1)in exports,'whole payload selected export')
  need(c['nativeArgv']==[pr['loader'],c['native']['path'],'36440','1','aarch64','-',str(n)]and interpretation(c['nativeArgv'])=={'typedI64':[n],'guestArgv':None,'effectiveArgc':7},'primary typed grammar no guest separator')
 need(pr['maximumLoaderCalls']==10 and pr['guestFuelPerCall']==16777216 and len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='16777216'and pr['zeroCapabilityGrants']=='-','original fuel env/capabilities')
 need(pr['guestArenaCaps']=={'pairs':2097152,'string-pool-bytes':65536,'vectors':4096,'vector-items':65536}and pr['environment']=={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':pr['freshOutputRoot'],'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_PAIRS':'2097152','KEXE_VECTOR_ITEMS':'65536','KEXE_CPU_SECONDS':'30','KEXE_WALL_SECONDS':'30','KEXE_FUEL':'16777216','KEXE_ARENA_USE':'1','PYTHONNOUSERSITE':'1','KEXE_STRUCTURED_REPORT':'1','KEXE_RESULT_TYPE':'i64'},'exact original arena17 environment')
 need(pr['operationalEnvironment']=={'version':'host-authorized-loader-owned-sandbox-v1','requiresOuterHostEscalation':True,'loaderOwnedSandboxRequired':True,'loaderSandboxWeakeningAuthorized':False,'hostEscalationDeclarationIsNotKernelMeasurement':True}and pr['C2']is False and pr['timingAuthorized']is False and pr['generalCompositionAdoptionAuthorized']is False,'bounded diagnostic only')
 return True

def go_header(g,pr,O):
 proofKeys=['OFFActualProof','ONActualProof','ONCompletion','C95Oracle','C95OracleProof','integrationFixtureProof']
 need(set(g)==set(['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews']+proofKeys),'exact GO keys')
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==10 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is True and g['C2']is False and g['outerHostLaunchRequiresEscalation']is True,'exact runtime10 only under declared host profile')
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
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);deadline=time.monotonic()+700
 try:
  for index,c in enumerate(pr['cases'],1):
   guard();need(time.monotonic()+60<=deadline,'finite original per-call deadlines before new child')
   seal={k:c[k]for k in ['label','nativeArgv','workload','arm','profile','symbol','offset','arity','native','container','source']};seal.update(format=pr['invocationSealVersion'],index=index,rootGO=dict(path=str(gp),**gr),sourcePinsSHA256=g['sourcePinsSHA256'],preregistrationSHA256=g['preregistrationSHA256']);p=O/(c['label']+'.admission.json');need(not p.exists(),'fresh single invocation seal');save(p,seal);need(p.stat().st_size<=4096,'bounded seal');p.chmod(0o444);sr=receipt(p);generated[str(p)]=sr;save(O/'generated-pins.json',generated)
   r=mod.call(D,O,pr,c,rows,save,sr['sha256']);results.append(r);save(O/'results.json',results)
   if index%2==0:
    a,b=results[-2:];need(all(a['report'][k]==b['report'][k]for k in ['result','fuelInitial','fuelRemaining','fuelConsumed','arena17']),'paired original result/fuel/17arena parity')
  guard();need(len(rows)==len(results)==10 and all(r['state']=='terminal'and r['returncode']==0 for r in rows),'10 new closed runtime children');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed']and not terminal['failure'],'durable terminal before COMPLETE')
 evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['terminal.json','attempts.json','generated-pins.json','results.json','effective-environment.json']};save(O/'report.json',{'status':'COMPLETE_HFT_COMPOSE511_BOUND_HOIST_ORIGINAL_NS_RUNTIME10_FINITE_PARITY_ONLY','runtimeCalls':10,'originalProfiles':[0,1,2,17,32],'pairedProfiles':5,'results':results,'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'evidence':evidence,'ONActualProof':g['ONActualProof'],'OFFActualProof':g['OFFActualProof'],'C95Oracle':g['C95Oracle'],'C95FuelArenaAvailable':False,'full19FunctionalQualified':False,'generalCandidateAdoptionQualified':False,'generalCompositionQualified':False,'performanceQualified':False,'hardPeakQualified':False,'strictPhysicalMemoryQualified':False,'new10StrictSampledPolicyPassed':all(r['strictOldMemoryPolicyPassed']for r in results),'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact root GO');main(sys.argv[1])
