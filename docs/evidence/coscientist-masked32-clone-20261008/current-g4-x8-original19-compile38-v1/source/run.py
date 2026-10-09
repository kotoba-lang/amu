"""Inert SOURCE. Published mode2 x8 G4 original19 compile38 compiler commands only after exact two reviews and GO."""
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
 need(c in pr['cases']and len(pr['cases'])==38 and argv==c['nativeArgv'],'38 exact current G4 commands')
 O=Path(pr['freshOutputRoot']);e=next(x for x in pr['entries']if x['workload']==c['workload']);need(c['kind']in ['compile','extract']and c['symbol']==e['symbol']and c['arity']==1 and c['producer']==pr['currentCompiler']['path'],'original own export, current G4 only')
 output=str(O/(c['workload']+('.kseed'if c['kind']=='compile'else'.bin')));inputPath=str(O/(c['workload']+('.kotoba'if c['kind']=='compile'else'.kseed')))
 args=['compile',inputPath,'--target','aarch64-macos','--output',output]if c['kind']=='compile'else['extract-native',inputPath,'--symbol',c['symbol'],'--output',output]
 need(c['outputPath']==output and argv==[pr['loader'],pr['currentCompiler']['path'],'0','0','aarch64','35,37,38,39','--']+args,'compiler main0 guest argv and owned IO')
 return True

def existing_g4_guard(pr):
 q=load(pin(pr['fixedpointActualProof']['path'],pr['fixedpointActualProof']))
 need(q['status']==pr['fixedpointActualProofStatus']and q['sourceCandidate']==pr['sourceCandidate']and q['G2G3G4WholeNativeEqual']is True and q['G2G3G4WholeContainerEqual']is True and q['G2G3G4WholeExportsEqual']is True,'saved current G4 complete fixedpoint proof')
 a=q['wholeArtifactsAndOwnExports'][2];need(a['generation']==4 and a['native']==pr['currentCompiler']and a['container']==pr['currentCompilerContainer']and a['exports']==[['main',0,0]]and q['generatedProducerReceipts']['4']==pr['fixedpointBuildReceipt'],'specific G4 owner/receipt')
 pin(pr['fixedpointBuildReceipt']['path'],pr['fixedpointBuildReceipt'])
 return True

