from pathlib import Path
import json,stat,hashlib,sys,importlib.util,copy
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'held-launch-v6-loader-build5-source-v3-20261009-independent';S=W/'current-runtime-process-ownership-race-source-v6-20261009-independent';O=S/'loader-build-outputs';G=W/'held-launch-v6-loader-build5-go-v3-root-20261009/root-go.json';A=Path(__file__).resolve().parent
seen={}
def ref(p,cap=402653184):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size<=cap;b=p.read_bytes();t=p.lstat();assert(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns);r={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};seen[str(p)]=r;return dict(path=str(p),**r)
def bare(p,cap=402653184):return {k:ref(p,cap)[k]for k in ['bytes','sha256']}
def load(p):return json.loads(Path(p).read_bytes())
def pin(r):assert bare(r['path'])=={k:r[k]for k in ['bytes','sha256']};return Path(r['path'])
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');go=load(G);subject=load(S/'preregistration.json');ss=load(S/'source-pins.json')
expected={'source-pins.json':'03df957a33c729761d7dc58350ba53b47fd12fafee7ee92b0236369c25d9ae44','input-pins.json':'8ec828444aff1db348d4eec931169621cefdd73df5ff06290d9e4497f54973e5','run.py':'5b30fcda0d44aea664e5cdfa19cfee25e676f9345823644184143f841ed35bf7','preregistration.json':'11a5aa2c0a9b3dcd47343e67b463f1a89c2f701c6cf53e82e27a5ed4e7f57c4e'}
for name,h in expected.items():assert ref(D/name)['sha256']==h
for name,key in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:assert go[key]==expected[name]
assert len(sp)==9 and len(ip)==65 and sum(v['bytes']for v in ip.values())==406915672
for p,v in sp.items():assert bare(D/p)==v
for p,v in ip.items():assert bare(p)==v
for p,v in ss.items():assert bare(S/p)==v
sys.path.insert(0,str(D));import run
assert run.scope(pr,ip)
assert set(go)=={'status','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','subjectReviews','maximumChildCalls','guestAuthorized','noRetry'} and go['status']==pr['rootGOStatus'] and go['maximumChildCalls']==5 and go['guestAuthorized']is False and go['noRetry']is True
for field,status in [('sourceReviews',pr['sourceReviewStatus']),('subjectReviews',pr['subjectReviewStatus'])]:
 assert len(go[field])==2 and len({z['path']for z in go[field]})==2
 for z in go[field]:
  q=load(pin(z));assert q['status']==status and q['sourcePinsSHA256']==(go['sourcePinsSHA256']if field=='sourceReviews'else pr['subjectSourcePins']['sha256']);assert q['driverSHA256']==(go['driverSHA256']if field=='sourceReviews'else pr['subjectDriver']['sha256']) and q['preregistrationSHA256']==(go['preregistrationSHA256']if field=='sourceReviews'else pr['subjectPreregistration']['sha256'])
co=load(O/'report.json');at=load(O/'attempts.json');term=load(O/'terminal.json');dep=load(O/'dependency-input-pins.json');sh=load(O/'local-header-shadow-paths.json');gr=ref(G)
assert term=={'childCalls':5,'allDirectChildrenClosed':True,'failure':False,'descendantClosureUniversal':False} and len(at)==5 and not(O/'failure.json').exists()
assert co['status']=='COMPLETE_SOURCE_BOUND_HELD_LAUNCH_V6_LOADER_BUILD5_V3_IDENTITY_ONLY' and co['childCalls']==5 and co['buildCalls']==1 and co['guestCalls']==0 and co['source']==pr['source']and co['compiler']==pr['compiler']and co['sdk']==pr['sdk'] and co['rootGO']==gr and co['sourcePinsSHA256']==go['sourcePinsSHA256']
for n,z in co['evidence'].items():assert z['path']==str(O/n);pin(z)
assert all(co[k]is False for k in ['sdkWholeTreeQualified','lifecycleFixtureQualified','functionalQualified','performanceQualified','cleanBuildDiagnosticsQualified','C2'])
calls=[]
for c,a in zip(pr['cases'],at):
 assert a['label']==c['label']and a['argv']==c['argv'] and a['state']=='terminal'and a['returncode']==0 and a['waitEntered']is True and type(a['pid'])is int and a['pid']>0 and not a.get('timeout')and not a.get('cleanupError')
 raw={}
 for k in ['stdout','stderr']:
  p=O/(c['label']+'.'+k);assert bare(p,1048576)==a[k];raw[k]=ref(p,1048576)
 b=Path(raw['stdout']['path']).read_bytes();e=Path(raw['stderr']['path']).read_bytes()
 if c['label'].startswith('version'):assert e==b''and b.startswith(b'Apple clang version ')and len(b)<=16384
 elif c['label']=='dependencies':assert run.bounded_diagnostic(e)==a['diagnosticEvidence'];assert set(run.dependencies(b,pr))==set(dep);assert sh==run.local_header_shadows(list(dep),pr);run.absent_paths(sh)
 elif c['label']=='link-preview':assert b==b''and run.preview(e,pr,ip)==load(O/'link-preview.json')
 else:assert b==b''and run.bounded_diagnostic(e)==a['diagnosticEvidence']
 calls.append({'label':c['label'],'argv':c['argv'],'pid':a['pid'],'directWait':0,'raw':raw,'diagnosticEvidence':a.get('diagnosticEvidence')})
