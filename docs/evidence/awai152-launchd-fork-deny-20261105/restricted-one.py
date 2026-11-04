import hashlib,json,pathlib,secrets,shlex,subprocess,tempfile
file=pathlib.Path('/private/tmp/awai152-launchd-sandbox-probe.py');payload=file.read_bytes();digest=hashlib.sha256(payload).hexdigest()
remote=r'''import hashlib,os,pathlib,platform,subprocess,sys,tempfile
b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==sys.argv[2]
with tempfile.TemporaryDirectory(prefix='awai152-launchd-fleet-',dir='/private/tmp') as d:
 p=pathlib.Path(d)/'probe.py';p.write_bytes(b)
 print('OS',platform.mac_ver()[0],platform.machine(),subprocess.check_output(['/usr/bin/sw_vers','-buildVersion'],text=True).strip(),flush=True)
 r=subprocess.run(['/usr/bin/sudo','-n','/usr/bin/python3',str(p)],capture_output=True,text=True,timeout=30)
 print('PROBE_RC',r.returncode,flush=True);print(r.stdout,end='',flush=True)
 if r.stderr:print('PROBE_ERR',r.stderr[-1000:],flush=True)
 ok=r.returncode==0
print('COMPLETE',sys.argv[1],ok,'temp_absent',not pathlib.Path(d).exists(),flush=True)
'''
status=json.loads(subprocess.check_output(['tailscale','status','--json'],timeout=8));peers={p.get('HostName'):p for p in status['Peer'].values()}
for host in ('naphtali',):
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
