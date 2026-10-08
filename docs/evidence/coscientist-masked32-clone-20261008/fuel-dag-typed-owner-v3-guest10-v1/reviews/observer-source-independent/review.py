"""SOURCE-only correction review. Does not execute actual validator/native."""
from pathlib import Path
import json,hashlib,stat,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent;S=W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-v3-controls';OLD=W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-v2-controls'
def r(p):
 p=Path(p);z=p.lstat();assert stat.S_ISREG(z.st_mode)and not p.is_symlink();return dict(bytes=z.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
assert r(S/'source-pins.json')['sha256']=='f10fb71125bfcdb58296688d4f47957552fed3eb0a248a077bb83ce69e429acc';sp=load(S/'source-pins.json');ip=load(S/'input-pins.json');assert len(ip)<=2048 and sum(v['bytes']for v in ip.values())<=402653184
for p,v in ip.items():assert r(p)==v
for n,v in sp.items():assert r(S/n)==v
for n in ['run.py','validate.py']:ast.parse((S/n).read_bytes())
a=(OLD/'validate.py').read_text();b=(S/'validate.py').read_text();assert a.count('w>>26==0b100101')==1 and b.replace('w>>26==0b000101','w>>26==0b100101')==a
pr=load(S/'preregistration.json');pf=load(pr['priorOfflineFailureReport']['path']);assert pf['counts']==dict(offlineValidations=1,newNativeCalls=0,oldClosedNativeCalls=3,oldFourthExtractUnexecuted=1,inputFiles=1844,logicalBytes=376389897)and pf['originalOfflineFailure']is True and pf['validatorRerun']is False
run=(S/'run.py').read_text();assert "vb=read(D/'validate.py',sp['validate.py'])"in run and "exec(compile(vb,str(D/'validate.py'),'exec'),ns)"in run and 'import validate'not in run and 'subprocess'not in run
for phase in [0,1]:
 for row in ['23 13 1 0 1','24 19 0 0 0','25 2 3 0 0']:assert 'FSIR '+str(phase)+' '+row in run
assert "rows['FFIX']==[[1,34,4,mask,0]]"in b and '(pc-1)*4+disp*4==(F[1][mask][13]-1)*4'in b
src=(W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width/unity-observer.kotoba').read_text();assert 'FX-BL26 resolves a function target and patches imm26; the opcode remains B.'in src and '(gn-put MM-CODE-N at) (gn-chain-fix f t n) (gn-emit (enc-b 0))'in src
# Independent finite instruction arithmetic only; no saved trace validator replay.
w=0x17ffffdf;imm=w&0x3ffffff;disp=imm-(1<<26)if imm&(1<<25)else imm;assert w>>26==0b000101 and disp==-33 and (34-1)*4+disp*4==0 and 0x97ffffdf>>26!=0b000101
for n in ['source-pins.json',*sp]:ip[str(S/n)]=r(S/n)
ip[str(D/'review.py')]=r(D/'review.py');save(D/'input-pins.json',dict(sorted(ip.items())))
v=dict(status='PASS_SOURCE_ONLY_FUEL_DAG_TYPED_OBSERVER_OFFLINE_VALIDATOR_V3',sourcePinsSHA256=r(S/'source-pins.json')['sha256'],driverSHA256=r(S/'run.py')['sha256'],validatorSHA256=r(S/'validate.py')['sha256'],preregistrationSHA256=r(S/'preregistration.json')['sha256'],inputPinsSHA256=r(D/'input-pins.json')['sha256'],checks=dict(exactOneOpcodeReverseToV2=True,strictTailBNotBroadBOrBLAcceptance=True,fullFunctionTargetFIXAux0AndSignedImm26TargetRetained=True,bothPhaseTypedExtraMaskCALL_RETurn_ENDRequired=True,allFiveOldPredicateCorrectionsAndWholeCodeFuelWordsRetained=True,exactPriorFAIL1_Native0AndFAIL3Bound=True,pinnedBufferExecutionNoImportOrReread=True,rootTwoSpecificReviewsOneOfflineOnly=True,fullFrozenClosureRehashed=True),participation='Independently audited prior failure3, SOURCE-reviewed V2 then audited its offline failure1. Prior V2 SOURCE approval missed tail-B versus kind4; preserved and disclosed. V3 correction authored controls, not this reviewer.',savedActualValidatorRuns=0,nativeCompilerSSHCalls=0,actualOfflineValidationQualified=False,actualCPUTrapQualified=False,performanceQualified=False,limits=['Fixed retained fixture only; no generic opcode/function correctness proof','Independent source arithmetic rejects BL while accepting source-tail B; no actual saved-validator execution','Original failed V2 receipt unchanged; guest10 remains separate GO'])
save(D/'report.json',v);print(json.dumps(dict(report=r(D/'report.json'),inputPins=r(D/'input-pins.json'))))
