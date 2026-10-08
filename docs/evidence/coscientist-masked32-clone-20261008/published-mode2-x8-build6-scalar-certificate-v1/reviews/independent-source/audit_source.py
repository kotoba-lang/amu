from pathlib import Path
import json,hashlib,stat,sys,importlib.util,contextlib,io,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-build-fixture6-source-v1-20261009';R=Path(__file__).parent
h=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=h(b))
def ck(p,v):assert stat.S_ISREG(p.lstat().st_mode)and not p.is_symlink();b=p.read_bytes();assert len(b)==v['bytes']and h(b)==v['sha256'];return b
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());fr=json.loads((D/'freeze.json').read_bytes());pr=json.loads((D/'preregistration.json').read_bytes())
for k,v in fr.items():
 if isinstance(v,dict)and set(v)=={'path','bytes','sha256'}:ck(Path(v['path']),v)
for k,v in sp.items():ck(D/k,v)
for k,v in ip.items():ck(Path(k),v)
assert len(sp)==22 and len(ip)==47 and sum(v['bytes']for v in ip.values())==9076290 and not Path(pr['freshOutputRoot']).exists()
old=W/'tc-current7618-off18-compile36-source-v1-20261009';same=[]
for n in ['capture.py','integration.py','controller.py','typed-adapter.py','artifact_admission.py','runtime.py','compiler_output.py','native-call.py']:
 assert (D/n).read_bytes()==(old/n).read_bytes();same.append(rec(D/n))
assert fr['sourcePins']['sha256']=='223b341e4140cf7e096b61fd40da4d38c66889ef8ca91ec8be6d2e374ad45bcb'
# Every operational path remains inert at import; pure controls use injected Journals/byte store only.
for p in D.glob('*.py'):ast.parse(p.read_text())
sys.path.insert(0,str(D));out=[]
for n in ['pure-controls','wrapper-controls']:
 spec=importlib.util.spec_from_file_location('independent_'+n,D/(n+'.py'));m=importlib.util.module_from_spec(spec);buf=io.StringIO()
 with contextlib.redirect_stdout(buf):spec.loader.exec_module(m)
 q=json.loads(buf.getvalue());assert q==json.loads((D/(n+'.json')).read_bytes());out.append(q)
import run
assert run.source_scope(pr,ip);O=Path(pr['freshOutputRoot']);assert O==D/'run-outputs'
for c in pr['cases']:assert run.compiler_case(c['nativeArgv'],pr,c)
# Specific maximum and actual first-failure admission are parent-controlled: inherited cap36 doesn't admit a seventh indexedcase.
assert len(pr['cases'])==pr['maximumLoaderCalls']==6 and len(pr['environment'])==17 and pr['maximumDistinctLoaderStarts']==6 and pr['maximumAuxiliaryThreadStarts']==12
challenge=json.loads(ck(Path(pr['candidateSourceChallenge']['path']),pr['candidateSourceChallenge']));assert not challenge['operationalGOEligible']and challenge['status'].startswith('HOLD_')
assert pr['clobberCertificateQualified']is False and pr['candidateAdoptionQualified']is False
f=json.loads(ck(Path(pr['qualifiedIntegrationFixtureProof']['path']),pr['qualifiedIntegrationFixtureProof']))
for n,k in [('capture.py','captureSHA256'),('integration.py','integrationSHA256'),('controller.py','controllerSHA256')]:assert f[k]==sp[n]['sha256']
# Recheck after injected controls: files unchanged, all receipts still exact.
for k,v in sp.items():ck(D/k,v)
for k,v in ip.items():ck(Path(k),v)
r={'status':pr['sourceReviewStatus'],'independent':True,'priorImplementationAuthorship':False,'sourcePinsSHA256':fr['sourcePins']['sha256'],'inputPinsSHA256':fr['inputPins']['sha256'],'driverSHA256':fr['driver']['sha256'],'preregistrationSHA256':fr['preregistration']['sha256'],'freeze':rec(D/'freeze.json'),'sourceRegistry':{'files':22,'logicalBytes':sum(v['bytes']for v in sp.values())},'inputRegistry':{'files':47,'logicalBytes':9076290},'qualifiedComponentsByteExactOFF18':same,'integrationFixtureProof':pr['qualifiedIntegrationFixtureProof'],'candidateSourceChallenge':pr['candidateSourceChallenge'],'pureControlsRecomputed':out,'cases':pr['cases'],'verified':['Targeted closure includes fixed current7618builder baseline proof and whole main0container, exactTC5cdaOFFcompiler/fixedpoint ownsource proof, exactcandidate16unity and sourceHOLD. All inputs regular exact; no wholehistorical archive claim.','Six sealed compiler commands only: candidatebuild/extract2 then identicalfixtureOFF2 then generatedcandidateON2. Arity0main loader uses -- for CLI; fixturebench1 is only selected extraction metadata, never a guest invocation.','Exact current16candidate unity reconstructed with sole41ce012 replacement; unchangedfixture source copied readonly. No workloadnamed eligibility or implicit assumed exportoffset.','Generated candidate receives sealed source/builder/rootGO/native/wholecontainer/2closedadmittedbuild receipts; wrapper verifies producerBuild for calls5/6, exactproducerbytes/main0 before exec. Neither receipt nor nativecreation upgrades sourceclobberHOLD.','Exact GO keyset/two distinct specific SOURCEreviews/6call limit/runtimefalse/C2false/noRetry; fullsource/input/generatedguards beforeeachchild; no lookup during sampling.','Compile output wholecontainer/reportbytes; each extraction resolves own symbolarity and compares fullpayload, not selected fragment.','Unchanged controller/capture/integration/nativecall/typedadapter/resources retain firstfailure, retire-before-wait, singlewait/no postuncertainty groupoperations, stoppedwriter hashes, durable namedsetter6rows and explicit17envexec.','CPU1800/hard1801 FSIZE64MiB soft4GiBfootprint max2members1810wall30cleanup;6child/12aux/18conservative stages, bounded8MiBstdout/1MiBstderr/16MiBsamplejournal/64KiBlimits and metadata. Cooperative bounds and1GiBreservation are not hardfilesystem or wall quota.','Final validlast terminal is durable before guard+COMPLETE; report binds allattempt/results/artifacts/buildreceipt/registrypins/environment/GO. Failure remains failure; no runtime/guest/full19/fixedpoint/performancecertification.'],'limitations':['This SOURCEPASS permits only separatelyGOed six compilerartifact calls; emittedx8/x7/fuelalias/lifetime/entry certificate remains HOLD.','Synthetic/injected controls do not demonstrate actual candidate syntax/admission/clobbers/privateentry or guestfueltrap parity.','Current7618 builder differs from TC5cdaOFF compiler; own generatedcandidate must be checked before its two fixturecalls.','Known owned memory gaps remain unavailablediagnostics; unknown/unbound errors refuse. No hardpeak/atomiccensus/OSthread universalproof.','No ComputeCID/ResultCID cache or C-or-better performance claim; native buildartifact is not optimizeradoption.'],'reviewerSchemaDiagnostic':rec(R/'reviewer-diagnostic.json'),'operations':{'nativeThreadFDPipeProcessGroupSetterNetworkCalls':0,'frozenSubjectOrProductWrites':0}}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
