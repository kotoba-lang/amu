"""Fixed owned-group fixture: leader + at most one fixed helper, no setters/native loader."""
import os,sys,json,subprocess,hashlib,stat
from pathlib import Path
D=Path(__file__).resolve().parent
def checked(p,v):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode)and not p.is_symlink()and a.st_size==v['bytes']and a.st_size<=384*1024**2
 b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns)
 assert hashlib.sha256(b).hexdigest()==v['sha256'];return str(p)
def fixed_helper_argv():
 pr=json.loads((D/'preregistration.json').read_bytes());sp=json.loads((D/'source-pins.json').read_bytes())
 interpreter=checked(pr['interpreter']['path'],pr['interpreter'])
 source=checked(D/'fixture.py',sp['fixture.py'])
 argv=[interpreter,source,'helper']
 assert pr['helperArgv']==argv,'fixed helper from preregistration'
 return argv
def emit(q):print(json.dumps(q,sort_keys=True),flush=True)
def command(want):
 b=sys.stdin.buffer.readline(64);assert b==want+b'\n','exact release command'
def main(role):
 if role=='helper':
  emit({'phase':'helper-ready','pid':os.getpid(),'pgid':os.getpgrp()});command(b'release');return 0
 assert role=='leader' and os.getpid()==os.getpgrp()
 helper=None
 try:
  emit({'phase':'one-ready','pid':os.getpid(),'pgid':os.getpgrp()});command(b'spawn')
  argv=fixed_helper_argv()
  helper=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ))
  raw=helper.stdout.readline(4096);q=json.loads(raw)
  assert q=={'phase':'helper-ready','pid':helper.pid,'pgid':os.getpgrp()}
  emit({'phase':'two-ready','pid':os.getpid(),'pgid':os.getpgrp(),'helperPID':helper.pid,'helperArgv':argv})
  command(b'drop');helper.stdin.write(b'release\n');helper.stdin.flush();helper.stdin.close()
  rc=helper.wait(timeout=2);assert rc==0 and helper.stdout.read(4096)==b'' and helper.stderr.read(4096)==b''
  emit({'phase':'one-again-ready','pid':os.getpid(),'pgid':os.getpgrp(),'helperPID':helper.pid,'helperReaped':True,'helperReturncode':rc});command(b'finish')
  emit({'phase':'leader-complete','pid':os.getpid(),'childStarts':2,'helperReaped':True});return 0
 finally:
  if helper is not None and helper.poll()is None:
   helper.kill();helper.wait(timeout=2)
if __name__=='__main__':
 assert len(sys.argv)==2 and sys.argv[1]in ['leader','helper'];sys.exit(main(sys.argv[1]))
