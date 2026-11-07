#!/usr/bin/env python3
"""Low-load local Darwin observation; not a supervisor or qualification."""
import ctypes,os,platform,resource,select,signal,time
if (platform.system(),platform.machine())!=('Darwin','arm64'):raise RuntimeError('Darwin ARM64 required')
resource.setrlimit(resource.RLIMIT_CPU,(3,4))
L=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
L.posix_spawnattr_init.argtypes=[ctypes.POINTER(ctypes.c_void_p)];L.posix_spawnattr_init.restype=ctypes.c_int
L.posix_spawnattr_setflags.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.c_short];L.posix_spawnattr_setflags.restype=ctypes.c_int
L.posix_spawnattr_destroy.argtypes=[ctypes.POINTER(ctypes.c_void_p)];L.posix_spawnattr_destroy.restype=ctypes.c_int
L.posix_spawn.argtypes=[ctypes.POINTER(ctypes.c_int),ctypes.c_char_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_char_p),ctypes.POINTER(ctypes.c_char_p)];L.posix_spawn.restype=ctypes.c_int
for mode in ('normal','shell','fork'):
 attr=ctypes.c_void_p();pid=ctypes.c_int();owned=False;reaped=False;kq=None
 try:
  if (rc:=L.posix_spawnattr_init(ctypes.byref(attr))):raise RuntimeError(('init',rc))
  # START_SUSPENDED | CLOEXEC_DEFAULT, defined by Darwin SDK sys/spawn.h.
  if (rc:=L.posix_spawnattr_setflags(ctypes.byref(attr),0x0080|0x4000)):raise RuntimeError(('flags',rc))
  args=[b'/bin/sleep',b'0.2'] if mode=='normal' else [b'/bin/sh',b'-c',b':' if mode=='shell' else b'/bin/sleep 0.2 & wait']
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
  kq=select.kqueue();change=select.kevent(pid.value,filter=select.KQ_FILTER_PROC,flags=select.KQ_EV_ADD|select.KQ_EV_ENABLE,fflags=select.KQ_NOTE_EXIT|select.KQ_NOTE_FORK|select.KQ_NOTE_EXEC,udata=12345)
  if kq.control([change],0,0):raise RuntimeError('unexpected registration events')
  os.kill(pid.value,signal.SIGCONT);events=[];deadline=time.monotonic()+3
  while time.monotonic()<deadline and not any(e.fflags & select.KQ_NOTE_EXIT for e in events):
   events.extend(kq.control(None,4,max(0,deadline-time.monotonic())))
  if not any(e.fflags & select.KQ_NOTE_EXIT for e in events) or any(e.ident!=pid.value or e.udata!=12345 for e in events):raise RuntimeError('unexpected event identity')
  if mode=='normal' and any(e.fflags & (select.KQ_NOTE_FORK|select.KQ_NOTE_EXEC) for e in events):raise RuntimeError('normal emitted transition')
  if mode=='shell' and not any(e.fflags & select.KQ_NOTE_EXEC for e in events):raise RuntimeError('shell exec not observed')
  if mode=='fork' and not any(e.fflags & select.KQ_NOTE_FORK for e in events):raise RuntimeError('fork not observed')
  got,status=os.waitpid(pid.value,0);reaped=True
  if got!=pid.value or not os.WIFEXITED(status) or os.WEXITSTATUS(status)!=0:raise RuntimeError(('exit',status))
  print('mode',mode,'stopped',True,'flags',[hex(e.fflags) for e in events],'child-reaped',True,flush=True)
 finally:
  if kq:kq.close()
  if owned and not reaped:
   try:os.kill(pid.value,signal.SIGKILL)
   except ProcessLookupError:pass
   try:os.waitpid(pid.value,0)
   except ChildProcessError:pass
  if attr.value:L.posix_spawnattr_destroy(ctypes.byref(attr))
