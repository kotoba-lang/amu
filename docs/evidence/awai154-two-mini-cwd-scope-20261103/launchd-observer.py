import concurrent.futures,hashlib,json,pathlib,shlex,subprocess
image=pathlib.Path('/private/tmp/awai154-launchd-acl2/probe.macho').read_bytes();expected=hashlib.sha256(image).hexdigest();assert expected=='3d03943226e74c3bf054e9b2cec025b1a220f4d50af7e3e0ee9333d5e66a55fd'
status=json.loads(subprocess.check_output(['tailscale','status','--json']));peers={p['HostName']:p['TailscaleIPs'][0] for p in status['Peer'].values() if p.get('HostName') in ('levi','benjamin') and p.get('TailscaleIPs')}
remote=r'''import hashlib,json,os,pathlib,plistlib,re,shutil,subprocess,sys,tempfile,time,uuid
expected='3d03943226e74c3bf054e9b2cec025b1a220f4d50af7e3e0ee9333d5e66a55fd';data=sys.stdin.buffer.read(100000);assert hashlib.sha256(data).hexdigest()==expected
root=pathlib.Path(tempfile.mkdtemp(prefix='codex-awai154-scope-',dir='/private/tmp'));os.chmod(root,0o700);jobs=[];report={'machine':subprocess.check_output(['hostname','-s'],text=True).strip(),'kernel':subprocess.check_output(['uname','-r'],text=True).strip(),'image_sha256':expected,'cases':{}}
domain='gui/'+str(os.getuid())
try:
 binary=root/'probe.macho';binary.write_bytes(data);os.chmod(binary,0o700);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(binary)],check=True,capture_output=True,timeout=10)
 scope=root/'scope';scope.mkdir(mode=0o700);(scope/'inside').write_text('synthetic-payload');assert scope.stat().st_uid==os.geteuid()
 for name,mode,acl,want in [('private',0o700,False,0),('shared',0o755,False,70),('acl',0o700,True,70)]:
  os.chmod(scope,mode)
  if acl:subprocess.run(['/bin/chmod','+a','everyone allow list,search',str(scope)],check=True,capture_output=True,timeout=5)
  label='com.codex.awai154.mini.'+uuid.uuid4().hex;jobs.append(label);plist=root/(name+'.plist');out=root/(name+'.out')
  with plist.open('xb') as f:plistlib.dump({'Label':label,'ProgramArguments':[str(binary),'A','/inside'],'WorkingDirectory':str(scope),'RunAtLoad':True,'StandardOutPath':str(out),'StandardErrorPath':str(root/(name+'.err'))},f)
  r=subprocess.run(['/bin/launchctl','bootstrap',domain,str(plist)],capture_output=True,text=True,timeout=8)
  if r.returncode:raise RuntimeError('bootstrap '+name+' '+r.stderr[:160])
  seen=None
  for _ in range(50):
   q=subprocess.run(['/bin/launchctl','print',domain+'/'+label],capture_output=True,text=True,timeout=3);m=re.search(r'last exit code = (\d+)',q.stdout)
   if m:seen=int(m.group(1));break
   time.sleep(.1)
  output=out.read_bytes() if out.exists() else b'';report['cases'][name]={'exit':seen,'output_expected':output==(b'\0FS2\0synthetic-payload\n' if want==0 else b'')}
  if seen!=want or not report['cases'][name]['output_expected']:raise RuntimeError('case '+name+' unexpected')
  if acl:subprocess.run(['/bin/chmod','-N',str(scope)],check=True,capture_output=True,timeout=5)
  os.chmod(scope,0o700)
finally:
 subprocess.run(['/bin/chmod','-N',str(root/'scope')],capture_output=True,timeout=5)
 absent=[]
 for label in jobs:
  subprocess.run(['/bin/launchctl','bootout',domain+'/'+label],capture_output=True,timeout=8);q=subprocess.run(['/bin/launchctl','print',domain+'/'+label],capture_output=True,timeout=8);absent.append(q.returncode!=0)
 report['job_cleanup']=all(absent);shutil.rmtree(root);report['temp_removed']=not root.exists();print(json.dumps(report),flush=True)
'''
def run(item):
 name,ip=item;cmd=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','StrictHostKeyChecking=yes','-o','HostName='+ip,name,'python3 -c '+shlex.quote(remote)]
 try:
  p=subprocess.run(cmd,input=image,capture_output=True,timeout=50);return name,p.returncode,p.stdout.decode(errors='replace'),p.stderr.decode(errors='replace')[-300:]
 except subprocess.TimeoutExpired:return name,'timeout','','SSH observer timed out; remote state requires inspection'
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as e:
 for row in e.map(run,peers.items()):print(json.dumps(row),flush=True)
