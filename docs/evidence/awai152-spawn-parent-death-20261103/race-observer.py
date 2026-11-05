# One-off Linux kernel race experiment; this does not run the Amu runtime.
import ctypes, json, os, select, signal, time
libc=ctypes.CDLL(None,use_errno=True)
def run(check_parent):
 ready_r,ready_w=os.pipe();go_r,go_w=os.pipe();result_r,result_w=os.pipe()
 controller=os.fork()
 if controller==0:
  os.close(ready_r);os.close(go_w);os.close(result_r)
  expected=os.getpid();helper=os.fork()
  if helper==0:
   os.write(ready_w,(str(os.getpid())+'\n').encode())
   os.read(go_r,1)
   rc=libc.prctl(1,9,0,0,0);changed=os.getppid()!=expected
   result='refused' if rc!=0 or (check_parent and changed) else 'would-dispatch'
   os.write(result_w,json.dumps({'prctlResult':rc,'parentChanged':changed,'decision':result}).encode())
   os._exit(0)
  time.sleep(8);os._exit(0)
 os.close(ready_w);os.close(go_r);os.close(result_w);helper=None
 try:
  if not select.select([ready_r],[],[],4)[0]:raise RuntimeError('helper did not start')
  helper=int(os.read(ready_r,128));os.kill(controller,signal.SIGKILL);os.waitpid(controller,0);controller=None
  os.write(go_w,b'x')
  if not select.select([result_r],[],[],4)[0]:raise RuntimeError('helper did not report')
  result=json.loads(os.read(result_r,512));print(json.dumps({'checkParent':check_parent,**result}),flush=True)
  if result['prctlResult']!=0 or not result['parentChanged'] or result['decision']!=('refused' if check_parent else 'would-dispatch'):raise RuntimeError('unexpected race result')
 finally:
  if controller:
   try:os.kill(controller,signal.SIGKILL);os.waitpid(controller,0)
   except ProcessLookupError:pass
  for fd in [ready_r,go_w,result_r]:os.close(fd)
run(True)
run(False)
