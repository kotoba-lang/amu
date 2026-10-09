"""Independent offline audit. Reads saved files only; never imports campaign code."""
from pathlib import Path
import hashlib, itertools, json, math, re, sys, tarfile

D = Path('/Users/junkawasaki/github/workspaces/codex/vector-leaf-straight-read-cache-current19-timing-source-v2-bounded-pipes')
O = Path(__file__).resolve().parent
G = D.parent / 'vector-leaf-straight-read-cache-current19-timing-go-v2-root/root-go.json'
EXPECTED_GO = '863b669cf86eb14235713ca1403da57a5eb5dda30ac20b2abebc2998f742154f'
ARMS = ('baseline', 'candidate', 'C')
ROLES = {'baseline':'OFF', 'candidate':'LC', 'C':'C'}
VARIABLE = {'calls','warmupCalls','elapsedNanoseconds','maxRssBytes'}

def need(v, why):
    if not v: raise ValueError(why)
def unique(items):
    d = {}
    for k,v in items:
        need(k not in d, 'duplicate JSON key'); d[k] = v
    return d
def load(p): return json.loads(Path(p).read_bytes(), object_pairs_hook=unique)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(p, r):
    p=Path(p); need(p.is_file() and not p.is_symlink(), 'regular evidence '+str(p))
    need(p.stat().st_size==r['bytes'] and sha(p)==r['sha256'], 'whole file '+str(p))
def same(a,b,path=''):
    if isinstance(a,dict):
        need(isinstance(b,dict) and set(a)==set(b),'JSON keys '+path)
        for k in a: same(a[k],b[k],path+'/'+k)
    elif isinstance(a,list):
        need(isinstance(b,list) and len(a)==len(b),'JSON list '+path)
        for i,(x,y) in enumerate(zip(a,b)): same(x,y,path+'/'+str(i))
    elif type(a) is float:
        need(type(b) in (float,int) and math.isfinite(b) and math.isclose(a,b,rel_tol=2e-12,abs_tol=1e-12),'number '+path)
    else: need(type(a) is type(b) and a==b,'exact value '+path)
def order(n,i):
    block,slot=divmod(i,6);salt='LC-current19-balanced-order/v1|'+n+'|'+str(block)+'|'
    return sorted(itertools.permutations(ARMS),key=lambda p:hashlib.sha256((salt+','.join(p)).encode()).digest())[slot]
def nextcalls(n,t):
    if t==0:return min(100000000,n*10)
    q,r=divmod(n*300000000,t)
    if r*2>t or (r*2==t and q%2):q+=1
    return min(100000000,max(1,q))
def avg(v):return math.fsum(v)/len(v)
class RNG:
    def __init__(self,s):self.s=int.from_bytes(hashlib.sha256(s.encode()).digest()[:4],'big') or 0x6d2b79f5
    def idx(self):
        while True:
            x=self.s;x^=(x<<13)&0xffffffff;x^=x>>17;x^=(x<<5)&0xffffffff;self.s=x&0xffffffff
            y=self.s-1
            if y < 0xffffffff-0xffffffff%30:return y%30
def ci(vectors,cohort,name,num,global_=False):
    prefix='LC-current19-fixed19-gm-ci/v1' if global_ else 'LC-current19-paired-ci/v1'
    rng=RNG('|'.join((prefix,cohort,name,num+'/candidate')))
    draws=[]
    for _ in range(20000):draws.append(math.exp(avg([avg([v[rng.idx()] for _ in range(30)]) for v in vectors])))
    draws.sort()
    r=dict(geometricMeanPairedRatio=math.exp(avg([avg(v)for v in vectors])),lower95=draws[499],upper95=draws[19499],replicates=20000,percentileRule='nearest rank ceil(p*20000)-1, p=.025/.975')
    if global_:r['scope']='fixed19; independent within-workload paired triple resampling; no workload resampling'
    return r
