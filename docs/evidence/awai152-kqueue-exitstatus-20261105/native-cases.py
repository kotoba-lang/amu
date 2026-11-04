import hashlib,os,re,resource,shutil,subprocess,tempfile
from pathlib import Path
repo=Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute');compiler=Path('/tmp/codex-amu-1762/seed/bootstrap/aarch64-macos/amu-full-root.macho');packager=Path('/private/tmp/awai-oci-range/candidate.macho')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for path,pin in [(compiler,'920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6'),(packager,'df0e94211a35d84901ebcf2a8620cb653140d957732474ff77bd0cdd5b5bf4c5')]:
 if sha(path)!=pin:raise ValueError('pin mismatch')
src=(repo/'seed/darwin-kqueue-event.kotoba').read_text();cases=(repo/'seed/tests/awai152-darwin-kqueue/event-cases.kotoba').read_text();s='(ns status-test (:export [main]))\n'+'\n'.join(x for x in (src+'\n'+cases).splitlines() if not x.startswith('(ns '))+'\n(defn main [] :i64 (if (test-darwin-kqueue-event) 0 1))\n'
needle='(not (= (bit-and (vector-at event 15) 4) 0))';assert s.count(needle)==1
with tempfile.TemporaryDirectory(prefix='awai152-exitstatus-native-',dir='/private/tmp') as d:
 root=Path(d);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
 if fd!=3:os.dup2(fd,3)
 def run(cmd,expected=0):
  x=subprocess.run([str(q) for q in cmd],cwd=root,pass_fds=(3,),capture_output=True,timeout=12,env={'PATH':'/nonexistent'},preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CPU,(3,3)))
  if x.returncode!=expected or x.stderr:raise RuntimeError((x.returncode,x.stdout[-300:],x.stderr[-300:]))
  return x.stdout
 for name,code,expected in [('positive',s,0),('missing-status-mutant',s.replace(needle,'true'),1)]:
  (root/(name+'.kotoba')).write_text(code);run([compiler,'compile',name+'.kotoba','--target','aarch64-macos','--output',name+'.kseed']);out=run([compiler,'extract-native',name+'.kseed','--symbol','main','--output',name+'.raw']);m=re.search(rb':offset (\d+), :length (\d+), :arity 0}',out)
  if not m or int(m[2])!=(root/(name+'.raw')).stat().st_size:raise RuntimeError('extract')
  run([packager,name+'-unsigned.macho',name+'.raw','fs2-cli-stdio-general',m[1].decode()]);image=root/(name+'.macho');shutil.copyfile(root/(name+'-unsigned.macho'),image);image.chmod(0o700);subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(image)],check=True,capture_output=True);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(image)],check=True,capture_output=True);run([image],expected);print(name,'source',hashlib.sha256(code.encode()).hexdigest(),'image',sha(image),flush=True)
