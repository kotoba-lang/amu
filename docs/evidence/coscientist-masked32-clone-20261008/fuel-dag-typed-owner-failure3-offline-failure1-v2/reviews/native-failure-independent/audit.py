"""Saved raw audit only. No native/process/author-validator execution."""
from pathlib import Path
import json,hashlib,stat,re,struct
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent;S=W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width';O=S/'run-outputs';GO=W/'vector-fuel-scalar-dag-emitted-observer4-go-v1-root/root-go.json'
def r(p):
 p=Path(p);z=p.lstat();assert stat.S_ISREG(z.st_mode)and not p.is_symlink();return dict(bytes=z.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
g=load(GO);assert r(GO)['sha256']=='9f417542ab5517e10d27394cd85731b9ac115b67d2515e735349dc82b6272c92';sp=load(S/'source-pins.json');pr=load(S/'preregistration.json');ip=load(S/'input-pins.json');assert r(S/'source-pins.json')['sha256']==g['sourcePinsSHA256']and r(S/'input-pins.json')['sha256']==g['inputPinsSHA256'];assert len(ip)<=2048 and sum(z['bytes']for z in ip.values())<=402653184
for p,v in ip.items():assert r(p)==v
for n,v in sp.items():assert r(S/n)==v
for z in g['sourceReviews']:
 assert r(z['path'])=={k:z[k]for k in ['bytes','sha256']};q=load(z['path']);assert q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==g['sourcePinsSHA256']
rows=load(O/'attempts.json');term=load(O/'terminal.json');failure=load(O/'failure.json');assert len(rows)==3 and term==dict(loaderCalls=3,allChildrenClosed=True,failure=True)and failure['closedOrStartedCalls']==3 and failure['error']=='AssertionError: '
assert [z['label']for z in rows]==['observer-compile','observer-extract','positive-compile'];assert not (O/'positive-extract.stdout').exists()and not (O/'positive.bin').exists()
fields=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes'];pattern=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in fields)+'}\n').encode())
expectedArgs=[['compile',str(O/'unity-observer.kotoba'),'--target','aarch64-macos','--output',str(O/'observer.kseed')],['extract-native',str(O/'observer.kseed'),'--symbol','main','--output',str(O/'observer.bin')],['compile',str(O/'positive.kotoba'),'--target','aarch64-macos','--output',str(O/'positive.kseed')]]
for i,z in enumerate(rows):
 assert z['index']==i+1 and z['state']=='terminal'and z['spawned']and z['reaped']and z['returncode']==0 and z['error']is None and z['terminationReason']is None and z['cleanupExceptions']==[]
 producer=pr['producer']if i<2 else str(O/'observer.bin');assert z['argv']==[pr['loader'],producer,'0','0','aarch64','35,37,38,39','--',*expectedArgs[i]];e=z['effectiveEnvironment'];assert set(e)=={'PATH','HOME','TMPDIR','LANG','LC_ALL','TZ','KEXE_COMMAND','KEXE_CAP_RESOURCES_35','KEXE_STRING_POOL','KEXE_VECTORS','KEXE_PAIRS','KEXE_VECTOR_ITEMS','KEXE_CPU_SECONDS','KEXE_WALL_SECONDS','KEXE_FUEL','KEXE_ARENA_USE'}and e['KEXE_FUEL']=='off'and e['KEXE_CAP_RESOURCES_35']==str(O)and e['KEXE_ARENA_USE']=='1'
 for name in ['stdout','stderr']:assert r(O/(z['label']+'.'+name))==z[name]
 m=pattern.fullmatch((O/(z['label']+'.stderr')).read_bytes());assert m;u=dict(zip(fields,map(int,m.groups())));assert z['counterObservation']['status']=='valid'and z['counterObservation']['values']==u and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items'];assert u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
