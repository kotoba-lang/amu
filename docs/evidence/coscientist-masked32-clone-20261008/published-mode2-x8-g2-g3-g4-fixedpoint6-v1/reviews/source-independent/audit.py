"""Independent SOURCE audit. File bytes and injected pure models only; no GO or native operations."""
from pathlib import Path
import hashlib,json,stat,ast,sys,runpy,contextlib,io,copy,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-g2-g3-g4-fixedpoint6-source-v1-20261009';R=W/'published-mode2-x8-fixedpoint6-source-review-independent-20261009'
receipts={}
def need(v,m):
 if not v:raise AssertionError(m)
def raw(p):
 p=Path(p)
 for q in [p,*p.parents]:need(not q.is_symlink(),'no symlink traversal '+str(q))
 a=p.lstat();need(stat.S_ISREG(a.st_mode) and a.st_size<=469762048,'bounded regular');b=p.read_bytes();z=p.lstat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stable bytes');receipts[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def pin(p,r):b=raw(p);need(receipts[str(Path(p))]=={k:r[k] for k in ['bytes','sha256']},'exact pin '+str(p));return b
def load(p):return json.loads(raw(p))
freeze=load(D/'freeze.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');delta=load(D/'delta.json')
need(len(sp)==freeze['sourceFiles']==21 and len(ip)==pr['exactInputFiles']==freeze['inputFiles']==50 and sum(r['bytes'] for r in ip.values())==pr['exactInputLogicalBytes']==freeze['inputLogicalBytes']==5292422,'closure')
for n,k in [('source-pins.json','sourcePins'),('input-pins.json','inputPins'),('preregistration.json','preregistration'),('run.py','driver')]:pin(D/n,freeze[k])
for n,r in sp.items():pin(D/n,r)
for p,r in ip.items():pin(p,r)
need(not Path(pr['freshOutputRoot']).exists() and not Path(pr['freshOutputRoot']).is_symlink(),'fresh output no runtime')
for p in D.glob('*.py'):ast.parse(raw(p),filename=str(p))
need(len(delta['unchangedComponents'])==8,'eight qualified components')
for n,r in delta['unchangedComponents'].items():pin(D/n,r);need(raw(D/n)==raw(Path(delta['baseWorkspace'])/n),'actual copied component '+n)
sys.dont_write_bytecode=True;sys.path.insert(0,str(D));import run
need(run.source_scope(pr,ip),'exact source scope')
need([c['generation'] for c in pr['cases']]==[2,2,3,3,4,4] and [c['kind'] for c in pr['cases']]==['compile','extract']*3,'exact calls')
need(pr['maximumLoaderCalls']==6 and pr['fixedpointGenerations']==[2,3,4] and pr['requireG2G3G4WholeEqual'] is True and pr['requireG1G2Equal'] is False,'fixedpoint scope')
fixture=load(pr['qualifiedIntegrationFixtureProof']['path']);need(fixture['status']=='PASS_INDEPENDENT_SAVED_FILEIO_CAPTURE_CONTROLLER_FIXTURE_ONLY','actual ownership fixture')
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:need(fixture[k]==sp[n]['sha256'],'fixture exact source')
proto=load(pr['loaderSupervisorProtocolView']['path']);need(proto['OSClosureTraceQualified'] is False and proto['universalCompilerProof'] is False,'protocol conditional only')
for r in proto['pins']:pin(r['path'],r)
cs,bp,lp,wp=proto['pins'];need(cs['sha256'].startswith('f44b5099') and bp['sha256'].startswith('5f7c433c') and lp['sha256'].startswith('e14c2919'),'exact loader lineage')
lines=raw(cs['path']).decode().splitlines(keepends=True)
for span in proto['spans']:need(hashlib.sha256(''.join(lines[span['start']-1:span['end']]).encode()).hexdigest()==span['sha256'],'source span digest')
need(pr['environment']['KEXE_FUEL']=='off' and len(pr['environment'])==17 and pr['capabilities']=='35,37,38,39','environment/grants')
need(pr['nativeCPUSeconds']==1800 and pr['kernelCPUHardSeconds']==1801 and pr['outerWallSeconds']==1810 and pr['cleanupSeconds']==30 and pr['maximumSequentialCampaignSeconds']==11100 and pr['controlledOutputReservationBytes']==1073741824,'resource bounds')
# Run reviewed pure controls only; neither control invokes operational APIs.
controls=[];namespaces=[]
for name in ['pure-controls','wrapper-controls']:
 out=io.StringIO()
 with contextlib.redirect_stdout(out):ns=runpy.run_path(str(D/(name+'.py')),run_name='independent_pure_audit')
 result=json.loads(out.getvalue());need(result==load(D/(name+'.json')),'saved pure result reproduction '+name);need(result['operationalCalls']==0,'pure no operations');controls.append(result);namespaces.append(ns)
