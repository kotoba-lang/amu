import concurrent.futures,hashlib,json,pathlib,shlex,subprocess
image=pathlib.Path('/private/tmp/awai154-launchd-acl2/probe.macho').read_bytes();digest=hashlib.sha256(image).hexdigest();assert digest=='3d03943226e74c3bf054e9b2cec025b1a220f4d50af7e3e0ee9333d5e66a55fd'
peers={p['HostName']:p['TailscaleIPs'][0] for p in json.loads(subprocess.check_output(['tailscale','status','--json']))['Peer'].values() if p.get('HostName') in ('levi','benjamin') and p.get('TailscaleIPs')}
remote=r'''import hashlib,json,os,pathlib,resource,shutil,subprocess,sys,tempfile
expected='3d03943226e74c3bf054e9b2cec025b1a220f4d50af7e3e0ee9333d5e66a55fd';data=sys.stdin.buffer.read(100000);assert hashlib.sha256(data).hexdigest()==expected
root=pathlib.Path(tempfile.mkdtemp(prefix='codex-awai154-direct-',dir='/private/tmp'));os.chmod(root,0o700);report={'kernel':subprocess.check_output(['uname','-r'],text=True).strip(),'image_sha256':expected,'cases':{}}
def limit():resource.setrlimit(resource.RLIMIT_CPU,(3,3))
try:
 binary=root/'probe.macho';binary.write_bytes(data);os.chmod(binary,0o700);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(binary)],check=True,capture_output=True,timeout=10)
 scope=root/'scope';scope.mkdir(mode=0o700);(scope/'inside').write_text('synthetic-payload');(root/'outside').write_text('outside-sentinel');(scope/'link').symlink_to(root/'outside');assert scope.stat().st_uid==os.geteuid()
 for name,mode,acl,op,path,want in [('private',0o700,False,'A','/inside',0),('shared',0o755,False,'A','/inside',70),('acl',0o700,True,'A','/inside',70),('traversal',0o700,False,'A','/../outside',-5),('symlink',0o700,False,'A','/link',-5)]:
  os.chmod(scope,mode)
  if acl:subprocess.run(['/bin/chmod','+a','everyone allow list,search',str(scope)],check=True,capture_output=True,timeout=5)
  r=subprocess.run([str(binary),op,path],cwd=scope,capture_output=True,timeout=6,preexec_fn=limit);ok=r.returncode==want and r.stdout==(b'\0FS2\0synthetic-payload\n' if want==0 else b'');report['cases'][name]={'exit':r.returncode,'expected':ok}
  if acl:subprocess.run(['/bin/chmod','-N',str(scope)],check=True,capture_output=True,timeout=5)
  if not ok:raise RuntimeError('unexpected '+name+' exit '+str(r.returncode))
finally:
 subprocess.run(['/bin/chmod','-N',str(root/'scope')],capture_output=True,timeout=5);shutil.rmtree(root);report['temp_removed']=not root.exists();print(json.dumps(report),flush=True)
'''
def run(item):
 name,ip=item
 try:
  r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','StrictHostKeyChecking=yes','-o','HostName='+ip,name,'python3 -c '+shlex.quote(remote)],input=image,capture_output=True,timeout=35)
  return name,r.returncode,r.stdout.decode(errors='replace'),r.stderr.decode(errors='replace')[-300:]
 except subprocess.TimeoutExpired:return name,'timeout','','remote observer timeout'
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as e:
 for row in e.map(run,peers.items()):print(json.dumps(row),flush=True)
