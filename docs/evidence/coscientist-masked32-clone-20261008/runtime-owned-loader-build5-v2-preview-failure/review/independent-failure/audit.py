"""Saved failure only, no Clang/native/process/FD/rerun queries."""
from pathlib import Path
import json,hashlib,stat,sys,importlib.util,shlex
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'held-launch-v5-loader-build5-source-v2-20261009-independent';R=W/'held-launch-v5-loader-build5-v2-actual-failure-review-independent-20261009-dense';G=W/'held-launch-v5-loader-build5-go-v2-root-20261009/root-go.json'
checked={}
def need(v,m):
 if not v:raise AssertionError(m)
def raw(p):
 p=Path(p)
 for q in [p,*p.parents]:need(not q.is_symlink(),'no symlink traversal')
 a=p.lstat();need(stat.S_ISREG(a.st_mode)and a.st_size<=536870912,'bounded regular');b=p.read_bytes();z=p.lstat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stable bytes');checked[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def load(p):return json.loads(raw(p))
def ref(p):raw(p);return dict(path=str(p),**checked[str(p)])
def pin(p,r):b=raw(p);need(checked[str(Path(p))]=={k:r[k]for k in ['bytes','sha256']},'exact pin '+str(p));return b
pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');fr=load(D/'freeze.json');g=load(G);gr=ref(G);O=Path(pr['outputRoot'])
need(len(sp)==9 and len(ip)==58 and sum(r['bytes']for r in ip.values())==406824755,'exact oldregistered closure')
for n,r in sp.items():pin(D/n,r)
for p,r in ip.items():pin(p,r)
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256')]:need(checked[str(D/n)]['sha256']==g[k]==fr[k],'GO frozenidentity')
need(gr['sha256']=='d9b009e78cd2fc30dcf3d5ec30600e2d040843a8a75b753c1a6ef3ea092fd27e'and g['status']==pr['rootGOStatus']and g['noRetry']is True and g['guestAuthorized']is False and g['maximumChildCalls']==5,'specificonceGO')
for field,status in [('sourceReviews',pr['sourceReviewStatus']),('subjectReviews',pr['subjectReviewStatus'])]:
 need(len(g[field])==2 and len({r['path']for r in g[field]})==2,'two reviews')
 for r in g[field]:
  q=json.loads(pin(r['path'],r));need(q['status']==status and q['sourcePinsSHA256']==(g['sourcePinsSHA256']if field=='sourceReviews'else pr['subjectSourcePins']['sha256']),'exact reviews')
  need(q['driverSHA256']==(g['driverSHA256']if field=='sourceReviews'else pr['subjectDriver']['sha256'])and q['preregistrationSHA256']==(g['preregistrationSHA256']if field=='sourceReviews'else pr['subjectPreregistration']['sha256']),'driver/prreviews')
sys.dont_write_bytecode=True;sys.path.insert(0,str(D));spec=importlib.util.spec_from_file_location('saved_build_run',D/'run.py');run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run);need(run.scope(pr,ip),'source scope stillexact')
rows=load(O/'attempts.json');terminal=load(O/'terminal.json');failure=load(O/'failure.json');deps=load(O/'dependency-input-pins.json')
need(terminal=={'childCalls':3,'allDirectChildrenClosed':True,'failure':True,'descendantClosureUniversal':False}and len(rows)==3,'threeclosed preservedfailure')
need(not(O/'kexe-loader').exists()and not(O/'loader.json').exists()and not(O/'report.json').exists(),'no build/artifact/completion')
need(not any(O.glob('build-loader.*'))and not any(O.glob('version-after.*')),'remaining2 neverexecuted')
details=[]
for r,c in zip(rows,pr['cases'][:3]):
 need(r['label']==c['label']and r['argv']==c['argv']and r['state']=='terminal'and r['returncode']==0 and r['waitEntered']is True and type(r['pid'])is int and not r.get('timeout',False),'exact closed0 tool')
 for stream in ['stdout','stderr']:pin(O/(c['label']+'.'+stream),r[stream])
 details.append(dict(label=r['label'],pid=r['pid'],returncode=0,stdout=r['stdout'],stderr=r['stderr']))
