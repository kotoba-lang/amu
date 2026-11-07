import hashlib,io,json,pathlib,secrets,shlex,subprocess,tarfile,tempfile
repo=pathlib.Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute')
items={'watch.macho':pathlib.Path('/private/tmp/awai152-ready-artifact-41793197780/public-macos-product/experimental-watch-fixture/watch.macho'),'probe.py':pathlib.Path('/private/tmp/fleet-awai152-native-attr-watch-resume.py'),'attribute.bin':pathlib.Path('/private/tmp/awai152-setexec-256-attribute.bin'),'check-macos-watch-helper.py':repo/'scripts/seed/check-macos-watch-helper.py'}
payload={k:v.read_bytes() for k,v in items.items()};hashes={k:hashlib.sha256(v).hexdigest() for k,v in payload.items()};assert hashes['watch.macho']=='0c7d6496a9b25ca9781152e6046751d259ee67433d87e92fb7d3ce5b04ff6dbf'
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w') as t:
 for name,data in payload.items():
  e=tarfile.TarInfo(name);e.size=len(data);e.mode=0o700 if name=='watch.macho' else 0o600;t.addfile(e,io.BytesIO(data))
remote=r'''import hashlib,io,pathlib,platform,subprocess,sys,tarfile,tempfile
expected=EXPECTED;nonce=sys.argv[1]
with tempfile.TemporaryDirectory(prefix='awai152-setexec-fleet-',dir='/private/tmp') as d:
 root=pathlib.Path(d)
 with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:') as t:
  for name,digest in expected.items():
   b=t.extractfile(name).read();assert hashlib.sha256(b).hexdigest()==digest
   p=root/name;p.write_bytes(b);p.chmod(0o700 if name=='watch.macho' else 0o600)
 for script in ('probe.py',):
  p=subprocess.run(['/usr/bin/python3',str(root/script)],cwd=root,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=15)
  print('SCRIPT',script,'RC',p.returncode,flush=True);print(p.stdout,end='',flush=True)
  if p.returncode or p.stderr:raise RuntimeError('fixture failed '+p.stderr[-800:])
 print('HOST_OS',platform.mac_ver()[0],platform.machine(),subprocess.check_output(['/usr/bin/sw_vers','-buildVersion'],text=True).strip(),flush=True)
print('COMPLETE',nonce,'temp_absent',not root.exists(),flush=True)
'''.replace('EXPECTED',repr(hashes),1)
status=json.loads(subprocess.check_output(['tailscale','status','--json'],timeout=8));peers={p.get('HostName'):p for p in status['Peer'].values()}
for host in ('benjamin','judah'):
 p=peers[host]
 if not p.get('Online') or not p.get('TailscaleIPs') or not p.get('sshHostKeys'):raise RuntimeError(host+' identity unavailable')
 keys=[k for k in p['sshHostKeys'] if k.startswith(('ssh-ed25519 ','ssh-rsa ','ecdsa-sha2-nistp256 ')) and '\n' not in k]
 if not keys:raise RuntimeError(host+' host key unavailable')
 nonce=secrets.token_hex(16)
 with tempfile.TemporaryDirectory(prefix='awai152-hostkeys-') as d:
  known=pathlib.Path(d)/'known';known.write_text(''.join(host+' '+k+'\n' for k in keys));known.chmod(0o600)
  cmd=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias='+host,'-o','UserKnownHostsFile='+str(known),'-o','GlobalKnownHostsFile=/dev/null','-o','HostName='+p['TailscaleIPs'][0],host+'@'+host,'/usr/bin/python3 -c '+shlex.quote(remote)+' '+shlex.quote(nonce)]
  r=subprocess.run(cmd,input=buf.getvalue(),capture_output=True,timeout=40);out=r.stdout.decode(errors='replace');err=r.stderr.decode(errors='replace');print('HOST',host,'SSH_EXIT',r.returncode);print(out,end='')
  if r.returncode or ('COMPLETE '+nonce+' temp_absent True') not in out:raise RuntimeError('unknown or failed host outcome '+err[-1000:])
