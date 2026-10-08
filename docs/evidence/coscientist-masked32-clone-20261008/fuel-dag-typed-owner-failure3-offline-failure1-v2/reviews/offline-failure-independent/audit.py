"""Saved offline-failure artifacts/source only; no validator rerun/native/process."""
from pathlib import Path
import json,hashlib,stat,re,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent;S=W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-v2-controls';O=S/'offline-outputs';GO=W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-go-v2-root/root-go.json';OLD=W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width';RAW=OLD/'run-outputs'
def r(p):
 p=Path(p);z=p.lstat();assert stat.S_ISREG(z.st_mode)and not p.is_symlink();return dict(bytes=z.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
g=load(GO);pr=load(S/'preregistration.json');sp=load(S/'source-pins.json');ip=load(S/'input-pins.json');assert len(ip)<=2048 and sum(z['bytes']for z in ip.values())<=402653184
for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('validate.py','validatorSHA256'),('preregistration.json','preregistrationSHA256'),('input-pins.json','inputPinsSHA256')]:assert r(S/n)['sha256']==g[k]
for p,z in ip.items():assert r(p)==z
for n,z in sp.items():assert r(S/n)==z
for z in g['sourceReviews']:
 assert r(z['path'])=={k:z[k]for k in ['bytes','sha256']};q=load(z['path']);assert q['status']==pr['sourceReviewStatus']and all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','validatorSHA256'])
assert g['maximumOfflineValidations']==1 and g['nativeAuthorized']is False and g['outputRoot']==str(O)and load(O/'terminal.json')==dict(offlineValidations=1,nativeCalls=0,failure=True);assert load(O/'failure.json')==dict(error='AssertionError()',offlineValidations=1,nativeCalls=0,noRetry=True);assert sorted(p.name for p in O.iterdir())==['failure.json','terminal.json']
k=(RAW/'positive.kseed').read_bytes();assert k==Path(pr['baselineContainer']).read_bytes()and len(k)==298;head,native=k.split(b'\n\n',1);assert head==b'KSEED1 272 1\nbench 140 1'and native==Path(pr['baselineNative']).read_bytes()and r(pr['baselineNative'])['sha256']==pr['baselineNativeSHA256'];assert (RAW/'positive.kotoba').read_bytes()==Path(pr['fixture']).read_bytes();assert load(RAW/'terminal.json')==dict(loaderCalls=3,allChildrenClosed=True,failure=True)
rows={}
for line in (RAW/'positive-compile.stdout').read_bytes().splitlines():
 if line.startswith(b'{'):continue
 p=line.split();rows.setdefault(p[0].decode(),[]).append(list(map(int,p[1:])))
code=dict(rows['FCODE']);sir={z[1]:z[2:]for z in rows['FSIR']if z[0]==0};frec={f:{z[2]:z[3]for z in rows['FF']if z[:2]==[1,f]}for f in range(1,5)}
assert rows['FFIX']==[[1,34,4,1,0]]and sir[23]==[13,1,0,1]and sir[24]==[19,0,0,0]and sir[25]==[2,3,0,0]and frec[1][13]==1;assert code[34]==402653151
assert b''.join(struct.pack('<I',code[i])for i in range(1,69))==native
w=code[34];opcode=w>>26;imm=w&((1<<26)-1);disp=imm-(1<<26)if imm&(1<<25)else imm;targetIndex=34+disp;targetByte=(34-1)*4+disp*4;assert opcode==0b000101 and disp==-33 and targetIndex==1 and targetByte==(frec[1][13]-1)*4==0
source=(OLD/'unity-observer.kotoba').read_text();assert '(def FX-BL26 4)'in source and 'FX-BL26 resolves a function target and patches imm26; the opcode remains B.'in source and '(gn-put MM-CODE-N at) (gn-chain-fix f t n) (gn-emit (enc-b 0))'in source;assert '(ly-branch M at t (ly-width kind))'in source
validator=(S/'validate.py').read_text();assert 'assert w>>26==0b100101'in validator
witness=dict(status='SOURCE_BOUND_TAIL_B_FUNCTION_FIX_KIND4_OPCODE_MISMATCH',codeIndex=34,wordDecimal=w,wordHex=f'{w:08x}',actualOpcodeBits='000101',validatorExpectedOpcodeBits='100101',FIX=rows['FFIX'][0],signedWordDisplacement=disp,targetCodeIndex=targetIndex,targetByte=targetByte,maskFF_CODE=frec[1][13],originalTailSIR=[sir[i]for i in [23,24,25]],sourceAnchors=dict(gn_call_generic='successor OP_RET returns same scalar temp selects gn-op-tail-call',gn_op_tail_call='gn-epilogue followed by RET replacement enc-b and gn-chain-fix',FX_BL26='kind4 resolves function, imm26; opcode B preserved',ly_patch26='patches low26 displacement preserving bits31:26'),nextCorrection='Strict fixedfixture B required, retain full typed extra owner→mask tail relation, full native identity and same FIX function target/aux0; do not accept arbitrary B/BL or relabel failed V2')
save(D/'failure-witness.json',witness)
for n in ['source-pins.json',*sp]:ip[str(S/n)]=r(S/n)
for z in g['sourceReviews']:ip[z['path']]=r(z['path'])
ip[str(GO)]=r(GO)
for p in O.iterdir():ip[str(p)]=r(p)
ip[str(D/'audit.py')]=r(D/'audit.py');ip[str(D/'failure-witness.json')]=r(D/'failure-witness.json');save(D/'input-pins.json',dict(sorted(ip.items())))
report=dict(status='FAIL_PRESERVED_INDEPENDENT_SAVED_OFFLINE_FUEL_OWNER_VALIDATOR_V2_TAIL_B_OPCODE_ONLY',sourcePinsSHA256=g['sourcePinsSHA256'],driverSHA256=g['driverSHA256'],validatorSHA256=g['validatorSHA256'],rootGOSHA256=r(GO)['sha256'],inputPinsSHA256=r(D/'input-pins.json')['sha256'],counts=dict(offlineValidations=1,newNativeCalls=0,oldClosedNativeCalls=3,oldFourthExtractUnexecuted=1,inputFiles=len(ip),logicalBytes=sum(z['bytes']for z in ip.values())),checks=dict(allExactFrozenProofInputsAndTwoSpecificReviews=True,originalFailure3Preserved=True,wholeRetained298Container272PayloadUnchanged=True,actualCODE34TailBFunctionFIXTargetDecoded=True,sourceTailPredicateAndOpcodePreservingRelocationContract=True,failedV2NotReclassified=True),originalOfflineFailure=True,nativeCompilerFailure=False,validatorRerun=False,sourceOrCandidateMutation=False,failureReason='V2 asserted BL opcode for existing source tail-call B using FX-BL26 function-target relocation.',participation='Previously authored primary savednative3 failure audit and independently SOURCE-approved V2. That SOURCE approval missed kind4 tail-B meaning; V2 authored controls and executed by root. Error is disclosed, earlier reports preserved.',executionBoundary='Root reported one offline run CLOSED1; independently audited artifact terminal/failure and exact saved inputs, not a separate OS-process trace.',completeObserverEvidenceAccepted=False,actualCPUTrapQualified=False,performanceQualified=False,reviewerNativeCompilerSSHCalls=0)
save(D/'report.json',report);print(json.dumps(dict(report=r(D/'report.json'),inputPins=r(D/'input-pins.json'),witness=r(D/'failure-witness.json'))))
