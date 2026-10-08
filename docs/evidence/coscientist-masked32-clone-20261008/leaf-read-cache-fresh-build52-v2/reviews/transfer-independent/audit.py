"""Read-only saved-receipt audit; no project imports or remote operations."""
from pathlib import Path
import json,hashlib,shlex
S=Path('/Users/junkawasaki/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-source-v2-lc-remote')
T=S/'transfer-outputs';O=Path(__file__).resolve().parent
G=Path('/Users/junkawasaki/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-go-v2-root/transfer-go.json')
SH='b12caa329a1532399cab8b2ee94b5096bb1811d952aa76c3287b672b05917b4b'
AH='3b099c22196af6ba53fae99c3696284e405714abacefef6015d39edcc210077a'
MH='67f00b5dae259c4a077ad104534a7a075f438127ab845513eaeb7ec7e865455b'
RH='2a4379322134f28ff101f20e829058495f3246366565b815dd86252ff77e49eb'
H=lambda b:hashlib.sha256(b).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def ref(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def pin(r):
 p=Path(r['path']);assert p.is_file() and not p.is_symlink() and ref(p)==r;return p
load=lambda p:json.loads(p.read_text())
assert sha(S/'source-pins.json')==SH
bank=load(S/'source-pins.json')
for n,r in bank.items():pin(dict(r,path=str(S/n)))
gb=(T/'transfer-go.json').read_bytes();assert gb==G.read_bytes();g=json.loads(gb);gh=H(gb)
assert g['phase']=='transfer' and g['authorized'] is True and g['maximumChildren']==3 and g['sourcePinsSHA256']==SH
assert g['preregistrationSHA256']==sha(S/'preregistration.json') and g['rootFunctional285AcceptanceSHA256']==RH
assert g['functionalAuthorized'] is False and g['timingAuthorized'] is False
host='zebulun@100.66.28.79';root='/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-build52-v2-root';stage=root+'-stage'
assert g['destination']==host and g['remoteRoot']==root and g['extractorSHA256']==sha(S/'extract.py')
assert len(g['sourceReviews'])==2 and g['sourceReviews'][0]['sha256']!=g['sourceReviews'][1]['sha256']
for r in g['sourceReviews']:
 q=load(pin(r));assert q['sourcePinsSHA256']==SH and q['status'].startswith('PASS')
assert pin(g['archive'])==S/'assembly-outputs/package.tgz' and g['archive']['sha256']==AH and g['archive']['bytes']==121263001
assert pin(g['manifest'])==S/'assembly-outputs/manifest.json' and g['manifest']['sha256']==g['manifestBytesSHA256']==MH
ar=load(pin(g['assemblyAcceptance']));assert ar['status'].startswith('PASS') and ar['archiveSHA256']==AH and ar['manifestSHA256']==MH
review=load(pin(ar['independentReview']));assert review['status'].startswith('PASS') and review['archiveSHA256']==AH and review['sourcePinsSHA256']==SH
opts=['-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1']
init="from pathlib import Path;import os;p=Path("+repr(stage)+");r=Path("+repr(root)+");assert Path.home()==Path('/Users/zebulun');assert not p.exists() and not r.exists();assert all(not q.is_symlink() for q in p.parents if q.exists());p.mkdir();print('FRESH_STAGE_ONLY',flush=True)"
wrap="import pathlib,hashlib,sys,signal;signal.alarm(250);p=pathlib.Path("+repr(stage+'/extract.py')+");assert hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(g['extractorSHA256'])+";gp=pathlib.Path("+repr(stage+'/transfer-go.json')+");assert hashlib.sha256(gp.read_bytes()).hexdigest()=="+repr(gh)+";sys.argv=[str(p),str(gp)];exec(compile(p.read_bytes(),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})"
cmds=[['/usr/bin/ssh',*opts,host,'python3 -c '+shlex.quote(init)],['/usr/bin/scp',*opts,g['archive']['path'],str(S/'extract.py'),str(T/'transfer-go.json'),host+':'+stage+'/'],['/usr/bin/ssh',*opts,host,'python3 -c '+shlex.quote(wrap)]]
env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/junkawasaki',TMPDIR='/private/tmp')
rows=load(T/'children/attempts.json');assert len(rows)==3
raw=[]
for i,r in enumerate(rows):
 assert r['index']==i+1 and r['label']==str(i+1) and r['argv']==cmds[i] and r['environment']==env and r['timeoutSeconds']==[30,300,300][i]
 assert r['state']=='terminal' and r['returncode']==0 and r['exception'] is None and r['cleanupException'] is None
 for k in ['stdout','stderr']:
  p=pin(r[k]);assert str(p)==r[k+'Path'] and p==T/'children'/(str(i+1)+'.'+k) and p.stat().st_size<=16777216
  b=p.read_bytes();assert H(b)==r[k]['sha256'];raw.append(r[k])
 assert Path(r['stderrPath']).read_bytes()==b''
assert (T/'children/1.stdout').read_bytes()==b'FRESH_STAGE_ONLY\n' and (T/'children/2.stdout').read_bytes()==b''
expected={'status':'PASS_REMOTE_EXTRACT_ONLY','regularMembers':3593,'expandedBytes':418457019,'archiveSHA256':AH,'manifestSHA256':MH,'sourcePinsSHA256':SH,'rootFunctional285AcceptanceSHA256':RH,'compilerCalls':0,'nativeCalls':0}
assert json.loads((T/'children/3.stdout').read_bytes())==load(T/'remote-extract-terminal.json')==expected
assert load(T/'terminal.json')=={'children':3,'allClosed':True,'failure':False}
assert load(T/'report.json')=={'status':'PASS_TRANSFER_AND_EXTRACT_ONLY','children':3,'archiveSHA256':AH,'manifestSHA256':MH,'sourcePinsSHA256':SH,'compilerCalls':0,'nativeCalls':0}
assert not (T/'failure.json').exists()
assert {str(p.relative_to(T)) for p in T.rglob('*') if p.is_file()}=={'children/attempts.json','children/1.stdout','children/1.stderr','children/2.stdout','children/2.stderr','children/3.stdout','children/3.stderr','report.json','terminal.json','remote-extract-terminal.json','transfer-go.json'}
inputs={str(p):ref(p) for p in T.rglob('*') if p.is_file()}
inputs[str(G)]=ref(G);inputs[g['assemblyAcceptance']['path']]=g['assemblyAcceptance'];inputs[g['archive']['path']]=g['archive'];inputs[g['manifest']['path']]=g['manifest']
for r in g['sourceReviews']:inputs[r['path']]=r
report={'status':'PASS_ACTUAL_TRANSFER_V2_INDEPENDENT_SAVED_RAW_AUDIT','archiveSHA256':AH,'manifestSHA256':MH,'sourcePinsSHA256':SH,'preregistrationSHA256':g['preregistrationSHA256'],'rootFunctional285AcceptanceSHA256':RH,'transferGOSHA256':gh,'children':3,'allClosed':True,'allReturnCodesZero':True,'exceptionCount':0,'cleanupExceptionCount':0,'retries':0,'compilerCalls':0,'nativeCalls':0,'guestCalls':0,'timingCalls':0,'remoteTerminalSeal':expected,'fullRawStreamRefs':raw,'checks':{'frozenRegistryMatches':True,'originalAndTypedGOWholeBytesMatch':True,'archiveManifestAndAssemblyAcceptanceRefsMatch':True,'twoDistinctSourcePASSReviewsMatch':True,'exactThreeLiteralIPAddressArgvMatch':True,'exactCleanEnvironmentAndTimeoutsMatch':True,'fullRawBytesHashesMatch':True,'allThreeClosedSuccessfulReceiptsWithoutReapError':True,'remoteFullJSONSealAndSavedSealMatch':True,'zeroNativeCompilerCalls':True},'independence':'This reviewer participated in frozen SOURCE review and independent actual-assembly review, but authored no operational driver and performed no operational execution. Only new read-only saved-receipt audit artifacts authored here. No SSH, extractor or driver rerun. Remote installation evidence is the authenticated SSH successful exit and exact raw terminal seal from the pinned extractor; no additional live remote inspection was performed.','remainingGates':['Root actual transfer acceptance and separate build GO','Independent actual build52 receipt acceptance','New consumer functional285','Separate quiet/timing source reviews and GO'],'reviewExecution':{'SSH':0,'extractor':0,'assembly':0,'compiler':0,'native':0,'guest':0,'timing':0}}
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(O/'input-pins.json').write_text(json.dumps(inputs,indent=2)+'\n')
(O/'README.md').write_text(report['status']+'\n\nExact3 saved-raw transfer review; no operational rerun. SOURCE and archive review participation disclosed in report.json. Build remains separately gated.\n')
for p,r in inputs.items():pin(r)
assert sha(S/'source-pins.json')==SH
freeze={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in O.iterdir() if p.is_file()}
(O/'review-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps({'status':report['status'],'report':freeze['report.json'],'reviewFreezeSHA256':sha(O/'review-freeze.json'),'transferGOSHA256':gh},indent=2))