def source_scope(pr,ip):
 proof=load(pin(pr['fixedpointActualProof']['path'],pr['fixedpointActualProof']));need(proof['status']==pr['fixedpointActualProofStatus']and proof['closedCompilerCalls']==6 and proof['G2G3G4WholeNativeEqual']is True and proof['G2G3G4WholeContainerEqual']is True and proof['G2G3G4WholeExportsEqual']is True and proof['sourceCandidate']==pr['sourceCandidate'],'current G4 exact fixedpoint proof, limited scope')
 images=proof['wholeArtifactsAndOwnExports'];need([i['generation']for i in images]==[2,3,4]and images[2]['native']==pr['currentCompiler']and images[2]['container']==pr['currentCompilerContainer']and images[2]['exports']==[['main',0,0]],'exact G4 whole owner, no G1 substitute')
 for im in images:
  payload,exports=container(pin(im['container']['path'],im['container']).read_bytes());need(payload==pin(im['native']['path'],im['native']).read_bytes()and exports==[('main',0,0)],'all generation whole compiler payloads')
 need(len(set(im['native']['sha256']for im in images))==len(set(im['container']['sha256']for im in images))==1,'whole generation identity')
 old=load(pin(pr['fixedpointPreregistration']['path'],pr['fixedpointPreregistration']));need(old['sourceCandidate']==pr['sourceCandidate']and proof['sourcePinsSHA256']==pr['fixedpointSourcePins']['sha256']and proof['generatedProducerReceipts']['4']==pr['fixedpointBuildReceipt'],'exact old admitted source and producer receipt')
 for r in proof['generatedProducerReceipts'].values():pin(r['path'],r)
 root=proof['rootGO'];pin(root['path'],root)
 from fixedpoint_lineage import build_guard
 build_guard(load(pr['fixedpointBuildReceipt']['path']),old,pr['currentCompiler'],pr['currentCompilerContainer'],root,4)
 assembly=load(pin(pr['sourceAssembly']['path'],pr['sourceAssembly']));need(len(assembly['offModulePins'])==16,'current16 whole source closure');mods=[pin(r['path'],r).read_bytes()for r in assembly['offModulePins']];need(hashlib.sha256(b''.join(x+b'\n'for x in mods)).hexdigest()=='94fe39401f5f0a1120b12b2d17bf000d14a54c9c68e1f8976b8b0ced8794f199','whole TC lineage');mods[10]=pin(assembly['onReplacementModule']['path'],assembly['onReplacementModule']).read_bytes();need(b''.join(x+b'\n'for x in mods)==pin(pr['sourceCandidate']['path'],pr['sourceCandidate']).read_bytes()and pr['sourceCandidate']['sha256']=='dcb9a0f229c9747495f4415b40143cb0b7aed692a06b71cec15ef4612201a971','current x8 unity exact')
 matrix=load(pin(pr['canonicalMatrix']['path'],pr['canonicalMatrix']));need(len(pr['entries'])==len(matrix['entries'])==19 and len(pr['cases'])==38,'full original19/38')
 labels=[]
 for e,m in zip(pr['entries'],matrix['entries']):
  need(e['workload']==m['workload']and e['symbol']==m['symbol']and e['iterations']==m['iterations']and e['source']['sha256']==m['expectedSourceSha256']and e['source']['path']=='/Users/junkawasaki/github/wt/amu-seed17/'+m['source'],'unchanged original matrix source/export/profiles');pin(e['source']['path'],e['source']);labels +=[e['workload']+'-compile',e['workload']+'-extract']
 need([c['label']for c in pr['cases']]==labels and all(compiler_case(c['nativeArgv'],pr,c)for c in pr['cases']),'exact all38 current G4 cases')
 O=pr['freshOutputRoot'];need(pr['environment']=={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':O,'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_FUEL':'off','KEXE_ARENA_USE':'1','PYTHONNOUSERSITE':'1','KEXE_CAP_RESOURCES_35':O,'KEXE_COMMAND':'1'}and pr['capabilities']=='35,37,38,39'and pr['compileFuel']=='off','same compiler17 resources/caps/fuel')
 pv=load(pin(pr['loaderSupervisorProtocolView']['path'],pr['loaderSupervisorProtocolView']));need(pv['status']=='SOURCE_PROTOCOL_VIEW_ONLY_NOT_DYNAMIC_PROCESS_PROOF','conditional loader protocol only')
 for r in pv['pins']:pin(r['path'],r)
 cs,bp,lp,_=pv['pins'];b=load(bp['path']);need(lp==pr['loaderArtifact']and b['loader']==lp and b['CSourceSHA256']==cs['sha256']and b['status']==pv['savedBuildProofStatus'],'source-bound e14 loader')
 need(pr['operationalEnvironment']=={'version':'host-authorized-loader-owned-sandbox-v1','requiresOuterHostEscalation':True,'loaderOwnedSandboxRequired':True,'loaderSandboxWeakeningAuthorized':False,'hostEscalationDeclarationIsNotKernelMeasurement':True}and pr['C2']is False and pr['timingAuthorized']is False and pr['runtimeGuestAuthorized']is False and pr['candidateAdoptionQualified']is False and pr['clobberCertificateQualified']is False and pr['reusesPreviousWorkloadArtifacts']is False,'current compile artifacts only, broad HOLD')
 np=load(pin(pr['nativeCallerActualProof']['path'],pr['nativeCallerActualProof']));ns=load(pin(pr['nativeCallerSourcePins']['path'],pr['nativeCallerSourcePins']))
 need(np['status']=='PASS_INDEPENDENT_SAVED_FAILURE_TC_REMAINING42_FIXEDPOINT_V3_ONLY'and np['sourcePinsSHA256']==pr['nativeCallerSourcePins']['sha256']and receipt(D/'native-call.py')==ns['native-call.py'],'unchanged previously audited42 caller; old refusal remains failed')
 need(pr['maximumLoaderCalls']==38 and pr['maximumSequentialCampaignSeconds']==71000 and pr['controlledOutputReservationBytes']==2147483648,'explicit38 campaign/time/output policy')
 return True

PROOF_KEYS=['fixedpointActualProof','integrationFixtureProof']
def go_header(g,pr,O):
 need(set(g)==set(['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','candidateSourcePinsSHA256']+PROOF_KEYS),'exact GO keys')
 need(g['status']==pr['rootGOStatus']and g['maximumLoaderCalls']==38 and g['outputRoot']==str(O)and g['noRetry']is True and g['timingAuthorized']is False and g['runtimeGuestAuthorized']is False and g['C2']is False and g['outerHostLaunchRequiresEscalation']is True,'exact new G4 compile38 only')
 return True

def main(goPath):
 import time
 gp=Path(goPath);g=load(gp);gr=receipt(gp);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);rows=[];results=[];artifacts=[];generated={};ok=False
 go_header(g,pr,O)
 for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(receipt(D/n)['sha256']==g[k],'exact source GO identity')
 need(g['candidateSourcePinsSHA256']==pr['candidateSourcePins']['sha256'],'candidate source frozen')
 need(len(g['sourceReviews'])==2 and len(set(r['path']for r in g['sourceReviews']))==2,'two exact distinct reviews')
 for r in g['sourceReviews']:
  q=load(pin(r['path'],r));need(q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'specific reviewed SOURCE')
 for k in PROOF_KEYS:
  target='qualifiedIntegrationFixtureProof'if k=='integrationFixtureProof'else k;need(g[k]==pr[target],'exact proof receipt');pin(g[k]['path'],g[k])
 f=load(g['integrationFixtureProof']['path']);need(f['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','actual component fixture scope')
 for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(f[k]==sp[n]['sha256'],'unchanged qualified components')
 def guard():
  need(receipt(gp)==gr and receipt(D/'input-pins.json')['sha256']==g['inputPinsSHA256']==pr['inputPinsSHA256'],'immutable GO/input registry')
  need(len(ip)==pr['exactInputFiles']<=256 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']<=33554432,'bounded targeted regular input closure')
  for n,r in sp.items():pin(D/n,r)
  for p,r in ip.items():pin(p,r)
  for p,r in generated.items():pin(p,r)
  source_scope(pr,ip)
 guard();need(not O.exists(),'fresh namespace');O.mkdir();save(O/'attempts.json',rows);save(O/'effective-environment.json',pr['environment']);save(O/'generated-pins.json',generated)
 spec=importlib.util.spec_from_file_location('bounded_native',D/'native-call.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);deadline=time.monotonic()+71000
 def artifact(p):
  r=receipt(p);need(r['bytes']<=4194560,'bounded artifact');generated[str(p)]=r;save(O/'generated-pins.json',generated);return dict(path=str(p),**r)
 try:
  for e in pr['entries']:
   p=O/(e['workload']+'.kotoba');p.write_bytes(pin(e['source']['path'],e['source']).read_bytes());p.chmod(0o444);need(receipt(p)=={k:e['source'][k]for k in ['bytes','sha256']},'immutable original workload copy');artifact(p)
  for index,c in enumerate(pr['cases'],1):
   guard();need(time.monotonic()+1840<=deadline,'finite38 campaign before another child');inputPath=Path(c['nativeArgv'][8]);seal={'format':pr['invocationSealVersion'],'index':index,'label':c['label'],'nativeArgv':c['nativeArgv'],'producer':pr['currentCompiler'],'producerContainer':pr['currentCompilerContainer'],'existingProducerProof':pr['fixedpointActualProof'],'input':dict(path=str(inputPath),**receipt(inputPath)),'outputPath':c['outputPath'],'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'preregistrationSHA256':g['preregistrationSHA256']};p=O/(c['label']+'.admission.json');need(not p.exists()and not Path(c['outputPath']).exists()and not Path(c['outputPath']).is_symlink(),'fresh exact output/seal');save(p,seal);need(p.stat().st_size<=4096,'bounded seal');p.chmod(0o444);sr=artifact(p)
   r=mod.call(D,O,pr,c,rows,save,sr['sha256']);results.append(r);out=artifact(Path(c['outputPath']))
   if c['kind']=='compile':need(r['report']=={'kind':'compile','containerBytes':out['bytes']},'whole compiler output');container(Path(c['outputPath']).read_bytes())
   else:
    packed=dict(path=str(inputPath),**receipt(inputPath));payload,exports=container(inputPath.read_bytes());entry=[e for e in exports if e[0]==c['symbol']];need(len(entry)==1 and entry[0][2]==1 and payload==Path(c['outputPath']).read_bytes()and r['report']=={'kind':'extract','offset':entry[0][1],'nativeBytes':out['bytes'],'arity':1},'new entire extracted payload/own export')
    e=next(e for e in pr['entries']if e['workload']==c['workload']);artifacts.append(dict(workload=c['workload'],source=e['source'],symbol=c['symbol'],iterations=e['iterations'],native=out,container=packed,selectedExport=entry[0],exports=exports));save(O/'artifacts.json',artifacts)
   save(O/'results.json',results)
  guard();need(len(rows)==len(results)==38 and len(artifacts)==19 and all(r['state']=='terminal'and r['returncode']==0 for r in rows),'38 new admitted closed compiler calls/19 whole images');ok=True
 except BaseException as ex:save(O/'failure.json',{'error':repr(ex),'loaderCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'loaderCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
 guard();terminal=load(O/'terminal.json');need(ok and terminal['allChildrenClosed']is True and terminal['failure']is False,'durable terminal before valid-last COMPLETE')
 evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['attempts.json','results.json','artifacts.json','generated-pins.json','effective-environment.json','terminal.json']};save(O/'report.json',dict(status='COMPLETE_PUBLISHED_MODE2_X8_G4_ORIGINAL19_COMPILE38_ARTIFACTS_ONLY',closedCompilerCalls=38,original19Images=artifacts,currentG4Native=pr['currentCompiler'],currentG4Container=pr['currentCompilerContainer'],fixedpointActualProof=pr['fixedpointActualProof'],rootGO=dict(path=str(gp),**gr),sourcePinsSHA256=g['sourcePinsSHA256'],evidence=evidence,reusedPreviousWorkloadArtifacts=False,guestRuntimeExecuted=False,full19FunctionalQualified=False,stageClobberCertificateQualified=False,candidateAdoptionQualified=False,performanceQualified=False,hardPeakQualified=False,strictPhysicalMemoryQualified=False,C2=False))
if __name__=='__main__':
 import sys
 need(len(sys.argv)==2,'one exact root GO');main(sys.argv[1])
