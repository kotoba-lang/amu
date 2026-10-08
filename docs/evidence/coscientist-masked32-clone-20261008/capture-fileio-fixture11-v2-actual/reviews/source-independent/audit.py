from pathlib import Path
import hashlib,json,stat,os
W=Path('/Users/junkawasaki/github/workspaces/codex');A=W/'crc-capture-popen-transfer-fixture-source-v1-20261009';D=W/'crc-capture-popen-transfer-fixture-source-v2-20261009';O=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def check(p,v):
 assert not p.is_symlink() and stat.S_ISREG(p.lstat().st_mode),str(p)
 b=p.read_bytes();assert len(b)==v['bytes'] and sha(b)==v['sha256'],str(p)
f=json.loads((D/'freeze.json').read_text());sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text());origin=json.loads((D/'canonical-input-origin.json').read_text())
assert sha((D/'source-pins.json').read_bytes())=='77a2ecf4fccb8362290155a7539407e5ec19abcd4f19968095ffd1304c35ecd1'
assert sha((D/'input-pins.json').read_bytes())=='25b8ae6d1246704b1c94fc21de31aa1097f20cfa2c8597880bed5d03447e1b99'
for name,v in sp.items():check(D/name,v)
for name,v in ip.items():check(Path(name),v)
assert len(sp)==f['sourceFiles']==9 and len(ip)==f['inputFiles']==1944
for name,v in json.loads((A/'source-pins.json').read_text()).items():check(A/name,v)
for name in sp:
 if name not in ['preregistration.json','input-pins.json','canonical-input-origin.json']:assert (D/name).read_bytes()==(A/name).read_bytes(),name
pa=json.loads((A/'preregistration.json').read_text());pd=json.loads((D/'preregistration.json').read_text());pa['fixedArgv'][1]=pd['fixedArgv'][1];pa['fixedSuppliedEnvironment']['TMPDIR']=pd['fixedSuppliedEnvironment']['TMPDIR'];assert pa==pd
oldip=json.loads((A/'input-pins.json').read_text());alias=origin['aliasPath'];target=origin['canonicalInputPath'];assert alias in oldip and target in oldip and alias not in ip and target in ip
removed=dict(oldip);removed.pop(alias);assert removed==ip
assert os.readlink(alias)==origin['linkText'] and str(Path(alias).resolve())==target and pin(Path(target))['sha256']==origin['exactTargetBytes']['sha256']
for k in ['frozenV1SourcePins','rootInitialDiagnostic']:
 v=origin[k];check(Path(v['path']),v)
assert len(pd['cases'])==11 and pd['cases']==origin['fixtureCasesUnchanged']
prior=W/'crc-capture-popen-transfer-fixture-source-review-independent-20261009/report.json';assert pin(prior)['sha256']=='018ba53c0622c8b860a95a94ab307c2259c2644b0e16231777eb1b052b46b8d7'
r={'status':'PASS_SOURCE_ONLY_FIXED_FILEIO_CAPTURE_CONTROLLER_FIXTURE','independent':True,'priorAuthorship':False,'sourcePinsSHA256':sha((D/'source-pins.json').read_bytes()),'driverSHA256':sha((D/'run.py').read_bytes()),'subject':str(D),'freeze':pin(D/'freeze.json'),'inputPins':pin(D/'input-pins.json'),'priorSourceReview':pin(prior),'verified':{'sourceFiles':9,'inputFiles':1944,'allSourceAndInputRegularNonSymlink':True,'allSourceAndInputHashes':True,'V1DeclaredSourceHashesPreserved':True,'PythonDesignSourceControlsByteIdenticalV1':True,'onlyPreregChanges':['fixedArgv[1]','fixedSuppliedEnvironment.TMPDIR'],'onlyInputRegistryChange':'remove alias key already represented by canonical exact-byte target','originEvidenceAndRootDiagnosticHashes':True,'fixedCases':11,'maximumPipes':17,'maximumAuxThreadStarts':10,'maximumSimultaneousAuxThreads':2,'maximumOwnedFDs':9},'aliasRebinding':origin,'scope':'Bounded exact V1-to-V2 registry/path delta; prior independent source mechanism review retained. No operational controls repeated. V1 source acceptance did not establish non-symlink registry eligibility; root runtime-input HOLD remains preserved for V1.','limitations':['Only fixed FileIO/pipe/thread and injected authority fixture SOURCE acceptance. No actual fixture/native/Popen/memory/guest qualification.','A separately reviewed exact root supervisor and GO are prerequisites for one execution; inherited stdio-only FD assumption and cooperative wall/IO limitations unchanged.','No universal grant interruption/OS ownership proof, no fixture proof of new nativeV4 observe wiring.'],'operationalCalls':0,'actualFDThreadProcessNativeNetworkAPICalls':0,'subjectEdits':0,'reviewerSource':pin(Path(__file__))}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(O/'report.json')))
