"""Inert SOURCE. Published mode2 x8 G2/G3/G4 fixedpoint6 compiler commands only after exact two reviews and GO."""
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

def compiler_case(argv,pr,c):
 need(c in pr['cases']and len(pr['cases'])==6 and argv==c['nativeArgv'],'six exact generation commands')
 g=c['generation'];O=Path(pr['freshOutputRoot']);need(g in [2,3,4]and c['symbol']=='main'and c['arity']==0,'generation main0')
 producer=pr['G1Native']['path']if g==2 else str(O/('G'+str(g-1)+'.bin'));need(c['producer']==producer,'previous generation builder')
 output=str(O/('G'+str(g)+('.kseed'if c['kind']=='compile'else'.bin')))
 args=['compile',str(O/'candidate-source.kotoba'),'--target','aarch64-macos','--output',output]if c['kind']=='compile'else['extract-native',str(O/('G'+str(g)+'.kseed')),'--symbol','main','--output',output]
 need(c['kind']in ['compile','extract']and c['outputPath']==output and argv==[pr['loader'],producer,'0','0','aarch64','35,37,38,39','--']+args,'compiler typed0/guest argv exact owner/output')
 return True

def whole_compiler(native,packed):
 payload,exports=container(pin(packed['path'],packed).read_bytes());need(payload==pin(native['path'],native).read_bytes()and exports==[('main',0,0)],'whole compiler sole main0');return True

def build_guard(b,pr,native,packed,rootGO,generation):
 from artifact_admission import accept_artifact_observation
 need(generation in [2,3,4],'bounded producer chain')
 need(set(b)=={'format','generation','source','builder','builderBuild','native','container','rootGO','closedCompilerCalls','attempts','certificateQualified'},'exact generated producer receipt')
 need(b['format']=='hft-compose511-bound-hoist-generation-producer/v1'and b['generation']==generation and b['source']==pr['sourceCandidate']and b['native']==native and b['container']==packed and b['rootGO']==rootGO and b['closedCompilerCalls']==2 and b['certificateQualified']is False,'current generated producer identity')
 O=Path(pr['freshOutputRoot']);need(native['path']==str(O/('G'+str(generation)+'.bin'))and packed['path']==str(O/('G'+str(generation)+'.kseed')),'generation artifact owner');whole_compiler(native,packed)
 if generation==2:need(b['builder']==pr['G1Native']and b['builderBuild']is None,'fixed saved G1, no guessed equality')
 else:
  need(b['builder']['path']==str(O/('G'+str(generation-1)+'.bin'))and b['builderBuild']['path']==str(O/('G'+str(generation-1)+'-build-receipt.json')),'previous current generated builder')
  previous=load(pin(b['builderBuild']['path'],b['builderBuild']));build_guard(previous,pr,b['builder'],previous['container'],rootGO,generation-1)
 need(len(b['attempts'])==2,'exact two admitted build calls')
 for n,r in enumerate(b['attempts']):
  i=(generation-2)*2+n;c=pr['cases'][i]
  need(r['index']==i+1 and r['label']==c['label']and r['nativeArgv']==c['nativeArgv']and r['state']=='terminal'and r['returncode']==0 and r['failure']is None and r['captureStopAcknowledged']is True and r['waitUncertain']is False,'two previous-stage calls closed and admitted')
  need(accept_artifact_observation(r['controllerObservation'])is True,'unchanged artifact/sample-or-gap admission')
 need(b['attempts'][0]['structuredReportObservation']=={'kind':'compile','containerBytes':packed['bytes']}and b['attempts'][1]['structuredReportObservation']=={'kind':'extract','offset':0,'nativeBytes':native['bytes'],'arity':0},'entire declared main0 compiler payload')
 return True

