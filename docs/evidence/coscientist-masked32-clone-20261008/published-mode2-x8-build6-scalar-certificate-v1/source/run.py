"""Inert SOURCE. Published mode2 x8 candidate/fixture6 compiler commands only after exact two reviews and GO."""
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

def source_scope(pr,ip):
 need(len(pr['cases'])==6 and [c['label']for c in pr['cases']]==['candidate-compile','candidate-extract','OFF-fixture-compile','OFF-fixture-extract','ON-fixture-compile','ON-fixture-extract'],'fixed six order')
 need([c['producer']for c in pr['cases']]==[pr['producer']]*2+[pr['offCompiler']['path']]*2+[pr['candidateNativePath']]*2,'fixed builder OFF and candidate only')
 need(all(compiler_case(c['nativeArgv'],pr,c)for c in pr['cases']),'precise guest command grammar')
 challenge=load(pin(pr['candidateSourceChallenge']['path'],pr['candidateSourceChallenge']));need(challenge['status']==pr['candidateSourceChallengeStatus']and challenge['sourcePinsSHA256']==pr['candidateSourcePins']['sha256'],'preserved source challenge HOLD');a=load(pin(pr['sourceAssembly']['path'],pr['sourceAssembly']));need(len(a['offModulePins'])==16 and len(a['modules'])==16,'current16 assembly')
 off=b''.join(pin(r['path'],r).read_bytes()+b'\n'for r in a['offModulePins']);need(hashlib.sha256(off).hexdigest()=='94fe39401f5f0a1120b12b2d17bf000d14a54c9c68e1f8976b8b0ced8794f199','current whole TC source')
 mods=[Path(r['path']).read_bytes()for r in a['offModulePins']];mods[10]=pin(a['onReplacementModule']['path'],a['onReplacementModule']).read_bytes();need(b''.join(b+b'\n'for b in mods)==pin(pr['sourceCandidate']['path'],pr['sourceCandidate']).read_bytes(),'exact novel rule replacement only')
 need(pr['sourceCandidate']['sha256']=='dcb9a0f229c9747495f4415b40143cb0b7aed692a06b71cec15ef4612201a971'and pr['clobberCertificateQualified']is False and pr['candidateAdoptionQualified']is False,'candidate source only; no stage certificate')
 baseline=load(pin(pr['baselineActualProof']['path'],pr['baselineActualProof']));tc=load(pin(pr['TCActualProof']['path'],pr['TCActualProof']));need(baseline['status']==pr['baselineActualProofStatus']and baseline['currentProducerBindingQualified']is True and baseline['wholeBaselineNative']==ip[pr['producer']],'audited current7618 builder')
 need(tc['status']==pr['TCActualProofStatus']and tc['G0Native']==pr['offCompiler']and tc['G0Container']==pr['offCompilerContainer']and tc['current16OwnSource']['sha256']==a['offUnity']['sha256']and tc['G0G1G2G3WholeNativeEqual']is True,'audited exact TC OFF compiler')
 for n,k in [(pr['producer'],pr['producerContainer']),(pr['offCompiler']['path'],pr['offCompilerContainer']['path'])]:
  payload,exports=container(Path(k).read_bytes());need(payload==Path(n).read_bytes()and exports==[('main',0,0)],'whole compiler main0')
 need(len(pr['environment'])==17 and pr['environment']['KEXE_FUEL']=='off'and pr['environment']['KEXE_COMMAND']=='1'and pr['environment']['KEXE_CAP_RESOURCES_35']==pr['freshOutputRoot']and pr['C2']is False,'compiler caps/fuel/environment retained')
 return True

def go_header(g,pr,O):
 keys=['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','integrationFixtureProof','baselineActualProof','TCActualProof','candidateSourcePinsSHA256']
 need(set(g)==set(keys),'exact GO fields');need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==6 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is False and g['C2']is False,'compiler6 only, no guest/certificate/adoption')
 return True

