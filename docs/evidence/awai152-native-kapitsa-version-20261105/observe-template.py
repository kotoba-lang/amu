import hashlib,importlib.util,os,resource,select,signal,struct,subprocess,tempfile,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(3,4));repo=Path(__file__).resolve().parent;sp=importlib.util.spec_from_file_location('h',repo/'check-macos-watch-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
launcher=repo/'launcher.macho';watcher_image=repo/'watch.macho'
for p,pin in [(launcher,'LAUNCHER_DIGEST'),(watcher_image,'ad32993a07f5e8b3db5d46f695c9d1a2b319974f145f13ebe3406c23810eba6e')]:
 if hashlib.sha256(p.read_bytes()).hexdigest()!=pin:raise RuntimeError('pin mismatch')
 subprocess.run(['/usr/bin/codesign','--verify','--strict',str(p)],capture_output=True,check=True,timeout=8)
with tempfile.TemporaryDirectory(prefix='awai152-native-setexec-',dir='/private/tmp') as d:
 root=Path(d);proc=None;watch=None;reaped=False
 try:
  target=Path.home()/'.local/share/awai/flint16-0.2.26/kapitsa-0.2.26-darwin-arm64/kapitsa'
  if hashlib.sha256(target.read_bytes()).hexdigest()!='20db8dadcb79de820d237367ca93d7ac66f8a70d91d5513f6e1ab77253925daa':raise RuntimeError('target hash mismatch')
  subprocess.run(['/usr/bin/codesign','--verify','--strict',str(target)],capture_output=True,check=True,timeout=8)
  profile='(version 1) (allow default) (deny process-fork)'
  proc=subprocess.Popen(['/usr/bin/sandbox-exec','-p',profile,str(launcher)],stdout=subprocess.PIPE,stderr=subprocess.PIPE);deadline=time.monotonic()+8
  while True:
   got,status=os.waitpid(proc.pid,os.WNOHANG|os.WUNTRACED)
   if got:
    if not os.WIFSTOPPED(status):reaped=True;raise RuntimeError(('not stopped',status,proc.communicate()))
    break
   if time.monotonic()>deadline:raise TimeoutError('not stopped')
   time.sleep(.01)
  ps=subprocess.run(['/bin/ps','-p',str(proc.pid),'-o','comm='],capture_output=True,text=True,timeout=3)
  print('stopped_target',ps.stdout.strip(),flush=True)
  target=Path.home()/'.local/share/awai/flint16-0.2.26/kapitsa-0.2.26-darwin-arm64/kapitsa'
  if ps.returncode or ps.stdout.strip()!=str(target):raise RuntimeError('target mismatch')
  inspect=r'''import ctypes as c,json,sys
L=c.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
class P(c.Structure): _fields_=[('active',c.c_int32),('active_attr',c.c_uint32),('inactive',c.c_int32),('inactive_attr',c.c_uint32)]
p=P();L.memorystatus_control.argtypes=[c.c_uint32,c.c_int32,c.c_uint32,c.c_void_p,c.c_size_t];rc=L.memorystatus_control(8,int(sys.argv[1]),0,c.byref(p),c.sizeof(p));print(json.dumps([rc,p.active,p.active_attr,p.inactive,p.inactive_attr]))'''
  r=subprocess.run(['/usr/bin/sudo','-n','/usr/bin/python3','-c',inspect,str(proc.pid)],capture_output=True,text=True,timeout=5)
  if r.returncode or r.stderr:raise RuntimeError('limit observer failed')
  import json
  observed=json.loads(r.stdout)
  if observed!=[0,256,1,256,1]:raise RuntimeError(('unexpected limit',observed))
  print('stopped_limit',observed,flush=True)
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
  if watch.returncode or out!=b'WS01\0\0\0\0'+req or err or proc.returncode or childout!=b'kapitsa 0.2.26 (6ef19b0)\n' or childerr:raise RuntimeError(('bad exit',watch.returncode,proc.returncode,out,err,childout,childerr))
  print('watcher_status',0,'child_exit',proc.returncode,'version_output_verified',True,flush=True)
 finally:
  if watch and watch.poll() is None:watch.kill();watch.wait(timeout=3)
  if proc and not reaped:
   try:proc.kill();proc.wait(timeout=3)
   except (ProcessLookupError,ChildProcessError):pass
