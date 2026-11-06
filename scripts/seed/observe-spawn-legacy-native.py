import argparse,hashlib,io,json,os,pathlib,shlex,subprocess,tarfile,tempfile

parser=argparse.ArgumentParser(description="Observe bounded native spawn isolation on Xavier")
parser.add_argument("--compiler",type=pathlib.Path,required=True)
parser.add_argument("--compiler-sha256",required=True)
args=parser.parse_args()
status=json.loads(subprocess.check_output(['tailscale','status','--json'],timeout=8));peer=next(x for x in status['Peer'].values() if x.get('HostName')=='xavier');keys=peer.get('sshHostKeys') or []
if not peer.get('Online') or not keys:raise SystemExit('host identity unavailable')
compiler=args.compiler.resolve(strict=True);source=pathlib.Path(__file__).resolve().parents[2]/'seed/tests/awai152-linux-close-range/native-spawn-probe.kotoba'
assert hashlib.sha256(compiler.read_bytes()).hexdigest()==args.compiler_sha256
archive=io.BytesIO()
with tarfile.open(fileobj=archive,mode='w') as t:
 for name,p in [('compiler',compiler),('source.kotoba',source)]:
  b=p.read_bytes();i=tarfile.TarInfo(name);i.size=len(b);i.mode=0o700 if name=='compiler' else 0o600;t.addfile(i,io.BytesIO(b))
remote=r'''import ctypes,hashlib,io,os,pathlib,resource,subprocess,sys,tarfile,tempfile,time
root=pathlib.Path(tempfile.mkdtemp(prefix='awai-native-spawn-'));data=sys.stdin.buffer.read()
with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as t:
 for n in ('compiler','source.kotoba'):
  p=root/n;p.write_bytes(t.extractfile(n).read());p.chmod(0o700 if n=='compiler' else 0o600)
def limit():resource.setrlimit(resource.RLIMIT_CPU,(3,4));resource.setrlimit(resource.RLIMIT_AS,(8589934592,8589934592));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def run(args,env,fd,extras=(),inject=False):
 def setup():
  os.dup2(fd,3);limit()
  if inject:
   class Filter(ctypes.Structure):_fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint)]
   class Prog(ctypes.Structure):_fields_=[('len',ctypes.c_ushort),('filter',ctypes.POINTER(Filter))]
   allow=Filter(0x06,0,0,0x7fff0000); deny=Filter(0x06,0,0,0x00050001)
   if inject=='fchdir':
    seq=[Filter(0x20,0,0,0),Filter(0x15,0,1,50),deny,allow]
   elif inject=='fcntl':
    seq=[Filter(0x20,0,0,0),Filter(0x15,0,3,25),Filter(0x20,0,0,24),Filter(0x15,0,1,2),deny,allow]
   elif inject=='second':
    seq=[Filter(0x20,0,0,0),Filter(0x15,0,5,436),Filter(0x20,0,0,32),Filter(0x15,0,3,0),Filter(0x20,0,0,16),Filter(0x25,0,1,3),deny,allow]
   else:
    seq=[Filter(0x20,0,0,0),Filter(0x15,0,3,436),Filter(0x20,0,0,32),Filter(0x15,0,1,0),deny,allow]
   ins=(Filter*len(seq))(*seq)
   prog=Prog(len(ins),ins);libc=ctypes.CDLL(None,use_errno=True)
   if libc.prctl(38,1,0,0,0)!=0 or libc.prctl(22,2,ctypes.byref(prog),0,0)!=0:os._exit(119)
 p=subprocess.Popen([str(x) for x in args],cwd=root,env=env,pass_fds=tuple(set((fd,)+extras)),preexec_fn=setup,stdout=subprocess.PIPE,stderr=subprocess.PIPE);start=time.monotonic();peak=0
 while p.poll() is None:
  if time.monotonic()-start>12:p.kill();break
  try:
   for l in pathlib.Path('/proc/'+str(p.pid)+'/status').read_text().splitlines():
    if l.startswith('VmRSS:'):peak=max(peak,int(l.split()[1]));break
   if peak>204800:p.kill();break
  except FileNotFoundError:pass
  time.sleep(.05)
 out,err=p.communicate();return p.returncode,out,err,peak
fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY);env=dict(os.environ,KEXE_CAP_RESOURCES_35=str(root),KEXE_CPU_SECONDS='3',KEXE_WALL_SECONDS='10')
r=run([root/'compiler','compile',root/'source.kotoba','--target','aarch64-linux','--output',root/'probe.elf','--format','static'],env,fd)
if r[0] or r[2]:raise RuntimeError(('compile',r[0],r[2][-300:]))
(root/'probe.elf').chmod(0o700);print('image',hashlib.sha256((root/'probe.elf').read_bytes()).hexdigest(),'compile_peak_kib',r[3],flush=True)
for mode in ('ok','missing','denied','fcntl','fchdir','second'):
 scope=root/mode;scope.mkdir();base=os.open('/dev/null',os.O_RDONLY);os.dup2(base,50);os.dup2(base,200);os.close(base)
 env=dict(os.environ,KEXE_ALLOW='20,35,37,38,39',KEXE_CAP_RESOURCES_20='/definitely-missing-awai' if mode=='missing' else '/bin/sh',KEXE_CAP_RESOURCES_35=str(scope),KEXE_SPAWN_ENV='AWAI_SCOPE',AWAI_SCOPE=str(scope),KEXE_CPU_SECONDS='3',KEXE_WALL_SECONDS='10')
 scopefd=os.open(scope,os.O_RDONLY|os.O_DIRECTORY)
 r=run([root/'probe.elf','missing' if mode=='missing' else 'normal'],env,scopefd,(50,200),mode if mode in ('denied','fcntl','fchdir','second') else False);os.close(scopefd);os.close(50);os.close(200);marker=(scope/'marker').exists()
 print('case',mode,'exit',r[0],'stdout',repr(r[1][-120:]),'stderr',repr(r[2][-200:]),'marker',marker,'peak_kib',r[3],flush=True)
 if mode=='ok':assert r[0]==0 and r[1]==b'0\nok' and not r[2] and marker
 elif mode=='missing':assert r[0]==126 and b'spawn/exec-failed' in r[2] and not marker
 elif mode=='fchdir':assert r[0]==126 and b'spawn/setup-failed' in r[2] and not marker
 else:assert r[0]==126 and b'spawn/isolation-unavailable' in r[2] and not marker
print('artifact-directory',root,flush=True)
'''
with tempfile.TemporaryDirectory(prefix='awai-xavier-hostkeys-') as d:
 known=pathlib.Path(d)/'known';known.write_text(''.join('xavier '+k+'\n' for k in keys if k.startswith(('ssh-ed25519 ','ssh-rsa ','ecdsa-sha2-nistp256 ')) and '\n' not in k));known.chmod(0o600)
 cmd=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=xavier','-o','UserKnownHostsFile='+str(known),'-o','GlobalKnownHostsFile=/dev/null','-o','HostName='+peer['TailscaleIPs'][0],'xavier@xavier','/usr/bin/python3 -c '+shlex.quote(remote)]
 r=subprocess.run(cmd,input=archive.getvalue(),capture_output=True,timeout=50);print('remote exit',r.returncode);print(r.stdout.decode(errors='replace')[-1800:]);print(r.stderr.decode(errors='replace')[-500:])
 if r.returncode: raise SystemExit(r.returncode)
