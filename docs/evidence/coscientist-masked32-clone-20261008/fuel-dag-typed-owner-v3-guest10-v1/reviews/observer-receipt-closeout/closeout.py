"""Finite saved-evidence byte/hash and correspondence receipt. No validator imports/execution."""
from pathlib import Path
import hashlib,json,stat,struct,datetime
W=Path('/Users/junkawasaki/github/workspaces/codex')
D=Path(__file__).resolve().parent
A=W/'vector-fuel-scalar-dag-emitted-observer4-offline-actual-review-v3-native-controls'
S=W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-v3-controls'
R=W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width/run-outputs'
cache={}; hashes={}; failures=[]; checks={}
def read(p):
 p=str(p)
 if p not in cache:
  q=Path(p); s=q.lstat()
  assert stat.S_ISREG(s.st_mode) and not q.is_symlink(),p
  cache[p]=q.read_bytes(); hashes[p]={'bytes':len(cache[p]),'sha256':hashlib.sha256(cache[p]).hexdigest()}
 return cache[p]
def load(p):return json.loads(read(p))
def ck(name,test):
 checks[name]=bool(test)
 if not test: failures.append(name)
report=load(A/'report.json'); pins=load(A/'input-pins.json'); join=load(A/'typed-machine-join.json'); audit=read(A/'audit.py'); src=load(S/'offline-outputs/report.json')
for p,z in pins.items():
 try: read(p); ck('pin:'+p,hashes[p]==z)
 except Exception as e: failures.append('pin:'+p+':'+str(e))
