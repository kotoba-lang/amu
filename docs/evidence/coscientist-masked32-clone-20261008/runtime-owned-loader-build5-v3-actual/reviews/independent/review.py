from pathlib import Path
import json,hashlib,stat,sys,runpy,io,contextlib,importlib.util,copy,shlex,ast
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'held-launch-v6-loader-build5-source-v3-20261009-independent';A=Path(__file__).resolve().parent
seen={}
def ref(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();t=p.lstat();assert(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns);r={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};seen[str(p)]=r;return dict(path=str(p),**r)
def load(p):return json.loads(Path(p).read_bytes())
def pins():
 for p,v in sp.items(): assert {k:ref(D/p)[k]for k in ['bytes','sha256']}==v
 for p,v in ip.items(): assert {k:ref(p)[k]for k in ['bytes','sha256']}==v
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json')
expected={'source-pins.json':'03df957a33c729761d7dc58350ba53b47fd12fafee7ee92b0236369c25d9ae44','input-pins.json':'8ec828444aff1db348d4eec931169621cefdd73df5ff06290d9e4497f54973e5','run.py':'5b30fcda0d44aea664e5cdfa19cfee25e676f9345823644184143f841ed35bf7','preregistration.json':'11a5aa2c0a9b3dcd47343e67b463f1a89c2f701c6cf53e82e27a5ed4e7f57c4e'}
for p,h in expected.items(): assert ref(D/p)['sha256']==h
assert len(sp)==9 and len(ip)==65 and sum(v['bytes']for v in ip.values())==406915672
pins();sys.path.insert(0,str(D));import run
buf=io.StringIO()
with contextlib.redirect_stdout(buf):runpy.run_path(str(D/'pure-controls.py'),run_name='__source_review_controls__')
controls=json.loads(buf.getvalue());assert len(controls['refusals'])==45 and controls['actualClangBuildCalls']==controls['actualFDProcessGuestCalls']==0
(A/'pure-controls-output.json').write_text(json.dumps(controls,indent=2)+'\n')
# Independent decode and rebind actual saved Clang preview, not its author template.
origin=pr['previewTemplateOrigin'];assert {k:ref(origin['path'])[k]for k in ['bytes','sha256']}=={k:origin[k]for k in ['bytes','sha256']}
old=[shlex.split(x)for x in Path(origin['path']).read_text().splitlines()if x.lstrip().startswith('"/')];assert len(old)==2
oldD=str(W/'current-runtime-process-ownership-race-source-v5-20261009-independent');newD=str(Path(pr['source']['path']).parent);obj=old[0][old[0].index('-o')+1]
rebound=[[t.replace(oldD,newD)for t in row]for row in old];newobj=obj.replace(oldD,newD);normalized=[['__OBJECT__'if t==newobj else t for t in row]for row in rebound];assert normalized==pr['previewCommandsTemplate']
def encoded(cs):return ('\n'.join(' '.join(json.dumps(t)for t in row)for row in cs)+'\n').encode()
assert run.preview(encoded(rebound),pr,ip)==rebound
neg=[]
def refuse(name,fn):
 try:fn()
 except (AssertionError,ValueError,KeyError,TypeError,UnicodeDecodeError):neg.append(name)
 else:raise AssertionError(name)
for name,fn in [('second-dumpdir',lambda z:z[0].extend(['-dumpdir',pr['outputRoot']+'/kexe-loader-'])),('object-outside',lambda z:z[0].__setitem__(z[0].index('-o')+1,'/tmp/foreign.o')),('loader-extra-lproc',lambda z:z[1].append('-lproc')),('LD-search-empty',lambda z:z[1].__setitem__(z[1].index('-L/usr/local/lib'),'-L')),('debug-prefix-injection',lambda z:z[0].append('-fdebug-prefix-map=/external=/'))]:
 q=copy.deepcopy(rebound);fn(q);refuse(name,lambda:run.preview(encoded(q),pr,ip))
subject=load(pr['subjectPreregistration']['path']);assert pr['cases'][3]['argv']==subject['prospectiveLoaderBuildArgv'];assert pr['source']['sha256']=='04428f47af807fcb19342d035ce730f980f97c001747c806e059bbc4380c52b2';assert not Path(pr['outputRoot']).exists()
# Static stage admission, lifecycle, source-before/after and valid-last evidence.
text=(D/'run.py').read_text();tree=ast.parse(text);assert text.index("finally:\n        save(O/'terminal.json'")<text.index("status='COMPLETE_SOURCE_BOUND_HELD_LAUNCH_V6");assert 'killpg'not in text and 'start_new_session=True'not in text;assert "if not wait_entered:"in text and "wait-uncertain-signal-authority-retired"in text
pins()
q={'status':pr['sourceReviewStatus'],'sourcePinsSHA256':expected['source-pins.json'],'inputPinsSHA256':expected['input-pins.json'],'driverSHA256':expected['run.py'],'preregistrationSHA256':expected['preregistration.json'],'reviewerRole':'Independent of LC V3 implementation; authored preserved V4 donor and reviewed V5 V2. Both prior SOURCE reviews missed first actual dumpdir case; new exact saved-preview delta independently checked.','verifiedClosure':{'sourceFiles':9,'inputFiles':65,'inputLogicalBytes':406915672,'regularFilesReread':len(seen)},'authorPureControls':controls,'independentPreviewNegativeControls':neg,'savedActualPreviewExactRebinding':True,'sourceProspectiveV6ArgvEqual':True,'scope':{'orderedToolCalls':5,'clangBuildCalls':1,'guestCalls':0,'nativeOperationalCallsByReviewer':0,'subjectWrites':0,'C2':False},'findings':[],'reviewedFacts':['Dumpdir output prefix and single cc1/ld matching object roles admitted only via exact normalized saved preview; unknown flags/path/search roles refuse','Actual -M dependency domain, byte/count bounds and mutable selected header/library local-shadow absence guards retained before and after each tool','Pinned wrapper/canonical frontend/ld/resource17/resolvedSDK+library aliases and pinned39 System/proc TBD closure; no full SDK/runtime claim','Bounded normal closed0 diagnostics preserve nonempty warnings; no clean-build qualification','Strict direct normal wait before raw/output hashes; timeout cleanup only known unreaped handle, arbitrary wait failure retires further signals/waits and excludes hashes','Fixed FSIZE8MiB CPU180/181 wrapper; absolute480 campaign, five starts, no new guest; valid-last terminal and guard before COMPLETE','Output Mach-O arm64 executable admits only System dylib/dyld install names and denies weak/reexport/rpath/env/linker-option classes'],'remainingActualGates':['new GO plus two exact SOURCE and subject V6 review receipts','actual five tool commands, dependency closure, preview, whole loader identity','source-bound held-launch FD/WNOWAIT lifecycle fixtures before any guest'],'limitations':['Pure SOURCE/saved-preview only; no Clang/native/process/FD/thread/network query','Search-shadow absence is guard-time conditional, not atomic snapshot or adversarial filesystem race proof','Dynamic loader/runtime/toolchain whole closure and universal compiler descendant closure unqualified','Mach-O declared install names are structural identity evidence, not actual loaded runtime identity','Parent+child FD count is conditional controlled ledger, not measured hard OS cap'],'sourceReviewFiles':seen}
(A/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(q['status']);print(ref(A/'report.json'))
