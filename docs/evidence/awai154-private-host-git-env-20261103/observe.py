# Test-only private-host environment and synthetic non-secret canary.
import os,pathlib,subprocess,resource
p=pathlib.Path('/private/tmp/awai154-host-git-env');d=p/'observe-root';d.mkdir();c=d/'capture';fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY);assert fd==3
e={'PATH':'/usr/bin:/bin','HOME':str(d),'GIT_CONFIG_NOSYSTEM':'0','SECRET_CANARY':'synthetic-canary'}
try:
 r=subprocess.run([str(p/'env-fixture.macho'),str(d),str(c)],cwd=p,env=e,pass_fds=(fd,),capture_output=True,text=True,timeout=10,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CPU,(5,5)));assert r.returncode==0,(r.returncode,r.stderr)
 lines=r.stdout.splitlines();assert 'GIT_CONFIG_NOSYSTEM=1' in lines and 'PATH=/usr/bin:/bin' in lines and 'LANG=C' in lines and not any(x.startswith('SECRET_CANARY=') or x=='GIT_CONFIG_NOSYSTEM=0' or x.startswith('HOME=') for x in lines)
 print('private host child env',r.stdout.strip(),flush=True)
finally:os.close(fd)
