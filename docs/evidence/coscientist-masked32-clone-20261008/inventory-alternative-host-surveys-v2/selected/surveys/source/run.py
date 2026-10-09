"""Exactly3 prospective readonly configured-host surveys; separate rootGO."""
from pathlib import Path
import json,hashlib,os,sys,shlex
import ledger
D=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def configured():
    rows={};aliases=[]
    for line in (Path.home()/'.ssh/config').read_text().splitlines():
        s=line.strip().split()
        if not s or s[0].startswith('#'):continue
        key=s[0].lower()
        if key=='host':aliases=s[1:]
        elif key in ['hostname','user'] and len(s)==2:
            for a in aliases:
                if a in ['benjamin','levi','issachar']:rows.setdefault(a,{})[key]=s[1]
    return rows
def main():
    assert len(sys.argv)==2
    pr=load(D/'preregistration.json');go=load(sys.argv[1]);sp=load(D/'source-pins.json')
    expected=dict(status='ROOT_GO_EMBENCH_ALTERNATIVE_HOST_SURVEYS_V1_ONLY',sourcePinsSHA256=H(D/'source-pins.json'),driverSHA256=H(D/'run.py'),preregistrationSHA256=H(D/'preregistration.json'),maximumNewSSHSurveyChildren=3,maximumCumulativeSSHSurveyChildren=6)
    assert go==expected and set(go)==set(expected)
    assert type(go['maximumNewSSHSurveyChildren'])is int and type(go['maximumCumulativeSSHSurveyChildren'])is int
    for n,r in sp.items():
        p=D/n;assert p.is_file() and not p.is_symlink() and p.stat().st_size==r['bytes'] and H(p)==r['sha256']
    for key in ['sanitizedInventory','inventoryAcceptance','SSHExecutable']:
        r=pr[key];p=Path(r['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==r['bytes'] and H(p)==r['sha256']
    inventory=load(pr['sanitizedInventory']['path']);cfg=configured()
    for h in pr['hosts']:
        assert cfg[h['alias']]==dict(hostname=h['IP'],user=h['user'])
        assert any(r['hostname']==h['alias'] and r['os']=='macOS' and r['online']is True and h['IP']in r['IP'] for r in inventory)
    out=D/'outputs';assert not out.exists(),'fresh namespace; no retry'
    os.umask(0o077);out.mkdir();ledger.save(out/'root-go.json',go)
    original=ledger.pump
    def bounded(proc,sinks,states,rawcap,until,stdin_payload=None):
        return original(proc,sinks,states,min(rawcap,pr['maximumBytesPerStream']),until,stdin_payload)
    ledger.pump=bounded
    led=ledger.Ledger(out/'children',dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',HOME=str(Path.home())),caps=dict(transport=3),deadline=pr['campaignDeadlineSeconds'])
    results=[];completed=False
    try:
        for h in pr['hosts']:
            argv=['/usr/bin/ssh',*pr['SSHOptions'],h['alias'],'python3 -B -c '+shlex.quote((D/'survey.py').read_text())]
            try:
                raw,err,row=led.call('readonly-'+h['alias']+'-10second-survey',argv,pr['timeoutPerChildSeconds'],'transport')
                ledger.save(out/(h['alias']+'-preparse.json'),dict(status='DURABLE_RAW_EXIT_BEFORE_PARSE',stdout=row['stdout'],stderr=row['stderr'],returncode=row['returncode'],effectivePerStreamCap=65536))
                assert not err
                q=json.loads(raw);assert type(q)is dict and q['timingQualified']is False
                result=dict(host=h,status='CLOSED_READONLY_SURVEY',survey=q)
            except Exception as ex:
                result=dict(host=h,status='FAILED_READONLY_SURVEY_NO_RETRY',exception=repr(ex),timingQualified=False)
                # Unclosed cleanup must stop before another host child.
                if not led.terminal()['allClosed']:
                    results.append(result);ledger.save(out/'results.json',results);raise
            results.append(result);ledger.save(out/'results.json',results)
        completed=True
    finally:
        # Use update so ledger's noRetry field cannot duplicate a keyword.
        terminal=led.terminal();terminal.update(completedAllSelectedHosts=completed,priorSurveyAttempts=3,cumulativeSurveyAttempts=3+len(led.rows),maximumCumulativeSurveyAttempts=6,timingQualified=False)
        ledger.save(out/'terminal.json',terminal)
    ledger.save(out/'report.json',dict(status='READONLY_ALTERNATIVE_HOST_SURVEYS_ONLY',results=results,terminal=terminal,compilerCalls=0,nativeBenchmarkCalls=0,transfers=0,remoteChanges=0,timingQualified=False))
    print(json.dumps(dict(status='READONLY_ALTERNATIVE_HOST_SURVEYS_ONLY',results=results)))
if __name__=='__main__':main()
