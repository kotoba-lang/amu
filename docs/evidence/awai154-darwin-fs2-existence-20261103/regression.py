import os,pathlib,resource,subprocess
p=pathlib.Path('/private/tmp/awai154-fs2-exists-error');d=p/'regression';d.mkdir();(d/'file').write_text('payload');os.chmod(d/'file',0o4644);fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY);assert fd==3
def limit():resource.setrlimit(resource.RLIMIT_CPU,(3,3))
def call(op,path,tail=''):
 r=subprocess.run([str(p/'general.macho'),op,path,tail],cwd=p,pass_fds=(fd,),capture_output=True,timeout=5,preexec_fn=limit);assert r.returncode==0,(op,r.returncode,r.stderr);assert r.stdout.startswith(b'\0FS2\0') and r.stdout.endswith(b'\n');v=r.stdout[5:-1].decode();print(op,path,repr(v),flush=True);return v
try:
 assert call('D','/regression/file')=='1'
 assert call('A','/regression/file')=='payload'
 assert call('O','/regression/file').split()[0]==str(0o644)
 assert call('U','/regression/file').split()[0]==str(0o4644)
 assert call('E','/regression/file','1:3')=='ayl'
 assert call('I','/regression/newdir')=='1'
 assert call('H','/regression/file','600')=='1'
 assert call('M','/regression/file')=='1'
 assert call('L','/regression/file','/regression/moved')=='1'
 assert call('D','/regression/moved')=='1' and call('D','/regression/file')=='0'
finally:os.close(fd)
