# Test-only loopback peer and process supervision. No external connections.
import os,pathlib,resource,socket,subprocess,threading
p=pathlib.Path('/private/tmp/awai153-darwin-tcp'); fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY);assert fd==3
def limit():resource.setrlimit(resource.RLIMIT_CPU,(3,3))
r=subprocess.run([str(p/'control-packager.macho'),'control.macho','strict'],cwd=p,pass_fds=(fd,),capture_output=True,timeout=5,preexec_fn=limit);assert r.returncode==0,(r.returncode,r.stderr)
os.chmod(p/'control.macho',0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(p/'control.macho')],check=True,capture_output=True)
def run(port,timeout=5):
 try:return subprocess.run([str(p/'control.macho')],input=port.to_bytes(2,'big'),capture_output=True,timeout=timeout,preexec_fn=limit).returncode
 except subprocess.TimeoutExpired:return 'timeout-killed'
for response,expected in ((b'PONG',0),(b'FAIL',1),(b'PO',1)):
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(5);port=listener.getsockname()[1];seen=[]
 def server():
  with listener:
   c,_=listener.accept()
   with c:c.settimeout(3);seen.append(c.recv(4));c.sendall(response)
 t=threading.Thread(target=server);t.start();code=run(port);t.join(6);assert not t.is_alive() and seen==[b'PING'] and code==expected,(seen,code)
 print(response.decode(),code,flush=True)
s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close();code=run(port);print('unused-port',code,flush=True);assert code==1
s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];code=run(port,1);s.close();print('bound-without-listen',code,flush=True);assert code=='timeout-killed'
os.close(fd)
