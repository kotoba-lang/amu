#!/usr/bin/env python3
"""Observe START_SUSPENDED and a pinned Darwin watcher on owned short-lived children.

This diagnostic is not a supervisor or a resource-governor qualification.
"""
import argparse,ctypes,hashlib,importlib.util,os,pathlib,platform,re,resource,select,signal,shutil,struct,subprocess,tempfile,time
resource.setrlimit(resource.RLIMIT_CPU,(3,4))
parser=argparse.ArgumentParser()
parser.add_argument('--watcher',type=pathlib.Path,required=True)
parser.add_argument('--expected-sha256',required=True)
args=parser.parse_args()
if (platform.system(),platform.machine())!=('Darwin','arm64'):raise RuntimeError('Darwin ARM64 required')
if not re.fullmatch('[0-9a-f]{64}',args.expected_sha256):raise ValueError('invalid hash')
image=args.watcher.resolve(strict=True)
if hashlib.sha256(image.read_bytes()).hexdigest()!=args.expected_sha256:raise ValueError('watcher hash mismatch')
subprocess.run(['/usr/bin/codesign','--verify','--strict',str(image)],check=True,capture_output=True,timeout=10)
spec=importlib.util.spec_from_file_location('h',str(pathlib.Path(__file__).with_name('check-macos-watch-helper.py')));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
L=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
L.posix_spawnattr_init.argtypes=[ctypes.POINTER(ctypes.c_void_p)];L.posix_spawnattr_init.restype=ctypes.c_int
L.posix_spawnattr_setflags.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.c_short];L.posix_spawnattr_setflags.restype=ctypes.c_int
L.posix_spawnattr_destroy.argtypes=[ctypes.POINTER(ctypes.c_void_p)];L.posix_spawnattr_destroy.restype=ctypes.c_int
L.posix_spawn.argtypes=[ctypes.POINTER(ctypes.c_int),ctypes.c_char_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_char_p),ctypes.POINTER(ctypes.c_char_p)];L.posix_spawn.restype=ctypes.c_int
with tempfile.TemporaryDirectory(prefix='awai152-suspended-watch-') as d:
 staged=pathlib.Path(d)/'watch.macho';shutil.copyfile(image,staged);staged.chmod(0o700);image=staged
 subprocess.run(['/usr/bin/codesign','--verify','--strict',str(image)],check=True,capture_output=True,timeout=10)
 for mode in ('normal','marker','fork'):
  attr=ctypes.c_void_p();pid=ctypes.c_int();owned=False;reaped=False;watch=None
  try:
   if (rc:=L.posix_spawnattr_init(ctypes.byref(attr))):raise RuntimeError(('init',rc))
   # Darwin SDK sys/spawn.h: START_SUSPENDED and CLOEXEC_DEFAULT.
   if (rc:=L.posix_spawnattr_setflags(ctypes.byref(attr),0x0080|0x4000)):raise RuntimeError(('flags',rc))
   marker=pathlib.Path(d)/(mode+'-started')
   if mode=='normal':args=[b'/bin/sleep',b'0.2']
   else:
    command=b'printf ready > "$1"' if mode=='marker' else b'printf ready > "$1"; /bin/sleep 0.2 & wait'
    args=[b'/bin/sh',b'-c',command,b'probe',os.fsencode(marker)]
   argv=(ctypes.c_char_p*(len(args)+1))(*args,None);env=(ctypes.c_char_p*2)(b'PATH=/usr/bin:/bin',None)
   if (rc:=L.posix_spawn(ctypes.byref(pid),args[0],None,ctypes.byref(attr),argv,env)):raise RuntimeError(('spawn',rc))
   owned=True;deadline=time.monotonic()+3
   while True:
    got,status=os.waitpid(pid.value,os.WNOHANG|os.WUNTRACED)
    if got:
     if not os.WIFSTOPPED(status):reaped=True;raise RuntimeError(('not-stopped',status))
     break
    if time.monotonic()>deadline:raise TimeoutError('not stopped')
    time.sleep(.01)
   sec,usec=h.identity(pid.value);req=struct.pack('<4sIQQII',b'WP01',pid.value,sec,usec,12345,3)
   watch=h.launch_watcher(image,pathlib.Path(d),req)
   ready=b'';deadline=time.monotonic()+3
   while len(ready)<40:
    rem=deadline-time.monotonic()
    if rem<=0 or not select.select([watch.stdout],[],[],rem)[0]:raise TimeoutError('watcher readiness')
    chunk=os.read(watch.stdout.fileno(),40-len(ready))
    if not chunk:raise RuntimeError('watcher EOF before ready')
    ready+=chunk
   if ready!=b'WR01\0\0\0\0'+req or watch.poll() is not None:raise RuntimeError('invalid readiness')
   if mode!='normal' and marker.exists():raise RuntimeError('child ran before watcher ready')
   os.kill(pid.value,signal.SIGCONT)
   out,err=watch.communicate(timeout=5)
   got,status=os.waitpid(pid.value,0);reaped=True
   if got!=pid.value or not os.WIFEXITED(status) or os.WEXITSTATUS(status)!=0 or err:raise RuntimeError(('child/err',status,err))
   if mode=='normal' and (watch.returncode!=0 or out!=b'WO01\0\0\0\0'+req):raise RuntimeError((mode,watch.returncode,out))
   if mode in ('marker','fork') and (watch.returncode!=1 or out):raise RuntimeError((mode,watch.returncode,out))
   if mode!='normal' and marker.read_bytes()!=b'ready':raise RuntimeError('child marker mismatch')
   print('mode',mode,'spawn-stopped',True,'watcher-ready-before-resume',True,'watcher-exit',watch.returncode,'output-bytes',len(out),'child-reaped',True,flush=True)
  finally:
   if watch and watch.poll() is None:watch.kill();watch.wait(timeout=3)
   if owned and not reaped:
    try:os.kill(pid.value,signal.SIGKILL)
    except ProcessLookupError:pass
    try:os.waitpid(pid.value,0)
    except ChildProcessError:pass
   if attr.value:L.posix_spawnattr_destroy(ctypes.byref(attr))
