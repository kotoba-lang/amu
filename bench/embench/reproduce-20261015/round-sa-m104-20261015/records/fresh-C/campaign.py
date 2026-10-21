"""BOOTSTRAP-TOOL: unchanged Embench C19 / official speed driver campaign."""
import hashlib,json,math,os,platform,re,statistics,subprocess,sys,time,shlex
from pathlib import Path

def global_idle(exclude_ancestors=False):
 q=subprocess.run(['/bin/ps','-axo','pid=,ppid=,command='],capture_output=True,text=True,check=True)
 parsed=[]
 for line in q.stdout.splitlines():
  m=re.match(r'\s*(\d+)\s+(\d+)\s+(.*)',line)
  if m:parsed.append(dict(pid=int(m[1]),ppid=int(m[2]),command=m[3]))
 own=os.getpid();ancestors=set();byid={r['pid']:r for r in parsed};p=byid.get(own,{}).get('ppid',0)
 while p in byid and p not in ancestors:
  ancestors.add(p);p=byid[p]['ppid']
 watched=[]
 pattern=re.compile(r'/Users/joseph/github/workspaces/codex/embench-picojpeg-edn-20261009|/Users/joseph/github/workspaces/codex/seed-logical-immediate|/Users/joseph/github/workspaces/codex/seed-logical-immediate|/Users/joseph/github/workspaces/codex/seed-logical-immediate|/(?:timer(?:s)?(?:\s|/|$)|kexe-loader(?:\s|$)|(?:one-controller|confirm-controller)\.py(?:\s|$)|ablate\.py(?:\s|$)|(?:campaign[^ /]*|run_trigger)\.py(?:\s|$))')
 active=re.compile(r'/(?:OFF|ON)/timer(?:\s|$)|/(?:one-controller|confirm-controller|ablate|(?:campaign[^ /]*|run_trigger))\.py(?:\s|$)')
 for row in parsed:
  if row['pid']==own:continue
  # Exclude only an actual ancestor invoking this exact script with no
  # additional command. macOS login wrappers are explicitly recognized.
  if row['pid'] in ancestors:
   ownscript=str(Path(__file__).resolve())
   try: argv=shlex.split(row['command'])
   except ValueError: argv=[]
   shellnames=['/bin/zsh','/bin/sh','/bin/bash','/bin/dash']
   tail=None
   if len(argv)>=3 and argv[0] in shellnames and argv[1]=='-c': tail=argv[2:]
   elif argv and argv[0]=='/usr/bin/login':
    # Only the login's real shell invocation suffix can qualify.
    positions=[i for i,x in enumerate(argv) if x in shellnames]
    if len(positions)==1:
     i=positions[0]
     if i+2<len(argv) and argv[i+1]=='-c': tail=argv[i+2:]
   if tail is not None:
    if len(tail)==1:
     try: tail=shlex.split(tail[0])
     except ValueError: tail=[]
    if tail==['python3',ownscript]:continue
  if pattern.search(row['command']):watched.append(row)
 return watched


