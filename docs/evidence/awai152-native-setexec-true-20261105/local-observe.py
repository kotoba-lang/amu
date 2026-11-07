import hashlib,importlib.util,os,resource,select,signal,struct,subprocess,tempfile,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(3,4));repo=Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute');sp=importlib.util.spec_from_file_location('h',repo/'scripts/seed/check-macos-watch-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
launcher=Path('/private/tmp/awai152-setexec-true.macho');watcher_image=Path('/private/tmp/awai152-wp04-watch.macho')
for p,pin in [(launcher,'49a7b8c80c83730448b6465b06063abf01b4e6c573b0e87114483c2f516afa2b'),(watcher_image,'ad32993a07f5e8b3db5d46f695c9d1a2b319974f145f13ebe3406c23810eba6e')]:
 if hashlib.sha256(p.read_bytes()).hexdigest()!=pin:raise RuntimeError('pin mismatch')
 subprocess.run(['/usr/bin/codesign','--verify','--strict',str(p)],capture_output=True,check=True,timeout=8)
with tempfile.TemporaryDirectory(prefix='awai152-native-setexec-',dir='/private/tmp') as d:
 root=Path(d);proc=None;watch=None;reaped=False
 try:
  profile='(version 1) (allow default) (deny process-fork)'
  proc=subprocess.Popen(['/usr/bin/sandbox-exec','-p',profile,str(launcher)],stdout=subprocess.PIPE,stderr=subprocess.PIPE);deadline=time.monotonic()+4
  while True:
   got,status=os.waitpid(proc.pid,os.WNOHANG|os.WUNTRACED)
   if got:
    if not os.WIFSTOPPED(status):reaped=True;raise RuntimeError(('not stopped',status,proc.communicate()))
    break
   if time.monotonic()>deadline:raise TimeoutError('not stopped')
   time.sleep(.01)
  ps=subprocess.run(['/bin/ps','-p',str(proc.pid),'-o','comm='],capture_output=True,text=True,timeout=3)
  print('stopped_target',ps.stdout.strip(),flush=True)
  if ps.returncode or ps.stdout.strip()!='/usr/bin/true':raise RuntimeError('target mismatch')
  sec,usec=h.identity(proc.pid);req=struct.pack('<4sIQQII',b'WP04',proc.pid,sec,usec,12345,2);watch=h.launch_watcher(watcher_image,root,req)
  ready=b'';deadline=time.monotonic()+3
  while len(ready)<40:
   remaining=deadline-time.monotonic()
   if remaining<=0 or not select.select([watch.stdout],[],[],remaining)[0]:raise TimeoutError('watcher ready')
   data=os.read(watch.stdout.fileno(),40-len(ready))
   if not data:raise RuntimeError('watcher EOF')
   ready+=data
  if ready!=b'WR01\0\0\0\0'+req or watch.poll() is not None:raise RuntimeError('bad ready')
  os.kill(proc.pid,signal.SIGCONT);out,err=watch.communicate(timeout=5);childout,childerr=proc.communicate(timeout=5);reaped=True
  if watch.returncode or out!=b'WS01\0\0\0\0'+req or err or proc.returncode or childout or childerr:raise RuntimeError(('bad exit',watch.returncode,proc.returncode,out,err,childout,childerr))
  print('watcher_status',0,'child_exit',proc.returncode,'sandboxed_native_setexec',True,flush=True)
 finally:
  if watch and watch.poll() is None:watch.kill();watch.wait(timeout=3)
  if proc and not reaped:
   try:proc.kill();proc.wait(timeout=3)
   except (ProcessLookupError,ChildProcessError):pass
