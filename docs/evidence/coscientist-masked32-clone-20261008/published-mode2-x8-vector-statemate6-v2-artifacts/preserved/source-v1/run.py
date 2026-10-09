"""Inert SOURCE. Published mode2 x8 vector/statemate6 compiler commands only after exact two reviews and GO."""
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
 need(c in pr['cases']and len(pr['cases'])==6 and argv==c['nativeArgv'],'only six fixed compiler commands')
 need(argv[:7]==[pr['loader'],c['producer'],'0','0','aarch64','35,37,38,39','--'],'compiler entry0/arity0 and guest argv boundary')
 need(argv[7]=='compile'and argv[9:]==['--target','aarch64-macos','--output',c['outputPath']]if c['kind']=='compile'else argv[7]=='extract-native'and argv[9:]==['--symbol',c['symbol'],'--output',c['outputPath']],'exact compiler subcommand')
 need(Path(argv[8]).parent==Path(pr['freshOutputRoot'])and Path(c['outputPath']).parent==Path(pr['freshOutputRoot']),'only owned compiler IO paths')
 return True

def build_guard(b,pr,native,packed,rootGO):
 from artifact_admission import accept_artifact_observation
 need(set(b)=={'format','source','builder','native','container','rootGO','closedCompilerCalls','attempts','certificateQualified'},'complete producer build receipt')
 need(b['format']=='published-mode2-x8-sealed-producer/v1'and b['source']==pr['sourceCandidate']and b['native']==native and b['container']==packed and b['rootGO']==rootGO and b['closedCompilerCalls']==2 and b['certificateQualified']is False,'specific candidate build receipt')
 need(b['builder']['path']==pr['producer']and b['builder']['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'and len(b['attempts'])==2,'specific current builder')
 for i,r in enumerate(b['attempts']):
  need(r['index']==i+1 and r['label']==pr['cases'][i]['label']and r['nativeArgv']==pr['cases'][i]['nativeArgv']and r['state']=='terminal'and r['returncode']==0 and r['failure']is None and r['captureStopAcknowledged']is True and r['waitUncertain']is False,'two closed admitted specific build calls')
  need(accept_artifact_observation(r['controllerObservation'])is True,'same semantic/sample-or-gap admission')
 need(b['attempts'][0]['structuredReportObservation']=={'kind':'compile','containerBytes':packed['bytes']}and b['attempts'][1]['structuredReportObservation']=={'kind':'extract','offset':0,'nativeBytes':native['bytes'],'arity':0},'whole main0 producer output')
 return True

def existing_candidate_guard(pr):
 proof=load(pin(pr['candidateActualProof']['path'],pr['candidateActualProof']))
 need(proof['status']==pr['candidateActualProofStatus']and proof['closedCompilerCalls']==6 and proof['stageClobberCertificateQualified']is False and proof['candidateAdoptionQualified']is False and proof['guestRuntimeExecuted']is False,'exact saved compiler artifact identity only')
 x=proof['wholeArtifactsAndOwnExports'][0];need(x['label']=='candidate-extract'and x['native']==pr['candidateCompiler']and x['container']==pr['candidateCompilerContainer']and x['exports']==[['main',0,0]]and x['selectedExport']==['main',0,0],'audited existing whole candidate')
 need(proof['sealedProducerBuild']==pr['candidateSealedBuild']and proof['rootGO']==pr['candidateBuildRootGO'],'preserve old build receipt and old GO')
 old=load(pin(pr['candidateSourcePreregistration']['path'],pr['candidateSourcePreregistration']));pin(pr['candidateHarnessSourcePins']['path'],pr['candidateHarnessSourcePins']);need(proof['sourcePinsSHA256']==pr['candidateHarnessSourcePins']['sha256'],'old SOURCE proof binding')
 # Saved old root GO stays bound to the old source and build, never rewritten for this campaign.
 need(proof['preregistrationSHA256']==pr['candidateSourcePreregistration']['sha256']and old['sourceCandidate']==pr['sourceCandidate']and old['candidateSourcePins']==pr['candidateSourcePins'],'saved source/prereg lineage')
 pin(pr['candidateBuildRootGO']['path'],pr['candidateBuildRootGO']);b=load(pin(pr['candidateSealedBuild']['path'],pr['candidateSealedBuild']));build_guard(b,old,pr['candidateCompiler'],pr['candidateCompilerContainer'],pr['candidateBuildRootGO'])
 raw=pin(pr['candidateCompiler']['path'],pr['candidateCompiler']).read_bytes();payload,exports=container(pin(pr['candidateCompilerContainer']['path'],pr['candidateCompilerContainer']).read_bytes());need(raw==payload and exports==[('main',0,0)],'existing producer full payload and entry')
 return True

def source_scope(pr,ip):
 need(len(pr['cases'])==6 and [c['label']for c in pr['cases']]==['OFF-vector-compile','OFF-vector-extract','ON-vector-compile','ON-vector-extract','ON-statemate-compile','ON-statemate-extract'],'fixed new six order')
 need([c['producer']for c in pr['cases']]==[pr['offCompiler']['path']]*2+[pr['candidateCompiler']['path']]*4,'two fixed audited producers only')
 need(all(compiler_case(c['nativeArgv'],pr,c)for c in pr['cases']),'exact compiler grammar');existing_candidate_guard(pr)
 tc=load(pin(pr['TCActualProof']['path'],pr['TCActualProof']));need(tc['status']==pr['TCActualProofStatus']and tc['G0Native']==pr['offCompiler']and tc['G0Container']==pr['offCompilerContainer'],'exact TC OFF')
 payload,exports=container(pin(pr['offCompilerContainer']['path'],pr['offCompilerContainer']).read_bytes());need(payload==pin(pr['offCompiler']['path'],pr['offCompiler']).read_bytes()and exports==[('main',0,0)],'OFF full producer')
 need(pr['fixtureSource']['sha256']=='aa3feb907fe7533d76b485d8ade164100b8a70e232e750f874a724d91d6562dd'and pr['statemateEntry']=={'workload':'statemate','source':{'path':'/Users/junkawasaki/github/wt/amu-seed17/bench/embench/batch-ports/statemate.kotoba','bytes':59847,'sha256':'977d840bc3beee78ff8fcc43fd5c34bdb786b65da494c5926a4745515cc0bf44'},'symbol':'batch','iterations':[0,1,2,17,32]},'exact frozen fixture and unchanged original statemate')
 for c in pr['cases']:
  need(c['arity']==1 and c['symbol']==('batch'if c['label'].startswith('ON-statemate')else'bench'),'own actual export arity')
 need(len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='off'and pr['environment']['KEXE_COMMAND']=='1'and pr['environment']['KEXE_CAP_RESOURCES_35']==pr['freshOutputRoot']and pr['C2']is False and pr['clobberCertificateQualified']is False and pr['candidateAdoptionQualified']is False,'unchanged compiler policy; stage HOLD')
 return True

def go_header(g,pr,O):
 keys=['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','integrationFixtureProof','baselineActualProof','TCActualProof','candidateSourcePinsSHA256','candidateActualProof']
 need(set(g)==set(keys),'exact GO keys');need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==6 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is False and g['C2']is False,'new compiler6 only')
 return True