root=Path(__file__).resolve().parent; up=root/'upstream'; out=root/'results'
assert global_idle()==[]
custody=json.loads((root/'custody-receipt.json').read_text());assert custody['status']=='PASS_EXACT_C65_BINARY_SOURCE_C114_GLOBAL_IDLE' and custody['root']==str(root) and custody['files']==23 and custody['members']==24 and custody['binaries']==19 and custody['sourceFiles']==40 and custody['ownedRows']==[]
out.mkdir(exist_ok=False)
(out/'global-preflight.json').write_text(json.dumps(dict(ownedRows=[]))+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(argv,**kw):
    timeout=kw.pop('timeout',240)
    p=subprocess.run(list(map(str,argv)),capture_output=True,text=True,timeout=timeout,**kw)
    if p.returncode: raise RuntimeError((argv,p.returncode,p.stdout,p.stderr))
    return p
baseline=json.loads((up/'baseline-data/speed.json').read_text()); names=sorted(baseline)
assert len(names)==19
manifest={str(p.relative_to(up)):sha(p) for folder in ['src','support','baseline-data'] for p in (up/folder).rglob('*') if p.is_file()}
report=dict(status='building',host=platform.node(),platform=platform.platform(),
            machine=platform.machine(),clang=run(['/usr/bin/clang','--version']).stdout,
            upstreamCommit='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70',sourceHashes=manifest,
            metric='Embench speed',runtime='original C, upstream main, verified outside timed interval',
            kotobaOfficialScore=None,exploratory=True,samplesPerWorkload=1,noRetry=False,cpuOnlyRetries=True,noAdaptiveRetry=True,selectionPolicy="FIRST_CPU_QUALIFIED_NOT_FASTEST",maxActualAttemptsPerWorkload=3,idleMinimumPercent=70,buildCommands=[],pilot={},globalScaleFactor=None)
def save(): (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
def build(gsf,label):
    import shutil
    assert gsf==32768
    custody=json.loads((root/'source-custody.json').read_text());assert custody['sourceHashes']==manifest
    bd=out/label
    for name in names:
        src=root/'binaries'/name;e=custody['binaries'][name];assert src.stat().st_size==e['bytes'] and sha(src)==e['sha256']
        d=bd/'src'/name;d.mkdir(parents=True);shutil.copyfile(src,d/name);(d/name).chmod(0o755)
    report['reusedFrozenRound65Binaries']=True;save();return bd

try:
    gsf=32768
    assert gsf>0
    max_lsf=max(int(m[1]) for name in names for p in (up/'src'/name).glob('*.c')
                for m in re.finditer(r'#define\s+LOCAL_SCALE_FACTOR\s+(\d+)',p.read_text()))
    assert max_lsf*gsf<2147483647,'scaled loop signed overflow'
    report['globalScaleFactor']=gsf; report['predictedNs']={k:v*gsf for k,v in report['pilot'].items()};save()
    print('COMMON_GSF',gsf,flush=True)
    bd=build(gsf,'measured')
    # Official script imports this normal board target through PYTHONPATH.
    env=os.environ.copy();env['PYTHONPATH']=str(root)
    cmd=[sys.executable,up/'benchmark_speed.py','--builddir',bd,'--logdir',out/'official-logs',
         '--target-module','run_trigger','--gsf',gsf,'--json-output','--samples','1']
    report['driverCommand']=list(map(str,cmd));save()
    q=run(cmd,env=env,cwd=up,timeout=3600)
    (out/'official.stdout').write_text(q.stdout);(out/'official.stderr').write_text(q.stderr)
    raw={n:json.loads((bd/'raw'/(n+'.json')).read_text()) for n in names}
    assert all(r['complete'] for r in raw.values()),'incomplete suite: upstream driver can omit failed workloads'
    ratios={n:baseline[n]/(statistics.median(s['elapsedNs'] for s in raw[n]['samples'] if s['accepted'])/1e6)*gsf for n in names}
    report.update(status='COMPLETE_EXPLORATORY_ORIGINAL_C19_SPEED_DRIVER',relativeSpeeds=ratios,
                  speedGeometricMean=math.exp(statistics.mean(map(math.log,ratios.values()))),
                  full19=True,officialDriverRun=True,clockMHzMeasured=False,
                  scorePerMHz=None,sourceUnchanged=manifest=={str(p.relative_to(up)):sha(p) for folder in ['src','support','baseline-data'] for p in (up/folder).rglob('*') if p.is_file()})
    assert report['sourceUnchanged']; print('COMPLETE',report['speedGeometricMean'],flush=True)
except BaseException as ex:
    report.update(status='FAILED',failure=repr(ex));raise
finally:
 save()
 closure=global_idle();assert closure==[],closure
 (out/'global-closure.json').write_text(json.dumps(dict(ownedRows=closure))+'\n')
