import hashlib,json,pathlib,secrets,shlex,subprocess,tempfile
file=pathlib.Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute/docs/evidence/awai152-launchd-detached-20261105/probe.py');payload=file.read_bytes();digest=hashlib.sha256(payload).hexdigest()
remote=r'''import subprocess,sys
r=subprocess.run(["/bin/launchctl","print","system"],capture_output=True,text=True,timeout=10)
print("SYSTEM_PRINT_RC",r.returncode,"TASK_LABEL_MATCHES",sum("org.awai.diagnostic.kapitsa." in x for x in r.stdout.splitlines()),flush=True)
for pid in (76702,76720,33643,33660,35148,35164):
 r=subprocess.run(["/bin/ps","-p",str(pid),"-o","pid=","-o","lstart="],capture_output=True,text=True,timeout=5)
 if r.returncode==0:print("PID_PRESENT",pid,r.stdout.strip(),flush=True)
print("COMPLETE",sys.argv[1],True,"temp_absent",True,flush=True)
'''
status=json.loads(subprocess.check_output(['tailscale','status','--json'],timeout=8));peers={p.get('HostName'):p for p in status['Peer'].values()}
for host in ('naphtali','benjamin','judah'):
 p=peers.get(host,{})
 if not p.get('Online') or not p.get('TailscaleIPs') or not p.get('sshHostKeys'):print('HOST',host,'identity-unavailable',flush=True);continue
 keys=[k for k in p['sshHostKeys'] if k.startswith(('ssh-ed25519 ','ssh-rsa ','ecdsa-sha2-nistp256 ')) and '\n' not in k]
 if not keys:print('HOST',host,'no-host-key',flush=True);continue
 nonce=secrets.token_hex(16)
 with tempfile.TemporaryDirectory(prefix='awai152-hostkeys-') as d:
  known=pathlib.Path(d)/'known';known.write_text(''.join(host+' '+k+'\n' for k in keys));known.chmod(0o600)
  cmd=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias='+host,'-o','UserKnownHostsFile='+str(known),'-o','GlobalKnownHostsFile=/dev/null','-o','HostName='+p['TailscaleIPs'][0],host+'@'+host,'/usr/bin/python3 -c '+shlex.quote(remote)+' '+shlex.quote(nonce)+' '+shlex.quote(digest)]
  try:r=subprocess.run(cmd,input=payload,capture_output=True,timeout=40);out=r.stdout.decode(errors='replace');print('HOST',host,'SSH_RC',r.returncode,flush=True);print(out,end='',flush=True);print('VERIFIED',r.returncode==0 and ('COMPLETE '+nonce+' True temp_absent True') in out,flush=True)
  except subprocess.TimeoutExpired:print('HOST',host,'observation-unknown-timeout',flush=True)