for p,v in load(O/'generated-pins.json').items():assert r(p)==v
assert (O/'positive.kotoba').read_bytes()==Path(pr['fixture']).read_bytes()and (O/'unity-observer.kotoba').read_bytes()==(S/'unity-observer.kotoba').read_bytes();container=(O/'positive.kseed').read_bytes();assert container==Path(pr['baselineContainer']).read_bytes()and len(container)==298
head,payload=container.split(b'\n\n',1);assert head==b'KSEED1 272 1\nbench 140 1'and payload==Path(pr['baselineNative']).read_bytes()and len(payload)==272
obs=(O/'observer.kseed').read_bytes();h,b=obs.split(b'\n\n',1);assert re.fullmatch(rb'KSEED1 [0-9]+ 1\nmain 0 0',h)and b==(O/'observer.bin').read_bytes()
width={'FH':7,'FSIR':6,'FF':4,'FNODE':5,'FSYM':5,'FTOK':5,'FCALL':17,'FG':4,'FOUT':7,'FCODE':2,'FLABEL':2,'FFIX':5,'FLIT':5,'FLITB':2,'FEXP':5,'FEND':2};rr={k:[]for k in width};ok=[]
for line in (O/'positive-compile.stdout').read_bytes().splitlines():
 if line.startswith(b'{:ok true,'):ok.append(line);continue
 p=line.split();tag=p[0].decode();assert tag in width and len(p)==width[tag]+1;rr[tag].append(list(map(int,p[1:])))
assert len(ok)==1 and rr['FH']==[[0,0,36,5,62,19,79],[1,0,36,5,62,19,79]]and rr['FEND']==[[1,0]]
sir={ph:{z[1]:z[2:]for z in rr['FSIR']if z[0]==ph}for ph in [0,1]};assert sir[0]==sir[1]and sorted(sir[0])==list(range(1,36));frecs={ph:{f:[next(z[3]for z in rr['FF']if z[:3]==[ph,f,k])for k in range(16)]for f in range(1,5)}for ph in [0,1]}
for f in range(1,5):assert all(frecs[0][f][k]==frecs[1][f][k]for k in range(16)if k!=13)
source=(O/'positive.kotoba').read_bytes();names={}
for f in range(1,5):
 sym=[z[4]for z in rr['FSYM']if z[:2]==[0,f]];names[f]=source[sym[0]:sym[1]].decode()
assert names=={1:'mask',2:'mix',3:'extra',4:'bench'};owner=0;owners={};ends={}
for i,z in sir[0].items():
 if z[0]==1:assert owner==0 and frecs[0][z[1]][12]==i;owner=z[1]
 assert owner>0;owners[i]=owner
 if z[0]==2:assert z[1]==owner;ends[owner]=i;owner=0
