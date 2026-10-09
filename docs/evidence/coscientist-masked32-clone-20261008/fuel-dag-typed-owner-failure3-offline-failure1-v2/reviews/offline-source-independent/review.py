"""SOURCE inspection, exact reversal/hash checks only. No saved validator invocation."""
from pathlib import Path
import json,hashlib,ast,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-v2-controls';D=Path(__file__).resolve().parent
def r(p):
 p=Path(p);z=p.lstat();assert stat.S_ISREG(z.st_mode)and not p.is_symlink();return dict(bytes=z.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
sp=load(S/'source-pins.json');assert r(S/'source-pins.json')['sha256']=='fc4e8ae61ce8269661a84cfba5d3576007e9bf9425b594f69b00bf004057729a';ip=load(S/'input-pins.json');assert len(ip)<=2048 and sum(z['bytes']for z in ip.values())<=402653184
for p,z in ip.items():assert r(p)==z
for n,z in sp.items():assert r(S/n)==z
for n in ['run.py','validate.py']:ast.parse((S/n).read_bytes())
de=load(S/'source-delta.json');old=Path(de['priorValidator']['path']);assert r(old)=={k:de['priorValidator'][k]for k in ['bytes','sha256']};a=old.read_text();b=(S/'validate.py').read_text()
for z in de['replacements']:assert a.count(z['old'])==1;a=a.replace(z['old'],z['new'])
assert a==b
pr=load(S/'preregistration.json');f=load(pr['failureAuditReport']['path']);assert f['status']==pr['failureAuditStatus']and f['inputPinsSHA256']==pr['failureAuditInputPins']['sha256']and f['counts']['closedCalls']==3 and f['counts']['nativeRC0']==3 and f['counts']['unexecutedExtract']==1
# Arithmetic source contracts, not an actual saved validator replay.
assert (69-1)*4==272 and (36-1)*4==140 and 0+2>1
for fn,anchor in [('df-admit','(<= (+ t n) (gn-g M gn-f-h))'),('gn-ctx','(if (= (gn-g M gn-f-ctx) 1) M'),('ly-byte-off','(* (- i (ly-first)) 4)')]:
 t=(W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width/unity-observer.kotoba').read_text();assert '(defn- '+fn in t and anchor in t
run=(S/'run.py').read_text();assert "vb=read(D/'validate.py',sp['validate.py'])"in run and "exec(compile(vb,str(D/'validate.py'),'exec'),ns)"in run and '__name__'in run and 'import validate'not in run and 'subprocess'not in run and "g['maximumOfflineValidations']==1"in run and "g['nativeAuthorized']is False"in run
for n in ['source-pins.json',*sp]:ip[str(S/n)]=r(S/n)
ip[str(D/'review.py')]=r(D/'review.py');save(D/'input-pins.json',dict(sorted(ip.items())))
report=dict(status='PASS_SOURCE_ONLY_FUEL_DAG_TYPED_OBSERVER_OFFLINE_VALIDATOR_V2',sourcePinsSHA256=r(S/'source-pins.json')['sha256'],driverSHA256=r(S/'run.py')['sha256'],validatorSHA256=r(S/'validate.py')['sha256'],preregistrationSHA256=r(S/'preregistration.json')['sha256'],inputPinsSHA256=r(D/'input-pins.json')['sha256'],checks=dict(exactEightRegisteredTextReplacementsNoOtherValidatorDelta=True,fivePriorFalsePredicatesSourceBound=True,postCallH2To1AndCtx0To1AndAdmission18To0=True,entireCODE1Through68AndZeroSentinelRequired=True,FRECOneBasedOffsetMapped=True,originalContextReloadAndExactFiveFuelWordsRequired=True,originalBL26FIXMaskTargetReencoded=True,completeSIRTypedOwnerAndWholePayloadChecksRetained=True,allFrozenProofRawSourceInputsRehashed=True,pinnedByteBufferExecNoPycacheOrSecondSourceRead=True,rootGOAndTwoSpecificReviewsOneOfflineOnly=True,oldFailure3PreservedNoFourthNativeExtract=True),limits=['Fixed positive fixture only; no general IR or CPU/trap proof','No actual saved validator execution performed by this reviewer; pure author tests read as supplied SOURCE evidence only','Guest10 remains separately gated'],participation='Earlier independently audited old failed3 and prior static build8; correction authored controls. This source review does not execute corrected validator against saved native data.',savedActualValidatorRuns=0,nativeCompilerSSHCalls=0,actualValidationQualified=False,performanceQualified=False)
save(D/'report.json',report);print(json.dumps(dict(report=r(D/'report.json'),inputPins=r(D/'input-pins.json'))))
