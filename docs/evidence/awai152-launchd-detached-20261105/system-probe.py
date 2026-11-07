import json,os,plistlib,resource,signal,subprocess,sys,tempfile,time,uuid
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(4,4))
uid=os.getuid();label='org.awai.diagnostic.tree.'+uuid.uuid4().hex;domain='system';service=f'{domain}/{label}'
child_script='''import json,os,resource,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(2,2))
root=Path(os.environ["TASK_DIR"]);kids=[]
for detached in (False,True):
 p=os.fork()
 if p==0:
  if detached: os.setsid()
  (root/("detached" if detached else "group")).write_text(str(os.getpid()))
  time.sleep(15);os._exit(0)
 kids.append(p)
(root/"parent").write_text(str(os.getpid()))
time.sleep(15)
for p in kids: os.waitpid(p,0)
'''
def cmd(args):return subprocess.run(args,capture_output=True,text=True,timeout=8)
def observe(pid):
 r=cmd(['/bin/ps','-p',str(pid),'-o','pid=','-o','ppid=','-o','pgid=','-o','sess=','-o','state=','-o','lstart='])
 return r.stdout.strip() if r.returncode==0 else None
with tempfile.TemporaryDirectory(prefix='awai152-launchd-probe-',dir='/private/tmp') as td:
 root=Path(td);root.chmod(0o700);script=root/'work.py';script.write_text(child_script);pl=root/'test.plist'
 pl.write_bytes(plistlib.dumps({'Label':label,'ProgramArguments':['/usr/bin/python3',str(script)],'EnvironmentVariables':{'TASK_DIR':td},'RunAtLoad':True,'AbandonProcessGroup':False,'StandardOutPath':str(root/'stdout'),'StandardErrorPath':str(root/'stderr')}))
 before={};boot=False
 try:
  b=cmd(['/bin/launchctl','bootstrap',domain,str(pl)]);print('bootstrap',b.returncode,flush=True)
  if b.returncode:raise RuntimeError(b.stderr[:400])
  boot=True;end=time.monotonic()+8
  while time.monotonic()<end and not all((root/n).exists() for n in ('parent','group','detached')):time.sleep(.05)
  for n in ('parent','group','detached'):
   pid=int((root/n).read_text()); snap=observe(pid)
   if not snap:raise RuntimeError('missing pre-stop '+n)
   before[n]=(pid,snap);print('before',n,snap,flush=True)
  detached_pid=before['detached'][0]
  if os.getsid(detached_pid)!=detached_pid or os.getpgid(detached_pid)!=detached_pid: raise RuntimeError('detached session not established')
  print('detached_session_confirmed',True,flush=True)
  b=cmd(['/bin/launchctl','bootout',service]);print('bootout',b.returncode,flush=True)
  if b.returncode:raise RuntimeError(b.stderr[:400])
  boot=False;time.sleep(.4)
  for n,(pid,_) in before.items():print('after',n,observe(pid),flush=True)
  check=cmd(['/bin/launchctl','print',service]);print('service_absent',check.returncode!=0,flush=True)
 finally:
  if boot:cmd(['/bin/launchctl','bootout',service])
  for n,(pid,first) in before.items():
   current=observe(pid)
   if current and current.split()[-5:]==first.split()[-5:]:
    try:os.kill(pid,signal.SIGKILL)
    except ProcessLookupError:pass
  time.sleep(.2)
  for n,(pid,first) in before.items():
   current=observe(pid)
   if current and current.split()[-5:]==first.split()[-5:] and " Z " not in (" "+current+" "): raise RuntimeError("cleanup unknown "+n)
  print("task_processes_absent_or_zombie",True,flush=True)
