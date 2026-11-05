import concurrent.futures,hashlib,json,pathlib,shlex,subprocess
image=pathlib.Path('/private/tmp/awai154-launchd-acl2/probe.macho').read_bytes();digest=hashlib.sha256(image).hexdigest();assert digest=='3d03943226e74c3bf054e9b2cec025b1a220f4d50af7e3e0ee9333d5e66a55fd'
peers={p['HostName']:p['TailscaleIPs'][0] for p in json.loads(subprocess.check_output(['tailscale','status','--json']))['Peer'].values() if p.get('HostName') in ('levi',) and p.get('TailscaleIPs')}
remote=r'''import hashlib,json,os,pathlib,plistlib,re,shutil,subprocess,sys,tempfile,time,uuid
expected='3d03943226e74c3bf054e9b2cec025b1a220f4d50af7e3e0ee9333d5e66a55fd';data=sys.stdin.buffer.read(100000);assert hashlib.sha256(data).hexdigest()==expected
root=pathlib.Path(tempfile.mkdtemp(prefix='codex-awai154-background-',dir='/private/tmp'));os.chmod(root,0o700);jobs=[];report={'kernel':subprocess.check_output(['uname','-r'],text=True).strip(),'image_sha256':expected,'cases':{}}
try:
 binary=root/'probe.macho';binary.write_bytes(data);os.chmod(binary,0o700);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(binary)],check=True,capture_output=True,timeout=8);scope=root/'scope';scope.mkdir(mode=0o700);(scope/'inside').write_text('synthetic-payload')
 for name,mode,acl,want in [('private',0o700,False,0),('shared',0o755,False,70),('acl',0o700,True,70)]:
  os.chmod(scope,mode)
  if acl:subprocess.run(['/bin/chmod','+a','everyone allow list,search',str(scope)],check=True,capture_output=True,timeout=5)
  label='com.codex.awai154.background.'+uuid.uuid4().hex;plist=root/(name+'.plist');jobs.append((label,plist));out=root/(name+'.out')
  with plist.open('xb') as f:plistlib.dump({'Label':label,'ProgramArguments':[str(binary),'A','/inside'],'WorkingDirectory':str(scope),'RunAtLoad':True,'LimitLoadToSessionType':'Background','StandardOutPath':str(out),'StandardErrorPath':str(root/(name+'.err'))},f)
  r=subprocess.run(['/bin/launchctl','load','-S','Background',str(plist)],capture_output=True,text=True,timeout=8)
  if r.returncode:raise RuntimeError('load '+name+' '+r.stderr[:150])
  seen=None
  for _ in range(60):
   q=subprocess.run(['/bin/launchctl','list',label],capture_output=True,text=True,timeout=3);m=re.search(r'"LastExitStatus"\s*=\s*(\d+)',q.stdout)
   if m:
    raw=int(m.group(1));seen=os.WEXITSTATUS(raw) if os.WIFEXITED(raw) else -1
   data=out.read_bytes() if out.exists() else b''
   if seen==want and data==(b'\0FS2\0synthetic-payload\n' if want==0 else b'') and out.exists():break
   time.sleep(.1)
  data=out.read_bytes() if out.exists() else b'';ok=seen==want and out.exists() and data==(b'\0FS2\0synthetic-payload\n' if want==0 else b'');report['cases'][name]={'exit':seen,'expected':ok}
  if acl:subprocess.run(['/bin/chmod','-N',str(scope)],check=True,capture_output=True,timeout=5)
  if not ok:raise RuntimeError('unexpected '+name+' '+str(seen)+' '+repr(data))
  os.chmod(scope,0o700)
finally:
 subprocess.run(['/bin/chmod','-N',str(root/'scope')],capture_output=True,timeout=5);absent=[]
 for label,plist in jobs:
  subprocess.run(['/bin/launchctl','unload','-S','Background',str(plist)],capture_output=True,timeout=8);q=subprocess.run(['/bin/launchctl','list',label],capture_output=True,timeout=5);absent.append(q.returncode!=0)
 report['jobs_absent']=all(absent);shutil.rmtree(root);report['temp_removed']=not root.exists();print(json.dumps(report),flush=True)
'''
def run(item):
 name,ip=item
 try:
  r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','StrictHostKeyChecking=yes','-o','HostName='+ip,name,'python3 -c '+shlex.quote(remote)],input=image,capture_output=True,timeout=45)
  return name,r.returncode,r.stdout.decode(errors='replace'),r.stderr.decode(errors='replace')[-350:]
 except subprocess.TimeoutExpired:return name,'timeout','','remote observer timeout; inspect before retry'
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as e:
 for row in e.map(run,peers.items()):print(json.dumps(row),flush=True)
