import hashlib,os,plistlib,pwd,resource,subprocess,tempfile,time,uuid
from pathlib import Path
if os.geteuid()!=0:raise RuntimeError('root required')
resource.setrlimit(resource.RLIMIT_CPU,(4,4));uid=int(os.environ.get('SUDO_UID','501'));user=pwd.getpwuid(uid);exe=Path(user.pw_dir)/'.local/share/awai/flint16-0.2.26/kapitsa-0.2.26-darwin-arm64/kapitsa';pin='20db8dadcb79de820d237367ca93d7ac66f8a70d91d5513f6e1ab77253925daa'
if hashlib.sha256(exe.read_bytes()).hexdigest()!=pin:raise RuntimeError('kapitsa pin mismatch')
def run(a):return subprocess.run([str(x) for x in a],capture_output=True,text=True,timeout=8)
if run(['/usr/bin/codesign','--verify','--strict',exe]).returncode:raise RuntimeError('signature failure')
label='org.awai.diagnostic.kapitsa.'+uuid.uuid4().hex;service='system/'+label
with tempfile.TemporaryDirectory(prefix='awai152-kapitsa-help-',dir='/private/tmp') as td:
 root=Path(td);root.chmod(0o755);out=root/'out';out.mkdir();os.chown(out,uid,user.pw_gid);out.chmod(0o700);pl=root/'job.plist';profile='(version 1) (allow default) (deny process-fork)'
 pl.write_bytes(plistlib.dumps({'Label':label,'UserName':user.pw_name,'ProgramArguments':['/usr/bin/sandbox-exec','-p',profile,str(exe),'serve','--help'],'RunAtLoad':True,'AbandonProcessGroup':False,'StandardOutPath':str(out/'stdout'),'StandardErrorPath':str(out/'stderr')}));pl.chmod(0o644);boot=False
 try:
  p=run(['/bin/launchctl','bootstrap','system',pl]);print('bootstrap',p.returncode,flush=True)
  if p.returncode:raise RuntimeError(p.stderr[-400:])
  boot=True;end=time.monotonic()+8
  while time.monotonic()<end:
   s=run(['/bin/launchctl','print',service]);line=[x.strip() for x in s.stdout.splitlines() if 'last exit code =' in x]
   if line and '(never exited)' not in line[0]:break
   time.sleep(.05)
  else:raise RuntimeError('job completion unknown')
  stdout=(out/'stdout').read_text() if (out/'stdout').exists() else '';stderr=(out/'stderr').read_text() if (out/'stderr').exists() else ''
  print('exit',line[0],'help_private',('--private' in stdout),'help_local',('--local' in stdout),'stdout_bytes',len(stdout),'stderr_bytes',len(stderr),flush=True)
  if 'last exit code = 0' not in line[0] or '--private' not in stdout or '--local' not in stdout:raise RuntimeError('unexpected help')
  p=run(['/bin/launchctl','bootout',service]);print('bootout',p.returncode,flush=True)
  if p.returncode:raise RuntimeError(p.stderr[-400:])
  boot=False;print('job_print_absent',run(['/bin/launchctl','print',service]).returncode!=0,flush=True)
 finally:
  if boot:run(['/bin/launchctl','bootout',service])
