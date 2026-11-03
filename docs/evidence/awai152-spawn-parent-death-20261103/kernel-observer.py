# One-off Linux kernel protocol experiment; not the Amu runtime under test.
import ctypes, json, os, select, signal, time
libc=ctypes.CDLL(None, use_errno=True)
def bound(parent):
 return parent>0 and libc.prctl(1,9,0,0,0)==0 and os.getppid()==parent
def live(pid):
 try:
  with open('/proc/%d/status'%pid) as f: return not any(line.startswith('State:') and ('Z' in line or 'X' in line) for line in f)
 except FileNotFoundError: return False
r,w=os.pipe();controller=os.fork()
if controller==0:
 os.close(r);expected=os.getpid();helper=os.fork()
 if helper==0:
  if not bound(expected):os._exit(21)
  expected2=os.getpid();worker=os.fork()
  if worker==0:
   if not bound(expected2):os._exit(22)
   os.write(w,('%d %d\n'%(expected2,os.getpid())).encode());time.sleep(8);os._exit(0)
  time.sleep(8);os._exit(0)
 time.sleep(8);os._exit(0)
os.close(w); helper=worker=None
try:
 ready,_,_=select.select([r],[],[],4)
 if not ready:raise RuntimeError('no child readiness')
 helper,worker=map(int,os.read(r,256).decode().split())
 os.kill(controller,signal.SIGKILL);os.waitpid(controller,0);controller=None;time.sleep(.5)
 result={'helperAlive':live(helper),'workerAlive':live(worker),'sampleDelaySeconds':.5}
 print(json.dumps(result),flush=True)
 if result['helperAlive'] or result['workerAlive']:raise RuntimeError('descendant still live')
finally:
 for pid in (controller,helper,worker):
  if pid:
   try:os.kill(pid,signal.SIGKILL)
   except ProcessLookupError:pass
 os.close(r)