def source_scope(pr,ip):
 registry_scope(pr,ip)
 need([c['label']for c in pr['cases']]==['G2-compile','G2-extract','G3-compile','G3-extract','G4-compile','G4-extract']and all(compiler_case(c['nativeArgv'],pr,c)for c in pr['cases']),'six new compiler calls only')
 need(pr['fixedpointGenerations']==[2,3,4]and pr['requireG2G3G4WholeEqual']is True and pr['requireG1G2Equal']is False,'G2/G3/G4 fixedpoint, G1 equality deliberately unconstrained')
 cs=load(pin(pr['candidateSourcePins']['path'],pr['candidateSourcePins']));base=Path(pr['candidateSourcePins']['path']).parent
 for n,r in cs.items():pin(base/n,r)
 need(cs['41-a64gen-candidate.kotoba']['sha256']=='62644967b69517b11936163a958b70e3ae3f8faeb21be185274aa2a57595f765','reviewed hoist module')
 reviews=[load(pin(r['path'],r))for r in pr['candidateArchitecturalReviews']]
 need(len(reviews)==2 and len({r['path']for r in pr['candidateArchitecturalReviews']})==2 and all(q['status']==pr['candidateArchitectureStatus']and q['sourcePinsSHA256']==pr['candidateSourcePins']['sha256']for q in reviews),'two conditional architecture SOURCE reviews')
 a=load(pin(pr['sourceAssembly']['path'],pr['sourceAssembly']));need(len(a['modules'])==len(a['modulePins'])==16,'current16 ordered assembly')
 mods=[pin(a['candidate41']['path'],a['candidate41']).read_bytes()if n=='seed/41-a64gen.kotoba'else pin(r['path'],r).read_bytes()for n,r in zip(a['modules'],a['modulePins'])]
 need(b''.join(b+b'\n'for b in mods)==pin(pr['sourceCandidate']['path'],pr['sourceCandidate']).read_bytes()and pr['sourceCandidate']['sha256']=='b8d9e273788a24748f6ddcb1f9b71b970fc78fc1cb6bb68e8f2a1c082004a1f5','exact candidate unity every generation')
 gp=load(pin(pr['G1ActualProof']['path'],pr['G1ActualProof']));completion=load(pin(pr['G1Completion']['path'],pr['G1Completion']));np=load(pin(pr['G1Native4Preregistration']['path'],pr['G1Native4Preregistration']))
 need(gp['status']==pr['G1ActualProofStatus']and gp['closedCompilerCalls']==4 and gp['qualification']['actualOriginalNS492WordEmission']is True and gp['qualification']['benchmarkGuest']is False,'G1 actual four compiler calls only')
 need(gp['wholeArtifactsAndOwnExports'][0]['native']==pr['G1Native']and gp['wholeArtifactsAndOwnExports'][0]['container']==pr['G1Container']and gp['wholeArtifactsAndOwnExports'][0]['selectedExport']==['main',0,0],'saved whole G1 sole main0');whole_compiler(pr['G1Native'],pr['G1Container'])
 need(pr['G1Native']['sha256']=='c3503b7f746b9279a27bba6f5b6a1e97f7a2770b694bdf42a558fd7cc856f445'and gp['completion']==pr['G1Completion']and gp['preregistrationSHA256']==pr['G1Native4Preregistration']['sha256'],'specific new G1 binding')
 need(completion['status']=='COMPLETE_HFT_COMPOSE511_BOUND_HOIST_BUILD_EXTRACT_ORIGINAL_NS_NATIVE4_V1_CODE_ONLY'and completion['calls']==4 and completion['sourcePinsSHA256']==gp['sourcePinsSHA256']and np['sourceCandidate']==pr['sourceCandidate'],'current exact G1 source completion')
 br=load(pin(pr['G1ProducerBuildReceipt']['path'],pr['G1ProducerBuildReceipt']));need(gp['generatedProducerBuildReceipt']==pr['G1ProducerBuildReceipt']and br['source']==pr['sourceCandidate']and br['native']==pr['G1Native']and br['container']==pr['G1Container']and br['rootGO']==gp['rootGO']and br['closedCompilerCalls']==2 and br['certificateQualified']is False,'G1 currentGO two admitted build calls')
 from artifact_admission import accept_artifact_observation
 for i,row in enumerate(br['attempts']):
  need(len(br['attempts'])==2 and row['index']==i+1 and row['label']==np['cases'][i]['label']and row['nativeArgv']==np['cases'][i]['nativeArgv']and row['state']=='terminal'and row['returncode']==0 and row['failure']is None and row['captureStopAcknowledged']is True and row['waitUncertain']is False and accept_artifact_observation(row['controllerObservation'])is True,'saved G1 actual closed admitted command lineage')
 op=load(pin(pr['qualifiedOperationComponentsActualProof']['path'],pr['qualifiedOperationComponentsActualProof']));need(op['status']=='PASS_INDEPENDENT_SAVED_PUBLISHED_MODE2_X8_G2_G3_G4_FIXEDPOINT6_COMPILER_ARTIFACTS_ONLY'and op['closedCompilerCalls']==6 and op['G2G3G4WholeNativeEqual']is True,'saved component qualification scope only, not new generations')
 O=pr['freshOutputRoot'];need(pr['environment']=={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':O,'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1','PYTHONNOUSERSITE':'1','KEXE_CAP_RESOURCES_35':O,'KEXE_COMMAND':'1'}and pr['capabilities']=='35,37,38,39'and pr['compileFuel']=='off','unchanged exact compiler17/capabilities/fuel')
 pv=load(pin(pr['loaderSupervisorProtocolView']['path'],pr['loaderSupervisorProtocolView']));need(pv['status']=='SOURCE_PROTOCOL_VIEW_ONLY_NOT_DYNAMIC_PROCESS_PROOF'and len(pv['pins'])==4,'conditional source protocol only')
 for r in pv['pins']:pin(r['path'],r)
 cs,bp,lp,_=pv['pins'];build=load(bp['path']);need(lp==pr['loaderArtifact']and build['loader']==lp and build['CSourceSHA256']==cs['sha256']and build['status']==pv['savedBuildProofStatus'],'same source-bound loader')
 lines=Path(cs['path']).read_text().splitlines(keepends=True)
 for v in pv['spans']:need(''.join(lines[v['start']-1:v['end']])==v['text'],'same supervisor source spans')
 need(pr['operationalEnvironment']=={'version':'host-authorized-loader-owned-sandbox-v1','requiresOuterHostEscalation':True,'loaderOwnedSandboxRequired':True,'loaderSandboxWeakeningAuthorized':False,'hostEscalationDeclarationIsNotKernelMeasurement':True}and pr['C2']is False and pr['timingAuthorized']is False and pr['runtimeGuestAuthorized']is False and pr['clobberCertificateQualified']is False and pr['candidateAdoptionQualified']is False,'compiler fixedpoint only, broader HOLD')
 return True

def registry_scope(pr,ip):
 need(type(pr['exactInputFiles'])is int and type(pr['exactInputLogicalBytes'])is int,'integer exact registry counts')
 need(len(ip)==pr['exactInputFiles']<=256 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']<=33554432,'bounded exact targeted input registry')
 return True

PROOF_KEYS=['G1ActualProof','G1Completion','G1ProducerBuildReceipt','integrationFixtureProof']
def go_header(g,pr,O):
 need(set(g)==set(['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','candidateSourcePinsSHA256']+PROOF_KEYS),'exact GO keys')
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==6 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is False and g['C2']is False and g['outerHostLaunchRequiresEscalation']is True,'compiler fixedpoint6 only, correct outerhost profile')
 return True

def fixedpoint(artifacts):
 need(len(artifacts)==3 and [a['generation']for a in artifacts]==[2,3,4],'three whole generations')
 contents=[]
 for a in artifacts:
  need(a['exports']==[('main',0,0)],'fixedpoint actual sole-main export');whole_compiler(a['native'],a['container']);contents.append((Path(a['native']['path']).read_bytes(),Path(a['container']['path']).read_bytes(),a['exports']))
 need(contents[0]==contents[1]==contents[2],'G2/G3/G4 whole bytes and exports identical')
 return True

def main(goPath):
 import time
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);rows=[];results=[];artifacts=[];generated={};builds={};ok=False
 go_header(g,pr,O)
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'exact GO source identity')
 need(g['candidateSourcePinsSHA256']==pr['candidateSourcePins']['sha256'],'frozen candidate source')
 need(len(g['sourceReviews'])==2 and len(set(r['path']for r in g['sourceReviews']))==2,'two exact distinct SOURCE reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'reviewed exact fixedpoint SOURCE')
 for k in PROOF_KEYS:
  target='qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k;need(g[k]==pr[target],'exact saved prerequisite');pin(g[k]['path'],g[k])
 f=load(g['integrationFixtureProof']['path']);need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','unchanged owned capture actual fixture')
 for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'same qualified component bytes')
 def guard():
  need(receipt(gp)==gr and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256'],'immutable GO/input registry')
  registry_scope(pr,ip)
  for n,r in sp.items():pin(D/n,r)
  for p,r in ip.items():pin(p,r)
  for p,r in generated.items():pin(p,r)
  source_scope(pr,ip)
 guard();need(not O.exists(),'fresh output namespace');O.mkdir();save(O/'attempts.json',rows);save(O/'effective-environment.json',pr['environment']);save(O/'generated-pins.json',generated)
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);deadline=time.monotonic()+11100
 def artifact(path):
  r=receipt(path);need(r['bytes']<=4194560,'bounded generated artifact/receipt');generated[str(path)]=r;save(O/'generated-pins.json',generated);return dict(path=str(path),**r)
 try:
  p=O/'candidate-source.kotoba';p.write_bytes(pin(pr['sourceCandidate']['path'],pr['sourceCandidate']).read_bytes());p.chmod(0o444);need(receipt(p)=={k:pr['sourceCandidate'][k]for k in ['bytes','sha256']},'same unity every generation');artifact(p)
  for index,c in enumerate(pr['cases'],1):
   guard();need(time.monotonic()+1840<=deadline,'finite campaign before new child');generation=c['generation'];producer=c['producer'];previous=generation-1
   nr=pr['G1Native']if generation==2 else dict(path=producer,**receipt(producer));kr=pr['G1Container']if generation==2 else dict(path=str(O/('G'+str(previous)+'.kseed')),**receipt(O/('G'+str(previous)+'.kseed')));whole_compiler(nr,kr)
   pb=None if generation==2 else builds[previous]
   if pb is not None:build_guard(load(pin(pb['path'],pb)),pr,nr,kr,dict(path=str(gp),**gr),previous)
   inputPath=Path(c['nativeArgv'][8]);seal={'format':pr['invocationSealVersion'],'index':index,'label':c['label'],'nativeArgv':c['nativeArgv'],'producer':nr,'producerContainer':kr,'producerBuild':pb,'input':dict(path=str(inputPath),**receipt(inputPath)),'outputPath':c['outputPath'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256']};sealPath=O/(c['label']+'.admission.json');need(not sealPath.exists()and not Path(c['outputPath']).exists()and not Path(c['outputPath']).is_symlink(),'fresh sealed generation invocation');save(sealPath,seal);need(sealPath.stat().st_size<=4096,'bounded seal');sealPath.chmod(0o444);sr=artifact(sealPath)
   r=mod.call(D,O,pr,c,rows,save,sr['sha256']);results.append(r);out=artifact(Path(c['outputPath']))
   if c['kind']=='compile':need(r['report']=={'kind':'compile','containerBytes':out['bytes']},'whole declared container');payload,exports=container(Path(c['outputPath']).read_bytes());need(exports==[('main',0,0)],'new compiler sole main0')
   else:
    packed=dict(path=str(inputPath),**receipt(inputPath));payload,exports=container(inputPath.read_bytes());need(exports==[('main',0,0)]and payload==Path(c['outputPath']).read_bytes()and r['report']=={'kind':'extract','offset':0,'nativeBytes':out['bytes'],'arity':0},'whole extracted main0 payload')
    a={'generation':generation,'native':out,'container':packed,'exports':exports};artifacts.append(a);save(O/'artifacts.json',artifacts)
    b={'format':'hft-compose511-bound-hoist-generation-producer/v1','generation':generation,'source':pr['sourceCandidate'],'builder':nr,'builderBuild':pb,'native':out,'container':packed,'rootGO':dict(path=str(gp),**gr),'closedCompilerCalls':2,'attempts':rows[-2:].copy(),'certificateQualified':False};build_guard(b,pr,out,packed,b['rootGO'],generation);bp=O/('G'+str(generation)+'-build-receipt.json');save(bp,b);bp.chmod(0o444);builds[generation]=artifact(bp)
   save(O/'results.json',results)
  guard();need(len(rows)==len(results)==6 and all(r['state']=='terminal'and r['returncode']==0 for r in rows),'six new admitted closed compiler calls');fixedpoint(artifacts);ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed']is True and terminal['failure']is False,'durable terminal before valid-last COMPLETE');fixedpoint(artifacts)
 evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['attempts.json','results.json','artifacts.json','generated-pins.json','G2-build-receipt.json','G3-build-receipt.json','G4-build-receipt.json','effective-environment.json','terminal.json']};save(O/'report.json',{'status':'COMPLETE_HFT_COMPOSE511_BOUND_HOIST_G2_G3_G4_WHOLE_FIXEDPOINT6_COMPILER_ARTIFACTS_ONLY','closedCompilerCalls':6,'artifacts':artifacts,'sourceCandidate':pr['sourceCandidate'],'G1Native':pr['G1Native'],'G1Container':pr['G1Container'],'G2G3G4WholeNativeEqual':True,'G2G3G4WholeContainerEqual':True,'G1EqualityRequired':False,'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'evidence':evidence,'guestRuntimeExecuted':False,'stageClobberCertificateQualified':False,'generatedProducerReceipts':[builds[g]for g in [2,3,4]],'wholeArtifactsAndOwnExports':artifacts,'candidateAdoptionQualified':False,'full19FunctionalQualified':False,'performanceQualified':False,'hardPeakQualified':False,'strictPhysicalMemoryQualified':False,'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact root GO');main(sys.argv[1])
