"""One-off bounded diagnostic harness SOURCE adaptation; zero operational calls."""
from pathlib import Path
import ast,copy,hashlib,json
D=Path(__file__).resolve().parent;W=D.parent;V=W/'crc-original-guest-native-controller-source-v4-20261009-dense'
def pin(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
oldSP=json.loads((V/'source-pins.json').read_text());assert pin(V/'source-pins.json')['sha256']=='0653ae78eb638c10074ed2c32bb4ed5e23c3d016c72fb3f5518f1e0b291d469f'
for n in ['capture.py','integration.py','controller.py','adapter.py','typed-adapter.py','runtime.py','validate-runtime.py','launch-wrapper.py','native-call.py','run.py']:
 assert pin(V/n)==oldSP[n];(D/n).write_bytes((V/n).read_bytes())
replacements=[
 ('Frozen8 original CRC guest plan','Frozen2 additional prefix1081 plan'),
 ('exact guest8 GO','exact prefix1081 paired2 GO'),
 ('SOURCE_FROZEN_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4_HOLD','SOURCE_FROZEN_TC_FULL256_PREFIX1081_PAIRED2_HOLD'),
 ('ROOT_GO_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4_ONLY','ROOT_GO_TC_FULL256_PREFIX1081_PAIRED2_ONLY'),
 ("g['maximumLoaderCalls']==8","g['maximumLoaderCalls']==2"),
 ("pr['maximumPythonWrapperStarts']==8","pr['maximumPythonWrapperStarts']==2"),
 ("pr['maximumNativeGuestChildStarts']==8","pr['maximumNativeGuestChildStarts']==2"),
 ('PASS_SOURCE_ONLY_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4','PASS_SOURCE_ONLY_TC_FULL256_PREFIX1081_PAIRED2'),
 ('len(rows)==8 and len(results)==8','len(rows)==2 and len(results)==2'),
 ('len(rows)==8 and all','len(rows)==2 and all'),
 ('all eight guests closed','both prefix1081 guests closed'),
 ('valid-last all eight closed','valid-last both prefix1081 closed'),
 ('COMPLETE_CURRENT_ORIGINAL_TC_GUEST8_CAPTURE_SEMANTIC_DIAGNOSTIC_ONLY','COMPLETE_TC_FULL256_PREFIX1081_PAIRED2_SEMANTIC_DIAGNOSTIC_ONLY'),
 ("'pairedCases':4","'pairedCases':1"),
 ('source-bound checksum via prefix-crc positive stop and bench1; selected physical site220 required by prior audited emission','original checksum prefix1081, selected physical site220; source certificate covers all256 indices'),
 ("'full256CandidateReachQualified':False","'full256CandidateReachQualified':False,'sourceBoundFull256PrefixParityQualified':True")]
p=D/'run.py';s=p.read_text()
for a,b in replacements:assert a in s,a;s=s.replace(a,b)
anchor=" guard();need(pr['qualifiedMemoryFixtureProof']is not None,'accepted actual fixture proof required')"
assert anchor in s
addition=""" proof=pr['priorActualGuest8IndependentProof'];prior=load(pin(proof['path'],proof))
 need(prior['status']=='PASS_INDEPENDENT_ACTUAL_CURRENT_ORIGINAL_TC_GUEST8_NATIVE_CAPTURE_V4_ONLY' and prior['sourcePinsSHA256']=='0653ae78eb638c10074ed2c32bb4ed5e23c3d016c72fb3f5518f1e0b291d469f','prior V4 actual proof required')
 cert=load(D/'fuel-reach-certificate.json');need(cert['argument']==1081 and cert['expectedCRC']==4018572661 and cert['expectedRemainingFuel']==997836 and cert['uniqueTableIndices']==256 and cert['selectedCallerSIR']==220,'frozen SOURCE reach/fuel expectation')
 need(len(pr['cases'])==2 and [c['arm']for c in pr['cases']]==['OFF','ON'] and all(c['argument']==1081 and c['symbol']=='prefix-crc' and c['expectedResult']==4018572661 and c['expectedRemainingFuel']==997836 for c in pr['cases']),'only fixed paired1081')
"""
s=s.replace(anchor,addition+anchor,1);p.write_text(s)
completionAnchor="  completion['strictOldMemoryPolicyPassed']=all(r['strictOldMemoryPolicyPassed']for r in results)"
assert completionAnchor in s
s=s.replace(completionAnchor,"  completion['priorActualGuest8IndependentProof']=pr['priorActualGuest8IndependentProof']\n  completion['fuelReachCertificate']=pr['fuelReachCertificate']\n"+completionAnchor,1);p.write_text(s)
p=D/'native-call.py';s=p.read_text();assert "len(rows)<8"in s and "fixed ordered original8 no retry"in s
s=s.replace('len(rows)<8','len(rows)<2').replace('fixed ordered original8 no retry','fixed ordered additional1081 pair no retry')
old="report['initialFuel']==1000000 and report['metered']is True"
assert old in s;s=s.replace(old,"report['initialFuel']==1000000 and report['remainingFuel']==case['expectedRemainingFuel'] and report['metered']is True",1);p.write_text(s)
pr=json.loads((V/'preregistration.json').read_text());pr['status']='SOURCE_FROZEN_TC_FULL256_PREFIX1081_PAIRED2_HOLD';pr['keyVersion']='crc-table-full256-prefix1081-paired2-v1'
oldcases=copy.deepcopy(pr['cases']);cases=[]
for i,c in enumerate(oldcases[:2],1):
 c['index']=i;c['label']='prefix-crc-1081-'+c['arm'].lower();c['argument']=1081;c['expectedResult']=4018572661;c['expectedRemainingFuel']=997836;c['nativeArgv'][-1]='1081';cases.append(c)
pr['cases']=cases;pr['orderedChildren']=copy.deepcopy(cases)
for k in ['maximumLoaderCalls','maximumPythonWrapperStarts','maximumNativeGuestChildStarts']:pr[k]=2
for k in ['maximumDistinctProcessStarts','maximumAuxiliaryThreadStarts']:pr[k]=4
for k in ['maximumGateLoaderCPUSeconds','maximumGateKernelCPUHardSeconds','maximumGateWallPlusReapSeconds','maximumGateRawPrefixBytes','maximumGateMemoryReceiptBytes','maximumGateGuestFuel']:pr[k]//=4
pr['environment']['TMPDIR']=str(D/'run-outputs');pr['freshOutputRoot']=str(D/'run-outputs');pr['gateScope']='additional OFF/ON prefix1081 only,2calls/1pair; no old8/full19/compiler/extraction calls'
proof=W/'crc-original-guest-native-controller-v4-actual-review-independent-20261009/report.json';assert pin(proof)['sha256']=='6c8e86547cb5311ce48a8ce7ef5a8eada9daac1568b59d4b4f841d643dc6105c'
pr['priorActualGuest8IndependentProof']=dict(path=str(proof),**pin(proof));pr['priorV4ActualProofBindingState']='CONFIRMED_DURING_AUTHORING; initial pending placeholder superseded by exact frozen proof6c8e8654'
pr['runtimeHOLD']='NO_PREFIX1081_RUNTIME_OBSERVATION; two SOURCE reviews +separate exact GO still required'
pr['full256RuntimeResults']=None;pr['fuelReachCertificate']=dict(path=str(D/'fuel-reach-certificate.json'),**pin(D/'fuel-reach-certificate.json'))
inputs=json.loads((V/'input-pins.json').read_text())
for q in [proof,V/'source-pins.json',V/'freeze.json',V/'run.py',V/'native-call.py',V/'preregistration.json']:
 inputs[str(q)]=pin(q)
certificate=json.loads((D/'fuel-reach-certificate.json').read_text())
for record in [certificate['source'],certificate['typedCurrentRaw']]:inputs[record['path']]={k:record[k]for k in ['bytes','sha256']}
pr['inputCount']=len(inputs);pr['inputLogicalBytes']=sum(v['bytes']for v in inputs.values())
(D/'input-pins.json').write_text(json.dumps(inputs,indent=2)+'\n');pr['inputRegistrySHA256']=pin(D/'input-pins.json')['sha256']
(D/'preregistration.json').write_text(json.dumps(pr,indent=2)+'\n')
(D/'go-schema.json').write_text(json.dumps({'status':'ROOT_GO_TC_FULL256_PREFIX1081_PAIRED2_ONLY','maximumLoaderCalls':2,'notAnExecutableGO':True,'requiredMemoryPolicyVersion':pr['memoryPolicyVersion'],'requiredSourceReviewStatus':'PASS_SOURCE_ONLY_TC_FULL256_PREFIX1081_PAIRED2','priorActualGuest8IndependentProof':pr['priorActualGuest8IndependentProof'],'runtimeObservation':None},indent=2)+'\n')
for p in D.glob('*.py'):ast.parse(p.read_text())
unchanged=['capture.py','integration.py','controller.py','adapter.py','typed-adapter.py','runtime.py','validate-runtime.py','launch-wrapper.py']
assert all((D/n).read_bytes()==(V/n).read_bytes()for n in unchanged)
controls={'status':'PASS_SOURCE_ONLY_BOUNDED_PAIR_ADAPTATION_AND_EXPECTATIONS','unchangedV4RuntimeComponentFiles':unchanged,'pairedCalls':2,'guestArgument':1081,'expectedCRC':4018572661,'expectedRemainingFuel':997836,'casesOrder':['OFF','ON'],'rootGOAvailable':False,'nativeCalls':0,'operationalAPICalls':0,'sourceAuthoringException':'one-off diagnostic harness adaptation, no existing mechanical refactor rule','oldNamespacesEdited':False}
(D/'source-controls.json').write_text(json.dumps(controls,indent=2)+'\n');print(json.dumps(controls,indent=2))
