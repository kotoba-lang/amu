"""Independent SOURCE/delta review, read/pure models only, no compiler/process APIs."""
from pathlib import Path
import json,hashlib,stat,sys,runpy,contextlib,io,ast,copy,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'held-launch-v5-loader-build5-source-v2-20261009-independent';R=W/'held-launch-v5-loader-build5-source-v2-review-independent-20261009-dense'
checked={}
def need(v,m):
 if not v:raise AssertionError(m)
def raw(p):
 p=Path(p)
 for q in [p,*p.parents]:need(not q.is_symlink(),'no symlink traversal '+str(q))
 a=p.lstat();need(stat.S_ISREG(a.st_mode)and a.st_size<=536870912,'bounded regular');b=p.read_bytes();z=p.lstat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'stablebytes');checked[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def load(p):return json.loads(raw(p))
def pin(p,r):b=raw(p);need(checked[str(Path(p))]=={k:r[k]for k in ['bytes','sha256']},'exact pin '+str(p));return b
pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');fr=load(D/'freeze.json')
need(len(sp)==fr['sourceFiles']==9 and len(ip)==pr['exactInputFiles']==fr['inputFiles']==58 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']==fr['inputLogicalBytes']==406824755,'exact closure')
for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:need(raw(D/n)and checked[str(D/n)]['sha256']==fr[k],'frozen registry/driver')
for n,r in sp.items():pin(D/n,r)
for p,r in ip.items():pin(p,r)
need(not Path(pr['outputRoot']).exists(),'fresh output absent no tools')
for p in D.glob('*.py'):ast.parse(raw(p))
sys.dont_write_bytecode=True;sys.path.insert(0,str(D));import run
need(run.scope(pr,ip),'full exact prereg closure scope')
subject=load(pr['subjectPreregistration']['path']);ss=load(pr['subjectSourcePins']['path']);need(pr['source']['path']==str(Path(pr['subjectPreregistration']['path']).parent/'kexe_loader_diagnostic.c')and pr['cases'][3]['argv']==subject['prospectiveLoaderBuildArgv'],'V5 source/fullargv exact')
need(pr['source']['sha256']=='04428f47af807fcb19342d035ce730f980f97c001747c806e059bbc4380c52b2'and pr['compiler']['path']=='/usr/bin/clang'and pr['resolvedCompiler']['path']=='/Library/Developer/CommandLineTools/usr/bin/clang','wrapper+resolvedCLT identity')
need(pr['subjectReviewStatus']=='PASS_SOURCE_ONLY_DIAGNOSTIC_HELD_OWNERSHIP_LOADER_PROTOCOL_PAIRED2_V5'and ss['run.py']['sha256']==pr['subjectDriver']['sha256'],'no V4approval substitution')
need(len(pr['libraryClosure'])==39 and sum(r['bytes']for r in pr['libraryClosure'])==652249,'targeted .tbd closure')
for r in pr['libraryClosure']:pin(r['path'],r)
need(pr['hardPerFileBytes']==8388608 and pr['maximumLoaderBytes']==4194304 and pr['maximumCampaignSeconds']==480 and pr['cleanupSeconds']==30 and pr['maximumRawBytesPerStream']==1048576 and pr['maximumChildCalls']==5 and pr['maximumClangBuildCalls']==1 and pr['guestCalls']==0,'fixed finite bootstrap bounds')
out=io.StringIO()
with contextlib.redirect_stdout(out):ns=runpy.run_path(str(D/'pure-controls.py'),run_name='independent_pure_review')
controls=json.loads(out.getvalue());need(controls==load(D/'pure-controls.json')and len(controls['refusals'])==31 and controls['actualClangBuildCalls']==controls['actualFDProcessGuestCalls']==0,'pure31 reproduction')
# Independent supplementary mutations of the changed defaults/warning and dependency contract.
neg=[]
def refuse(name,f):
 try:f()
 except (AssertionError,ValueError,KeyError,TypeError,UnicodeDecodeError):neg.append(name)
 else:raise AssertionError('mutant admitted '+name)
for name,change in [('old-extra-sysroot',lambda z:z['cases'][3]['argv'].extend(['-isysroot',z['sdk']])),('old-extra-warning-option',lambda z:z['cases'][3]['argv'].append('-Wno-deprecated-declarations')),('wrong-subject-output',lambda z:z.update(outputRoot='/foreign/build')),('registry-byte-corrupt',lambda z:z.update(exactInputLogicalBytes=z['exactInputLogicalBytes']-1))]:
 z=copy.deepcopy(pr);change(z);refuse(name,lambda:run.scope(z,ip))
refuse('dependency-no-ownsource',lambda:run.dependencies(('x: '+pr['sdk']+'/usr/include/stdio.h\n').encode(),pr))
refuse('diagnostic-fatal',lambda:run.bounded_diagnostic(b'fatal error: no build\n'))
need(run.bounded_diagnostic(b'note: retained evidence\n')['nonempty']is True,'normal rc0 bounded note retained not cleaned')
text=raw(D/'run.py').decode();wrapper=raw(D/'limit-exec.py').decode()
for t in ['wait-uncertain-signal-authority-retired','if not wait_entered:',"proc.kill()",'proc.wait(timeout=',"safe = rc == 0 and not r.get('timeout')",'normal direct wait before hashing writers',"bounded_diagnostic(e)","one explicit preview SDK",'pinned frontend resources'] :need(t in text,'lifecycle/closed raw/SDK guard '+t)
need('killpg'not in text and 'start_new_session=True'not in text,'no group operations')
need(text.index("finally:\n        save(O/'terminal.json'")<text.index("status='COMPLETE_SOURCE_BOUND_HELD_LAUNCH_V5"),'terminal before COMPLETE')
need("(resource.RLIMIT_FSIZE, 8388608, 8388608)"in wrapper and "(resource.RLIMIT_CPU, 180, 181)"in wrapper and 'os.execve' in wrapper,'named inherited-compatible bootstrap limits')
# Exact pinned V5 review receipts already available, verify scope but not invent operational GO.
subjectreviews=[]
for p in [W/'current-runtime-process-ownership-race-source-v5-review-root-20261009/report.json',W/'current-runtime-process-ownership-race-source-v5-review-independent-20261009-crc/report.json']:
 q=load(p);need(q['status']==pr['subjectReviewStatus']and q['sourcePinsSHA256']==pr['subjectSourcePins']['sha256']and q['driverSHA256']==pr['subjectDriver']['sha256']and q['preregistrationSHA256']==pr['subjectPreregistration']['sha256'],'available exact V5 reviews');subjectreviews.append(dict(path=str(p),**checked[str(p)]))
for p,r in list(checked.items()):pin(p,r)
report={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':checked[str(D/'source-pins.json')]['sha256'],'inputPinsSHA256':checked[str(D/'input-pins.json')]['sha256'],'driverSHA256':checked[str(D/'run.py')]['sha256'],'preregistrationSHA256':checked[str(D/'preregistration.json')]['sha256'],'independent':True,'authorshipDisclosure':'Reviewer authored frozen V4 C-bootstrap donor, not LC exact V5 wrapper/SDK/subject/warning-policy adaptation. Review independently checks delta and whole registration; root/LC subject code authorship is not the reviewer work. No operations executed.','sourceFiles':9,'inputFiles':58,'inputLogicalBytes':406824755,'exactV5BuildArgv':pr['cases'][3]['argv'],'subjectSource':pr['source'],'availableSubjectReviews':subjectreviews,'libraryStubClosure':{'files':39,'bytes':652249},'pureControls':controls,'independentNegativeControls':neg,'blockingFindings':[],'qualificationLimits':['No actual Clang identity/dependency scan/link preview/build has executed; source PASS only.','Clang compiles only C bootstrap; no Kotoba LLVM fallback and no guest execution.','Normal direct child wait is trusted tool semantics, not a universal descendant/dynamic-toolchain runtime closure proof.','Declared controlled FD/bytes budgets are not measured hard OS process-tree/memory/filesystem caps.','Actual build may refuse unknown default SDK/linker paths or diagnostics; no fallback or retry is authorized.','Build identity does not qualify held-launch WNOWAIT/FD/ticket/ownership fixtures or semantic runtime/performance.'],'guestCalls':0,'ClangBuildCalls':0,'GOcreated':False,'productEdits':0,'checkedRegularPins':checked}
(R/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'sha256':hashlib.sha256((R/'report.json').read_bytes()).hexdigest(),'bytes':(R/'report.json').stat().st_size,'files':len(checked)}))