def main(goPath):
 import time
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);rows=[];results=[];artifacts=[];generated={};ok=False
 go_header(g,pr,O)
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'exact GO identity')
 need(g['candidateSourcePinsSHA256']==pr['candidateSourcePins']['sha256'],'frozen candidate source')
 need(len(g['sourceReviews'])==2 and len(set(r['path']for r in g['sourceReviews']))==2,'two exact distinct reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'exact reviewed harness')
 for k in ['integrationFixtureProof','baselineActualProof','TCActualProof','candidateActualProof']:
  target='qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k;need(g[k]==pr[target],'exact inherited proof');pin(g[k]['path'],g[k])
 f=load(g['integrationFixtureProof']['path']);need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','qualified component scope')
 for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'same actual components')
 def guard():
  need(receipt(gp)==gr and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256'],'immutable GO/input registry')
  need(len(ip)==pr['exactInputFiles']<=256 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']<=33554432,'targeted closure finite')
  for n,r in sp.items():pin(D/n,r)
  for p,r in ip.items():pin(p,r)
  for p,r in generated.items():pin(p,r)
  source_scope(pr,ip)
 guard();need(not O.exists(),'fresh namespace');O.mkdir();save(O/'attempts.json',rows);save(O/'effective-environment.json',pr['environment']);save(O/'generated-pins.json',generated)
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);deadline=time.monotonic()+11100
 def artifact(path):
  r=receipt(path);need(r['bytes']<=4194560,'bounded artifact/seal');generated[str(path)]=r;save(O/'generated-pins.json',generated);return dict(path=str(path),**r)
 try:
  for name,src in [('vector-fixture.kotoba',pr['fixtureSource']),('statemate.kotoba',pr['statemateEntry']['source'])]:
   p=O/name;p.write_bytes(pin(src['path'],src).read_bytes());p.chmod(0o444);need(receipt(p)=={k:src[k]for k in ['bytes','sha256']},'exact source copy');artifact(p)
  for index,c in enumerate(pr['cases'],1):
   guard();need(time.monotonic()+1840<=deadline,'original finite campaign before new child')
   on=index>=3;nr=pr['candidateCompiler']if on else pr['offCompiler'];kr=pr['candidateCompilerContainer']if on else pr['offCompilerContainer'];inputPath=Path(c['nativeArgv'][8]);seal={'format':pr['invocationSealVersion'],'index':index,'label':c['label'],'nativeArgv':c['nativeArgv'],'producer':nr,'producerContainer':kr,'existingProducerProof':pr['candidateActualProof']if on else pr['TCActualProof'],'input':dict(path=str(inputPath),**receipt(inputPath)),'outputPath':c['outputPath'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256']};sealPath=O/(c['label']+'.admission.json');need(not sealPath.exists()and not Path(c['outputPath']).exists()and not Path(c['outputPath']).is_symlink(),'fresh outputs');save(sealPath,seal);need(sealPath.stat().st_size<=4096,'bounded seal');sealPath.chmod(0o444);sr=artifact(sealPath)
   r=mod.call(D,O,pr,c,rows,save,sr['sha256']);results.append(r);out=artifact(Path(c['outputPath']))
   if c['kind']=='compile':need(r['report']=={'kind':'compile','containerBytes':out['bytes']},'whole compiled container');container(Path(c['outputPath']).read_bytes())
   else:
    payload,exports=container(inputPath.read_bytes());entry=[e for e in exports if e[0]==c['symbol']];need(len(entry)==1 and entry[0][2]==1 and payload==Path(c['outputPath']).read_bytes()and r['report']=={'kind':'extract','offset':entry[0][1],'nativeBytes':out['bytes'],'arity':1},'whole extracted payload/own export');artifacts.append({'label':c['label'],'native':out,'container':dict(path=str(inputPath),**receipt(inputPath)),'selectedExport':entry[0],'exports':exports});save(O/'artifacts.json',artifacts)
   save(O/'results.json',results)
  guard();need(len(rows)==len(results)==6 and len(artifacts)==3 and all(r['state']=='terminal'and r['returncode']==0 for r in rows),'six closed compiler calls');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed']and not terminal['failure'],'durable terminal before COMPLETE')
 evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['attempts.json','results.json','artifacts.json','generated-pins.json','effective-environment.json','terminal.json']};save(O/'report.json',{'status':'COMPLETE_PUBLISHED_MODE2_X8_VECTOR_STATEMATE6_COMPILER_ARTIFACTS_ONLY','closedCompilerCalls':6,'artifacts':artifacts,'fixtureSource':pr['fixtureSource'],'unchangedStatemateSource':pr['statemateEntry']['source'],'candidateActualProof':pr['candidateActualProof'],'preservedCandidateBuildRootGO':pr['candidateBuildRootGO'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'evidence':evidence,'guestRuntimeExecuted':False,'actualTypedMode2AdmissionObserved':False,'stageClobberCertificateQualified':False,'candidateAdoptionQualified':False,'selfhostFixedpointQualified':False,'original19FunctionalQualified':False,'performanceQualified':False,'hardPeakQualified':False,'strictPhysicalMemoryQualified':False,'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact root GO');main(sys.argv[1])