def main(goPath):
 import time
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);rows=[];results=[];artifacts=[];generated={};ok=False;producerBuild=None
 go_header(g,pr,O)
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'exact GO identity')
 need(g['candidateSourcePinsSHA256']==pr['candidateSourcePins']['sha256'],'frozen rule source')
 need(len(g['sourceReviews'])==2 and len(set(r['path']for r in g['sourceReviews']))==2,'two distinct exact SOURCE reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'specific reviewed harness')
 for k in ['integrationFixtureProof','baselineActualProof','TCActualProof']:
  target='qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k;need(g[k]==pr[target],'fixed proof');pin(g[k]['path'],g[k])
 f=load(g['integrationFixtureProof']['path']);need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','component fixture scope')
 for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'same actual qualified components')
 def guard():
  need(receipt(gp)==gr and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256'],'immutable GO/input registry')
  need(len(ip)==pr['exactInputFiles']<=256 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']<=33554432,'bounded targeted launch closure')
  for n,r in sp.items():pin(D/n,r)
  for p,r in ip.items():pin(p,r)
  for p,r in generated.items():pin(p,r)
  source_scope(pr,ip)
 guard();need(not O.exists(),'fresh namespace');O.mkdir();save(O/'attempts.json',rows);save(O/'effective-environment.json',pr['environment']);save(O/'generated-pins.json',generated)
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);deadline=time.monotonic()+11100
 def artifact(path):
  r=receipt(path);need(r['bytes']<=4194560,'bounded artifact or sealed metadata');generated[str(path)]=r;save(O/'generated-pins.json',generated);return dict(path=str(path),**r)
 try:
  for name,k in [('candidate-source.kotoba','sourceCandidate'),('fixture-source.kotoba','fixtureSource')]:
   p=O/name;p.write_bytes(Path(pr[k]['path']).read_bytes());p.chmod(0o444);need(receipt(p)=={q:pr[k][q]for q in ['bytes','sha256']},'whole immutable input copy');artifact(p)
  for index,c in enumerate(pr['cases'],1):
   guard();need(time.monotonic()+1840<=deadline,'finite campaign before child')
   producer=c['producer'];pk=pr['producerContainer']if producer==pr['producer']else pr['offCompilerContainer']['path']if producer==pr['offCompiler']['path']else pr['candidateContainerPath']
   nr=dict(path=producer,**receipt(producer));kr=dict(path=pk,**receipt(pk));payload,exports=container(Path(pk).read_bytes());need(payload==Path(producer).read_bytes()and exports==[('main',0,0)],'specific complete compiler producer')
   if index>=5:need(producerBuild is not None and build_guard(load(producerBuild['path']),pr,nr,kr,dict(path=str(gp),**gr)),'closed generated producer before its execution')
   inputPath=Path(c['nativeArgv'][8]);seal={'format':pr['invocationSealVersion'],'index':index,'label':c['label'],'nativeArgv':c['nativeArgv'],'producer':nr,'producerContainer':kr,'producerBuild':producerBuild if index>=5 else None,'input':dict(path=str(inputPath),**receipt(inputPath)),'outputPath':c['outputPath'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256']};sealPath=O/(c['label']+'.admission.json');need(not sealPath.exists()and not Path(c['outputPath']).exists()and not Path(c['outputPath']).is_symlink(),'fresh exact outputs');save(sealPath,seal);need(sealPath.stat().st_size<=4096,'bounded seal');sealPath.chmod(0o444);sr=artifact(sealPath)
   r=mod.call(D,O,pr,c,rows,save,sr['sha256']);results.append(r);out=artifact(Path(c['outputPath']))
   if c['kind']=='compile':need(r['report']=={'kind':'compile','containerBytes':out['bytes']},'entire declared container');container(Path(c['outputPath']).read_bytes())
   else:
    payload,exports=container(inputPath.read_bytes());entry=[e for e in exports if e[0]==c['symbol']];need(len(entry)==1 and entry[0][2]==c['arity']and payload==Path(c['outputPath']).read_bytes()and r['report']=={'kind':'extract','offset':entry[0][1],'nativeBytes':out['bytes'],'arity':c['arity']},'whole extracted payload and own export ABI');artifacts.append({'label':c['label'],'native':out,'container':dict(path=str(inputPath),**receipt(inputPath)),'selectedExport':entry[0],'exports':exports});save(O/'artifacts.json',artifacts)
   save(O/'results.json',results)
   if index==2:
    need(artifacts[-1]['exports']==[('main',0,0)],'generated candidate sole-main0');b={'format':'published-mode2-x8-sealed-producer/v1','source':pr['sourceCandidate'],'builder':dict(path=pr['producer'],**ip[pr['producer']]),'native':artifacts[-1]['native'],'container':artifacts[-1]['container'],'rootGO':dict(path=str(gp),**gr),'closedCompilerCalls':2,'attempts':rows.copy(),'certificateQualified':False};build_guard(b,pr,b['native'],b['container'],b['rootGO']);bp=O/'candidate-build-receipt.json';save(bp,b);bp.chmod(0o444);producerBuild=artifact(bp)
  guard();need(len(rows)==len(results)==6 and len(artifacts)==3 and all(r['state']=='terminal'and r['returncode']==0 for r in rows),'all six closed compiler-only calls');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed']is True and terminal['failure']is False,'durable closed valid-last terminal')
 evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['attempts.json','results.json','artifacts.json','generated-pins.json','candidate-build-receipt.json','effective-environment.json','terminal.json']};save(O/'report.json',{'status':'COMPLETE_PUBLISHED_MODE2_X8_BUILD_FIXTURE6_COMPILER_ARTIFACTS_ONLY','closedCompilerCalls':6,'artifacts':artifacts,'candidateSource':pr['sourceCandidate'],'fixtureSource':pr['fixtureSource'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'evidence':evidence,'guestRuntimeExecuted':False,'stageClobberCertificateQualified':False,'candidateAdoptionQualified':False,'selfhostFixedpointQualified':False,'original19FunctionalQualified':False,'performanceQualified':False,'hardPeakQualified':False,'strictPhysicalMemoryQualified':False,'C2':False})
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact root GO');main(sys.argv[1])
