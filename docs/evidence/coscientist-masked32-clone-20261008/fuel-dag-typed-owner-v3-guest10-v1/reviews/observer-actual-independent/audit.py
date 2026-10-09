"""Independent saved raw/artifact composition, no author-validator or native rerun."""
from pathlib import Path
import json,hashlib,stat,re,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent;S=W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-v3-controls';O=S/'offline-outputs';OLD=W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width';RAW=OLD/'run-outputs';GO=W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-go-v3-root/root-go.json';M=W/'vector-fuel-scalar-dag-emitted-build8-actual-review-v1-native-controls'
def r(p):
 p=Path(p);z=p.lstat();assert stat.S_ISREG(z.st_mode)and not p.is_symlink();return dict(bytes=z.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
g=load(GO);pr=load(S/'preregistration.json');sp=load(S/'source-pins.json');ip=load(S/'input-pins.json');assert r(GO)['sha256']=='c033596a3c5027e9823758f6d3699b1c82d00035586e6c1cb6abf045c6a947b6'
for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('validate.py','validatorSHA256'),('preregistration.json','preregistrationSHA256'),('input-pins.json','inputPinsSHA256')]:assert r(S/n)['sha256']==g[k]
assert len(ip)<=2048 and sum(z['bytes']for z in ip.values())<=402653184
for p,z in ip.items():assert r(p)==z
for n,z in sp.items():assert r(S/n)==z
for z in g['sourceReviews']:
 assert r(z['path'])=={k:z[k]for k in ['bytes','sha256']};v=load(z['path']);assert v['status']==pr['sourceReviewStatus']and all(v[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','validatorSHA256'])
report=load(O/'report.json');term=load(O/'terminal.json');assert report['status']=='COMPLETE_OFFLINE_FUEL_DAG_TYPED_OWNER_SAVED_RAW_VALIDATOR_V3_ONLY'and report['offlineValidations']==1 and report['nativeCalls']==0 and report['rootGOSHA256']==r(GO)['sha256']and report['sourcePinsSHA256']==g['sourcePinsSHA256']and report['validatorSHA256']==g['validatorSHA256'];assert term==dict(offlineValidations=1,nativeCalls=0,failure=False)and sorted(p.name for p in O.iterdir())==['report.json','terminal.json'];assert report['oldFailedNativeCallsPreserved']==3 and report['newNativeExtracts']==0
assert load(RAW/'terminal.json')==dict(loaderCalls=3,allChildrenClosed=True,failure=True);assert load(Path(pr['priorOfflineFailureNamespace'])/'terminal.json')==dict(offlineValidations=1,nativeCalls=0,failure=True)
source=(RAW/'positive.kotoba').read_bytes();assert source==Path(pr['fixture']).read_bytes();k=(RAW/'positive.kseed').read_bytes();assert k==Path(pr['baselineContainer']).read_bytes()and len(k)==298;head,native=k.split(b'\n\n',1);assert head==b'KSEED1 272 1\nbench 140 1'and native==Path(pr['baselineNative']).read_bytes()and len(native)==272
raw=(RAW/'positive-compile.stdout').read_bytes();assert report['savedRawSHA256']==hashlib.sha256(raw).hexdigest();width={'FH':7,'FSIR':6,'FF':4,'FNODE':5,'FSYM':5,'FTOK':5,'FCALL':17,'FG':4,'FOUT':7,'FCODE':2,'FLABEL':2,'FFIX':5,'FLIT':5,'FLITB':2,'FEXP':5,'FEND':2};rr={q:[]for q in width};ok=[]
for line in raw.splitlines():
 if line.startswith(b'{:ok true,'):ok.append(line);continue
 z=line.split();tag=z[0].decode();assert tag in width and len(z)==width[tag]+1;v=list(map(int,z[1:]));assert all(-(1<<63)<=x<(1<<63)for x in v);rr[tag].append(v)
assert len(ok)==1 and rr['FH']==[[0,0,36,5,62,19,79],[1,0,36,5,62,19,79]]and rr['FEND']==[[1,0]]
SIR={ph:{z[1]:z[2:]for z in rr['FSIR']if z[0]==ph}for ph in [0,1]};assert SIR[0]==SIR[1]and sorted(SIR[0])==list(range(1,36));F={ph:{f:[next(z[3]for z in rr['FF']if z[:3]==[ph,f,j])for j in range(16)]for f in range(1,5)}for ph in [0,1]};names={}
for ph in [0,1]:
 assert len([z for z in rr['FF']if z[0]==ph])==64
 for f in range(1,5):
  rec=F[ph][f];nodes=[z for z in rr['FNODE']if z[:2]==[ph,f]];symbols=[z for z in rr['FSYM']if z[:2]==[ph,f]];tokens=[z for z in rr['FTOK']if z[:2]==[ph,f]];assert [z[3]for z in nodes]==list(range(8))and [z[3]for z in symbols]==list(range(8))and [z[3]for z in tokens]==list(range(4));assert all(z[2]==rec[1]for z in nodes)and all(z[2]==rec[0]for z in symbols)and 0<rec[1]<62 and 0<rec[0]<19
  nv=[z[4]for z in nodes];sv=[z[4]for z in symbols];tv=[z[4]for z in tokens];assert all(z[2]==nv[3]for z in tokens)and 0<nv[3]<79 and 0<=tv[1]<=tv[2]<=len(source)and 0<=sv[0]<sv[1]<=len(source);name=source[sv[0]:sv[1]].decode();assert name in ['mask','mix','extra','bench'];names[ph,f]=name
  assert rec[4]==1 and rec[3]==(2 if name=='mix'else 1)and all(rec[5+j]==1 for j in range(rec[3]))and rec[11]==(1 if name=='bench'else 0)and rec[14]==(0 if name=='mask'else 1)
assert {f:names[0,f]for f in range(1,5)}=={1:'mask',2:'mix',3:'extra',4:'bench'}and all(names[0,f]==names[1,f]for f in range(1,5));assert all(F[0][f][j]==F[1][f][j]for f in range(1,5)for j in range(16)if j!=13)
owner=0;owners={};ends={}
for i,z in SIR[0].items():
 if z[0]==1:assert owner==0 and F[0][z[1]][12]==i and z[2]==F[0][z[1]][3]and z[3]==F[0][z[1]][10];owner=z[1]
 assert owner>0;owners[i]=owner
 if z[0]==2:assert z==[2,owner,0,0];ends[owner]=i;owner=0
assert owner==0 and ends=={1:7,2:18,3:25,4:35}
assert [SIR[0][i]for i in range(1,8)]==[[1,1,1,1],[9,1,0,0],[4,0,1,0],[3,1,4294967295,0],[6,5,0,0],[19,0,0,0],[2,1,0,0]]
assert [SIR[0][i]for i in range(8,19)]==[[1,2,2,2],[18,0,0,0],[9,2,0,0],[4,0,1,0],[3,1,1,0],[6,8,0,0],[4,1,2,0],[6,7,0,0],[13,1,0,1],[19,0,0,0],[2,2,0,0]]
assert [i for i,z in SIR[0].items()if z[0]==18]==[9,20,27]and all(SIR[0][i]==[18,0,0,0]for i in [9,20,27]);assert [i for i,z in SIR[0].items()if z[0]==13]==[16,23,31]and owners[31]==4 and SIR[0][31]==[13,2,0,2]
assert SIR[0][23]==[13,1,0,1]and SIR[0][24]==[19,0,0,0]and SIR[0][25]==[2,3,0,0]
a=[31,4,2,0,2,18,0,47,62,0,1,0,1,0,0,0,0];assert [z for z in rr['FCALL']if z[5]>0]==[a]
fg={ph:[next(z[3]for z in rr['FG']if z[:3]==[31,ph,j])for j in range(16)]for ph in [0,1]};assert fg[0][6:8]==[2,0]and fg[1][6:8]==[1,1]and all(v[0]==v[11]==0 and v[3]==64 and v[4]==1 and v[5]==2 for v in fg.values())
assert rr['FOUT']==[[69,272,5,2,1,1,2]]and sorted(dict(rr['FCODE']))==list(range(69));code=dict(rr['FCODE']);assert code[0]==0 and all(0<=x<2**32 for x in code.values())and b''.join(struct.pack('<I',code[i])for i in range(1,69))==native
assert rr['FEXP']==[[1,4,140,1,0]]and (F[1][4][13]-1)*4==140 and F[1][2][13]==5 and F[1][1][13]==1
assert [code[i]for i in range(47,50)]==[0xaa1303e0,0xd28000e1,0xf9401fe7];fuel=[0xf94004f0,0xf1000610,0x54000042,0xd4200000,0xf90004f0];assert [code[i]for i in range(50,55)]==fuel and [code[i]for i in range(42,47)]==fuel
assert rr['FFIX']==[[1,34,4,1,0]];word=code[34];assert word>>26==0b000101;imm=word&0x3ffffff;disp=imm-(1<<26)if imm&(1<<25)else imm;assert 34+disp==F[1][1][13]and (34-1)*4+disp*4==0
expected=dict(status='PASS_FINITE_TYPED_OWNER_OBSERVER_RECORDS_ONLY',functionNamesToIDs=dict(mask=1,mix=2,extra=3,bench=4),SIRRows=35,admittedCall=a,staticMaskReferences=2,calleeEnd=18,codeWords=69,nativeBytes=272,benchOffset=140,ordinaryTypedSourceOwnerCorrespondence=True,actualCPUTrapQualified=False,performanceQualified=False);assert report['observed']==expected
mp=load(M/'machine-proof.json');ar=load(M/'report.json');assert ar['status']=='PASS_INDEPENDENT_SAVED_RAW_FUEL_DAG_EMITTED_BUILD8_IDENTITY_STATIC_MACHINE_ONLY'and mp['status']=='PASS_STATIC_ACTUAL_MACHINE_FUEL_ORDER_FIXED_FIXTURE_ONLY'
for im in mp['images']:
 for role in ['source','container','native']:assert r(im[role]['path'])=={key:im[role][key]for key in ['bytes','sha256']}
on=next(z for z in mp['images']if z['fixture']=='positive'and z['arm']=='ON')
assert Path(on['container']['path']).read_bytes()==(RAW/'positive.kseed').read_bytes()and Path(on['native']['path']).read_bytes()==native and on['offset']==140 and on['arity']==1;assert mp['fuelTransactionProof']==dict(benchEntryUnits=1,outerUnits=1,additionalDynamicCharges=0,privateContextX7Preserved=True,fuelInteriorIngress=False,directBenchABI=True)
joined=dict(schema='FUEL_DAG_EMITTED_TYPED_MACHINE_JOIN/v1',status='PASS_FINITE_POSITIVE_ON_TYPED_OWNER_AND_EXISTING_STATIC_MACHINE8_JOIN_ONLY',native=dict(path=pr['baselineNative'],**r(pr['baselineNative'])),container=dict(path=pr['baselineContainer'],**r(pr['baselineContainer'])),typedNames=dict(mask=1,mix=2,extra=3,bench=4),ownerCallSIR=31,ownerFN=4,calleeFN=2,calleeSIR=[8,18],maskFN=1,calleeCodeByte=16,benchCodeByte=140,inlineFuelByte=196,benchEntryFuelByte=164,originalSIRUnchanged=True,staticFuelTransaction=mp['fuelTransactionProof'],checkedMetadataCapturedFor='positive/ON only; no invented OFF typed trace',scope='Same272B whole candidate payload, source-declared checked owner/signatures and complete SIR; static source-bound e14 synchronous context, baseA64 decoding from existingbuild8. No CPU execution/trap or universal IR theorem.',actualCPUTrapQualified=False,performanceQualified=False)
save(D/'typed-machine-join.json',joined)
for n in ['source-pins.json',*sp]:ip[str(S/n)]=r(S/n)
for z in g['sourceReviews']:ip[z['path']]=r(z['path'])
ip[str(GO)]=r(GO)
for p in O.iterdir():ip[str(p)]=r(p)
for n in ['report.json','input-pins.json','machine-proof.json']:ip[str(M/n)]=r(M/n)
for p,z in load(M/'input-pins.json').items():assert p not in ip or ip[p]==z;ip[p]=z
for p in [D/'audit.py',D/'typed-machine-join.json']:ip[str(p)]=r(p)
assert len(ip)<=2048 and sum(v['bytes']for v in ip.values())<=402653184
save(D/'input-pins.json',dict(sorted(ip.items())))
result=dict(status='PASS_INDEPENDENT_SAVED_OFFLINE_FUEL_DAG_TYPED_OWNER_V3_STATIC_MACHINE_JOIN_ONLY',sourcePinsSHA256=g['sourcePinsSHA256'],driverSHA256=g['driverSHA256'],validatorSHA256=g['validatorSHA256'],rootGOSHA256=r(GO)['sha256'],inputPinsSHA256=r(D/'input-pins.json')['sha256'],actualOfflineReportSHA256=r(O/'report.json')['sha256'],typedMachineJoinSHA256=r(D/'typed-machine-join.json')['sha256'],counts=dict(offlineValidations=1,newNativeCalls=0,priorClosedNativeCalls=3,unexecutedFourthNativeExtract=1,fullTypedSIRRows=35,typedFunctions=4,qualifiedInlineSites=1,inputFiles=len(ip),inputLogicalBytes=sum(v['bytes']for v in ip.values())),checks=dict(fullSourceRootGOAndTwoSpecificReviewsRehashed=True,rootArtifactTerminalSuccessOneOfflineNoNative=True,oldNativeFailure3AndOfflineFailure1Preserved=True,whole298Container272NativeStaticMachine8Joined=True,fullPrePost35SIR_FREC_SourceNodesSymbolsTokensOwnersParsed=True,exactI64SignaturesAndFuelRowsOwned=True,admissionBefore18After0AndHeightCtxTransitionExact=True,entireCODE1_68AndContextReloadAndFuel5Exact=True,strictTailBFunctionFIXDecodedTargetMaskEntryExact=True,rootObservedResultIndependentlyRecomputedWithoutValidatorExec=True),typedPositiveONCorrespondenceQualified=True,staticSourceBoundMachineJoinQualified=True,actualCPUTrapQualified=False,performanceQualified=False,guest10Authorized=False,participation='Authored existing staticbuild8 audit and failed3/failure1 audits; independently reviewed correctedV3 SOURCE. Corrections authored controls; root executed once. This auditor parses independent saved facts, never invokes author validator or native.',executionBoundary='Artifact terminal/report plus root communicated CLOSED0; no independent OS-exec trace or extra offline/native rerun.',limits=['PositiveON typed trace only; OFF and negative image facts are existing raw staticbuild8, not new typed traces','No generated workload guest or nonresuming CPUtrap qualification','Guest10 still requires separate root composed acceptance and GO'],reviewerNativeCompilerSSHCalls=0,reviewerSavedValidatorRuns=0)
save(D/'report.json',result);print(json.dumps(dict(report=r(D/'report.json'),inputPins=r(D/'input-pins.json'),typedMachineJoin=r(D/'typed-machine-join.json'))))
