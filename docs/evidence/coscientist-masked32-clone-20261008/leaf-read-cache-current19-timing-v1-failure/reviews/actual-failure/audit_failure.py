"""Finite independent saved-failure audit, separate from complete timing validator."""
from validate_saved import *
import tarfile

def main():
    C=G.parent/'collected';R=load(C/'collection-receipt.json');lg=load(G);rg=load(C/'control/root-go.json');schema=load(D/'go-schema.json');sp=load(D/'source-pins.json');root=Path(rg['remoteRoot'])
    need(set(lg)==set(schema['exactLocalFields']),'exact local GO')
    for k,v in schema['fixedFields'].items():same(v,lg[k],k)
    for n,k in schema['hashBindings'].items():need(sha(D/n)==lg[k]==rg[k],'eight source bindings')
    for n,r in sp.items():check(D/n,r);check(C/'source'/n,r)
    need(sha(C/'source/source-pins.json')==lg['sourcePinsSHA256'],'source registry')
    need(set(rg)==set(lg)|{'originalLocalGOSHA256'} and rg['originalLocalGOSHA256']==sha(G),'remote GO')
    for k in lg:
        if k!='sourceReviews':same(lg[k],rg[k],k)
    need(len(lg['sourceReviews'])==2 and len({r['sha256']for r in lg['sourceReviews']})==2,'two exact independent reviews')
    for l,r in zip(lg['sourceReviews'],rg['sourceReviews']):
        check(l['path'],l);p=C/Path(r['path']).relative_to(root);check(p,r);need(sha(p)==l['sha256'],'transported review')
        q=load(p);need(q['status']==schema['sourceReviewStatus'],'SOURCE PASS')
        for k in schema['hashBindings'].values():need(q[k]==lg[k],'review binding')
    need(R['status']=='READONLY_TIMING_COLLECTION_ONLY_NOT_ACTUAL_ACCEPTANCE' and R['sourcePinsSHA256']==lg['sourcePinsSHA256'],'collector binding')
    for m in R['members']:check(C/m['path'],m)
    paths={m['path']for m in R['members']};need(len(paths)==len(R['members'])==87,'complete87plusreceipt members');need({str(p.relative_to(C))for p in C.rglob('*')if p.is_file()}==paths|{'collection-receipt.json'},'no dropped or unexpected collection')
    need(sum(m['bytes']for m in R['members'])<=805306368,'collection budget')
    term=load(C/'timing/terminal.json');need(term['children']==14 and term['classes']==dict(runner=5,load=9,transport=0) and term['allClosed']is True and term['failure']is True and term['noRetry']is True and term['timingComplete']is False,'failed complete closure census')
    need(term['sourcePinsSHA256']==lg['sourcePinsSHA256'] and term['remoteGOSHA256']==sha(C/'control/root-go.json'),'terminal exact binding')
    initial=load(C/'timing/input-seal.json');same(initial,term['closure'],'initial closure terminal retained')
    bank=load(C/'source/remote-input-pins.json');refs=[dict(r,path=p)for p,r in bank.items()]+[dict(path=str(root/'control/root-go.json'),bytes=(C/'control/root-go.json').stat().st_size,sha256=sha(C/'control/root-go.json'))]+rg['sourceReviews']+[dict(r,path=str(root/'source'/n))for n,r in sp.items()]+[dict(path=str(root/'source/source-pins.json'),bytes=(C/'source/source-pins.json').stat().st_size,sha256=sha(C/'source/source-pins.json'))]
    need(initial['logicalFiles']==len(refs)==4420 and initial['logicalBytes']==sum(r['bytes']for r in refs)==433038822,'complete initial seal accounting')
    need({x['reference']['path']:x['reference']for x in initial['files']}=={r['path']:r for r in refs},'complete seal reference bank');need(initial['uniquePhysicalPaths']==len(initial['files'])==4418,'seal unique physical count')
    env=load(C/'timing/effective-environment.json');need(env['allInheritedVariablesRemoved']is True,'clean env');expected_env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/zebulun',TMPDIR=str(root/'timing/tmp'));same(expected_env,env['environment'],'env')
    pr=load(C/'source/preregistration.json');e=pr['entries'][0];sem=load(C/'source/expected-semantics.json')[e['workload']];need(e['workload']=='aha-mont64','first original workload')
    rows=[]
    for i in range(1,15):
        r=load(C/'timing/children'/('%05d'%i)/'receipt.json');need(r['index']==i and r['state']=='terminal' and r['exception']is None and r['cleanupException']is None,'reaped child row');same(expected_env,r['environment'],'child env')
        for k in ('stdout','stderr'):check(C/Path(r[k]['path']).relative_to(root),r[k])
        need(r['stderr']['bytes']==0,'empty child stderr');need(r['returncode']==(-25 if i==14 else 0),'expected terminal exit')
        need(r['waitedCPU']['childCpuNs']==round((r['waitedCPU']['userSeconds']+r['waitedCPU']['systemSeconds'])*1000000000),'actual wait4 CPU')
        if r['kind']=='load':need(r['argv']==['/usr/sbin/sysctl','-n','vm.loadavg'] and r['timeoutSeconds']==5,'load fixed argv');need(re.fullmatch(rb'\{ ([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+) \}\n',(C/Path(r['stdout']['path']).relative_to(root)).read_bytes()),'load raw format')
        else:need(r['kind']=='runner' and r['timeoutSeconds']==30,'runner row')
        rows.append(r)
    need(load(C/'timing/children/terminal.json')=={k:term[k]for k in ('children','classes','allClosed','noRetry')},'last child terminal')
    state=load(C/'timing/aha-mont64-state.json');need(not state['triples'] and not state['accepted'] and len(state['calibration'])==4,'no paired timing samples')
    counts={'baseline':3,'candidate':3};successful=[]
    for c,i in zip(state['calibration'],(2,5,8,11)):
        r=rows[i-1];a=c['arm'];role=ROLES[a];count=counts[a];need(c['calls']==count,'calibration exact rational calls');need(r['argv']==[e['runner']['path'],'raw',e[role]['path'],str(e[role]['offset']),'aarch64','32',str(count),'1','16777216'],'exact calibration runner argv')
        p=C/Path(r['stdout']['path']).relative_to(root);raw=p.read_bytes();q=load(p);need(raw.endswith(b'\n') and raw.count(b'\n')==1,'one telemetry line');same(sem[a],{k:v for k,v in q.items()if k not in VARIABLE},'accepted exact nmax semantics');need(q['calls']==count and q['warmupCalls']==1,'counters')
        for k in ['calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed']:need(type(q[k])is int and 0<=q[k]<2**64,'strict uint64')
        en=load(p.parent/'envelope.json');same(r,en['runner'],'runner envelope');need(c['rawId']==sha(p.parent/'envelope.json'),'raw envelope id')
        before,after=r['CPUbefore'],r['CPUafter'];dt=after['monotonicNs']-before['monotonicNs'];ticks=[(b-a)&0xffffffff for a,b in zip(before['ticks'],after['ticks'])];need(dt>0 and sum(ticks)>0,'CPU envelope');idle=100*ticks[2]/sum(ticks);cpu=before['processors'];need(cpu==after['processors']==10,'CPU topology');bg=min(100,idle+100*r['waitedCPU']['childCpuNs']/(dt*cpu));same(bg,en['activity']['estimatedBackgroundIdlePercent'],'independent background estimate');same(ticks,en['activity']['deltaTicks'],'tick deltas');same(idle,en['activity']['idlePercent'],'idle');same(dt,en['activity']['envelopeNs'],'elapsed CPU envelope')
        loads=[]
        for side,j in [('before',i-2),('after',i)]:
            lr=rows[j];same(lr,en[side+'LoadReceipt'],'load receipt');v=float((C/Path(lr['stdout']['path']).relative_to(root)).read_bytes().split()[1]);same(v,en['load'+side.title()],'load value');loads.append(v)
        quiet=q['elapsedNanoseconds']>=50000000 and max(loads)<=4 and bg>=90;need(c['elapsedNs']==q['elapsedNanoseconds'] and c['quiet']is quiet,'calibration quiet decision');counts[a]=nextcalls(count,q['elapsedNanoseconds']);successful.append(dict(index=i,arm=a,calls=count,elapsedNs=q['elapsedNanoseconds'],quiet=quiet))
    last=rows[-1];need(last['label']=='aha-mont64-cal-C-0' and last['argv']==[e['runner']['path'],'dylib',e['C']['path'],'bench','aarch64','32','3','1','16777216'],'failed fifth runner exact argv');need(last['stdout']['bytes']==last['stderr']['bytes']==0,'failed raw empty');need(not(C/'timing/children/00014/envelope.json').exists(),'failed child no admission envelope')
    need(not any('-measure-'in r['label']for r in rows) and not(C/'timing/statistics.json').exists() and not(C/'timing/host-after.json').exists(),'no paired timing stats or completed host exit')
    fail=load(C/'timing/failure.json');need(fail['noRetry']is True and fail['firstFailureStop']is True and 'aha-mont64-cal-C-0'in fail['exception'] and "'returncode': -25"in fail['exception'],'first failure durable')
    lp=D/'launch-outputs';launch=load(lp/'children/00001/receipt.json');lt=load(lp/'terminal.json');need(launch['state']=='terminal' and launch['returncode']==0 and launch['exception']is None and launch['cleanupException']is None and lt==dict(children=1,classes=dict(transport=1),allClosed=True,noRetry=True,failure=True),'closed launch but failed seal')
    for k in ('stdout','stderr'):check(launch[k]['path'],launch[k])
    need(launch['stdout']['bytes']==0 and 'aha-mont64-cal-C-0'in Path(launch['stderr']['path']).read_text() and not(lp/'report.json').exists(),'no launch success seal')
    archive=G.parent/'collection-outputs/collection.tgz'
    archive_ref=None
    if archive.exists():
        archive_ref=dict(path=str(archive),bytes=archive.stat().st_size,sha256=sha(archive))
        attempt=load(G.parent/'collection-outputs/attempt.json');need(attempt['state']=='terminal' and attempt['returncode']==0 and attempt['exception']is None and attempt['cleanupException']is None and attempt['maximumChildren']==1 and attempt['noRetry']is True,'one closed read-only collection')
        need(archive_ref['sha256']==attempt['archiveSHA256']=='c300a00dd97a45fdff0aa9dc39810fde1820303cc68d983a42eba35351ed35fc','exact archive')
        with tarfile.open(archive,'r:gz')as tar:
            members=tar.getmembers();need(len(members)==88 and {m.name for m in members}==paths|{'collection-receipt.json'} and all(m.isfile()for m in members),'archive complete regular88')
            for m in members:need(tar.extractfile(m).read()==(C/m.name).read_bytes(),'archive collected whole bytes')
    report=dict(status='PASS_SAVED_FAILURE_LC_CURRENT19_TIMING_V1_INDEPENDENT_NO_TIMING_ACCEPTANCE',independent=True,priorOperationalAuthorship=False,priorParticipation=['Second independent SOURCE review only','Offline saved-raw validator preparation; not operational source author'],**{k:lg[k]for k in schema['hashBindings'].values()},localGOSHA256=sha(G),remoteGOSHA256=sha(C/'control/root-go.json'),collectionReceiptSHA256=sha(C/'collection-receipt.json'),collectedMembersVerified=88,collectedMemberBytes=sum(m['bytes']for m in R['members']),archive=archive_ref,launchChildren=1,launchAllClosed=True,launchTransportReturncode=0,launchSuccessSeal=False,remoteChildren=14,runnerChildren=5,loadChildren=9,allRemoteChildrenClosed=True,successfulNativeCalibrationRunners=4,failedCResourcesRunnerIndex=14,failedRunnerReturncode=-25,failedRunnerSignal='SIGXFSZ on Darwin (25)',failedRunnerStdoutBytes=0,failedRunnerStderrBytes=0,calibrations=successful,measuredPairedTriples=0,acceptedPairedTriples=0,statisticsPresent=False,timingComplete=False,timingQualified=False,quietCampaignQualified=False,all19IndividualCOrBetter=False,officialScore=False,CIDRuntimeEffect=False,productAdopted=False,initialSealLogicalFiles=4420,initialSealLogicalBytes=433038822,noRetry=True,firstFailureStop=True,compilerCalls=0,nativeCalls=0,SSHCalls=0,CPUAPICalls=0,operationalDriverExecutions=0,limits=['Failure evidence accepted only; campaign timing failed and calibration intervals are not qualified paired timing.','Returncode -25 is observed; exact underlying SIGXFSZ cause is not proven by saved empty raw streams.','Initial seal retained and binding verified, but failure prevented workload/end full revalidation.','No remote bank rehash or live host interrogation by reviewer.'])
    report['collectionRegularMembersIncludingReceipt']=88;report['collectionLogicalBytesIncludingReceipt']=sum(m['bytes']for m in R['members'])+(C/'collection-receipt.json').stat().st_size;report['readOnlyCollectionChildren']=1;report['collectionAllClosed']=True;report['archiveWholeMembersCompared']=88
    p=O/'failure-report.json'
    if p.exists():p.chmod(0o644)
    p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o444);print(json.dumps(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),status=report['status'])))
if __name__=='__main__':main()
