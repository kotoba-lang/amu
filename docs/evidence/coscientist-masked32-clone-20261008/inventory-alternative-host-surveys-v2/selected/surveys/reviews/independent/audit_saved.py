"""Read/hash saved surveys only; no imports of executable survey or driver code."""
from pathlib import Path
import hashlib,json,math,shlex,stat
O=Path(__file__).resolve().parent;D=O.parent/'embench-alternative-host-survey-source-v1-20261008'
def load(p):return json.loads(Path(p).read_bytes())
def need(v,m):
    if not v:raise ValueError(m)
def ref(p):
    p=Path(p);need(p.is_file()and not p.is_symlink(),'regular evidence');return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def check(p,r):need({k:ref(p)[k]for k in ['bytes','sha256']}=={k:r[k]for k in ['bytes','sha256']},'saved hash')
def main():
    sp=load(D/'source-pins.json');pr=load(D/'preregistration.json');out=D/'outputs';g=load(out/'root-go.json')
    for n,r in sp.items():check(D/n,r)
    need(g==dict(status='ROOT_GO_EMBENCH_ALTERNATIVE_HOST_SURVEYS_V1_ONLY',sourcePinsSHA256=ref(D/'source-pins.json')['sha256'],driverSHA256=ref(D/'run.py')['sha256'],preregistrationSHA256=ref(D/'preregistration.json')['sha256'],maximumNewSSHSurveyChildren=3,maximumCumulativeSSHSurveyChildren=6),'exact GO')
    for k in ['sanitizedInventory','inventoryAcceptance']:check(pr[k]['path'],pr[k])
    terminal=load(out/'terminal.json');need(terminal==dict(children=3,classes=dict(transport=3),allClosed=True,noRetry=True,completedAllSelectedHosts=True,priorSurveyAttempts=3,cumulativeSurveyAttempts=6,maximumCumulativeSurveyAttempts=6,timingQualified=False),'complete closed3')
    need(load(out/'children/terminal.json')=={k:terminal[k]for k in ['children','classes','allClosed','noRetry']},'child census');saved=load(out/'results.json');need(load(out/'report.json')['results']==saved and load(out/'report.json')['terminal']==terminal,'saved report consistency')
    fields={'hostname','OS','architecture','timingQualified','OSVersion','OSBuild','CPU','logicalCores','loadBefore','loadAfter','idlePercent','ticksBefore','ticksAfter','deltaTicks','CPUIntervalSeconds','busyProcessThresholdCPUPercent','busySafeCommandCounts','busyOtherProcesses','processArgumentsRead','remoteSurveyChildren','quietSurveyEligible'};results=[];evidence=[]
    for i,(host,entry)in enumerate(zip(pr['hosts'],saved),1):
        r=load(out/'children'/('%05d'%i)/'receipt.json');need(r['index']==i and r['label']=='readonly-'+host['alias']+'-10second-survey'and r['state']=='terminal'and r['returncode']==0 and r['exception']is None and r['cleanupException']is None,'closed0 survey child')
        need(r['argv']==['/usr/bin/ssh',*pr['SSHOptions'],host['alias'],'python3 -B -c '+shlex.quote((D/'survey.py').read_text())] and r['timeoutSeconds']==30,'exact pinned readonly SSH command')
        need(r['environment']==dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',HOME='/Users/junkawasaki'),'clean env')
        for k in ['stdout','stderr']:
            check(r[k]['path'],r[k]);p=Path(r[k]['path']);need(stat.S_IMODE(p.stat().st_mode)==0o600 and p.stat().st_size<=65536,'private bounded raw');need(r['pipeStates'][k]==dict(bytes=p.stat().st_size,EOF=True,overflowByte=None),'closed pipe EOF')
        need(r['stderr']['bytes']==0 and r['stdinBytesSent']==0 and r['regularFileBytesMaximum']==16777216,'safe transport mechanics')
        need(load(out/(host['alias']+'-preparse.json'))==dict(status='DURABLE_RAW_EXIT_BEFORE_PARSE',stdout=r['stdout'],stderr=r['stderr'],returncode=0,effectivePerStreamCap=65536),'durable preparse')
        raw=Path(r['stdout']['path']).read_bytes();need(raw.endswith(b'\n')and raw.count(b'\n')==1,'single complete JSON line');q=json.loads(raw);need(set(q)==fields and q['OS']=='Darwin'and q['architecture']=='arm64'and q['timingQualified']is False,'exact Darwin arm64 survey schema')
        for k in ['ticksBefore','ticksAfter']:need(len(q[k])==4 and all(type(x)is int and 0<=x<=0xffffffff for x in q[k]),'tick schema')
        delta=[(b-a)&0xffffffff for a,b in zip(q['ticksBefore'],q['ticksAfter'])];need(delta==q['deltaTicks']and sum(delta)>0,'tick deltas');idle=100*delta[2]/sum(delta);need(math.isclose(idle,q['idlePercent'],rel_tol=1e-14),'independent idle')
        for k in ['loadBefore','loadAfter']:need(len(q[k])==3 and all(type(x)in(int,float)and math.isfinite(x)and x>=0 for x in q[k]),'load3')
        need(type(q['logicalCores'])is int and 1<=q['logicalCores']<=256 and 10<=q['CPUIntervalSeconds']<=30,'bounded recorded topology interval')
        quiet=max(q['loadBefore'][0],q['loadAfter'][0])<=4 and idle>=90;need(q['quietSurveyEligible']is quiet and q['processArgumentsRead']is False and q['remoteSurveyChildren']==1,'quiet predicate/read scope')
        need(q['busyProcessThresholdCPUPercent']==1 and type(q['busyOtherProcesses'])is int and q['busyOtherProcesses']>=0 and set(q['busySafeCommandCounts'])<=set(['node','python3','Python','clang','amu','java','Google Chrome','Code'])and all(type(x)is int and x>=0 for x in q['busySafeCommandCounts'].values()),'safe process count schema')
        need(entry==dict(host=host,status='CLOSED_READONLY_SURVEY',survey=q),'raw saved-result identity')
        results.append(dict(alias=host['alias'],OS=q['OS'],architecture=q['architecture'],OSVersion=q['OSVersion'],OSBuild=q['OSBuild'],CPU=q['CPU'],logicalCores=q['logicalCores'],loadBefore1=q['loadBefore'][0],loadAfter1=q['loadAfter'][0],rawIdlePercent=idle,recordedCPUIntervalSeconds=q['CPUIntervalSeconds'],quietSurveyEligible=quiet,busyOtherProcesses=q['busyOtherProcesses'],timingQualified=False))
        evidence +=[ref(out/'children'/('%05d'%i)/'receipt.json'),ref(out/(host['alias']+'-preparse.json'))]
    need(len(results)==len(saved)==3,'all selected3')
    source=(D/'run.py').read_text();need(source.index("ledger.save(out/(h['alias']+'-preparse.json')")<source.index('q=json.loads(raw)'),'source preparse order')
    report=dict(status='PASS_INDEPENDENT_SAVED_READONLY_ALTERNATIVE_HOST_SURVEYS_ONLY',independent=True,sourceAuthorSameAsAuditor=False,sourcePinsSHA256=ref(D/'source-pins.json')['sha256'],driverSHA256=ref(D/'run.py')['sha256'],preregistrationSHA256=ref(D/'preregistration.json')['sha256'],rootGOSHA256=ref(out/'root-go.json')['sha256'],newSSHChildren=3,priorSurveyAttempts=3,cumulativeSurveyAttempts=6,allClosed=True,allReturncodeZero=True,rawHashesPrivateMode0600AndEOFVerified=True,preparseClosureReviewed=True,effectivePerStreamBytesMaximum=65536,independentRawTickIdleAndLoadEligibilityRecomputed=True,results=results,reviewerSSHCalls=0,reviewerCPUAPICalls=0,reviewerCompilerCalls=0,reviewerNativeCalls=0,reviewerCLIStatusCalls=0,timingQualified=False,rawPublication=False,evidence=evidence+[ref(out/'report.json'),ref(out/'terminal.json')],limitations=['Saved10second survey windows only, not current host quietness or timing qualification.','No compiler/toolchain/SDK eligibility, workload execution or per-sample quiet qualification is established.','Safe busy-process counts were type/whitelist checked from survey JSON; raw ps output was not retained, so underlying process census is not independently reconstructed.','Reviewer made no SSH, native, compiler, CLI or CPU API calls.'])
    p=O/'report.json';p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o444);print(json.dumps(dict(path=str(p),bytes=p.stat().st_size,sha256=ref(p)['sha256'],status=report['status'],results=results),indent=2))
if __name__=='__main__':main()