need(len(controls[0]['refusedMutants'])==47 and len(controls[1]['refusedMutants'])==12 and controls[1]['positiveCases']==6,'pure mutant counts')
# Independent recursive chain mutations, with deliberately recalculated outer hashes.
ns=namespaces[1];files=ns['files'];basefiles=copy.deepcopy(files);modelbuilds=ns['builds'];P=ns['P'];rec=ns['rec'];pinned=ns['pinned'];realPath=run.Path;realPin=run.pin;run.Path=P;run.pin=pinned
neg=[]
try:
 for generation,field,value in [(2,'returncode',1),(2,'state','unclosed'),(2,'failure','synthetic'),(3,'returncode',2),(3,'captureStopAcknowledged',False),(3,'waitUncertain',True)]:
  files.clear();files.update(copy.deepcopy(basefiles));chain=copy.deepcopy(modelbuilds);chain[generation]['attempts'][0][field]=value
  for g in range(generation,4):
   path=str(Path(pr['freshOutputRoot'])/('G'+str(g)+'-build-receipt.json'));files[path]=json.dumps(chain[g]).encode()
   if g+1<=4:chain[g+1]['builderBuild']=rec(path)
  b=chain[4]
  try:run.build_guard(b,pr,b['native'],b['container'],b['rootGO'],4)
  except (AssertionError,KeyError,TypeError,IndexError):neg.append('nested-G'+str(generation)+'-'+field)
  else:raise AssertionError('nested mutation admitted')
finally:files.clear();files.update(basefiles);run.Path=realPath;run.pin=realPin
# Source structure binds all operational entrypoints behind main/GO, finite admission/terminal guards.
text=raw(D/'run.py').decode();native=raw(D/'native-call.py').decode();wrapper=raw(D/'launch-wrapper.py').decode()
for s in ["need(len(g['sourceReviews'])==2", "for p,r in generated.items():pin(p,r)","build_guard(load(pin(pb['path'],pb))","need(time.monotonic()+1840<=deadline", "finally:save(O/'terminal.json'", "fixedpoint(artifacts)","contents[0]==contents[1]==contents[2]"]:need(s in text,'driver structural guard '+s)
for s in ["start_new_session=True","close_fds=True","pass_fds=(limitFile.fileno(),)","not waitCalled","captureAck","stopWatchdog", "proc.wait(timeout=max(.001,min(30,budget)))"]:need(s in native,'native lifecycle '+s)
for s in ["build_guard(json.loads", "KEXE_CAP_RESOURCES_35", "nativeExecEnvironmentExact", "resource.setrlimit", "not Path(c['outputPath']).exists()", "os.execve(argv[0],argv,dict(pr['environment']))"]:need(s in wrapper,'wrapper guard '+s)
for p,r in list(receipts.items()):pin(p,r)
report={'status':pr['sourceReviewStatus'],'independent':True,'priorImplementationAuthorship':False,'sourcePinsSHA256':receipts[str(D/'source-pins.json')]['sha256'],'inputPinsSHA256':receipts[str(D/'input-pins.json')]['sha256'],'preregistrationSHA256':receipts[str(D/'preregistration.json')]['sha256'],'driverSHA256':receipts[str(D/'run.py')]['sha256'],'verifiedClosure':{'sourceFiles':21,'inputFiles':50,'inputLogicalBytes':5292422},'candidateSource':pr['sourceCandidate'],'G1Native':pr['G1Native'],'G1Container':pr['G1Container'],'candidateSourcePinsSHA256':pr['candidateSourcePins']['sha256'],'fixedCompilerCalls':6,'fixedpointGenerations':[2,3,4],'requireWholeNativeContainerExportsEquality':True,'G1EqualityRequired':False,'qualifiedCopiedComponents':8,'pureControls':controls,'independentNestedReceiptMutantsRefused':neg,'operationalSafetyAssessment':'No blocking SOURCE gap found for the declared one-off six-call diagnostic. Exact GO/two reviews and host launch still required. Recursive producer receipts bind whole artifacts and same current-GO two-call admission before reuse; loader protocol remains conditional source correspondence.','nonBlockingLimits':['The unchanged native-call outer count guard is len(rows)<36, but indexing exact six preregistered cases refuses seventh before sampler/API setup; pure control confirms.','4096 controller event cap may refuse a long compiler call before the 90502 sample/1800-second ceilings; this is a preserved refusal bound, not a guarantee every call can run to those ceilings.','Sampled aggregate footprint and declared filesystem reservation are not hard memory or disk quotas.','Targeted interpreter binary pin does not cover all dynamic loader/runtime binaries.','Machine clobber certificate, candidate adoption, full original19 and C timing remain HOLD.'],'blockingFindings':[],'noGOProduced':True,'nativeGuestProcessThreadFDResourceNetworkOperations':0,'runtimeExecuted':False,'productFilesChanged':0,'C2':False,'checkedRegularPins':receipts,'auditor':{'path':str(R/'audit.py'),'bytes':len((R/'audit.py').read_bytes()),'sha256':hashlib.sha256((R/'audit.py').read_bytes()).hexdigest()}}
(R/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'sha256':hashlib.sha256((R/'report.json').read_bytes()).hexdigest(),'checkedFiles':len(receipts),'independentMutants':len(neg)}))
