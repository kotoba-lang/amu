# Test-only: loopback TCP peer, synthetic ports and process supervisor.
import os,pathlib,resource,socket,subprocess,threading,time
p=pathlib.Path('/private/tmp/awai153-connect-deadline');fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY);assert fd==3
def limit():resource.setrlimit(resource.RLIMIT_CPU,(3,3))
r=subprocess.run([str(p/'deadline-packager.macho'),'deadline.macho','strict'],cwd=p,pass_fds=(fd,),capture_output=True,timeout=5,preexec_fn=limit);assert r.returncode==0
os.chmod(p/'deadline.macho',0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(p/'deadline.macho')],check=True,capture_output=True)
def run(port):
 start=time.monotonic();r=subprocess.run([str(p/'deadline.macho')],input=port.to_bytes(2,'big'),capture_output=True,timeout=3,preexec_fn=limit);return r.returncode,round(time.monotonic()-start,3)
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(3);port=listener.getsockname()[1];accepted=[]
def accept():
 with listener:
  c,_=listener.accept();accepted.append(True);c.close()
t=threading.Thread(target=accept);t.start();result=run(port);t.join(4);assert not t.is_alive() and accepted and result[0]==0,(result,accepted);print('listener',result,flush=True)
s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close();result=run(port);assert result[0]==1,result;print('unbound',result,flush=True)
s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];result=run(port);s.close();assert result[0]==2 and result[1]<2,result;print('bound-not-listening',result,flush=True)
r=subprocess.run([str(p/'deadline.macho')],input=b'\x01',capture_output=True,timeout=3,preexec_fn=limit);assert r.returncode==1;print('short-input',r.returncode,flush=True)
os.close(fd)
