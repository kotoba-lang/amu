import os,platform,resource,select,signal,subprocess,time
if platform.system()!='Darwin' or platform.machine()!='arm64':raise RuntimeError('Darwin ARM64 required')
resource.setrlimit(resource.RLIMIT_CPU,(3,4));note_status=0x04000000
for case in ('zero','seven','signal'):
 p=subprocess.Popen(['/usr/bin/python3','-c','import sys,time;time.sleep(0.3);sys.exit('+('7' if case=='seven' else '0')+')'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);k=select.kqueue();reaped=False
 try:
  k.control([select.kevent(p.pid,filter=select.KQ_FILTER_PROC,flags=select.KQ_EV_ADD|select.KQ_EV_ENABLE,fflags=select.KQ_NOTE_EXIT|note_status,udata=12345)],0,0)
  if case=='signal':os.kill(p.pid,signal.SIGKILL)
  events=k.control(None,2,3)
  if len(events)!=1:raise RuntimeError(('event count',case,len(events)))
  e=events[0];pid,status=os.waitpid(p.pid,0);reaped=True
  print(case,'fflags',hex(e.fflags),'data',e.data,'waitstatus',status,'identity',e.ident==pid,'token',e.udata==12345,flush=True)
  if e.ident!=pid or e.udata!=12345 or not (e.fflags&select.KQ_NOTE_EXIT) or e.data!=status:raise RuntimeError('mismatch')
  if case=='zero' and not (os.WIFEXITED(status) and os.WEXITSTATUS(status)==0):raise RuntimeError('zero')
  if case=='seven' and not (os.WIFEXITED(status) and os.WEXITSTATUS(status)==7):raise RuntimeError('seven')
  if case=='signal' and not (os.WIFSIGNALED(status) and os.WTERMSIG(status)==signal.SIGKILL):raise RuntimeError('signal')
 finally:
  k.close()
  if not reaped:
   try:p.kill();p.wait(timeout=3)
   except ProcessLookupError:pass
