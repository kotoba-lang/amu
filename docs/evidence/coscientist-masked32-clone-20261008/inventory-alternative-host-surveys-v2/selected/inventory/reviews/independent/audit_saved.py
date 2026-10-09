"""Independent saved-file audit only. Never publishes private raw JSON."""
from pathlib import Path
import hashlib, ipaddress, json, stat
O=Path(__file__).resolve().parent
D=O.parent/'embench-host-inventory-v2-20261008'
F=O.parent/'embench-host-inventory-v2-review-root-20261008/outer-failure.json'
def load(p):return json.loads(Path(p).read_bytes())
def need(v,s):
    if not v:raise ValueError(s)
def ref(p):
    p=Path(p);need(p.is_file() and not p.is_symlink(),'regular evidence')
    return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def check(p,r):need({k:ref(p)[k]for k in ['bytes','sha256']}=={k:r[k]for k in ['bytes','sha256']},'exact saved hash')
def main():
    sp=load(D/'source-pins.json');pr=load(D/'preregistration.json');out=D/'outputs';g=load(out/'root-go.json')
    need(ref(D/'source-pins.json')['sha256']=='6a673cbbe30251ed028ca766c3795659425d8d7b82d2be972f35fc9e7eabc6f6','exact frozen V2 source')
    for n,r in sp.items():check(D/n,r)
    need(g==dict(status='ROOT_GO_EMBENCH_HOST_INVENTORY_V2_READONLY_ONLY',sourcePinsSHA256=ref(D/'source-pins.json')['sha256'],driverSHA256=ref(D/'inventory.py')['sha256'],preregistrationSHA256=ref(D/'preregistration.json')['sha256'],maximumNewStatusCalls=1,maximumCumulativeStatusCalls=2),'exact saved GO')
    for key in ['priorFailure','priorPreregistration']:check(pr[key]['path'],pr[key])
    r=load(out/'children/00001/receipt.json');ct=load(out/'children/terminal.json');pc=load(out/'preparse-closure.json')
    need(r['index']==1 and r['kind']=='transport' and r['label']=='single-readonly-status-inventory-v2' and r['argv']==pr['argv'] and r['timeoutSeconds']==30,'single status argv')
    need(ct==dict(children=1,classes=dict(transport=1),allClosed=True,noRetry=True) and r['state']=='terminal' and r['returncode']==0 and r['exception']is None and r['cleanupException']is None,'child closed zero')
    need(r['environment']==dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',HOME='/Users/junkawasaki') and r['stdinBytesSent']==0 and r['CPUbefore']is None and r['CPUafter']is None,'sanitized child environment')
    for stream in ['stdout','stderr']:
        check(r[stream]['path'],r[stream]);p=Path(r[stream]['path']);s=p.lstat();need(stat.S_IMODE(s.st_mode)==0o600 and s.st_size<=1048576,'private raw0600 bounded1MiB')
        need(r['pipeStates'][stream]==dict(bytes=s.st_size,EOF=True,overflowByte=None),'complete pipe EOF no overflow')
    need(r['stderr']['bytes']==0 and r['regularFileBytesMaximum']==16777216 and r['pipeCapture']=='nonblocking-cap-plus-one','bounded pipe mechanics')
    need(pc==dict(status='RAW_AND_EXIT_DURABLE_BEFORE_PARSE',stdout=r['stdout'],stderr=r['stderr'],returncode=0,allClosed=True,maximumEffectiveBytesPerStream=1048576,priorStatusCalls=1,cumulativeStatusCalls=2),'preparse receipt exact')
    source=(D/'inventory.py').read_text();need(source.index("ledger.save(out/'preparse-closure.json'")<source.index('data=json.loads(raw)'),'source persists closure before parsing')
    need('min(rawcap,pr[\'maximumBytesPerStream\'])'in source,'effective1MiB pump cap despite generic8MiB receipt field')
    need('dict(**led.terminal(),success=success,priorStatusCalls=1,cumulativeStatusCalls=1+len(led.rows),noRetry=True)'in source,'preserved duplicate noRetry source bug')
    data=load(r['stdout']['path']);need(type(data)is dict and type(data.get('Peer'))is dict,'private saved inventory structure');sanitized=[]
    for v in [data.get('Self',{}),*data['Peer'].values()]:
        need(type(v)is dict,'peer structure');host=v.get('HostName');os_=v.get('OS');online=v.get('Online');ips=v.get('TailscaleIPs',[])
        need(type(host)is str and len(host)<=255 and type(os_)is str and len(os_)<=64 and type(online)is bool and type(ips)is list and len(ips)<=4,'fourfield schema')
        need(all(type(ip)is str and str(ipaddress.ip_address(ip))==ip for ip in ips),'canonical IP')
        sanitized.append(dict(hostname=host,os=os_,online=online,IP=ips))
    need(len(sanitized)==44 and sanitized==load(out/'sanitized-inventory.json'),'exact reconstructed sanitized44')
    saved=load(out/'report.json');need(saved['status']=='PASS_READONLY_INVENTORY_V2_SANITIZED_ONLY' and saved['peers']==sanitized and saved['allClosed']is True and saved['newStatusCalls']==1 and saved['cumulativeStatusCalls']==2 and saved['rawPublication']is False,'saved inventory report only')
    outer=load(F);need(outer['observedOuterExitCode']==1 and outer['rerun']is False and "multiple values for keyword argument 'noRetry'"in outer['reason'],'outer wrapper failed1')
    need(not(out/'terminal.json').exists(),'driver final terminal absent; never invent wrapper success')
    need(len([p for p in (out/'children').iterdir()if p.is_dir()])==1,'one child folder only')
    p=O/'sanitized-inventory.json';p.write_text(json.dumps(sanitized,indent=2)+'\n');p.chmod(0o600)
    report=dict(status='PASS_INDEPENDENT_SAVED_SANITIZED_INVENTORY_ONLY_OUTER_WRAPPER_FAILED',independent=True,sourceAuthorSameAsAuditor=False,operationalExecutionByReviewer=False,sourcePinsSHA256=ref(D/'source-pins.json')['sha256'],driverSHA256=ref(D/'inventory.py')['sha256'],preregistrationSHA256=ref(D/'preregistration.json')['sha256'],rootGOSHA256=ref(out/'root-go.json')['sha256'],savedStatusChildClosedZero=True,bothPipesEOFWithoutOverflow=True,privateRawHashesAndMode0600Verified=True,preparseClosureExactAndSourceOrderReviewed=True,effectiveStreamCapBytes=1048576,genericReceiptDeclaredStreamCapBytes=8388608,sanitizedFourFieldsIndependentlyReconstructed=True,sanitizedEntries=44,sanitizedInventory=ref(p),sourceFinalWriterDuplicateNoRetryBug=True,outerExitCode=1,outerCompletionAccepted=False,driverFinalTerminalAbsent=True,newStatusCalls=1,cumulativeStatusCalls=2,reviewerStatusCalls=0,SSHCalls=0,compilerCalls=0,nativeCalls=0,CPUAPICalls=0,rawPublication=False,timingQualified=False,sourceUnchanged=True,evidence=[ref(out/q)for q in ['children/00001/receipt.json','children/terminal.json','preparse-closure.json','sanitized-inventory.json','report.json']]+[ref(F)],limitations=['Acceptance covers the saved inventory snapshot only; outer wrapper failed and no final driver terminal exists.','Status online flags do not establish current reachability, architecture, SSH access, compiler setup or quiet benchmark eligibility.','Private raw JSON was read locally for independent reconstruction; no private raw fields were copied into this report.'])
    p=O/'report.json';p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o444);print(json.dumps(dict(path=str(p),bytes=p.stat().st_size,sha256=ref(p)['sha256'],status=report['status'],sanitizedEntries=44)))
if __name__=='__main__':main()
