"""Single readonly existing tailscale inventory. Root SOURCE GO required."""
from pathlib import Path
import hashlib,json,os,sys,ipaddress
import ledger
D=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def main():
    assert len(sys.argv)==2
    sp=load(D/'source-pins.json');pr=load(D/'preregistration.json');go=load(sys.argv[1])
    assert set(go)=={'status','sourcePinsSHA256','driverSHA256','preregistrationSHA256','maximumNewStatusCalls','maximumCumulativeStatusCalls'}
    assert type(go['maximumNewStatusCalls'])is int and type(go['maximumCumulativeStatusCalls'])is int
    assert go==dict(status='ROOT_GO_EMBENCH_HOST_INVENTORY_V2_READONLY_ONLY',sourcePinsSHA256=H(D/'source-pins.json'),driverSHA256=H(D/'inventory.py'),preregistrationSHA256=H(D/'preregistration.json'),maximumNewStatusCalls=1,maximumCumulativeStatusCalls=2)
    for n,r in sp.items():
        p=D/n;assert p.is_file() and not p.is_symlink() and p.stat().st_size==r['bytes'] and H(p)==r['sha256']
    for key in ['priorFailure','priorPreregistration','tailscaleExecutable']:
        r=pr[key];p=Path(r['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==r['bytes'] and H(p)==r['sha256']
    out=D/'outputs';assert not out.exists(),'one fresh invocation; no retry'
    os.umask(0o077);out.mkdir()
    ledger.save(out/'root-go.json',go)
    # Reduce the copied transport pump's cap from8MiB to preregistered1MiB.
    original=ledger.pump
    def bounded(proc,sinks,states,rawcap,until,stdin_payload=None):
        return original(proc,sinks,states,min(rawcap,pr['maximumBytesPerStream']),until,stdin_payload)
    ledger.pump=bounded
    led=ledger.Ledger(out/'children',dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',HOME='/Users/junkawasaki'),caps=dict(transport=1),deadline=35)
    success=False
    try:
        raw,err,row=led.call('single-readonly-status-inventory-v2',pr['argv'],pr['timeoutSeconds'],'transport')
        # Ledger already fsynced raw streams, waitedCPU, exact exit and terminal.
        # Persist a separate closure attestation BEFORE any inventory parsing.
        ledger.save(out/'preparse-closure.json',dict(status='RAW_AND_EXIT_DURABLE_BEFORE_PARSE',stdout=row['stdout'],stderr=row['stderr'],returncode=row['returncode'],allClosed=led.terminal()['allClosed'],maximumEffectiveBytesPerStream=pr['maximumBytesPerStream'],priorStatusCalls=1,cumulativeStatusCalls=2))
        assert not err,'nonempty status stderr; raw retained privately'
        data=json.loads(raw);assert type(data)is dict and type(data.get('Peer'))is dict
        rows=[]
        for v in [data.get('Self',{}),*data['Peer'].values()]:
            assert type(v)is dict
            host=v.get('HostName');system=v.get('OS');online=v.get('Online');ips=v.get('TailscaleIPs',[])
            assert type(host)is str and len(host)<=255 and type(system)is str and len(system)<=64 and type(online)is bool and type(ips)is list and len(ips)<=4
            assert all(type(ip)is str and str(ipaddress.ip_address(ip))==ip for ip in ips)
            rows.append(dict(hostname=host,os=system,online=online,IP=ips))
        assert len(rows)<=4096
        ledger.save(out/'sanitized-inventory.json',rows)
        ledger.save(out/'report.json',dict(status='PASS_READONLY_INVENTORY_V2_SANITIZED_ONLY',peers=rows,newStatusCalls=1,cumulativeStatusCalls=2,allClosed=True,maximumEffectiveBytesPerStream=pr['maximumBytesPerStream'],noSSH=True,compilerCalls=0,nativeBenchmarkCalls=0,transfers=0,daemonStarts=0,settingsChanges=0,timingQualified=False,rawPublication=False))
        success=True
        print(json.dumps(dict(status='PASS_READONLY_INVENTORY_V2_SANITIZED_ONLY',peers=rows)))
    except BaseException as ex:
        ledger.save(out/'failure.json',dict(exception=repr(ex),rawRetainedPrivately=True,noRetry=True,timingQualified=False))
        raise
    finally:
        ledger.save(out/'terminal.json',dict(**led.terminal(),success=success,priorStatusCalls=1,cumulativeStatusCalls=1+len(led.rows),noRetry=True))
if __name__=='__main__':main()
