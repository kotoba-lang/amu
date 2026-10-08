"""One-off host orchestration SOURCE authoring; no SSH/compiler/native/driver calls."""
from pathlib import Path
import json,hashlib,ast,tarfile,base64,stat
W=Path('/Users/junkawasaki/github/workspaces/codex')
A=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-source-v1'
D=Path(__file__).resolve().parent
B=W/'vector-leaf-straight-read-cache-current19-build52-go-v2-root'
G=W/'vector-leaf-straight-read-cache-fresh-consumer-functional285-go-v1-root'
NEW='/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-fresh-consumer-functional285-v2-root'
def load(p):return json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def ref(p):return dict(path=str(p),**rec(p))
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
assert not(D/'preregistration.json').exists(),'one authoring only'
old=load(A/'preregistration.json');sp=load(A/'source-pins.json');go=load(G/'root-go.json')
assert rec(G/'root-go.json')['sha256']=='ae075a402261a08adea17cf0c1cb76f8b36f4cb5f92d46e38699c783ed62adf9'
for n,z in sp.items():assert rec(A/n)==z
rows=load(A/'launch-outputs/children/attempts.json');terminal=load(A/'launch-outputs/terminal.json');failed=load(A/'launch-outputs/failure.json')
assert len(rows)==1 and rows[0]['state']=='terminal'and rows[0]['returncode']==0 and rows[0]['exception']is None and rows[0]['cleanupException']is None
assert terminal==dict(children=1,allClosed=True,failure=True)
assert failed['noRetry']is True and 'explicit closed remote seal'in failed['exception']
stdout=A/'launch-outputs/children/1.stdout';stderr=A/'launch-outputs/children/1.stderr'
assert stdout.read_bytes()==b''and len(stderr.read_bytes())==2059 and b'FileNotFoundError'in stderr.read_bytes()and (old['buildRoot']+'/collection-receipt.json').encode()in stderr.read_bytes()
assert rec(stdout)=={k:rows[0]['stdout'][k]for k in ('bytes','sha256')}and rec(stderr)=={k:rows[0]['stderr'][k]for k in ('bytes','sha256')}
inputs=load(A/'input-pins.json');original_inputs=dict(inputs)
for p,z in inputs.items():assert rec(p)==z
# Preserve all prior SOURCE, GO, two exact reviews, and local failed launch records.
preserved={}
for folder in (A,G):
 for p in folder.rglob('*'):
  if p.is_file()and '__pycache__'not in p.parts:
   z=rec(p);inputs[str(p)]=z;preserved[str(p)]=z
for z in go['sourceReviews']:
 p=Path(z['path']);assert ref(p)==z;inputs[str(p)]=rec(p);preserved[str(p)]=rec(p)
save('prior-v1-input-pins.json',preserved)
embedded_files={}
for p in [G/'root-go.json',A/'source-pins.json',A/'source-report.json',A/'source-freeze.json',A/'launch-outputs/derived-remote-go.json',A/'launch-outputs/terminal.json',A/'launch-outputs/failure.json',A/'launch-outputs/children/attempts.json',stdout,stderr,*[Path(z['path'])for z in go['sourceReviews']]]:
 embedded_files[str(p)]=dict(**ref(p),base64=base64.b64encode(p.read_bytes()).decode())
save('prior-launch-proof.json',dict(status='PRESERVED_V1_CLOSED_FAILED_LAUNCH1_PRE_NATIVE_MISSING_SYNTHETIC_RECEIPT',priorLocalGOSHA256=rec(G/'root-go.json')['sha256'],closedLaunchChildren=1,sshReturncode=0,remoteSealPresent=False,stdoutBytes=0,stderrBytes=2059,remoteNativeChildrenStarted=0,nativeZeroBasis='Exact traceback at initial bounded_bank before output mkdir/Ledger construction; authoring does not independently survey remote filesystem.',failureRemainsFailure=True,noRetryV1=True,files=embedded_files))
receipt=B/'collected/collection-receipt.json';(D/'collection-receipt.json').write_bytes(receipt.read_bytes());receipt_ref=ref(receipt)
assert receipt_ref['sha256']=='2af1a04fc0b49320eabbf0eeafe4583dc408d85a17b9f9c2784deb1d559aa51a'
bank=load(A/'remote-input-pins.json');oldbank=dict(bank);oldreceipt=old['buildRoot']+'/collection-receipt.json'
assert bank.pop(oldreceipt)=={k:receipt_ref[k]for k in ('bytes','sha256')}
bank[NEW+'/source/collection-receipt.json']={k:receipt_ref[k]for k in ('bytes','sha256')}
# Inventory installed vs collector-synthetic roles using collector source and receipt members.
collector=B/'collect-build52-remote.py';collector_source=collector.read_text()
assert "files['collection-receipt.json']=json.dumps(receipt,indent=2).encode()+b'\\n'" in collector_source
assert "for dirname in ['build52','control']" in collector_source
inputs[str(collector)]=rec(collector)
with tarfile.open(B/'collected-build52.tgz')as archive:
 archive_names={m.name.rstrip('/')for m in archive.getmembers()if m.isfile()}