assert owner==0 and set(ends)==set(names);calls=[i for i,z in sir[0].items()if z[0]==13];assert calls==[16,23,31]and [z[0]for z in rr['FCALL']]==calls
admitted=[z for z in rr['FCALL']if z[5]>0];assert admitted==[[31,4,2,0,2,18,0,47,62,0,1,0,1,0,0,0,0]];a=admitted[0];assert owners[31]==4 and sir[0][31]==[13,2,0,2]and ends[2]==18
states={ph:[next(z[3]for z in rr['FG']if z[:3]==[31,ph,k])for k in range(16)]for ph in [0,1]};assert states[0][6]==2 and states[1][6]==1 and states[0][7]==0 and states[1][7]==1
false=dict(postAdmissionEqualsPreEnd=dict(required=[18,18],actual=[a[5],a[6]],source='df-admit requires t+n<=gn-f-h; after gn-take/gn-fin h is1, while t+n is2'),preContextAlreadyOne=dict(required=[1,1],actual=[a[11],a[12]],source='gn-ctx performs lazy context restore0→1 during df-call'),preFGContextAlreadyOne=dict(required=1,actual=states[0][7]),reservedCODEIncludedInPayload=dict(requiredBytes=69*4,actualBytes=272),FRECExportIndexAsByteOffset=dict(requiredByValidator=frecs[1][4][13]*4,actualExportOffset=140,actualCodeIndex=frecs[1][4][13],source='ly-byte-off=(index−ly-first)*4; ly-first=1'))
assert rr['FOUT']==[[69,272,5,2,1,1,2]];code=dict(rr['FCODE']);assert sorted(code)==list(range(69))and code[0]==0 and b''.join(struct.pack('<I',code[i])for i in range(1,69))==payload and rr['FEXP']==[[1,4,140,1,0]]and (frecs[1][4][13]-1)*4==140
machine=W/'vector-fuel-scalar-dag-emitted-build8-actual-review-v1-native-controls/machine-proof.json';mp=load(machine);on=next(z for z in mp['images']if z['fixture']=='positive'and z['arm']=='ON');assert on['native']==dict(path=pr['baselineNative'],**r(pr['baselineNative']))and mp['status']=='PASS_STATIC_ACTUAL_MACHINE_FUEL_ORDER_FIXED_FIXTURE_ONLY'
save(D/'failure-conjuncts.json',dict(status='SAVED_RAW_HOST_VALIDATOR_CONTRACT_MISMATCH_ONLY',admittedCall=a,preG=states[0],postG=states[1],falsePredicates=false,fullSIRBeforeAfterIdentical=True,typedOwners=names,wholeOrdinaryPositiveKSEED298Equal=True,wholeNativePayload272Equal=True,staticMachineProofWholeImageJoin=True,failureReclassifiedPASS=False))
ip.update({str(S/n):r(S/n)for n in ['source-pins.json',*sp]});ip[str(GO)]=r(GO)
for z in g['sourceReviews']:ip[z['path']]=r(z['path'])
for p in O.iterdir():assert p.is_file()and not p.is_symlink();ip[str(p)]=r(p)
ip[str(machine)]=r(machine);ip[str(D/'audit.py')]=r(D/'audit.py');ip[str(D/'failure-conjuncts.json')]=r(D/'failure-conjuncts.json');save(D/'input-pins.json',dict(sorted(ip.items())))
report=dict(status='FAIL_PRESERVED_INDEPENDENT_SAVED_RAW_FUEL_DAG_OBSERVER4_HOST_VALIDATOR_ONLY',rootGOSHA256=r(GO)['sha256'],sourcePinsSHA256=g['sourcePinsSHA256'],driverSHA256=g['driverSHA256'],inputPinsSHA256=r(D/'input-pins.json')['sha256'],counts=dict(closedCalls=3,nativeRC0=3,compile=2,extract=1,unexecutedExtract=1,inputFiles=len(ip),logicalBytes=sum(v['bytes']for v in ip.values())),originalTerminalFailure=True,originalHostFailure='AssertionError in FCALL admission conjunct',nativeCompilerFailure=False,checks=dict(allRawReceiptsExact=True,allThreeExactArgsAndCleanRegisteredEnv=True,allChildrenClosedReapedRC0=True,all17CountersSourceCapacityExact=True,wholePositive298BContainerAnd272BPayloadIdentity=True,full35SIRRowsUnchangedAndFourTypedOwnersBound=True,sourceBackedLazyCtxAndPostCallHeightFailure=True,additionalReservedCODEAndIndexOffsetValidatorMismatches=True,wholeImageStaticMachine8Join=True),candidateCorruptionObserved=False,repairOrRerunPerformed=False,participation='Authored earlier native_controls static build8 audit. Observer/source/validator authored width; root executed. This independent audit parses saved data, not the author validator.',generatedGuestExecution=False,actualCPUTrapQualified=False,completeObserver4Accepted=False,performanceQualified=False,officialScore=False,reviewerNativeCompilerSSHCalls=0)
save(D/'report.json',report);print(json.dumps(dict(report=r(D/'report.json'),inputPins=r(D/'input-pins.json'),conjuncts=r(D/'failure-conjuncts.json'))))