def summaries(rows,names,cohort,changed):
    if len(rows)!=19:return dict(status='PARTIAL_ACTUAL_NO_SUBSET_GM',completedWorkloads=len(rows),fixed19PairedGM=None,full19AggregateCOrBetter=False,all19IndividualCOrBetter=False,officialScore=False,CIDEffectQualified=False,productAdopted=False)
    per={}
    for name in names:
        xs=rows[name];arms={}
        for a in ARMS:
            vs=[x[a]for x in xs];m=avg(vs);s=math.sqrt(math.fsum((v-m)**2 for v in vs)/29)
            arms[a]=dict(meanNsPerBody=m,sampleSDNsPerBody=s,relativeSD=s/m)
        stable=all(v['relativeSD']<=.1 for v in arms.values())
        intervals={num+'/candidate':ci([[math.log(x[num]/x['candidate'])for x in xs]],cohort,name,num)for num in ('baseline','C')}
        b,c,k=(arms[a]for a in ARMS)
        adoption=stable and b['meanNsPerBody']/c['meanNsPerBody']>=1.05 and b['meanNsPerBody']-c['meanNsPerBody']>b['sampleSDNsPerBody']+c['sampleSDNsPerBody'] and intervals['baseline/candidate']['lower95']>=1.05
        per[name]=dict(arms=arms,stable=stable,pairedCI95=intervals,baselineAdoptionBenefit=bool(name in changed and adoption),codeChanged=name in changed,neutralAttribution=name not in changed,COrBetter=stable and k['meanNsPerBody']>=c['meanNsPerBody'] and intervals['C/candidate']['lower95']>=1,individualConfidenceScope='marginal95 per workload; no joint95 claim')
    gm={num+'/candidate':ci([[math.log(x[num]/x['candidate'])for x in rows[n]]for n in names],cohort,'FULL19',num,True)for num in ('baseline','C')}
    agm={num+'/candidate':math.exp(avg([math.log(per[n]['arms'][num]['meanNsPerBody']/per[n]['arms']['candidate']['meanNsPerBody'])for n in names]))for num in ('baseline','C')}
    return dict(status='COMPLETE_ACTUAL_FIXED19',workloads=per,fixed19ArithmeticMeanRatioGM=agm,fixed19PairedGM=gm,full19AggregateCOrBetter=all(v['stable']for v in per.values()) and agm['C/candidate']>=1 and gm['C/candidate']['lower95']>=1,all19IndividualCOrBetter=all(v['COrBetter']for v in per.values()),officialScore=False,CIDEffectQualified=False,productAdopted=False,formulaVersion='LC-current19-statistics/xorshift32-rejection-nearest-rank/v1')

