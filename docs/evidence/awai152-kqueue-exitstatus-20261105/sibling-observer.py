import json,os,platform,resource,select,signal,subprocess,time
if platform.system()!='Darwin' or platform.machine()!='arm64':raise RuntimeError('Darwin ARM64 required')
resource.setrlimit(resource.RLIMIT_CPU,(3,4))
worker=r'''import json,select,sys
p=int(sys.argv[1]);k=select.kqueue();n=0x04000000
try:
 k.control([select.kevent(p,filter=select.KQ_FILTER_PROC,flags=select.KQ_EV_ADD|select.KQ_EV_ENABLE,fflags=select.KQ_NOTE_EXIT|n,udata=12345)],0,0)
 print('READY',flush=True);events=k.control(None,2,3)
 if len(events)!=1:raise RuntimeError('count')
 e=events[0];print(json.dumps({'id':e.ident,'fflags':e.fflags,'data':e.data,'token':e.udata}),flush=True)
finally:k.close()'''
for case in ('zero','seven','signal'):
 target=subprocess.Popen(['/usr/bin/python3','-c','import sys,time;time.sleep(1);sys.exit('+('7' if case=='seven' else '0')+')'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);watch=None;reaped=False
 try:
  watch=subprocess.Popen(['/usr/bin/python3','-c',worker,str(target.pid)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  readable,_,_=select.select([watch.stdout],[],[],3)
  if not readable or watch.stdout.readline().strip()!='READY':raise RuntimeError('watcher not ready')
  if case=='signal':os.kill(target.pid,signal.SIGKILL)
  line=watch.stdout.readline();event=json.loads(line);out,err=watch.communicate(timeout=3)
  pid,status=os.waitpid(target.pid,0);reaped=True
  print(case,'data',event['data'],'waitstatus',status,'fflags',hex(event['fflags']),'watcher_exit',watch.returncode,flush=True)
  if watch.returncode or err or out or event['id']!=pid or event['token']!=12345 or not event['fflags']&select.KQ_NOTE_EXIT or event['data']!=status:raise RuntimeError('mismatch')
 finally:
  if watch and watch.poll() is None:watch.kill();watch.wait()
  if not reaped:
   try:target.kill();target.wait(timeout=3)
   except ProcessLookupError:pass
