"""Independent reader of closed saved evidence only; never loads author parsers."""
from pathlib import Path
import json, hashlib, stat, re

W=Path('/Users/junkawasaki/github/workspaces/codex')
D=W/'vector-fuel-scalar-dag-original19-functional285-plan-v2-launcher-controls'
O=D/'run-outputs'
G=W/'vector-fuel-scalar-dag-original19-functional285-go-v2-root/root-go.json'
Q=Path(__file__).resolve().parent
def need(x,m):
    if not x: raise AssertionError(m)
def raw(p,cap=469762048):
    p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size<=cap,'bounded regular '+str(p));b=p.read_bytes();t=p.lstat();need((s.st_ino,s.st_size,s.st_mtime_ns)==(t.st_ino,t.st_size,t.st_mtime_ns),'stable read');return b
def rec(p):
    b=raw(p);return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def unique(items):
    d={}
    for k,v in items:
        need(k not in d,'duplicate key');d[k]=v
    return d
def load(p):return json.loads(raw(p),object_pairs_hook=unique)
def pin(p,z):need(rec(p)=={k:z[k] for k in ('bytes','sha256')},'exact pin '+str(p))
def save(n,v):(Q/n).write_text(json.dumps(v,indent=2)+'\n')

def native(b,n):
    # Independent full-byte grammar, success-only. No budget-boundary trap inference.
    number=rb'([0-9]{1,20})'
    pattern=rb'\{:status :ok :result '+number+rb' :fuel \{:initial '+number+rb' :remaining '+number+rb'\}'
    for key in (b'heap',b'string-pool',b'vectors',b'vector-items'):
        pattern+=rb' :'+key+rb' \{:capacity '+number+rb' :used '+number+rb'\}'
    m=re.fullmatch(pattern+rb'\}\n',b);need(m is not None,'exact whole native success grammar')
    v=list(map(int,m.groups()));need(all(0<=x<2**64 for x in v),'native u64')
    need(v[0]==int(n!=0) and v[1]==16777216 and 0<v[2]<=v[1],'native boolean/fuel')
    a={}
    for i,(key,cap)in enumerate(zip(('heap','string-pool','vectors','vector-items'),(2097152,65536,4096,65536))):
        capacity,used=v[3+2*i:5+2*i];need(capacity==cap and 0<=used<=cap,'terminal arena bound');a[key]=dict(capacity=capacity,used=used)
    return dict(status='ok',result=v[0],fuel=dict(initial=v[1],remaining=v[2]),terminalArenas=a,trap=None,resumed=False)

def cparse(b,n):
    need(b.endswith(b'\n') and b.count(b'\n')==1,'single C JSON line')
    c=json.loads(b,object_pairs_hook=unique)
    numeric=('calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed')
    other={'format','nativeArtifactAbi','artifactKind','nativeArenaStatus','nativeArenas'}
    need(set(c)==set(numeric)|other,'exact C schema')
    need(all(type(c[k])is int and 0<=c[k]<2**64 for k in numeric),'C u64')
    need(c['format']=='kotoba.runtime-sample/v1' and c['calls']==1 and c['warmupCalls']==0 and c['result']==int(n!=0),'C source boolean')
    need(c['fuelPerCall']==c['contextFuelBefore']==c['contextFuelAfter']==16777216 and c['contextFuelConsumed']==0,'C fuel metadata')
    need(c['nativeArtifactAbi']=='kotoba.native-artifact-i64x8-to-i64-indirect/v1' and c['artifactKind']=='dylib' and c['nativeArenaStatus']=='unavailable-C' and c['nativeArenas']is None,'C ABI/arena unavailable')
    return {k:v for k,v in c.items()if k not in ('elapsedNanoseconds','maxRssBytes')}

def container(p):
    b=raw(p,4194560);head,payload=b.split(b'\n\n',1);lines=head.split(b'\n')
    need(lines[0]==('KSEED1 '+str(len(payload))+' '+str(len(lines)-1)).encode() and 0<len(payload)<=4194304,'whole KSEED declaration')
    ex=[]
    for line in lines[1:]:
        m=re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)',line);need(m is not None,'export grammar');name,offset,arity=m.groups();offset=int(offset);arity=int(arity);need(offset%4==0 and offset+4<=len(payload),'export offset');ex.append(dict(name=name.decode(),offset=offset,arity=arity))
    need(len({v['name']for v in ex})==len(ex),'all export uniqueness');return ex,payload