need(len({r['pid']for r in rows})==3,'distinct toolPIDs')
version=raw(O/'version-before.stdout');need(version.startswith(b'Apple clang version ')and b'InstalledDir: /Library/Developer/CommandLineTools/usr/bin'in version and raw(O/'version-before.stderr')==b'','actualbeforecompiler identity')
paths=run.dependencies(raw(O/'dependencies.stdout'),pr);need(set(paths)==set(deps)and len(deps)==240 and sum(r['bytes']for r in deps.values())==5270106,'exact240 headerreadclosure')
for p,r in deps.items():pin(p,r)
need(rows[1]['diagnosticEvidence']==run.bounded_diagnostic(raw(O/'dependencies.stderr')),'saved diagnostic identity')
preview=raw(O/'link-preview.stderr');need(raw(O/'link-preview.stdout')==b'','completepreview raw')
commands=[shlex.split(x)for x in preview.decode().splitlines()if x.lstrip().startswith('"/')];need(len(commands)==2 and commands[0][0]==pr['resolvedCompiler']['path']and commands[1][0]==pr['linker']['path'],'actualfrontendlinker')
cc=commands[0];ix=cc.index('-dumpdir');prefix=str(O/'kexe-loader-');need(cc.count('-dumpdir')==1 and cc[ix+1]==prefix,'exact outputmetadataoption role')
expected="AssertionError('unregistered absolute link/compiler input: "+prefix+"')";need(failure['error']==expected and failure['childCalls']==3 and failure['noRetry']is True,'exactpreserved first failure')
try:run.preview(preview,pr,ip)
except AssertionError as ex:need(str(ex)=='unregistered absolute link/compiler input: '+prefix,'pure samefailed previewguard')
else:raise AssertionError('oldpreview unexpectedly admitted')
roles=[]
for command in commands:
 for j,t in enumerate(command):
  if t.startswith('/')and t not in ip and t not in [pr['sdk'],pr['sdkAlias'],pr['compilerResourceDirectory']]:roles.append({'token':t,'previousOptionOrToken':command[j-1]if j else None,'isRegisteredOutputPrefix':t==prefix,'futureRegistrationRoleOnly':True})
for p,r in list(checked.items()):pin(p,r)
report={'status':'PASS_INDEPENDENT_SAVED_FAILURE_HELD_LAUNCH_V5_BUILD5_V2_PREVIEW_ONLY','authorshipDisclosure':'Reviewer authored blocked V4 C-bootstrap donor and reviewed LC V5 SOURCE delta; root executed once. Saved actual audit does not claim independent SOURCE review of own donor. Root and reviewer SOURCEchecks missed real -dumpdir case.','sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':g['inputPinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'rootGO':gr,'sourceReviews':g['sourceReviews'],'subjectReviews':g['subjectReviews'],'sourceFiles':9,'inputFiles':58,'inputLogicalBytes':406824755,'toolCalls':3,'closed0':3,'actualBuildCalls':0,'guestCalls':0,'cases':details,'terminal':terminal,'failure':failure,'actualDependencyFiles':240,'actualDependencyLogicalBytes':5270106,'source':pr['source'],'actualPreviewCommands':commands,'firstRefusedToken':{'value':prefix,'option':'-dumpdir','frontendTokenIndex0':ix+1,'classification':'declared output metadata prefix, not an input file'},'additionalSavedAbsoluteTokensForFutureTypedRoleReview':roles,'unclosedDescendantUniversalProof':False,'resourceLimits':'SOURCE wrapper specifies FSIZE8MiB CPU180/181; no separate actual resource journal was captured','remainingUnexecuted':['build-loader','version-after'],'strictBuild5CampaignPassed':False,'retryAuthorized':False,'loaderIdentityQualified':False,'lifecycleQualified':False,'performanceQualified':False,'noNewOperationalCalls':True,'checkedRegularPins':checked}
(R/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'sha256':hashlib.sha256((R/'report.json').read_bytes()).hexdigest(),'bytes':(R/'report.json').stat().st_size,'files':len(checked)}))
