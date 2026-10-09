"""One bounded read-only SSH collection, strict receipt validation and local extraction."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,resource,shlex,signal,stat,subprocess,tarfile,time
D=Path(__file__).resolve().parent
HOST='zebulun@100.66.28.79';ROOT='/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-timing-v1-root'
SP='eb859a2064b863b3cfbdfda2f18e6e4beb88e9edd9b3e2cb375f5b7ec7dc1dbb'
H=lambda b:hashlib.sha256(b).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 script=D/'collect-timing-remote.py';s=script.lstat();assert stat.S_ISREG(s.st_mode) and not script.is_symlink() and s.st_size<=131072
 source=script.read_bytes();out=D/'collection-outputs';assert not out.exists();out.mkdir()
 env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',HOME='/Users/junkawasaki',LANG='C',LC_ALL='C',TZ='UTC',TMPDIR='/private/tmp')
 argv=['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',HOST,'python3 -c '+shlex.quote(source.decode())]
 assert len(argv[-1].encode())<=131072
 archive=out/'collection.tgz';errpath=out/'collection.stderr';proc=None;error=None;cleanup=None
 attempt=dict(argv=argv,environment=env,maximumChildren=1,noRetry=True,timeoutSeconds=660,remoteAlarmSeconds=600,archiveBytesMaximum=872415232,memberBytesMaximum=16777216,memberCountMaximum=65536,remoteCollectorSHA256=H(source),state='started')
 save(out/'attempt.json',attempt)
 def alarm(signum,frame):raise TimeoutError('collection absolute deadline720')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(720)
 try:
  with archive.open('xb') as o,errpath.open('xb') as e:
   try:
    def limit():resource.setrlimit(resource.RLIMIT_FSIZE,(872415232,872415232))
    proc=subprocess.Popen(argv,cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=o,stderr=e,start_new_session=True,preexec_fn=limit);until=time.monotonic()+660
    while proc.poll() is None:
     if time.monotonic()>=until:raise TimeoutError('collection wall cap660')
     if archive.stat().st_size>872415232 or errpath.stat().st_size>16777216:raise RuntimeError('collection stream cap')
     time.sleep(.05)
    proc.wait(timeout=30)
   except BaseException as ex:
    error=repr(ex)
    if proc is not None:
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     try:proc.wait(timeout=30)
     except BaseException as ex2:
      cleanup=repr(ex2)
      try:proc.kill();proc.wait(timeout=30)
      except BaseException as ex3:cleanup+='; '+repr(ex3)
  attempt.update(state='spawn-failed' if proc is None else 'terminal' if proc.poll() is not None else 'unclosed',returncode=None if proc is None else proc.returncode,exception=error,cleanupException=cleanup,archiveBytes=archive.stat().st_size,archiveSHA256=H(archive.read_bytes()),stderrBytes=errpath.stat().st_size,stderrSHA256=H(errpath.read_bytes()));save(out/'attempt.json',attempt)
  assert attempt['state']=='terminal' and attempt['returncode']==0 and error is None and cleanup is None and errpath.stat().st_size==0 and archive.stat().st_size<=872415232
  files={};total=0
  with tarfile.open(archive,'r:gz') as t:
   for m in t:
    p=PurePosixPath(m.name)
    assert m.isfile() and not m.issym() and not m.islnk() and not p.is_absolute() and '..' not in p.parts and str(p)==m.name and m.name not in files
    assert m.name=='collection-receipt.json' or len(p.parts)>=2 and p.parts[0] in ['source','control','timing']
    assert 0<=m.size<=16777216 and len(files)<65536;total+=m.size;assert total<=805306368
    b=t.extractfile(m).read(16777217);assert len(b)==m.size;files[m.name]=b
  receipt=json.loads(files['collection-receipt.json']);assert receipt['status']=='READONLY_TIMING_COLLECTION_ONLY_NOT_ACTUAL_ACCEPTANCE' and receipt['root']==ROOT and receipt['sourcePinsSHA256']==SP
  members=receipt['members'];assert len(members)==len(files)-1 and len({r['path'] for r in members})==len(members)
  assert {r['path'] for r in members}==set(files)-{'collection-receipt.json'}
  for r in members:assert set(r)=={'path','bytes','sha256'} and len(files[r['path']])==r['bytes'] and H(files[r['path']])==r['sha256']
  assert H(files['source/source-pins.json'])==SP
  registry=json.loads(files['source/source-pins.json']);assert {n.removeprefix('source/') for n in files if n.startswith('source/')}==set(registry)|{'source-pins.json'}
  for n,r in registry.items():assert '/' not in n and len(files['source/'+n])==r['bytes'] and H(files['source/'+n])==r['sha256']
  destination=D/'collected';assert not destination.exists();destination.mkdir()
  for n,b in sorted(files.items()):
   p=destination/n;p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb') as f:f.write(b)
   p.chmod(0o444)
  save(out/'report.json',dict(status='PASS_ONE_READONLY_TIMING_COLLECTION_ONLY_ACTUAL_REVIEW_PENDING',members=len(files),logicalBytes=total,archiveSHA256=attempt['archiveSHA256'],sourcePinsSHA256=SP,presentSubtrees=sorted({n.split('/')[0] for n in files if '/' in n}),timingTerminalPresent='timing/terminal.json' in files,timingReportPresent='timing/report.json' in files,SSHChildren=1,noRetry=True,timingAccepted=False))
 except BaseException as ex:save(out/'failure.json',dict(exception=repr(ex),noRetry=True));raise
 finally:signal.alarm(0)
if __name__=='__main__':main()
