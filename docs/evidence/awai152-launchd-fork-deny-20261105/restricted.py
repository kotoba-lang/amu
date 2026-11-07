import errno,json,os,plistlib,pwd,resource,subprocess,tempfile,time,uuid
from pathlib import Path
if os.geteuid()!=0:raise RuntimeError('root required for system bootstrap')
resource.setrlimit(resource.RLIMIT_CPU,(4,4));uid=int(os.environ.get('SUDO_UID','501'));user=pwd.getpwuid(uid);label='org.awai.diagnostic.sandbox.'+uuid.uuid4().hex;service='system/'+label
program='''import errno,json,os,resource,threading,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(2,2)); result={'uid':os.getuid(),'gid':os.getgid(),'pid':os.getpid()}; value=[]
t=threading.Thread(target=lambda:value.append(1));t.start();t.join();result['thread']=value==[1]
try:
 p=os.fork()
 if p==0:os._exit(0)
 _,status=os.waitpid(p,0);result['fork']='ok' if status==0 else 'bad'
except OSError as e:result['fork']='errno:'+str(e.errno)
try:
 p=os.posix_spawn('/usr/bin/true',['/usr/bin/true'],os.environ);_,status=os.waitpid(p,0);result['spawn']='ok' if status==0 else 'bad'
except OSError as e:result['spawn']='errno:'+str(e.errno)
Path(os.environ['TASK_OUTPUT']).write_text(json.dumps(result));time.sleep(12)
'''
def run(cmd):return subprocess.run(cmd,capture_output=True,text=True,timeout=8)
def identity(pid):
 r=run(['/bin/ps','-p',str(pid),'-o','pid=','-o','uid=','-o','lstart='])
 return r.stdout.strip() if r.returncode==0 else None
with tempfile.TemporaryDirectory(prefix='awai152-sandbox-job-',dir='/private/tmp') as td:
 root=Path(td);root.chmod(0o755);prog=root/'work.py';prog.write_text(program);prog.chmod(0o644);out=root/'out';out.mkdir();os.chown(out,uid,user.pw_gid);out.chmod(0o700)
 pl=root/'job.plist';profile='(version 1) (allow default) (deny process-fork)'
 pl.write_bytes(plistlib.dumps({'Label':label,'UserName':user.pw_name,'ProgramArguments':['/usr/bin/sandbox-exec','-p',profile,'/usr/bin/python3',str(prog)],'EnvironmentVariables':{'TASK_OUTPUT':str(out/'result')},'RunAtLoad':True,'AbandonProcessGroup':False,'StandardOutPath':str(out/'stdout'),'StandardErrorPath':str(out/'stderr')}));pl.chmod(0o644)
 boot=False;expected_pid=None;original=None
 try:
  r=run(['/bin/launchctl','bootstrap','system',str(pl)]);print('bootstrap',r.returncode,flush=True)
  if r.returncode:raise RuntimeError(r.stderr[-400:])
  boot=True;end=time.monotonic()+8
  while time.monotonic()<end and not (out/'result').exists():time.sleep(.05)
  if not (out/'result').exists():
   print('job_stderr', (out/'stderr').read_text()[-800:] if (out/'stderr').exists() else 'missing',flush=True)
   q=run(['/bin/launchctl','print',service]);print('job_print_tail',q.stdout[-800:],q.stderr[-200:],flush=True)
  res=json.loads((out/'result').read_text());expected_pid=res['pid'];original=identity(expected_pid);print('result',json.dumps(res,sort_keys=True),'ps',original,flush=True)
  if res['uid']!=uid or res['gid']!=user.pw_gid or not res['thread'] or res['fork']!='errno:'+str(errno.EPERM) or res['spawn']!='errno:'+str(errno.EPERM) or not original:raise RuntimeError('sandbox or identity failed')
  r=run(['/bin/launchctl','bootout',service]);print('bootout',r.returncode,flush=True)
  if r.returncode:raise RuntimeError(r.stderr[-400:])
  boot=False;time.sleep(.3);print('after',identity(expected_pid),flush=True)
  if identity(expected_pid) is not None:raise RuntimeError('job process still observed')
  print('job_print_absent',run(['/bin/launchctl','print',service]).returncode!=0,flush=True)
 finally:
  if boot:run(['/bin/launchctl','bootout',service])
  if expected_pid and original and identity(expected_pid)==original:
   os.kill(expected_pid,9)
