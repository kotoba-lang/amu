import hashlib,os,re,resource,shutil,subprocess,tempfile
from pathlib import Path
repo=Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute');compiler=Path('/tmp/codex-amu-1762/seed/bootstrap/aarch64-macos/amu-full-root.macho');packager=Path('/private/tmp/awai-oci-range/candidate.macho')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for path,pin in [(compiler,'920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6'),(packager,'df0e94211a35d84901ebcf2a8620cb653140d957732474ff77bd0cdd5b5bf4c5')]:
 if sha(path)!=pin:raise ValueError('pin mismatch')
src=(repo/'seed/darwin-spawn-attribute.kotoba').read_text();old='(ns amu.darwin-spawn-attribute (:export [darwin-spawn-attribute]))';assert src.count(old)==1;src=src.replace(old,'(ns attr-test (:export [main]))')
fixture=(repo/'seed/tests/awai152-darwin-spawn/attribute-emitter.kotoba').read_text().replace('(darwin-spawn-attribute "25G332" 64 false)','(darwin-spawn-attribute "25G332" 256 true)');code=src+'\n'+fixture
with tempfile.TemporaryDirectory(prefix='awai152-attr-native-',dir='/private/tmp') as d:
 root=Path(d);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
 if fd!=3:os.dup2(fd,3)
 def run(cmd):
  x=subprocess.run([str(q) for q in cmd],cwd=root,pass_fds=(3,),capture_output=True,timeout=12,env={'PATH':'/nonexistent'},preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CPU,(3,3)))
  if x.returncode or x.stderr:raise RuntimeError((x.returncode,x.stdout[-300:],x.stderr[-300:]))
  return x.stdout
 (root/'a.kotoba').write_text(code);run([compiler,'compile','a.kotoba','--target','aarch64-macos','--output','a.kseed']);out=run([compiler,'extract-native','a.kseed','--symbol','main','--output','a.raw']);m=re.search(rb':offset (\d+), :length (\d+), :arity 0}',out)
 if not m or int(m[2])!=(root/'a.raw').stat().st_size:raise RuntimeError('extract')
 run([packager,'a-unsigned.macho','a.raw','fs2-cli-stdio-general',m[1].decode()]);image=root/'a.macho';shutil.copyfile(root/'a-unsigned.macho',image);image.chmod(0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(image)],check=True,capture_output=True);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(image)],check=True,capture_output=True);run([image]);data=(root/'attributes.bin').read_bytes()
 if len(data)!=248:raise RuntimeError('length')
 expected=bytearray(248);expected[0]=192;expected[56]=1;expected[64:66]=bytes([12,128]);expected[68:72]=b'\xff'*4;expected[72:76]=(256).to_bytes(4,'little');expected[76:80]=(256).to_bytes(4,'little');expected[112:128]=b'\xff'*16
 if data!=expected:raise RuntimeError('independent byte mismatch')
 dest=Path('/private/tmp/awai152-setexec-256-attribute.bin');
 with dest.open('xb') as f:f.write(data)
 dest.chmod(0o600);print('PASS native source',hashlib.sha256(code.encode()).hexdigest(),'image',sha(image),'attribute',sha(dest),flush=True)
