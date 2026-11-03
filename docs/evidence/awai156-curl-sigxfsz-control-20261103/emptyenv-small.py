# One-off guarded diagnostic; only a local synthetic peer and task-owned unit.
import hashlib,json,os,pathlib,shlex,subprocess,tempfile
image=pathlib.Path('/private/tmp/awai156-sigguard-emptyenv.42EWX4QW/guard.elf').read_bytes();digest='b0b57e2fb8859f8eb7a61fd393d134da8799db685c0f743bc6d348df8e3053c4';assert hashlib.sha256(image).hexdigest()==digest
s=json.loads(subprocess.check_output(['tailscale','status','--json']));peer=next(x for x in s['Peer'].values() if x.get('HostName')=='xavier');assert peer.get('Online') and peer.get('sshHostKeys')
remote=r'''import hashlib,json,os,pathlib,resource,socket,subprocess,sys,tempfile,threading,time,uuid
b=sys.stdin.buffer.read(4097);assert len(b)==4096 and hashlib.sha256(b).hexdigest()==DIGEST
unit='awai156-guard-'+uuid.uuid4().hex+'.service';out={};peer={};seen=threading.Event();gate=threading.Event();allow={'overflow':False};report=pathlib.Path('/var/crash/_usr_bin_curl.1000.crash')
def snap():
 try:
  st=report.stat();return (st.st_ino,st.st_size,st.st_mtime_ns,hashlib.sha256(report.read_bytes()).hexdigest())
 except FileNotFoundError:return None
before=snap()
with tempfile.TemporaryDirectory(prefix='awai156-guard-') as d:
 root=pathlib.Path(d);exe=root/'guard';exe.write_bytes(b);exe.chmod(0o700);sock=root/'peer.sock';resp=root/'response';server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.settimeout(8);server.bind(str(sock));server.listen(1)
 def serve():
  try:
   c,_=server.accept();c.settimeout(4);request=b''
   while b'\r\n\r\n' not in request and len(request)<8192:
    data=c.recv(1024)
    if not data:break
    request+=data
   peer['request_seen']=request.startswith(b'GET /test HTTP/');seen.set();gate.wait(2)
   body=b'x'*(4*1024*1024+65536) if allow['overflow'] else b'ok'
   c.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body)).encode()+b'\r\nConnection: close\r\n\r\n'+body);c.close()
  except Exception as e:peer['error']=type(e).__name__
 t=threading.Thread(target=serve,daemon=True);t.start()
 cmd=['/usr/bin/systemd-run','--user','--quiet','--no-block','--unit='+unit,'--property=Type=oneshot','--property=RemainAfterExit=yes','--property=NoNewPrivileges=yes','--property=LimitFSIZE=4M','--property=LimitCORE=0','--property=Environment=AWAI_DIAGNOSTIC_MARKER=present','--property=LimitAS=128M','--property=TimeoutStartSec=8s',str(exe),'--disable','--http1.1','--noproxy','*','--unix-socket',str(sock),'-fsS','--max-time','4','--output',str(resp),'http://localhost/test']
 def state():
  r=subprocess.run(['/usr/bin/systemctl','--user','show',unit,'-p','LoadState','-p','ActiveState','-p','SubState','-p','Result','-p','MainPID','-p','ExecMainStatus'],capture_output=True,text=True,timeout=4);return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=5);out['start_exit']=r.returncode
  if r.returncode==0 and seen.wait(2):
   try:
    st=state();pid=int(st.get('MainPID','0'));assert pid>1;proc=pathlib.Path('/proc')/str(pid);assert (proc/'comm').read_text().strip()=='curl'
    before_id=(proc/'stat').read_text().rsplit(')',1)[1].split()[19];status=(proc/'status').read_text();mask=int(next(x.split()[1] for x in status.splitlines() if x.startswith('SigIgn:')),16)
    line=next(x for x in (proc/'limits').read_text().splitlines() if x.startswith('Max file size'));fields=line.split();soft=int(fields[3]);hard=int(fields[4]);after_id=(proc/'stat').read_text().rsplit(')',1)[1].split()[19]
    out.update(sigxfsz_ignored=bool(mask & (1<<24)),file_soft=soft,file_hard=hard,identity_stable=before_id==after_id);env=(proc/'environ').read_bytes();out['env_empty']=len(env)==0;out['marker_present']=b'AWAI_DIAGNOSTIC_MARKER=present' in env
    allow['overflow']=False
   except (OSError,ValueError,StopIteration,AssertionError,IndexError) as e:out['preflight_error']=type(e).__name__
  else:out['peer_not_ready']=True
  gate.set();deadline=time.monotonic()+7;st={}
  while time.monotonic()<deadline:
   st=state()
   if st.get('SubState') in ('exited','failed') or st.get('LoadState')=='not-found':break
   time.sleep(.1)
  out['overflow_sent']=allow['overflow'];out['state']={k:st.get(k) for k in ('LoadState','ActiveState','SubState','Result','ExecMainStatus')};out['response_size']=resp.stat().st_size if resp.exists() else None
 finally:
  gate.set();st=state()
  if st.get('LoadState')!='not-found':
   x=subprocess.run(['/usr/bin/systemctl','--user','stop',unit],capture_output=True,text=True,timeout=5);out['stop_exit']=x.returncode
   x=subprocess.run(['/usr/bin/systemctl','--user','reset-failed',unit],capture_output=True,text=True,timeout=5);out['reset_exit']=x.returncode
  st=state();out['after']={k:st.get(k) for k in ('LoadState','ActiveState')};t.join(timeout=9);server.close();out['peer']=peer;out['peer_thread_alive']=t.is_alive()
out['task_dir_removed']=not pathlib.Path(d).exists();out['prior_crash_report_unchanged']=(snap()==before)
print(json.dumps(out))'''
remote='DIGEST='+repr(digest)+'\n'+remote
with tempfile.TemporaryDirectory(prefix='awai156-hostkeys-') as d:
 k=pathlib.Path(d)/'known';k.write_text(''.join('xavier '+x+'\n' for x in peer['sshHostKeys']));os.chmod(k,0o600)
 cmd=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=6','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=xavier','-o','UserKnownHostsFile='+str(k),'-o','GlobalKnownHostsFile=/dev/null','-o','HostName='+peer['TailscaleIPs'][0],'xavier@xavier','/usr/bin/python3 -c '+shlex.quote(remote)]
 r=subprocess.run(cmd,input=image,capture_output=True,timeout=28);print('ssh_exit',r.returncode);print(r.stdout.decode());print('stderr_nonempty',bool(r.stderr))