assert archive_names
actual_remote_members={v['path'] for v in load(receipt)['members']}
synthetic=[]
for path,z in oldbank.items():
 rel=path.removeprefix(old['buildRoot']+'/')
 # Archive also contains the synthesized receipt; receipt.members records filesystem reads.
 if not rel.startswith('package/')and rel not in actual_remote_members:
  synthetic.append(dict(oldRemotePath=path,localCollectedPath=str(B/'collected'/rel),**z))
 assert rel.startswith('package/') or rel in archive_names
assert [v['oldRemotePath']for v in synthetic]==[oldreceipt],synthetic
save('synthetic-origin-audit.json',dict(status='PASS_FINITE_COLLECTED_ORIGIN_ROLE_AUDIT',collector=ref(collector),allOtherCollectedBuildControlRawOriginsPresentInAcceptedArchiveAndReceiptFileReadMembers=True,syntheticCollectedOrigins=synthetic,reboundRemotePath=NEW+'/source/collection-receipt.json',transportedFullBytes=True,installedPackageMembers=3592,priorRemoteRegistryFiles=len(oldbank),newRemoteRegistryFiles=len(bank),fullActualBuildInputReferences=228))
save('remote-input-pins.json',bank);save('input-pins.json',inputs)
for n in ('build52-acceptance.json','build52-independent-report.json','ledger.py'):(D/n).write_bytes((A/n).read_bytes())
pr=dict(old);pr.update(status='PROSPECTIVE_SOURCE_ONLY_FRESH_CONSUMER_FUNCTIONAL285_V2_RECEIPT_BINDING_NO_GO',schema='LC_FRESH_CONSUMER_FUNCTIONAL285/v2',remoteRoot=NEW,outputRoot=NEW+'/functional285',rootGOStatus='ROOT_GO_LC_FRESH_CONSUMER_FUNCTIONAL285_V2_RECEIPT_BINDING_ONLY',sourceReviewStatus='PASS_SOURCE_LC_FRESH_CONSUMER_FUNCTIONAL285_V2_RECEIPT_BINDING',priorFailedLaunches=1,priorNativeChildren=0,maximumCumulativeNativeChildren=285,maximumCumulativeLaunchChildren=2,priorLaunchProof=dict(path=NEW+'/source/prior-launch-proof.json',**rec(D/'prior-launch-proof.json')),syntheticReceiptBinding=dict(role='Local collector-generated proof; transported byte-identical SOURCE, not installed build artifact',originalLocal=receipt_ref,priorInvalidRemotePath=oldreceipt,remotePath=NEW+'/source/collection-receipt.json',sourceFilename='collection-receipt.json',receipt={k:receipt_ref[k]for k in ('bytes','sha256')}),priorV1InputPins=ref(D/'prior-v1-input-pins.json'),localClosureFiles=len(inputs),localClosureBytes=sum(v['bytes']for v in inputs.values()),remoteClosureFiles=len(bank),remoteClosureBytes=sum(v['bytes']for v in bank.values()),beforeOperativeSourceWriting=True)
assert len(inputs)<=4096 and sum(v['bytes']for v in inputs.values())<=448*1024**2
save('preregistration.json',pr) # Before operative functional/launch SOURCE is written.
s=(A/'functional285.py').read_text().replace(old['remoteRoot'],NEW)
s=s.replace("'noRetry','sourceReviews'","'noRetry','sourceReviews','priorFailedLaunches','priorNativeChildren','maximumCumulativeNativeChildren','maximumCumulativeLaunchChildren'")
s=s.replace("compilerAuthorized=False,noRetry=True)","compilerAuthorized=False,noRetry=True,priorFailedLaunches=1,priorNativeChildren=0,maximumCumulativeNativeChildren=285,maximumCumulativeLaunchChildren=2)")
hook=""" proof=load(pin(dict(path=str(D/'prior-launch-proof.json'),bytes=pr['priorLaunchProof']['bytes'],sha256=pr['priorLaunchProof']['sha256'])))
 need(proof['status']=='PRESERVED_V1_CLOSED_FAILED_LAUNCH1_PRE_NATIVE_MISSING_SYNTHETIC_RECEIPT' and proof['closedLaunchChildren']==1 and proof['remoteNativeChildrenStarted']==0 and proof['failureRemainsFailure']is True and proof['noRetryV1']is True and proof['remoteSealPresent']is False,'retained prior failed launch1/native0')
 binding=pr['syntheticReceiptBinding'];need(binding['remotePath']==str(ROOT/'source/collection-receipt.json') and binding['sourceFilename']=='collection-receipt.json','explicit synthetic receipt role')
 pin(dict(path=str(D/'collection-receipt.json'),**binding['receipt']))
"""
s=s.replace(' return g\n',hook+' return g\n')
s=s.replace("PASS_FRESH_CONSUMER_ORIGINAL19_FUNCTIONAL285_ONLY","PASS_FRESH_CONSUMER_ORIGINAL19_FUNCTIONAL285_V2_ONLY").replace('FAIL_FRESH_CONSUMER_FUNCTIONAL285_FIRST_FAILURE','FAIL_FRESH_CONSUMER_FUNCTIONAL285_V2_FIRST_FAILURE')
s=s.replace("compilerCalls=0,C2skip=False,noRetry=True,sourcePinsSHA256=", "compilerCalls=0,C2skip=False,noRetry=True,priorFailedLaunches=1,priorNativeChildren=0,cumulativeNativeChildren=len(led.rows),maximumCumulativeNativeChildren=285,cumulativeLaunchChildren=2,sourcePinsSHA256=")
ast.parse(s);(D/'functional285.py').write_text(s)
s=(A/'launch.py').read_text().replace('PASS_FRESH_FUNCTIONAL285_ONE_SSH_LAUNCH_ONLY_ACTUAL_REVIEW_PENDING','PASS_FRESH_FUNCTIONAL285_V2_ONE_SSH_LAUNCH_ONLY_ACTUAL_REVIEW_PENDING').replace("launchChildren=1,expectedInnerChildren=285,","launchChildren=1,priorFailedLaunches=1,cumulativeLaunchChildren=2,maximumCumulativeLaunchChildren=2,expectedInnerChildren=285,")
ast.parse(s);(D/'launch.py').write_text(s)
schema=load(A/'go-schema.json');schema['exactLocalFields']+=['priorFailedLaunches','priorNativeChildren','maximumCumulativeNativeChildren','maximumCumulativeLaunchChildren'];schema['exactLocalFields']=sorted(schema['exactLocalFields']);schema['fixedFields'].update(remoteRoot=NEW,outputRoot=NEW+'/functional285',priorFailedLaunches=1,priorNativeChildren=0,maximumCumulativeNativeChildren=285,maximumCumulativeLaunchChildren=2);schema['fixedAuthorization']['status']=pr['rootGOStatus'];schema['sourceReviews']['status']=pr['sourceReviewStatus'];save('go-schema.json',schema)
role=load(A/'evidence-role-contract.json');role['syntheticReceiptBinding']=pr['syntheticReceiptBinding'];role['priorFailurePreservation']='All V1 SOURCE/GO/reviews and failed launch refs remain in local closure; bounded proof transports as SOURCE. Failed1/native0 remains failure, no baseline result retained.';save('evidence-role-contract.json',role)
(D/'README.md').write_text((A/'README.md').read_text()+'\nV2 receipt binding: the collector-generated collection-receipt.json was never an installed build-root member. V1 failed at initial closure stat before constructing a native Ledger; SSH return0 with traceback2059B/stdout0 is failed transport, never functional acceptance. Preserve all V1 files and exact GO/review hashes; no retry there. New remote v2 root transports the full31372B receipt byte-identically as read-only SOURCE and binds it in both SOURCE registry and remote input guard. The other collected build/control/raw origins are members of the immutable collection archive. All3896 original local refs, full228 actual build refs, all3592 installed package members/full lossless chunks remain. Fresh285 native/C children maximum; prior native0; cumulative launches maximum2=failed1+new1. New exact GO and two V2 SOURCE reviews are required. No SOURCE-author operational/SSH/compiler/native calls; SOURCE is not root GO. Ledger/parser/functional budgets/body semantics unchanged.\n')
# Pure static controls inherit saved parser fixtures, never execute operational main.
controls=(A/'pure-controls.py').read_text()
controls+= "\nassert (D/'collection-receipt.json').read_bytes()==Path(pr['syntheticReceiptBinding']['originalLocal']['path']).read_bytes()\nassert pr['syntheticReceiptBinding']['remotePath'] in json.loads((D/'remote-input-pins.json').read_bytes())\nassert pr['priorFailedLaunches']==1 and pr['priorNativeChildren']==0 and pr['maximumCumulativeLaunchChildren']==2 and pr['maximumCumulativeNativeChildren']==285\n"
(D/'pure-controls.py').write_text(controls)
print(json.dumps(dict(localFiles=len(inputs),localBytes=sum(v['bytes']for v in inputs.values()),remoteFiles=len(bank),remoteBytes=sum(v['bytes']for v in bank.values()),syntheticOrigins=len(synthetic),operativeExecutions=0)))
