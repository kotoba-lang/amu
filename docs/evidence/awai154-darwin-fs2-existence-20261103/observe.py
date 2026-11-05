import os,pathlib,resource,subprocess
p=pathlib.Path('/private/tmp/awai154-fs2-exists-error');(p/'directory').mkdir();(p/'directory'/'file').write_text('payload');(p/'deny-dir').mkdir();(p/'deny-dir'/'file').write_text('secret');(p/'deny-file').write_text('secret');(p/'link').symlink_to('directory/file');os.chmod(p/'deny-dir',0);os.chmod(p/'deny-file',0)
fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY);assert fd==3
def limit():resource.setrlimit(resource.RLIMIT_CPU,(3,3))
def run(artifact,op,path):
 r=subprocess.run([str(p/(artifact+'.macho')),op,path],cwd=p,pass_fds=(fd,),capture_output=True,text=True,timeout=5,preexec_fn=limit);return r.returncode,r.stdout.strip()
try:
 for path in ('deny-dir/file','deny-file'):
  try:
   if path=='deny-file':open(p/path).read()
   else:os.stat(p/path)
   raise AssertionError(('permission succeeded',path))
  except PermissionError:pass
 for path,expected in [('/directory/file','1'),('/directory','1'),('/missing','0'),('/missing/nested','0'),('/deny-dir/file','?'),('/deny-file','?'),('/link','?')]:
  result=run('new','D',path);assert result==(0,'reply='+expected),(path,result);print('new D',path,result,flush=True)
 for path in ('/deny-dir/file','/deny-file','/link'):
  result=run('old','D',path);assert result==(0,'reply=0'),(path,result);print('old D',path,result,flush=True)
 for artifact in ('new','old'):
  result=run(artifact,'A','/directory/file');assert result==(0,'reply=payload'),(artifact,result);print(artifact,'A',result,flush=True)
finally:os.close(fd);os.chmod(p/'deny-dir',0o700);os.chmod(p/'deny-file',0o600)