ck('pinned-count-bytes',len(pins)==report['counts']['inputFiles'] and sum(z['bytes'] for z in pins.values())==report['counts']['inputLogicalBytes'])
for name,path in [('inputPinsSHA256',A/'input-pins.json'),('actualOfflineReportSHA256',S/'offline-outputs/report.json'),('typedMachineJoinSHA256',A/'typed-machine-join.json')]:ck(name,report[name]==hashes[str(path)]['sha256'])
ck('finished-saved-reports',report['status']=='PASS_INDEPENDENT_SAVED_OFFLINE_FUEL_DAG_TYPED_OWNER_V3_STATIC_MACHINE_JOIN_ONLY' and src['status']=='COMPLETE_OFFLINE_FUEL_DAG_TYPED_OWNER_SAVED_RAW_VALIDATOR_V3_ONLY' and all(report['checks'].values()))
ck('terminal-boundary',load(S/'offline-outputs/terminal.json')=={'offlineValidations':1,'nativeCalls':0,'failure':False} and sorted(p.name for p in (S/'offline-outputs').iterdir())==['report.json','terminal.json'])
ck('qualifications-boundary',all(x.get('actualCPUTrapQualified') is False and x.get('performanceQualified') is False for x in [report,src,join]) and report['guest10Authorized'] is False and src['generatedCodeExecution'] is False)
go=load(W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-go-v3-root/root-go.json')
for key in ['sourcePinsSHA256','driverSHA256','validatorSHA256','rootGOSHA256']:ck('report-root:'+key,report[key]==(hashes[str(W/'vector-fuel-scalar-dag-emitted-observer4-offline-validator-go-v3-root/root-go.json')]['sha256'] if key=='rootGOSHA256' else go[key]))
for key in ['sourcePinsSHA256','validatorSHA256','rootGOSHA256']:ck('source-review:'+key,src[key]==report[key])
raw=read(R/'positive-compile.stdout');source=read(R/'positive.kotoba');native=read(join['native']['path']);container=read(join['container']['path'])
ck('saved-raw-hash',src['savedRawSHA256']==hashes[str(R/'positive-compile.stdout')]['sha256'])
width={'FH':7,'FSIR':6,'FF':4,'FNODE':5,'FSYM':5,'FTOK':5,'FCALL':17,'FG':4,'FOUT':7,'FCODE':2,'FLABEL':2,'FFIX':5,'FLIT':5,'FLITB':2,'FEXP':5,'FEND':2};rr={q:[] for q in width};ok=[]
try:
 for line in raw.splitlines():
  if line.startswith(b'{:ok true,'):ok.append(line);continue
  z=line.split();tag=z[0].decode();assert tag in width and len(z)==width[tag]+1
  vals=list(map(int,z[1:]));assert all(-(1<<63)<=x<(1<<63) for x in vals);rr[tag].append(vals)
 assert len(ok)==1 and rr['FH']==[[0,0,36,5,62,19,79],[1,0,36,5,62,19,79]] and rr['FEND']==[[1,0]]
 sir={ph:{z[1]:z[2:] for z in rr['FSIR'] if z[0]==ph} for ph in [0,1]}
 assert all(len([z for z in rr['FSIR'] if z[0]==ph])==35 for ph in [0,1]) and sir[0]==sir[1] and sorted(sir[0])==list(range(1,36))
 funcs={};names={}
 for ph in [0,1]:
  assert len([z for z in rr['FF'] if z[0]==ph])==64
  for f in range(1,5):
   rows=[z for z in rr['FF'] if z[:2]==[ph,f]];assert sorted(z[2] for z in rows)==list(range(16));rec=[next(z[3] for z in rows if z[2]==j) for j in range(16)];funcs[ph,f]=rec
   nodes=[z for z in rr['FNODE'] if z[:2]==[ph,f]];symbols=[z for z in rr['FSYM'] if z[:2]==[ph,f]];tokens=[z for z in rr['FTOK'] if z[:2]==[ph,f]]
   assert [z[3] for z in nodes]==list(range(8)) and [z[3] for z in symbols]==list(range(8)) and [z[3] for z in tokens]==list(range(4))
   assert all(z[2]==rec[1] for z in nodes) and all(z[2]==rec[0] for z in symbols) and 0<rec[1]<62 and 0<rec[0]<19
   nv=[z[4] for z in nodes];sv=[z[4] for z in symbols];tv=[z[4] for z in tokens]
   assert all(z[2]==nv[3] for z in tokens) and 0<nv[3]<79 and 0<=tv[1]<=tv[2]<=len(source) and 0<=sv[0]<sv[1]<=len(source)
   name=source[sv[0]:sv[1]].decode();names[ph,f]=name
   assert rec[4]==1 and rec[3]==(2 if name=='mix' else 1) and all(rec[5+j]==1 for j in range(rec[3])) and rec[11]==(1 if name=='bench' else 0) and rec[14]==(0 if name=='mask' else 1)
 assert {names[0,f]:f for f in range(1,5)}==join['typedNames']=={'mask':1,'mix':2,'extra':3,'bench':4}
 assert all(names[0,f]==names[1,f] for f in range(1,5)) and all(funcs[0,f][j]==funcs[1,f][j] for f in range(1,5) for j in range(16) if j!=13)
 owner=0;owners={};ends={}
 for i,z in sir[0].items():
  if z[0]==1:
   assert owner==0 and funcs[0,z[1]][12]==i and z[2]==funcs[0,z[1]][3] and z[3]==funcs[0,z[1]][10];owner=z[1]
  assert owner>0;owners[i]=owner
  if z[0]==2:assert z==[2,owner,0,0];ends[owner]=i;owner=0
 assert owner==0 and ends=={1:7,2:18,3:25,4:35}
 assert [i for i,z in sir[0].items() if z[0]==18]==[9,20,27] and all(sir[0][i]==[18,0,0,0] for i in [9,20,27])
 assert sir[0][31]==[13,2,0,2] and owners[31]==4 and sir[0][16]==sir[0][23]==[13,1,0,1]
 admitted=[31,4,2,0,2,18,0,47,62,0,1,0,1,0,0,0,0];assert [z for z in rr['FCALL'] if z[5]>0]==[admitted]
 fg={ph:[next(z[3] for z in rr['FG'] if z[:3]==[31,ph,j]) for j in range(16)] for ph in [0,1]}
 assert fg[0][6:8]==[2,0] and fg[1][6:8]==[1,1] and all(v[0]==v[11]==0 and v[3]==64 and v[4]==1 and v[5]==2 for v in fg.values())
 code=dict(rr['FCODE']);assert len(rr['FCODE'])==69 and sorted(code)==list(range(69)) and code[0]==0 and all(0<=x<2**32 for x in code.values())
 assert b''.join(struct.pack('<I',code[i]) for i in range(1,69))==native==read(R/'positive.kseed').split(b'\n\n',1)[1]
 assert container==read(R/'positive.kseed') and container.split(b'\n\n',1)[0]==b'KSEED1 272 1\nbench 140 1' and len(container)==298 and len(native)==272
 assert rr['FOUT']==[[69,272,5,2,1,1,2]] and rr['FEXP']==[[1,4,140,1,0]] and (funcs[1,4][13]-1)*4==140 and funcs[1,2][13]==5 and funcs[1,1][13]==1
 assert [code[i] for i in range(47,50)]==[0xaa1303e0,0xd28000e1,0xf9401fe7]
 fuel=[0xf94004f0,0xf1000610,0x54000042,0xd4200000,0xf90004f0];assert [code[i] for i in range(50,55)]==fuel and [code[i] for i in range(42,47)]==fuel
 assert rr['FFIX']==[[1,34,4,1,0]];word=code[34];assert word>>26==0b000101;imm=word&0x3ffffff;disp=imm-(1<<26) if imm&(1<<25) else imm;assert 34+disp==funcs[1,1][13] and (34-1)*4+disp*4==0
 assert join['ownerCallSIR']==31 and join['ownerFN']==4 and join['calleeFN']==2 and join['calleeSIR']==[8,18] and join['maskFN']==1 and join['calleeCodeByte']==16 and join['benchCodeByte']==140 and join['inlineFuelByte']==196 and join['benchEntryFuelByte']==164 and join['originalSIRUnchanged'] is True
 assert src['observed']==dict(status='PASS_FINITE_TYPED_OWNER_OBSERVER_RECORDS_ONLY',functionNamesToIDs={'mask':1,'mix':2,'extra':3,'bench':4},SIRRows=35,admittedCall=admitted,staticMaskReferences=2,calleeEnd=18,codeWords=69,nativeBytes=272,benchOffset=140,ordinaryTypedSourceOwnerCorrespondence=True,actualCPUTrapQualified=False,performanceQualified=False)
 ck('strict-typed-owner-and-full272-correspondence',True)
except Exception as e:ck('strict-typed-owner-and-full272-correspondence',False);failures.append(repr(e))
receipt={'status':'PASS' if not failures else 'HOLD','scope':'Finite saved-evidence freeze of current V3 report and input pins; no validator replay, native, compiler, driver or SSH execution.','participation':'Receipt closeout subagent independently read and hashed existing saved evidence; did not author V3 source, validator, raw trace, machine join or original report. Prior auditor authorship is retained in the source report and is not upgraded to an independent original-agent freeze.','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'counts':report['counts'],'allPinnedFilesChecked':len(pins),'allPinnedLogicalBytes':sum(z['bytes'] for z in pins.values()),'checks':{k:v for k,v in checks.items() if not k.startswith('pin:')},'pinMismatches':[x for x in failures if x.startswith('pin:')],'failures':failures,'exactArtifactHashes':{str(p):hashes[str(p)] for p in [A/'report.json',A/'input-pins.json',A/'audit.py',A/'typed-machine-join.json',S/'offline-outputs/report.json']},'actualCPUTrapQualified':False,'performanceQualified':False,'guest10Authorized':False,'reviewerValidatorReplayRuns':0,'reviewerNativeCompilerSSHDriverCalls':0}
(D/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(D/'checked-input-hashes.json').write_text(json.dumps({p:hashes.get(p) for p in pins},indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,indent=2))
