import os,pathlib,resource,subprocess
p=pathlib.Path('/private/tmp/awai154-fs2-exists-error');d=p/'bridge-denied';d.mkdir();(d/'request').write_text('wanted');os.chmod(d,0);fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY);assert fd==3
def limit():resource.setrlimit(resource.RLIMIT_CPU,(3,3))
try:
 try:os.stat(d/'request');raise AssertionError('expected access denied')
 except PermissionError:pass
 for binary,arguments,expected in [('bridge-old',['/bridge-denied/request','other'],'bridge/request-ready'),('bridge-new',['/bridge-denied/request','other'],'bridge/request-unknown'),('head-old',['/bridge-denied/request'],'bridge/head-ready'),('head-new',['/bridge-denied/request'],'bridge/request-unknown')]:
  r=subprocess.run([str(p/(binary+'.macho')),*arguments],cwd=p,pass_fds=(fd,),capture_output=True,text=True,timeout=5,preexec_fn=limit);print(binary,r.returncode,r.stdout.strip(),flush=True);assert (r.returncode,r.stdout.strip())==(0,expected)
finally:os.close(fd);os.chmod(d,0o700)
