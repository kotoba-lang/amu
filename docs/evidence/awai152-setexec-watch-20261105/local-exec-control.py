import ctypes,hashlib,importlib.util,os,pathlib,resource,select,shutil,signal,struct,subprocess,tempfile,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(3,4));repo=Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute');sp=importlib.util.spec_from_file_location('h',repo/'scripts/seed/check-macos-watch-helper.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
image=Path('/private/tmp/awai152-ready-artifact-41793197780/public-macos-product/experimental-watch-fixture/watch.macho');assert hashlib.sha256(image.read_bytes()).hexdigest()=='0c7d6496a9b25ca9781152e6046751d259ee67433d87e92fb7d3ce5b04ff6dbf';subprocess.run(['/usr/bin/codesign','--verify','--strict',str(image)],check=True,capture_output=True,timeout=8)
base='/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9';orig=base+'/Resources/Python.app/Contents/MacOS/Python'
worker=r'''import ctypes as c,os,sys,struct
p,policy,final,base,orig=sys.argv[1:]
sb=c.CDLL('/usr/lib/libsandbox.dylib');sb.sandbox_init.argtypes=[c.c_char_p,c.c_uint64,c.POINTER(c.c_char_p)];e=c.c_char_p();rc=sb.sandbox_init(policy.encode(),0,c.byref(e));print('SANDBOX',rc,flush=True)
if rc:sys.exit(2)
L=c.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True);raw=bytearray(248)
for fmt,off,val in [('<H',0,0xc0),('<Q',56,1),('<i',68,-1),('<i',72,-1),('<i',76,-1)]:struct.pack_into(fmt,raw,off,val)
for i in range(4):struct.pack_into('<i',raw,112+i*4,-1)
a=c.create_string_buffer(bytes(raw),248);desc=(c.c_uint64*18)();desc[0]=248;desc[1]=c.addressof(a)
argv=(c.c_char_p*6)(p.encode(),b'-c',final.encode(),p.encode(),orig.encode(),None);env=(c.c_char_p*3)(b'PATH=/usr/bin:/bin',('PYTHONHOME='+base).encode(),None)
L.syscall.argtypes=[c.c_int];L.syscall.restype=c.c_int;pid=c.c_int(-1);rc=L.syscall(244,c.byref(pid),c.c_char_p(p.encode()),c.byref(desc),argv,env)
print('UNEXPECTED_RETURN',rc,c.get_errno(),flush=True);sys.exit(3)
'''
final=r'''import os
print('FINAL_STARTED',flush=True)
os.execv('/usr/bin/true',['/usr/bin/true'])
'''

with tempfile.TemporaryDirectory(prefix='awai152-setexec-watch-',dir='/private/tmp') as d:
 root=Path(d);staged=root/'watch.macho';shutil.copyfile(image,staged);staged.chmod(0o700);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(staged)],check=True,capture_output=True,timeout=8);image=staged;p=root/'a/b/c/d/entry';p.parent.mkdir(parents=True);os.link(orig,p);os.symlink(base+'/Python3',root/'Python3')
 policy='(version 1)(allow default)(deny process-fork)'
 env=os.environ.copy();env['PYTHONHOME']=base;proc=None;watch=None;reaped=False
 try:
  proc=subprocess.Popen([orig,'-c',worker,str(p),policy,final,base,orig],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env);deadline=time.monotonic()+8
  while True:
   got,st=os.waitpid(proc.pid,os.WNOHANG|os.WUNTRACED)
   if got:
    if not os.WIFSTOPPED(st):reaped=True;raise RuntimeError(('early-exit',st,proc.communicate()))
    break
   if time.monotonic()>deadline:raise TimeoutError('no stop')
   time.sleep(.01)
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
  wout,werr=watch.communicate(timeout=5);out,err=proc.communicate(timeout=5);reaped=True
  print('watcher_exit',watch.returncode,'final_frame',wout==b'WO01\0\0\0\0'+req,'child_exit',proc.returncode,'watch_stderr',len(werr),'child_stderr',len(err),flush=True)
  print('output',out.splitlines(),flush=True)
  if proc.returncode or watch.returncode!=1 or werr or err or wout:raise RuntimeError('exec refusal missing')
  if 'SANDBOX 0' not in out or 'FINAL_STARTED' not in out:raise RuntimeError('missing child marker')

 finally:
  if watch and watch.poll() is None:watch.kill();watch.wait(timeout=3)
  if proc and not reaped:
   try:proc.kill();proc.wait(timeout=3)
   except (ProcessLookupError,ChildProcessError):pass