def audit():
    go,pr=load(G),load(D/'preregistration.json')
    need(rec(G)['sha256']=='ab868dcabb59ccd5ab26996fa2082b0f334158b51ba9aafa799bc7b988f932d1','exact V2 GO')
    expected=dict(sourcePinsSHA256='73b30414f646737149f5a3775a90914e63a20e0cc0e37faa2750152b705db98f',driverSHA256='cb5caf46fa33579e9bcafcef7e3d19727e9bfe77271f75147fbb9699fec5271a',preregistrationSHA256='15312d9437f1f194b89a134a12b34f6fc24c97d5b3cbb00b91d149e16f25b5fd',inputClosureSHA256='900ff6c36aca23cb74ff7f07967856e076ee262eb25056de0d8ee9b5cf660bf7')
    for file,key in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('preregistration.json','preregistrationSHA256'),('input-closure.json','inputClosureSHA256')]:need(rec(D/file)['sha256']==go[key]==expected[key],'frozen SOURCE')
    need(go['status']==pr['rootGOStatus'] and go['outputRoot']==str(O) and go['maximumChildCalls']==285 and go['functionalAuthorized']is True and go['timingAuthorized']is False and go['compilerSSHAuthorized']is False and go['noRetry']is True,'exact GO scope')
    need(go['launcherTool']=='functions.exec_command' and go['launcherSandboxPermissions']=='require_escalated' and go['nativeLauncherAuthorized']is True and go['priorFailedAttempts']==1 and go['maximumCumulativeAttempts']==286,'outer launcher attestation')
    need(len(go['sourceReviews'])==2 and len({x['path']for x in go['sourceReviews']})==2,'two reviews')
    for v in go['sourceReviews']:
        pin(v['path'],v);r=load(v['path']);need(r['status']==pr['sourceReviewStatus'] and r['independent']is True and r['priorAuthorship']is False and all(r[k]==z for k,z in expected.items()),'specific independent SOURCE receipts')
    need(go['scalar44RootAcceptance']==pr['scalar44RootAcceptance'],'exact44 prerequisite');pin(go['scalar44RootAcceptance']['path'],go['scalar44RootAcceptance'])
    cl=load(D/'input-closure.json');need(len(cl)==3323 and sum(v['bytes']for v in cl.values())==446076749,'full inherited closure census')
    for p,v in cl.items():pin(p,v)
    for n,v in load(D/'source-pins.json').items():pin(D/n,v)
    prior=pr['priorFailedNamespace'];fr=load(prior['independentReview']['path']);need(fr['status']=='CLOSED_FAIL1_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_SANDBOX_INIT_ONLY' and fr['calls']==1 and fr['bodyResultEvidence']is False and fr['candidateONCalls']==fr['CCalls']==fr['completedTriples']==0,'retained failed1 never parity evidence')
    need(load(prior['terminal']['path'])==dict(calls=1,allCallsClosed=True,failure=True,noRetry=True),'prior closed failure retained')
    terminal=load(O/'terminal.json');report=load(O/'report.json');rows=load(O/'attempts.json');comparisons=load(O/'comparisons.json')
    need(terminal==dict(calls=285,allCallsClosed=True,failure=False,noRetry=True),'exact CLOSED285')
    need(report['status']=='PASS_FINITE_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_V2_ONLY' and report['calls']==report['freshOriginal19Calls']==report['joinedOriginal19Calls']==285 and report['completedTriples']==95 and report['retainedAcceptedCalls']==0 and report['priorFailedAttempts']==1 and report['cumulativeAttempts']==report['maximumCumulativeAttempts']==286,'actual report finite scope')
    need(report['comparisons']==comparisons and len(comparisons)==95 and len(rows)==285 and not(O/'failure.json').exists(),'whole report/comparisons/no failure')
    need(report['timingQualified']is False and report['officialScore']is False and report['registerCanaryQualified']is False,'no overclaim')
    base=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/junkawasaki',TMPDIR=str(O/'tmp'),LANG='C',LC_ALL='C',TZ='UTC')
    env={**base,'KEXE_ARG_TYPES':'i64','KEXE_RESULT_TYPE':'i64','KEXE_STRUCTURED_REPORT':'1','KEXE_FUEL':'16777216','KEXE_PAIRS':'2097152','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_VECTOR_ITEMS':'65536','KEXE_CPU_SECONDS':'30','KEXE_WALL_SECONDS':'30'}
    need(load(O/'effective-environment.json')==dict(native=env,C=base,allInheritedRemoved=True),'exact effective environment')
    matrix=load(pr['canonicalMatrix']['path']);ci=load(pr['proofs']['CConsumer19']['report']['path']);need(len(pr['cases'])==len(matrix['entries'])==19,'whole19')
    rebuilt=[];index=0
    for case,m in zip(pr['cases'],matrix['entries']):
        name=case['workload'];need(name==m['workload'] and case['symbol']==m['symbol'] and case['iterations']==m['iterations'] and case['source']['sha256']==m['expectedSourceSha256'],'canonical whole source/symbol/profile');pin(case['source']['path'],case['source'])
        for arm in ('OFF','ON'):
            pin(case[arm]['path'],case[arm]);pin(case[arm+'Container']['path'],case[arm+'Container']);exports,payload=container(case[arm+'Container']['path']);need(exports==case[arm+'Exports'] and payload==raw(case[arm]['path']) and dict(name=case['symbol'],offset=case[arm+'Offset'],arity=1)in exports,'whole artifact/all exports/payload/selected offset')
        need([(v['name'],v['arity'])for v in case['OFFExports']]==[(v['name'],v['arity'])for v in case['ONExports']],'whole exported ABI parity')
        pin(case['C']['path'],case['C']);pin(case['CRunner']['path'],case['CRunner']);z=next(v for v in ci['images']if v['workload']==name);cb,rb=raw(case['C']['path']),raw(case['CRunner']['path']);need(rb.count(cb)==1 and rb.find(cb)==z['immutableImageByteAnchors']['C'],'whole C consumer anchor')
        for n in case['iterations']:
            arms={}
            for arm in ('OFF','ON','C'):
                row=rows[index];index+=1;label=name+'-'+arm+'-n'+str(n)
                argv=[case['CRunner']['path'],'dylib',case['C']['path'],case['CSymbol'],'aarch64',str(n),'1','0','16777216']if arm=='C'else[pr['loader']['path'],case[arm]['path'],str(case[arm+'Offset']),'1','aarch64','-',str(n)]
                need(row['index']==index and row['label']==label and row['argv']==argv and row['environment']==(base if arm=='C'else env) and row['timeoutSeconds']==40,'exact285 argv/env/order')
                need(row['state']=='terminal' and row['returncode']==0 and row['failure']is None and row['cleanupException']is None,'closed0 no exceptions')
                stdout,stderr=O/(label+'.stdout'),O/(label+'.stderr');b,e=raw(stdout,1048576),raw(stderr,1048576);need(hashlib.sha256(b).hexdigest()==row['stdoutSHA256'] and hashlib.sha256(e).hexdigest()==row['stderrSHA256'] and e==b'','raw SHA and empty stderr')
                arms[arm]=cparse(b,n)if arm=='C'else native(b,n)
            need(arms['OFF']==arms['ON'] and arms['OFF']['result']==arms['C']['result'],'OFF/ON exact status/result/fuel/four arenas and C boolean')
            rebuilt.append(dict(workload=name,n=n,arms=arms))
    need(index==285 and rebuilt==comparisons,'all95 whole saved comparisons independently rebuilt')
    need(report['nativePairTerminalArenaFuelExact']is True and report['nativeNonresumingTrapStatusExact']is True and report['noGuestTrapOrResumeAccepted']is True,'author successful-only fields consistent')
    # Full inherited plus registered SOURCE/GO/reviews/all closed actual raw retained.
    pins=dict(cl)
    for p in D.iterdir():
        if p.is_file():pins[str(p)]=rec(p)
    for p in O.iterdir():
        if p.is_file():pins[str(p)]=rec(p)
    pins[str(G)]=rec(G)
    for v in go['sourceReviews']:pins[v['path']]={k:v[k]for k in ('bytes','sha256')}
    save('input-pins.json',dict(sorted(pins.items())));save('comparisons.json',rebuilt)
    return dict(status='PASS_INDEPENDENT_SAVED_RAW_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_V2_ONLY',independent=True,priorAuthorship=False,authorshipDisclosure='No functional SOURCE/driver authorship; prior independent V1/V2 SOURCE, scalar44 actual and FAIL1 reviews participated in by this reviewer.',**expected,rootGO=dict(path=str(G),**rec(G)),auditInputPinsSHA256=rec(Q/'input-pins.json')['sha256'],inputPinsSHA256=rec(Q/'input-pins.json')['sha256'],auditExactInputFiles=len(pins),auditExactInputLogicalBytes=sum(v['bytes']for v in pins.values()),closedFunctionalCalls=285,calls=285,allCallsClosed=True,failure=False,workloads=19,comparisons=95,nativeCalls=190,CCalls=95,retainedAcceptedCalls=0,priorFailedAttempts=1,cumulativeAttempts=286,maximumCumulativeAttempts=286,exact285ArgvEnvRawSHAReturn0Closed=True,wholeOriginal19BodiesSymbolsProfilesExportsPayloadOffsets=True,wholeCConsumerAnchors=True,nativeFuelAndFourTerminalArenaPairExact=True,CBooleanSourceParity=True,CNativeArenas='unavailable-C/null',successfulOnly=True,newTrapBoundaryQualified=False,guest10EvidenceScope='Separate finite Guest10 prerequisite; this285 successful-only run introduces no budget-boundary trap test.',terminalUsedIsNotPeak=True,timingQualified=False,C2Enabled=False,officialScore=False,registerCanaryQualified=False,fullSelfhostGoalAchieved=False,operationalCompilerNativeGuestSSHRerunCalls=0,findings=[])

if __name__=='__main__':
    need(not(Q/'report.json').exists(),'fresh audit report')
    try: result=audit()
    except Exception as e: result=dict(status='HOLD_INDEPENDENT_SAVED_RAW_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_V2',failure=str(e),operationalCompilerNativeGuestSSHRerunCalls=0)
    save('report.json',result)
    print(json.dumps(dict(path=str(Q/'report.json'),**rec(Q/'report.json'),status=result['status'])))