def audit(C):
    C=Path(C).resolve();s=load(D/'source-pins.json');sr=load(D/'source-report.json');schema=load(D/'go-schema.json');lg=load(G);rg=load(C/'control/root-go.json')
    need(sha(G)==EXPECTED_GO,'exact authorized V2 local GO')
    need(set(lg)==set(schema['exactLocalFields']),'local GO exact fields')
    for k,v in schema['fixedFields'].items():same(v,lg[k],k)
    for n,k in schema['hashBindings'].items():need(sha(D/n)==sr[k]==lg[k]==rg[k],'eight exact bindings '+n)
    for n,r in s.items():check(D/n,r);check(C/'source'/n,r)
    need(sha(C/'source/source-pins.json')==lg['sourcePinsSHA256'],'remote source registry')
    need(set(rg)==set(lg)|{'originalLocalGOSHA256'} and rg['originalLocalGOSHA256']==sha(G),'derived GO schema')
    for k in lg:
        if k!='sourceReviews':same(lg[k],rg[k],k)
    need(len(lg['sourceReviews'])==2 and len({r['path']for r in lg['sourceReviews']})==2 and len({r['sha256']for r in lg['sourceReviews']})==2,'two reviews')
    root=Path(rg['remoteRoot'])
    for local,remote in zip(lg['sourceReviews'],rg['sourceReviews']):
        check(local['path'],local);p=C/Path(remote['path']).relative_to(root);check(p,remote);need(sha(p)==local['sha256'],'review transported unchanged')
        q=load(p);need(q['status']==schema['sourceReviewStatus'],'SOURCE PASS')
        for k in schema['hashBindings'].values():need(q[k]==lg[k],'SOURCE review bindings')
    prior=load(C/'source/prior-v1-failure-binding.json');accepted=load(C/'source/prior-v1-failure-acceptance.json');failure=load(C/'source/prior-v1-failure-report.json')
    need(prior['status']=='PRESERVED_INDEPENDENTLY_ACCEPTED_V1_TIMING_FAILURE_NO_RETRY' and prior['allClosed']is True and prior['timingQualified']is False and prior['noRetry']is True,'prior failed campaign retained')
    need([prior[k]for k in ['launchChildren','remoteChildren','runnerChildren','loadChildren','acceptedTriples']]==[1,14,5,9,0],'exact prior census')
    need(accepted['independentReview']==prior['independentFailureReview'] and failure['status']=='PASS_SAVED_FAILURE_LC_CURRENT19_TIMING_V1_INDEPENDENT_NO_TIMING_ACCEPTANCE','independent prior acceptance')
    check(C/'source/prior-v1-failure-report.json',prior['independentFailureReview']);check(C/'source/prior-v1-failure-acceptance.json',prior['acceptance'])
    receipt=load(C/'collection-receipt.json');need(receipt['status']=='READONLY_TIMING_COLLECTION_ONLY_NOT_ACTUAL_ACCEPTANCE','collection scope')
    need(receipt['maximumMembers']==65536 and receipt['maximumExpandedBytes']==805306368 and receipt['compilerCalls']==receipt['nativeCalls']==receipt['timingCalls']==0,'read only collector contract')
    paths=[]
    for m in receipt['members']:
        n=Path(m['path']);need(not n.is_absolute() and '..'not in n.parts and str(n)==m['path'],'relative member');need(type(m['bytes'])is int and 0<=m['bytes']<=16777216,'member16MiB cap');check(C/n,m);paths.append(str(n))
    need(len(paths)==len(set(paths)) and len(paths)<65536 and sum(m['bytes']for m in receipt['members'])+ (C/'collection-receipt.json').stat().st_size<=805306368,'collection limits')
    actual={str(p.relative_to(C))for p in C.rglob('*')if p.is_file()};need(actual==set(paths)|{'collection-receipt.json'},'complete collection file set')
    need(all(not p.is_symlink()for p in C.rglob('*')),'no collection symlinks')
    need(receipt['sourcePinsSHA256']==lg['sourcePinsSHA256'],'collector source binding')
    pr=load(C/'source/preregistration.json');sem=load(C/'source/expected-semantics.json');env=load(C/'timing/effective-environment.json')['environment'];terminal=load(C/'timing/terminal.json')
    need(pr['finalSourceFreeze']is True and len(pr['entries'])==19 and len({e['workload']for e in pr['entries']})==19 and set(sem)=={e['workload']for e in pr['entries']},'all19 frozen closure')
    initial=load(C/'timing/input-seal.json');same(initial,terminal['closure'],'retained initial input seal')
    bank=load(C/'source/remote-input-pins.json');refs=[dict(r,path=p)for p,r in bank.items()]+[dict(path=str(root/'control/root-go.json'),bytes=(C/'control/root-go.json').stat().st_size,sha256=sha(C/'control/root-go.json'))]+rg['sourceReviews']+[dict(r,path=str(root/'source'/n))for n,r in s.items()]+[dict(path=str(root/'source/source-pins.json'),bytes=(C/'source/source-pins.json').stat().st_size,sha256=sha(C/'source/source-pins.json'))]
    need(initial['logicalFiles']==len(refs)<=8192 and initial['logicalBytes']==sum(r['bytes']for r in refs)<=469762048,'sealed complete bank accounting')
    need({x['reference']['path']:x['reference']for x in initial['files']}=={r['path']:r for r in refs} and initial['uniquePhysicalPaths']==len(initial['files']),'sealed reference closure')
    same(['dev','ino','size','mtime_ns','ctime_ns','mode','uid','gid','nlink'],initial['fingerprintFields'],'identity fields')
    for x in initial['files']:need(len(x['fingerprint'])==9 and all(type(v)is int for v in x['fingerprint']),'integer metadata fingerprint')
    cleanenv=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/zebulun',TMPDIR=str(root/'timing/tmp'));same(cleanenv,env,'exact clean environment');need(load(C/'timing/effective-environment.json')['allInheritedVariablesRemoved']is True,'no inherited environment')
    need(terminal['failure']is False and terminal['allClosed']is True and terminal['noRetry']is True,'campaign success closure')
    need(not(C/'timing/failure.json').exists(),'no saved campaign failure')
    need(terminal['sourcePinsSHA256']==lg['sourcePinsSHA256'] and terminal['remoteGOSHA256']==sha(C/'control/root-go.json'),'terminal binding')
    rows={};runner=[];classes={'runner':0,'load':0,'transport':0};host=load(C/'timing/host-before.json');same(host,load(C/'timing/host-after.json'),'same fresh identity');cpu=host['hw.logicalcpu']
    need(host['kern.osproductversion']==pr['acceptedHostIdentity']['OS'] and host['kern.osversion']==pr['acceptedHostIdentity']['OSBuild'],'OS identity')
    need(host['hw.optional.arm.FEAT_CRC32']==host['hw.optional.arm.FEAT_AES']==1 and type(cpu)is int and 1<=cpu<=256,'fresh topology feature eligibility')
    hs=load(C/'timing/compiler-sdk-seal.json');hi=pr['acceptedHostIdentity'];expected_host={hi['compiler']:hi['compilerSHA256'],'/usr/bin/clang':hi['usrBinClangSHA256'],**hi['SDKSettings']};need({x['reference']['path']:x['reference']['sha256']for x in hs['files']}==expected_host and hs['logicalFiles']==len(expected_host)<=4 and hs['logicalBytes']<=536870912,'explicit compiler SDKsettings seal')
    folders=sorted((C/'timing/children').iterdir());folders=[p for p in folders if p.is_dir()]
    for i,f in enumerate(folders,1):
        r=load(f/'receipt.json');need(r['index']==i and f.name=='%05d'%i,'contiguous children')
        need((f/'receipt.json').stat().st_size<=8192 and r['regularFileBytesMaximum']==16777216 and r['pipeCapture']=='nonblocking-cap-plus-one' and r['stdinBytesSent']==0,'V2 bounded pipe receipt')
        cap=16384 if r['kind']=='runner'else 1024
        need(r['rawBytesMaximumPerStream']==cap and set(r['pipeStates'])=={'stdout','stderr'},'stream cap schema')
        for stream in ('stdout','stderr'):
            ps=r['pipeStates'][stream];need(set(ps)=={'bytes','EOF','overflowByte'} and type(ps['bytes'])is int and ps['bytes']==r[stream]['bytes']<=cap and ps['EOF']is True and ps['overflowByte']is None,'both pipes complete EOF no overflow')
        need(r['state']=='terminal' and r['returncode']==0 and r['exception']is None and r['cleanupException']is None,'closed zero child')
        same(env,r['environment'],'effective env');need(r['label']not in rows,'unique labels');rows[r['label']]=r;classes[r['kind']]+=1
        for k in ('stdout','stderr'):check(C/Path(r[k]['path']).relative_to(root),r[k])
        need(r['stderr']['bytes']==0,'empty stderr')
        waited=r['waitedCPU'];need(waited['userSeconds']>=0 and waited['systemSeconds']>=0 and waited['childCpuNs']==round((waited['userSeconds']+waited['systemSeconds'])*1000000000),'waited CPU')
        if r['kind']=='load':need(r['argv']==['/usr/sbin/sysctl','-n','vm.loadavg'] and r['timeoutSeconds']==5,'load argv timeout')
        else:need(r['kind']=='runner' and r['timeoutSeconds']==30,'runner timeout');runner.append(r)
    need(classes==terminal['classes'] and terminal['children']==len(folders) and classes['runner']<=5415 and classes['load']==2*classes['runner']<=10830 and len(folders)<=16245,'finite class totals')
    same({k:terminal[k]for k in ('children','classes','allClosed','noRetry')},load(C/'timing/children/terminal.json'),'last child census')
    consumed=set();normalized={};rawcount=0;nextindex=1
    def sample(e,a,count,label):
        nonlocal rawcount,nextindex
        r=rows[label];role=ROLES[a];kind='dylib'if a=='C'else'raw';entry=e['CSymbol']if a=='C'else str(e[role]['offset'])
        need(r['index']==nextindex+1,'chronological replay');nextindex+=3
        need(r['argv']==[e['runner']['path'],kind,e[role]['path'],entry,'aarch64',str(e['n']),str(count),'1','16777216'],'exact runner argv')
        qpath=C/Path(r['stdout']['path']).relative_to(root);b=qpath.read_bytes();need(b.endswith(b'\n') and b.count(b'\n')==1,'one raw telemetry line');q=load(qpath)
        need(set(q)==set(sem[e['workload']][a])|VARIABLE,'strict14 schema')
        for k in ['calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed']:need(type(q[k])is int and 0<=q[k]<2**64,'strict uint64')
        need(q['calls']==count and q['warmupCalls']==1,'call counters');same(sem[e['workload']][a],{k:v for k,v in q.items()if k not in VARIABLE},'exact nmax semantics')
        f=qpath.parent;en=load(f/'envelope.json');same(r,en['runner'],'enclosing receipt')
        need((f/'envelope.json').stat().st_size<=32768 and en['scope']=='complete process including startup/warmup; not timed-loop CPU','bounded complete process envelope')
        loads=[]
        for side in ('before','after'):
            lr=rows[label+'-load-'+side];consumed.add(lr['label']);need(lr['index']==r['index']+(-1 if side=='before'else 1),'load encloses runner');same(lr,en[side+'LoadReceipt'],'load receipt')
            raw=(C/Path(lr['stdout']['path']).relative_to(root)).read_bytes();need(re.fullmatch(rb'\{ ([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+) \}\n',raw),'Darwin load syntax');value=float(raw.split()[1]);same(value,en['load'+side.title()],'load value');loads.append(value)
        before,after=r['CPUbefore'],r['CPUafter'];need(before['processors']==after['processors']==cpu,'CPU topology')
        for point in (before,after):need(len(point['ticks'])==4 and all(type(t)is int and 0<=t<=0xffffffff for t in point['ticks']),'CPU tick schema')
        dt=after['monotonicNs']-before['monotonicNs'];ticks=[(y-x)&0xffffffff for x,y in zip(before['ticks'],after['ticks'])];need(dt>0 and sum(ticks)>0,'CPU interval');idle=100*ticks[2]/sum(ticks);share=100*r['waitedCPU']['childCpuNs']/(dt*cpu);need(0<=share<=100,'CPU capacity');bg=min(100,idle+share)
        ac=dict(before=before,after=after,deltaTicks=ticks,idlePercent=idle,envelopeNs=dt,scope='runner invocation including process setup and warmup, enclosing timed interval',childCpuNs=r['waitedCPU']['childCpuNs'],logicalCpuCount=cpu,estimatedBackgroundIdlePercent=bg,backgroundEstimateScope='raw tick idle plus waited child user/system CPU share of enclosing host capacity');same(ac,en['activity'],'independent CPU envelope')
        quiet=q['elapsedNanoseconds']>=50000000 and max(loads)<=4 and bg>=90;consumed.add(label);rawcount+=1
        return q,quiet,sha(f/'envelope.json')
    for e in pr['entries']:
        n=e['workload'];st=load(C/'timing'/(n+'-state.json'));need(st['workload']==n,'state workload');cal=st['calibration'];pos=0;counts={}
        need((C/'timing'/(n+'-state.json')).stat().st_size<=1048576 and e['n']==e['matrixMaxN']==e['bodyCountPerCall']==(2000 if n=='depthconv'else 32),'original maxN and bounded state')
        for a in ARMS:
            count=3
            for attempt in range(5):
                need(pos<len(cal),'calibration presence');c=cal[pos];pos+=1;q,quiet,rid=sample(e,a,count,n+'-cal-'+a+'-'+str(attempt))
                same(dict(arm=a,attempt=attempt,calls=count,elapsedNs=q['elapsedNanoseconds'],quiet=quiet,rawId=rid),c,'calibration decision')
                if quiet and 225000000<=q['elapsedNanoseconds']<=450000000:counts[a]=count;break
                count=nextcalls(count,q['elapsedNanoseconds'])
            if a not in counts:break
        need(pos==len(cal),'no extra calibration');accepted=[]
        if len(counts)!=3:need(st['status']=='PARTIAL_CALIBRATION_CAP' and not st['triples'] and not st['accepted'],'partial calibration')
        else:
            need(len(st['triples'])<=90,'triple cap')
            for attempt,t in enumerate(st['triples']):
                od=order(n,attempt);need(t['attempt']==attempt and tuple(t['order'])==od,'six balanced order');vals={};events={}
                for a in od:
                    q,quiet,rid=sample(e,a,counts[a],n+'-measure-'+str(attempt)+'-'+a);vals[a]=[q['elapsedNanoseconds'],counts[a]];events[a]=dict(quiet=quiet,rawId=rid)
                ok=all(x['quiet']for x in events.values()) and all(x[0]>=50000000 for x in vals.values());same(dict(attempt=attempt,order=list(od),elapsedAndCalls=vals,events=events,accepted=ok),t,'paired triple')
                if ok:accepted.append({a:vals[a][0]/(vals[a][1]*e['bodyCountPerCall'])for a in ARMS})
                need(len(accepted)<=30 and (len(accepted)<30 or attempt==len(st['triples'])-1),'first30 stop')
            same(accepted,st['accepted'],'accepted paired rows')
            if len(accepted)==30:need(st['status']=='COMPLETE30','complete status');normalized[n]=accepted
            else:need(st['status']=='PARTIAL_QUIET_TRIPLE_CAP' and len(st['triples'])==90,'exhausted partial')
    need(consumed==set(rows) and rawcount==classes['runner'],'every saved child consumed exactly once')
    expected=summaries(normalized,[e['workload']for e in pr['entries']],lg['sourcePinsSHA256'],{e['workload']for e in pr['entries']if e['codeChanged']});same(expected,load(C/'timing/statistics.json'),'independently recomputed statistics')
    need(terminal['timingComplete']==(len(normalized)==19),'complete scope');need(terminal['officialScore']is False and terminal['CIDRuntimeEffect']is False and terminal['productAdopted']is False,'qualification limits')
    lp=D/'launch-outputs';launch=load(lp/'children/00001/receipt.json');lt=load(lp/'terminal.json');lr=load(lp/'report.json')
    need(lt==dict(children=1,classes=dict(transport=1),allClosed=True,noRetry=True,failure=False) and launch['state']=='terminal' and launch['returncode']==0 and launch['exception']is None and launch['cleanupException']is None,'one closed successful launch')
    for k in ('stdout','stderr'):check(launch[k]['path'],launch[k]);need(launch['pipeStates'][k]['EOF']is True and launch['pipeStates'][k]['overflowByte']is None and launch['pipeStates'][k]['bytes']==launch[k]['bytes'],'transport pipe EOF')
    need(Path(launch['stdout']['path']).read_bytes()==b'LC_CURRENT19_TIMING_V2_REMOTE_TERMINAL\n' and launch['stderr']['bytes']==0 and launch['regularFileBytesMaximum']==16777216 and launch['rawBytesMaximumPerStream']==8388608,'exact launch seal')
    need(lr['status']=='CLOSED_LC_CURRENT19_TIMING_V2_LAUNCH_ACTUAL_INDEPENDENT_AUDIT_PENDING' and lr['launchChildren']==1 and lr['originalLocalGOSHA256']==sha(G) and lr['remoteGOSHA256']==sha(C/'control/root-go.json') and lr['timingAccepted']is False and launch['stdinBytesSent']==lr['payloadBytes']<=8388608,'launch proof bindings')
    co=G.parent/'collection-outputs';attempt=load(co/'attempt.json');archive=co/'collection.tgz';need(attempt['state']=='terminal' and attempt['returncode']==0 and attempt['exception']is None and attempt['cleanupException']is None and attempt['maximumChildren']==1 and attempt['noRetry']is True,'one closed collector')
    need(sha(archive)==attempt['archiveSHA256'] and archive.stat().st_size==attempt['archiveBytes']<=872415232 and attempt['remoteCollectorSHA256']==sha(D/'collect_remote.py'),'exact read only archive source')
    with tarfile.open(archive,'r:gz')as tar:
        members=tar.getmembers();need(len(members)==len(paths)+1 and {m.name for m in members}==set(paths)|{'collection-receipt.json'} and all(m.isfile()for m in members),'all regular archived members')
        for m in members:need(m.size==(C/m.name).stat().st_size<=16777216 and tar.extractfile(m).read()==(C/m.name).read_bytes(),'archived whole byte identity')
    report=dict(status='PASS_ACTUAL_LC_CURRENT19_TIMING_V2_INDEPENDENT_SAVED_RAW_ONLY',independent=True,priorOperationalAuthorship=False,priorParticipation=['Second independent SOURCE review only','Offline saved-raw validator author'],**{k:lg[k]for k in schema['hashBindings'].values()},localGOSHA256=sha(G),remoteGOSHA256=sha(C/'control/root-go.json'),collectionReceiptSHA256=sha(C/'collection-receipt.json'),collectedFilesVerified=len(paths),runnerChildren=classes['runner'],loadChildren=classes['load'],allClosed=True,rawSamplesVerified=rawcount,completedWorkloads=len(normalized),timingQualified=len(normalized)==19,all19IndividualCOrBetter=expected['all19IndividualCOrBetter'],full19AggregateCOrBetter=expected['full19AggregateCOrBetter'],independentBootstrapRecomputed=True,bootstrapReplicates=20000,marginalIndividual95NotJoint=True,officialScore=False,CIDRuntimeEffect=False,productAdopted=False,SDKWholeTreeHashQualified=False,compilerCalls=0,nativeCalls=0,SSHCalls=0,CPUAPICalls=0,operationalDriverExecutions=0,limitations=['Saved evidence only; no independent live execution or CPU API calls.','Complete process quiet envelope includes startup and warmup; no timed-loop CPU claim.','Source input seals rely on ordinary trusted kernel metadata and exclude privileged forgery.'])
    report.update(priorParticipation=['V1 second independent SOURCE review','V1 independent saved-failure audit','V2 second independent SOURCE review','Offline saved-raw validator author'],closedPipeEOFAndNoOverflowVerified=True,regularFileLimitBytes=16777216,launchChildren=1,launchAllClosed=True,launchSealExact=True,collectionChildren=1,collectionAllClosed=True,collectionArchiveSHA256=sha(archive),archivedWholeMembersVerified=len(paths)+1,priorRunnerChildren=5,priorLoadChildren=9,priorTimingChildren=14,cumulativeRunnerChildren=classes['runner']+5,cumulativeLoadChildren=classes['load']+9,cumulativeTimingChildren=len(folders)+14,cumulativeLaunchChildren=2,priorFailureUnqualifiedPreserved=True,initialSealLogicalFiles=initial['logicalFiles'],initialSealLogicalBytes=initial['logicalBytes'],fullLiveInputBankRehashByReviewer=False)
    if len(normalized)!=19:report['status']='PASS_SAVED_PARTIAL_LC_CURRENT19_TIMING_V2_NO_FIXED19_TIMING_ACCEPTANCE'
    (O/'recomputed-statistics.json').write_text(json.dumps(expected,indent=2)+'\n');(O/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    need(len(sys.argv)==2,'provide root collected directory; no execution default')
    try: print(json.dumps(audit(sys.argv[1]),indent=2))
    except BaseException as ex:
        (O/'audit-failure.json').write_text(json.dumps(dict(status='HOLD_SAVED_RAW_AUDIT_FAILED_NO_ACTUAL_PASS',exception=repr(ex),operationalCalls=0),indent=2)+'\n');raise
