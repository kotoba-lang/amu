"""Finite source/data authoring only. Does not invoke producer, loader, process APIs or setters."""
from pathlib import Path
import hashlib,json
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent
OLD=W/'crc-table-decision-collapse-native-component-v4-portable-env-20261008'
R=Path('/Users/junkawasaki/github/wt/amu-seed17')
H=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=H(b))
def save(n,q): (D/n).write_text(json.dumps(q,indent=2)+'\n')
modules=[line.strip()for line in (R/'seed/MANIFEST').read_text().splitlines()if line.strip()and not line.startswith('#')]
assert len(modules)==16
base=b''.join((R/n).read_bytes()+b'\n'for n in modules)
assert H(base)=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418'
candidate=W/'crc-table-decision-collapse-v2-20261008/41-a64gen-candidate.kotoba'
cb=candidate.read_bytes();assert H(cb)=='3d7c169818cdf0fabc151da98017d3b28bbe38fc3407d9b42921b646520c2aba'
(D/'41-a64gen-candidate.kotoba').write_bytes(cb)
parts={n:(cb if n=='seed/41-a64gen.kotoba'else(R/n).read_bytes()).decode()for n in modules}
on='\n'.join(parts[n]for n in modules)+'\n';assert on.encode()==b''.join((cb if n=='seed/41-a64gen.kotoba'else(R/n).read_bytes())+b'\n'for n in modules)
(D/'unity-candidate.kotoba').write_text(on)
helpers=(OLD/'observer-helpers.kotoba').read_text()
p=parts['seed/41-a64gen.kotoba'];assert p.count('(defn- gn-op-call [')==1 and p.count('(defn- tc-call [')==1
p=p.replace('(defn- tc-call [','(defn- fo-original-tc-call [',1)
tc='''(defn- tc-call [M :vector-i64 i :i64 f :i64 t :i64 base :i64] :vector-i64
 (if (not (and (fo-enabled) (fo-ready M))) (fo-original-tc-call M i f t base)
  (let [start (vector-at M MM-CODE-N) fix (vector-at M MM-FIX-N)
        used (gn-g M di-used) sites (gn-g M di-sites)
        result (fo-original-tc-call M i f t base)
        out (fo-print "TCEMIT" [i f t base (tc-mask M i t) start (vector-at result MM-CODE-N)
              fix (vector-at result MM-FIX-N) used (gn-g result di-used)
              sites (gn-g result di-sites) (vector-at result MM-ERR)])] result)))
'''
p=p.replace('(defn- gn-op-call [',helpers+'\n'+tc+'\n(defn- fo-original-call [',1)
marker='(defn- gn-call-generic [';assert p.count(marker)==1
p=p.replace(marker,'(defn- gn-op-call [M :vector-i64 i :i64 f :i64 t :i64 n :i64] :vector-i64 (fo-call M i f t n))\n'+marker,1)
parts['seed/41-a64gen.kotoba']=p
p=parts['seed/50-out.kotoba'];assert p.count('(defn- out-build [')==1
p=p.replace('(defn- out-build [','(defn- fo-original-build [',1)
p+='\n(defn- out-build [M :vector-i64 S :string] :vector-i64\n (let [result (fo-original-build M S) w (if (fo-enabled) (fo-final result) 0)] result))\n';parts['seed/50-out.kotoba']=p
p=parts['seed/90-drv.kotoba'];assert p.count('(defn- drv-c5 [')==1
p=p.replace('(defn- drv-c5 [','(defn- fo-original-c5 [',1)
p+='\n(defn- drv-c5 [M :vector-i64 S :string path :string out :string] :i64\n (let [w (if (fo-enabled) (fo-pre M) 0)] (fo-original-c5 M S path out)))\n';parts['seed/90-drv.kotoba']=p
(D/'unity-emitter-observer.kotoba').write_text('\n'.join(parts[n]for n in modules)+'\n')
(D/'observer-helpers.kotoba').write_text(helpers)
(D/'observer-tc-call.kotoba').write_text(tc)
(D/'original-input.kotoba').write_bytes((R/'bench/embench/batch-ports/crc32.kotoba').read_bytes())
for n in ['adapter.py','launch-wrapper.py','validate.py']:(D/n).write_bytes((OLD/n).read_bytes())
save('source-assembly.json',{'modules':modules,'modulePins':[pin(R/n)for n in modules], 'manifest':pin(R/'seed/MANIFEST'),'baselineUnity':pin(OLD/'unity-baseline.kotoba'),'candidate41':pin(candidate),'candidateUnity':pin(D/'unity-candidate.kotoba'),'observerUnity':pin(D/'unity-emitter-observer.kotoba'),'sourceRule':'One-off structural algorithm authoring exception, not mechanical refactoring. Product candidate remains exact 3d7c. Observer calls original TC emitter and original gn-op-call once each; printing allocates compiler arena, byteidentity required.'})
