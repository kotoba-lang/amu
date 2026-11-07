import hashlib,importlib.util,os,re,shutil,subprocess,tempfile,resource
from pathlib import Path
repo=Path('/Users/junkawasaki/github/workspaces/codex/awai152-darwin-spawn-attribute')
source=Path('/private/tmp/awai152-watch-original.kotoba').read_text();declaration='(ns amu.darwin-watch-reply (:export [darwin-watch-ready? darwin-watch-heartbeat? darwin-watch-exit-class darwin-watch-monitor-step darwin-watch-reply-class]))';assert source.count(declaration)==1
cases=Path('/private/tmp/awai152-watch-original-cases.kotoba').read_text();code='(ns watcher-reply-test (:export [main]))\n'+source.replace(declaration,'')+'\n'+cases+'\n(defn main [] :i64 (if (and (test-darwin-watch-reply) (test-darwin-watch-monitor)) 0 1))\n'
code=code.replace('(defn main []', '(defn test-cross-request-accepted [] :bool\n (let [r (vector-assoc! (dwr-case-request) 3 50)\n       other (-> (dwr-case-request) (vector-assoc! 3 50) (vector-assoc! 24 47))\n       init [0 1 100 20 100] ready (dwr-case-frame r 82 0)\n       s1 (darwin-watch-monitor-step r init "ready" ready -1 false 110 true)\n       foreign (dwr-case-frame other 72 1)\n       s2 (darwin-watch-monitor-step other s1 "heartbeat" foreign -1 false 120 true)]\n  (= (vector-at s2 0) 1)))\n' + '(defn main []').replace('(test-darwin-watch-monitor)) 0 1)', '(test-darwin-watch-monitor) (test-cross-request-accepted)) 0 1)')
compiler=Path('/tmp/codex-amu-1762/seed/bootstrap/aarch64-macos/amu-full-root.macho');packager=Path('/private/tmp/awai154-fs2-darwin-gate/candidate.macho')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,w in [(compiler,'920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6'),(packager,'f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d')]:
 if sha(p)!=w:raise ValueError('pin mismatch')
root=Path(tempfile.mkdtemp(prefix='awai150-meta-',dir='/private/tmp'));fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
if fd!=3:os.dup2(fd,3)
def run(cmd,expected=0):
 r=subprocess.run([str(x) for x in cmd],cwd=root,pass_fds=(3,),capture_output=True,timeout=12,env={'PATH':'/nonexistent'},preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CPU,(3,3)))
 if r.returncode!=expected or r.stderr:raise RuntimeError((r.returncode,r.stdout[-300:],r.stderr[-300:]))
 return r.stdout
def build(name,content):
 (root/(name+'.kotoba')).write_text(content);run([compiler,'compile',name+'.kotoba','--target','aarch64-macos','--output',name+'.kseed']);out=run([compiler,'extract-native',name+'.kseed','--symbol','main','--output',name+'.raw']);m=re.search(rb':offset (\d+), :length (\d+), :arity 0}',out)
 if not m or int(m[2])!=(root/(name+'.raw')).stat().st_size:raise ValueError('extraction mismatch')
 run([packager,name+'-unsigned.macho',name+'.raw','fs2-cli-stdio-general',m[1].decode()]);img=root/(name+'.macho');shutil.copyfile(root/(name+'-unsigned.macho'),img);img.chmod(0o700)
 subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(img)],capture_output=True,check=True);subprocess.run(['/usr/bin/codesign','--verify','--strict',str(img)],capture_output=True,check=True)
 return img
positive=build('positive',code);run([positive]);anchor='(< now observed)';assert code.count(anchor)==1
mut=build('mutant',code.replace(anchor,'(< now last)'));run([mut],1)
print('PASS',hashlib.sha256(code.encode()).hexdigest(),sha(positive),'rollback-mutant-detected')
