import ctypes,hashlib,importlib.util,os,pathlib,resource,select,shutil,signal,struct,subprocess,tempfile,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(3,4));repo=Path(__file__).resolve().parent;sp=importlib.util.spec_from_file_location('h',repo/'check-macos-watch-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
image=repo/'watch.macho';assert hashlib.sha256(image.read_bytes()).hexdigest()=='0c7d6496a9b25ca9781152e6046751d259ee67433d87e92fb7d3ce5b04ff6dbf';subprocess.run(['/usr/bin/codesign','--verify','--strict',str(image)],check=True,capture_output=True,timeout=8)
base='/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9';orig=base+'/Resources/Python.app/Contents/MacOS/Python'
worker=r'''import ctypes as c,os,sys,struct
p,policy,final,base,orig,attrhex=sys.argv[1:]
sb=c.CDLL('/usr/lib/libsandbox.dylib');sb.sandbox_init.argtypes=[c.c_char_p,c.c_uint64,c.POINTER(c.c_char_p)];e=c.c_char_p();rc=sb.sandbox_init(policy.encode(),0,c.byref(e));print('SANDBOX',rc,flush=True)
if rc:sys.exit(2)
L=c.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True);raw=bytearray.fromhex(attrhex)
a=c.create_string_buffer(bytes(raw),248);desc=(c.c_uint64*18)();desc[0]=248;desc[1]=c.addressof(a)
argv=(c.c_char_p*6)(p.encode(),b'-c',final.encode(),p.encode(),orig.encode(),None);env=(c.c_char_p*3)(b'PATH=/usr/bin:/bin',('PYTHONHOME='+base).encode(),None)
L.syscall.argtypes=[c.c_int];L.syscall.restype=c.c_int;pid=c.c_int(-1);rc=L.syscall(244,c.byref(pid),c.c_char_p(p.encode()),c.byref(desc),argv,env)
print('UNEXPECTED_RETURN',rc,c.get_errno(),flush=True);sys.exit(3)
'''
final=r'''import os,signal
print('FINAL_STARTED',flush=True);os.kill(os.getpid(),signal.SIGSTOP)
a=[]
for i in range(96):
 b=bytearray(1048576)
 for j in range(0,len(b),4096):b[j]=1
 a.append(b)
 if (i+1)%16==0:print('MIB='+str(i+1),flush=True)
print('FINAL_DONE',flush=True)
'''

with tempfile.TemporaryDirectory(prefix='awai152-setexec-watch-',dir='/private/tmp') as d:
 root=Path(d);staged=root/'watch.macho';shutil.copyfile(image,staged);staged.chmod(0o700);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(staged)],check=True,capture_output=True,timeout=8);image=staged;p=root/'a/b/c/d/entry';p.parent.mkdir(parents=True);os.link(orig,p);os.symlink(base+'/Python3',root/'Python3')
 policy='(version 1)(allow default)(deny process-fork)(deny process-exec (require-not (literal "'+str(p)+'")))(deny file-write* (literal "'+str(p)+'"))'
 attribute=(repo/'attribute.bin').read_bytes();assert hashlib.sha256(attribute).hexdigest()=='04adb7b2105f6671a0b95a3d48f21a1abd5ce8a0df14b333d3767d8e9eacd4ac';env=os.environ.copy();env['PYTHONHOME']=base;proc=None;watch=None;reaped=False
 try:
  proc=subprocess.Popen([orig,'-c',worker,str(p),policy,final,base,orig,attribute.hex()],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env);deadline=time.monotonic()+8
  while True:
   got,st=os.waitpid(proc.pid,os.WNOHANG|os.WUNTRACED)
   if got:
    if not os.WIFSTOPPED(st):reaped=True;raise RuntimeError(('early-exit',st,proc.communicate()))
    break
   if time.monotonic()>deadline:raise TimeoutError('no stop')
   time.sleep(.01)
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
  sec,usec=h.identity(proc.pid);req=struct.pack('<4sIQQII',b'WP01',proc.pid,sec,usec,12345,3);watch=h.launch_watcher(image,root,req)
  ready=b'';end=time.monotonic()+3
  while len(ready)<40:
   remaining=end-time.monotonic()
   if remaining<=0 or not select.select([watch.stdout],[],[],remaining)[0]:raise TimeoutError('watcher ready')
   chunk=os.read(watch.stdout.fileno(),40-len(ready))
   if not chunk:raise RuntimeError('watcher EOF')
   ready+=chunk
  if ready!=b'WR01\0\0\0\0'+req or watch.poll() is not None:raise RuntimeError('bad ready')
  os.unlink(p);os.kill(proc.pid,signal.SIGCONT)
  end=time.monotonic()+2
  while True:
   got,status=os.waitpid(proc.pid,os.WNOHANG|os.WUNTRACED)
   if got:
    if not os.WIFSTOPPED(status):raise RuntimeError(('unexpected after-resume status',status))
    break
   if time.monotonic()>end:raise TimeoutError('no post-resume stop')
   time.sleep(.01)
  r=subprocess.run(['/usr/bin/sudo','-n','/usr/bin/python3','-c',inspect,str(proc.pid)],capture_output=True,text=True,timeout=5)
  if r.returncode or r.stderr:raise RuntimeError('post-resume observer failed')
  later=json.loads(r.stdout)
  if later!=[0,256,1,256,1]:raise RuntimeError(('unexpected post-resume limit',later))
  print('after_resume_limit',later,flush=True);os.kill(proc.pid,signal.SIGCONT)
  wout,werr=watch.communicate(timeout=5);out,err=proc.communicate(timeout=5);reaped=True
  print('watcher_exit',watch.returncode,'final_frame',wout==b'WO01\0\0\0\0'+req,'child_exit',proc.returncode,'watch_stderr',len(werr),'child_stderr',len(err),flush=True)
  print('output',out.splitlines(),flush=True)
  if watch.returncode or werr or err or wout!=b'WO01\0\0\0\0'+req:raise RuntimeError('watcher refused')
  if 'SANDBOX 0' not in out or 'FINAL_STARTED' not in out:raise RuntimeError('missing marker')
  if proc.returncode!=0 or 'FINAL_DONE' not in out:raise RuntimeError('control outcome not observed')

 finally:
  if watch and watch.poll() is None:watch.kill();watch.wait(timeout=3)
  if proc and not reaped:
   try:proc.kill();proc.wait(timeout=3)
   except (ProcessLookupError,ChildProcessError):pass
