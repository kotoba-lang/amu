"""Saved first preexec failure only. No operational imports or invocations."""
from pathlib import Path
import hashlib,json,stat
O=Path(__file__).resolve().parent;D=O.parent/'crc-table-decision-collapse-native-component-v2-20261008';G=O.parent/'crc-table-decision-collapse-current-bind8-go-v2-root-20261008/root-go.json'
def load(p):return json.loads(Path(p).read_bytes())
def need(v,m):
    if not v:raise ValueError(m)
def ref(p):
    p=Path(p);need(stat.S_ISREG(p.lstat().st_mode)and not p.is_symlink(),'regular evidence');return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def check(p,r):need({k:ref(p)[k]for k in ['bytes','sha256']}=={k:r[k]for k in ['bytes','sha256']},'exact saved pin')
def main():
    need(ref(G)['sha256']=='359c176f61730ec84e5be6e5be576429d34556036386f576e354a834b43215d4','exact root GO')
    g=load(G);sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');pr=load(D/'preregistration.json');out=D/'run-outputs'
    need(ref(D/'source-pins.json')['sha256']=='0e2159885a5bc78cbca2ded8da02d8ae736d4cb3cad3bdc4bb3f6a6d5cd333d0','exact frozen V2')
    for n,r in sp.items():check(D/n,r)
    for p,r in ip.items():check(p,r)
    need(set(g)=={'status','maximumLoaderCalls','outputRoot','outerExecution','noRetry','TCEmitterExecutionAuthorized','generatedWorkloadExecutionAuthorized','timingAuthorized','sha256','sourceReviews'},'exact GO fields')
    need(g['status']=='ROOT_GO_READONLY_TC_CURRENT_BIND8_ONLY'and g['maximumLoaderCalls']==8 and g['outputRoot']==str(out)and g['outerExecution']=='require_escalated'and g['noRetry']is True and g['TCEmitterExecutionAuthorized']is False and g['generatedWorkloadExecutionAuthorized']is False and g['timingAuthorized']is False,'narrow GO')
    need(set(g['sha256'])=={'run.py','preregistration.json','source-pins.json','input-pins.json'},'four gate hashes')
    for n,h in g['sha256'].items():need(ref(D/n)['sha256']==h,'gate hash')
    need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two exact SOURCE reviews')
    for r in g['sourceReviews']:
        check(r['path'],r);q=load(r['path']);need(q['status']=='PASS_SOURCE_ONLY_READONLY_TC_CURRENT_BIND8'and q['sourcePinsSHA256']==g['sha256']['source-pins.json']and q['driverSHA256']==g['sha256']['run.py'],'specific SOURCE PASS')
    rows=load(out/'attempts.json');need(len(rows)==1,'one first attempt only');r=rows[0]
    need(r['index']==1 and r['label']=='current-baseline-compile'and r['argv']==pr['orderedChildren'][0]['argv'],'exact attempted first argv')
    env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/junkawasaki',TMPDIR=str(out),LANG='C',LC_ALL='C',TZ='UTC',KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(out),KEXE_STRING_POOL='268435456',KEXE_VECTORS='4194304',KEXE_PAIRS='16777216',KEXE_VECTOR_ITEMS='134217728',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',KEXE_FUEL='off',KEXE_ARENA_USE='1')
    need(r['environment']==env==load(out/'effective-environment.json'),'exact sanitized env')
    need(r['state']=='terminal'and r['spawned']is False and r['reaped']is False and r['returncode']is None and r['reason']=='exception'and r['exception']=="SubprocessError('Exception occurred in preexec_fn.')"and not r['cleanup']and 'pid'not in r,'preexec Popen constructor failure')
    for k in ['stdout','stderr']:
        p=out/(r['label']+'.'+k);check(p,r[k]);need(p.stat().st_size==0,'empty bounded raw')
    need(r['counterObservation']==dict(status='unavailable-or-invalid',values=None,entireStderrIsCounterLine=False),'no native counter evidence')
    need(load(out/'failure.json')==dict(status='FAIL_FIRST_FAILURE_NO_RETRY',exception="AssertionError('first failure stop closed')",attemptedCalls=1),'first failure saved')
    need(load(out/'terminal.json')==dict(attemptedCalls=1,allChildrenClosed=True,failure=True,noRetry=True),'saved ledger closure only')
    pins=load(out/'generated-pins.json');need(set(pins)=={str(out/n)for n in ['unity-baseline.kotoba','unity-observer.kotoba','original-input.kotoba']},'only three source copies before failure')
    for n in ['unity-baseline.kotoba','unity-observer.kotoba','original-input.kotoba']:
        p=out/n;check(p,pins[str(p)]);need(p.read_bytes()==(D/n).read_bytes()and stat.S_IMODE(p.stat().st_mode)==0o444,'immutable whole source copy')
    names={p.name for p in out.iterdir()};need(names=={'attempts.json','effective-environment.json','generated-pins.json','failure.json','terminal.json','unity-baseline.kotoba','unity-observer.kotoba','original-input.kotoba','current-baseline-compile.stdout','current-baseline-compile.stderr'},'no compile artifacts/other calls/completion')
    report=dict(status='PASS_INDEPENDENT_SAVED_NATIVE_BIND8_V2_PREEXEC_FAILURE_ONLY',independent=True,priorOperationalAuthorship=False,priorParticipation=['V1/V2 independent observer SOURCE review; no driver/observer/validator implementation authorship'],sourcePinsSHA256=ref(D/'source-pins.json')['sha256'],driverSHA256=ref(D/'run.py')['sha256'],preregistrationSHA256=ref(D/'preregistration.json')['sha256'],inputPinsSHA256=ref(D/'input-pins.json')['sha256'],rootGOSHA256=ref(G)['sha256'],sourceFilesWholeHashed=len(sp),inputFilesWholeHashed=len(ip),inputBytesWholeHashed=sum(x['bytes']for x in ip.values()),attemptedPopenCalls=1,PopenReturnedProcessObject=False,savedSpawnedFlag=False,savedReapedFlag=False,savedReturncode=None,savedLedgerAllChildrenClosed=True,firstFailureStop=True,noRetry=True,loaderNativeExecCompleted=False,actualCompilerExecutions=0,generatedNativeArtifacts=0,generatedSourceCopies=3,stdoutBytes=0,stderrBytes=0,exactFailingResourceCallKnown=False,preexecResourceSequence=['RLIMIT_FSIZE64MiB','RLIMIT_CPU1800s','RLIMIT_AS4GiB'],outerExitCodeReportedByRoot=1,outerExitCodeIndependentlySaved=False,currentProducerBindingEstablished=False,TCEmitterExecuted=False,generatedWorkloadExecuted=False,selfhostFixedPointQualified=False,timingQualified=False,reviewerCompilerCalls=0,reviewerNativeCalls=0,reviewerSSHCalls=0,reviewerCPUAPICalls=0,evidence=[ref(out/n)for n in sorted(names)]+[ref(G)],limits=['Popen may have forked an internal child to run preexec_fn; spawned=false means no Popen object was assigned, not proof that no OS child existed. Internal fork/reap census and PID are not independently recorded.','Saved preexec_fn exception occurs before loader exec; no actual compiler invocation, compiler artifact or current-producer witness is accepted.','Three resource setters are present but no per-call marker; exact failing setter and kernel error are unknown.','allChildrenClosed is the driver ledger terminal state for its failed constructor; it is not a recorded native child wait/returncode.','Root reported outer exit1; this audit has no independent saved outer transport receipt and accepts only inner saved failure.'])
    p=O/'report.json';p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o444);print(json.dumps(dict(path=str(p),bytes=p.stat().st_size,sha256=ref(p)['sha256'],status=report['status'])))
if __name__=='__main__':main()