assert len({x['pid']for x in at})==5 and (O/'version-before.stdout').read_bytes()==(O/'version-after.stdout').read_bytes()
assert len(dep)<=4096 and sum(z['bytes']for z in dep.values())<=67108864
for p,v in dep.items():assert bare(p,67108864)==v
run.absent_paths(pr['localLibraryShadowPaths']);loader=co['loader'];assert loader==load(O/'loader.json');pin(loader);assert loader['bytes']==215224 and loader['sha256']=='35441a47f8c2f64adde93a08d98767ca94c9c22078fdd5889df2228e98b7078c';names=run.macho_loader(Path(loader['path']).read_bytes(),pr);assert names==load(O/'loader-load-names.json')
assert pr['cases'][3]['argv']==subject['prospectiveLoaderBuildArgv']
# Pure actual-word/file decoding mutations, never kernel or execution.
negative=[]
def refuse(name,fn):
 try:fn()
 except(AssertionError,ValueError,KeyError,TypeError,UnicodeDecodeError):negative.append(name)
 else:raise AssertionError(name)
raw=Path(loader['path']).read_bytes()
refuse('actual-MachO-wrong-cpu',lambda:run.macho_loader(raw[:4]+bytes(4)+raw[8:],pr));refuse('actual-MachO-short',lambda:run.macho_loader(raw[:31],pr));refuse('actual-MachO-dyld-contract-mutation',lambda:run.macho_loader(raw,dict(pr,allowedMachODynamicLinker='/external/dyld')))
for p,v in sp.items():assert bare(D/p)==v
for p,v in ip.items():assert bare(p)==v
for p,v in ss.items():assert bare(S/p)==v
for p,v in dep.items():assert bare(p,67108864)==v
assert ref(G)==gr
q={'status':'PASS_INDEPENDENT_ACTUAL_DIAGNOSTIC_HELD_OWNERSHIP_LOADER_V6_BUILD_IDENTITY_ONLY','artifact':loader,'copiedCSource':pr['source'],'originalCSource':subject['originalLoaderCSource'],'compileArgv':pr['cases'][3]['argv'],'compileFlag':'KEXE_OWNERSHIP_DIAGNOSTIC_V3','closedBuildCalls':1,'noRetry':True,'CSourceSHA256':pr['source']['sha256'],'sourcePinsSHA256':pr['subjectSourcePins']['sha256'],'subjectSourcePinsSHA256':pr['subjectSourcePins']['sha256'],'buildSourcePinsSHA256':go['sourcePinsSHA256'],'buildInputPinsSHA256':go['inputPinsSHA256'],'buildDriverSHA256':go['driverSHA256'],'buildPreregistrationSHA256':go['preregistrationSHA256'],'rootGO':gr,'sourceReviews':go['sourceReviews'],'subjectReviews':go['subjectReviews'],'completion':ref(O/'report.json'),'terminal':ref(O/'terminal.json'),'calls':calls,'dependencyClosure':{'files':len(dep),'logicalBytes':sum(z['bytes']for z in dep.values()),'exactPins':ref(O/'dependency-input-pins.json'),'localSelectedHeaderShadows':ref(O/'local-header-shadow-paths.json'),'absenceReread':True},'libraryClosure39':pr['libraryClosure'],'linkPreview':ref(O/'link-preview.json'),'MachOLoadNames':names,'actualSavedDecodeRefusals':negative,'verifiedClosure':{'buildSourceFiles':9,'buildInputFiles':65,'buildInputLogicalBytes':406915672,'subjectSourceFiles':len(ss),'regularFilesReread':len(seen)},'reviewerRole':'Independent saved-byte audit from parent once execution; reviewed LC build V3 SOURCE, authored preserved V4 donor; no operational calls or subject writes','qualification':{'sourceBoundLoaderBuildIdentity':True,'heldLaunchLifecycle':False,'actualFDHandshake':False,'WNOWAITBehavior':False,'guestRuntime':False,'functional':False,'performance':False,'hardPeak':False,'dynamicRuntimeWhole':False,'C2':False},'limitations':['All five direct wrapper waits closed0; compiler internal descendant closure remains conditional/universal unqualified','FSIZE8MiB and CPU180/181 specified by pinned wrapper source, no separate actual resource-limit journal retained','Empty actual build diagnostic retained; clean-build diagnostics qualification intentionally remains false','Guard-time dependency and shadow identities are not atomic filesystem snapshot proof','Static arm64 Mach-O install names are not dynamic loaded-runtime identity or actual held-launch protocol proof'],'operationalCalls':0,'subjectWrites':0,'savedFilePins':seen}
(A/'report.json').write_text(json.dumps(q,indent=2)+'\n')
# Exact consumer admission via inert imported binder; no guest launch.
spec=importlib.util.spec_from_file_location('held_v6_saved_binder',S/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);proof=ref(A/'report.json');assert m.diagnostic_loader({'diagnosticLoaderBuildProof':proof,'diagnosticLoaderArtifact':loader},subject)
print(proof);print('CONSUMER_ADMISSION_PASS_SOURCE_ONLY')
