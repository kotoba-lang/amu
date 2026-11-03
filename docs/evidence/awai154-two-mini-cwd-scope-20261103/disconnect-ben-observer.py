import hashlib,json,pathlib,shlex,subprocess,sys,uuid
image=pathlib.Path('/private/tmp/awai154-launchd-acl2/probe.macho').read_bytes();expected=hashlib.sha256(image).hexdigest();assert expected=='3d03943226e74c3bf054e9b2cec025b1a220f4d50af7e3e0ee9333d5e66a55fd'
p=next(p for p in json.loads(subprocess.check_output(['tailscale','status','--json']))['Peer'].values() if p.get('HostName')=='benjamin');ip=p['TailscaleIPs'][0];tag=uuid.uuid4().hex;root='/private/tmp/codex-awai154-disconnect-'+tag;label='com.codex.awai154.disconnect.'+tag
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','StrictHostKeyChecking=yes','-o','HostName='+ip,'benjamin']
def execute(code,inputs=None,timeout=28):
 r=subprocess.run(ssh+['python3 -c '+shlex.quote(code)],input=inputs,capture_output=True,timeout=timeout);return {'ssh_exit':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')[-500:]}
setup=r'''import hashlib,json,os,pathlib,plistlib,shutil,subprocess,sys
root=pathlib.Path(ROOT);label=LABEL;data=sys.stdin.buffer.read(100000);assert hashlib.sha256(data).hexdigest()==EXPECTED
os.mkdir(root,0o700);loaded=False
try:
 binary=root/'probe.macho';binary.write_bytes(data);os.chmod(binary,0o700);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(binary)],check=True,capture_output=True,timeout=8);scope=root/'scope';scope.mkdir(mode=0o700);(scope/'inside').write_text('synthetic-payload');plist=root/'job.plist'
 with plist.open('xb') as f:plistlib.dump({'Label':label,'ProgramArguments':[str(binary),'A','/inside'],'WorkingDirectory':str(scope),'StartInterval':15,'LaunchOnlyOnce':True,'LimitLoadToSessionType':'Background','ProcessType':'Background','HardResourceLimits':{'CPU':3},'StandardOutPath':str(root/'job.out'),'StandardErrorPath':str(root/'job.err')},f)
 r=subprocess.run(['/bin/launchctl','load','-S','Background',str(plist)],capture_output=True,text=True,timeout=8)
 if r.returncode:raise RuntimeError('load '+r.stderr[:200])
 loaded=True;output=root/'job.out';before=output.exists() and output.read_bytes()!=b'';print(json.dumps({'setup':'loaded','output_before_disconnect':before}),flush=True)
except Exception:
 if loaded:subprocess.run(['/bin/launchctl','unload','-S','Background',str(root/'job.plist')],capture_output=True,timeout=8)
 shutil.rmtree(root);raise
'''
observe=r'''import json,os,pathlib,re,subprocess,time
root=pathlib.Path(ROOT);label=LABEL;report={'exists':root.exists(),'ran':False,'exit':None};out=root/'job.out'
for _ in range(100):
 if not root.exists():break
 q=subprocess.run(['/bin/launchctl','list',label],capture_output=True,text=True,timeout=4);m=re.search(r'"LastExitStatus"\s*=\s*(\d+)',q.stdout)
 if m:
  raw=int(m.group(1));report['exit']=os.WEXITSTATUS(raw) if os.WIFEXITED(raw) else -1
 data=out.read_bytes() if out.exists() else b''
 if report['exit']==0 and data==b'\0FS2\0synthetic-payload\n':report['ran']=True;break
 time.sleep(.25)
print(json.dumps(report),flush=True)
'''
cleanup=r'''import json,pathlib,shutil,subprocess
root=pathlib.Path(ROOT);label=LABEL;plist=root/'job.plist';result={'root_present':root.exists()}
if plist.exists():
 q=subprocess.run(['/bin/launchctl','unload','-S','Background',str(plist)],capture_output=True,text=True,timeout=8);result['unload_exit']=q.returncode
q=subprocess.run(['/bin/launchctl','list',label],capture_output=True,text=True,timeout=5);result['label_absent']=q.returncode!=0
if result['label_absent'] and root.exists():shutil.rmtree(root)
result['temp_removed']=not root.exists();print(json.dumps(result),flush=True)
'''
def fill(s):return 'ROOT='+repr(root)+'\nLABEL='+repr(label)+'\nEXPECTED='+repr(expected)+'\n'+s
try:
 r=execute(fill(setup),image,25);print('setup',json.dumps(r),flush=True)
 if r['stderr'] or not r['stdout'].strip():raise RuntimeError('setup did not yield a clean receipt')
 x=json.loads(r['stdout']);assert x=={'setup':'loaded','output_before_disconnect':False},x
 # The first SSH process has fully exited before starting the observer.
 r=execute(fill(observe),None,32);print('observe',json.dumps(r),flush=True)
 if r['stderr'] or not r['stdout'].strip():raise RuntimeError('observer did not yield clean receipt')
 assert json.loads(r['stdout'])['ran'] is True
finally:
 try:print('cleanup',json.dumps(execute(fill(cleanup),None,20)),flush=True)
 except subprocess.TimeoutExpired:print('cleanup timed out for exact label '+label+' and temp '+root,flush=True)
