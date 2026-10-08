"""Author copied diagnostic SOURCE only. Never execute compiler/native/process APIs."""
from pathlib import Path
import hashlib,json,re
R=Path('/Users/junkawasaki/github/wt/amu-seed17'); W=Path('/Users/junkawasaki/github/workspaces/codex'); O=Path(__file__).parent
manifest=R/'seed/MANIFEST'; paths=[R/x.strip() for x in manifest.read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
assert len(paths)==16
base=(R/'seed/41-a64gen.kotoba').read_text()
def form_span(text,name):
    start=text.index('(defn- '+name+' ');depth=0;quoted=False;escaped=False;comment=False
    for i in range(start,len(text)):
        c=text[i]
        if comment:
            if c=='\n':comment=False
            continue
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
            continue
        if c==';':comment=True
        elif c=='"':quoted=True
        elif c=='(':depth+=1
        elif c==')':
            depth-=1
            if depth==0:return start,i+1
    raise ValueError(name)
helpers=''';; Readonly compiler diagnostic; no M/G writes, no predicate re-evaluation.
(defn- ct-print [tag :string xs :vector-i64] :i64
 (let [head (io-out tag)
       body (loop [j 0] (if (= j (vector-count xs)) 0
         (let [v (io-out (string-concat " " (string-from-i64 (vector-at xs j))))] (recur (inc j)))))]
  (io-out "\\n")))
(defn- ct-ready [M :vector-i64] :bool
 (and (= (vector-at M MM-ERR) 0)
      (> (vector-at M MM-SIR-N) 1) (<= (vector-at M MM-SIR-N) 32768)
      (> (vector-at M MM-FN-N) 1) (<= (vector-at M MM-FN-N) 1024)
      (> (vector-at M MM-CODE-N) 0) (<= (vector-at M MM-CODE-N) 131072)
      (> (vector-at M MM-FIX-N) 0) (<= (vector-at M MM-FIX-N) 16384)))
(defn- ct-call-done [M :vector-i64 xs :vector-i64] :vector-i64
 (if (not (ct-ready M)) M
 (let [a (ct-print "CTCALL" xs)
       b (ct-print "CTCALL-END" [(vector-at xs 0) (vector-at xs 4)
          (vector-at M MM-CODE-N) (vector-at M MM-FIX-N)
          (gn-g M gn-f-leaf) (gn-g M gn-f-fb) (gn-g M gn-f-ctx) (vector-at M MM-ERR)
          (gn-g M gn-f-vmode) (gn-g M gn-f-vslot) (gn-g M gn-f-h)])] M)))
(defn- ct-dump [M :vector-i64 phase :i64] :i64
 (if (not (ct-ready M)) (ct-print "CTHOLD" [phase (vector-at M MM-ERR)])
  (let [h (ct-print "CTTABLES" [phase (vector-at M MM-SIR-N) (vector-at M MM-FN-N)
             (vector-at M MM-CODE-N) (vector-at M MM-FIX-N)])
        s (loop [j 1] (if (= j (vector-at M MM-SIR-N)) 0
             (let [v (ct-print "CTSIR" [phase j (gn-op M j) (gn-sir M j IF-A) (gn-sir M j IF-B) (gn-sir M j IF-C)])] (recur (inc j)))))
        f (loop [j 1] (if (= j (vector-at M MM-FN-N)) 0
             (let [v (loop [k 0] (if (= k 16) 0 (let [w (ct-print "CTFN" [phase j k (gn-fnf M j k)])] (recur (inc k)))))] (recur (inc j)))))
        c (if (= phase 0) 0 (loop [j 0] (if (= j (vector-at M MM-CODE-N)) 0
             (let [v (ct-print "CTCODE" [j (vector-at M (+ MM-CODE-BASE j))])] (recur (inc j))))))
        x (if (= phase 0) 0 (loop [j 1] (if (= j (vector-at M MM-FIX-N)) 0
             (let [v (loop [k 0] (if (= k MM-FIX-W) 0
                   (let [w (ct-print "CTFIX" [j k (vector-at M (+ MM-FIX-BASE (* j MM-FIX-W) k))])] (recur (inc k)))))] (recur (inc j))))))]
    (ct-print "CTDUMP-END" [phase 1]))))
'''
instrumented=base
edits=[]
def replace_form(name,new):
    global instrumented
    a,b=form_span(instrumented,name);old=instrumented[a:b];edits.append({'name':name,'old':old,'new':new});instrumented=instrumented[:a]+new+instrumented[b:]
a,b=form_span(base,'gn-op-call');old=base[a:b]
new=old.replace('dag (di-admit M i f t n)]','dag (di-admit M i f t n) start (vector-at M MM-CODE-N) fix (vector-at M MM-FIX-N) leaf (gn-g M gn-f-leaf) frame (gn-g M gn-f-fb) ctx (gn-g M gn-f-ctx)]')
arms=[('(gn-call-affine-reader M i t f reader)',1),('(gn-call-scalar-mask M i t mask)',2),('(gn-call-clamp M i f t q)',3),('(gn-call-mask-writer M t)',4),('(gn-call-sign M i t w)',5),('(di-call M i f t n dag)',7),('(gn-call-generic M i f t n)',8)]
for expr,arm in arms:
    assert new.count(expr)==1;new=new.replace(expr,f'(ct-call-done {expr} [i f t n {arm} start fix leaf frame ctx])')
expr='(if (= slot 1) (gn-gs M1 gn-f-h (inc t)) (gn-op-rt M1 i slot t n))';assert new.count(expr)==1
new=new.replace(expr,f'(ct-call-done {expr} [i f t n 6 start fix leaf frame ctx])');replace_form('gn-op-call',new)
a,b=form_span(base,'gn-call-generic');old=base[a:b]
new=old.replace(' (cond\n',' (let [start (vector-at M MM-CODE-N) fix (vector-at M MM-FIX-N) leaf (gn-g M gn-f-leaf) frame (gn-g M gn-f-fb) ctx (gn-g M gn-f-ctx)]\n (cond\n',1)
new=new.replace('(gn-op-tail-call M f t n)','(ct-call-done (gn-op-tail-call M f t n) [i f t n 9 start fix leaf frame ctx])',1)
new=new.replace('    (-> M\n','    (ct-call-done (-> M\n',1)
assert new.endswith('(gn-take i t 0))))');new=new[:-len('(gn-take i t 0))))')]+'(gn-take i t 0)) [i f t n 10 start fix leaf frame ctx]))))'
replace_form('gn-call-generic',new)
a,b=form_span(base,'gn-loop');old=base[a:b]
new=old.replace('(let [M1 (gn-ins M i (gn-op M i))','(let [start (vector-at M MM-CODE-N) fix (vector-at M MM-FIX-N) op (gn-op M i)\n          mode (gn-g M gn-f-vmode) slot (gn-g M gn-f-vslot) ctx (gn-g M gn-f-ctx) height (gn-g M gn-f-h)\n          M1 (gn-ins M i op)',1)
new=new.replace('k (gn-g M1 gn-f-skip)]','k (gn-g M1 gn-f-skip)\n          observed (if (ct-ready M1) (ct-print "CTEMIT" [i op start (vector-at M1 MM-CODE-N) fix (vector-at M1 MM-FIX-N) k (gn-g M1 gn-f-leaf) (gn-g M1 gn-f-fb) (gn-g M1 gn-f-fuel) (gn-g M1 gn-f-freg) (gn-g M1 gn-f-ctx) (vector-at M1 MM-ERR) mode slot ctx height (gn-g M1 gn-f-vmode) (gn-g M1 gn-f-vslot) (gn-g M1 gn-f-h)]) 0)]',1)
replace_form('gn-loop',new)
a,b=form_span(base,'gn-run-open');old=base[a:b]
new=old.replace('M3 (if (= (vector-at M2 MM-ERR) 0)','before (ct-dump M2 0)\n        M3 (if (= (vector-at M2 MM-ERR) 0)',1)
new=new.replace('n (vector-at M3 MM-CODE-N)]','n (vector-at M3 MM-CODE-N) after (ct-dump M3 1)]',1);replace_form('gn-run-open',new)
pos=instrumented.index('(defn- gn-op-fn2 ');instrumented=instrumented[:pos]+helpers+'\n'+instrumented[pos:]
# Author-time exact reversion proves all source changes are the declared diagnostic insertions.
reverse=instrumented.replace(helpers+'\n','',1)
for e in reversed(edits):assert reverse.count(e['new'])==1;reverse=reverse.replace(e['new'],e['old'],1)
assert reverse==base
def balance(s):
    # Parsing quoted strings/comments, not type acceptance; exact parenthesis invariant.
    depth=0;quote=False;esc=False;comment=False
    for c in s:
        if comment:
            if c=='\n':comment=False
        elif quote:
            if esc:esc=False
            elif c=='\\':esc=True
            elif c=='"':quote=False
        elif c==';':comment=True
        elif c=='"':quote=True
        elif c=='(':depth+=1
        elif c==')':depth-=1;assert depth>=0
    assert depth==0 and not quote
balance(instrumented)
(O/'41-observer.kotoba').write_text(instrumented);(O/'observer-helpers.kotoba').write_text(helpers)
unity=''.join((instrumented if p.name=='41-a64gen.kotoba' else p.read_text())+'\n' for p in paths)
baseline=''.join(p.read_text()+'\n' for p in paths)
(O/'unity-observer.kotoba').write_text(unity);(O/'unity-baseline.kotoba').write_text(baseline)
(O/'declared-edits.json').write_text(json.dumps(edits,indent=2)+'\n')
inputs=paths+[manifest,W/'vector-typed-observer-native-v8/unity-observer.kotoba',W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width/helpers.kotoba',W/'vector-leaf-straight-read-cache-full19-selfbuild40-plan-v1-native-controls/run-outputs/G3.bin',R/'bench/embench/batch-ports/statemate.kotoba',R/'bench/embench/batch-ports/nsichneu.kotoba']
pins={str(p):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs}
(O/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
(O/'source-report.json').write_text(json.dumps({'schema':'CONTINUATION_OBSERVER_SOURCE/v1','status':'AUTHOR_SOURCE_ONLY_UNCOMPILED_NO_GO','manifestModules':16,'exactReverseEqualsCurrent41':True,'parenthesesBalancedOnly':True,'diagnosticTargetMGWrites':0,'admissionPredicatesReevaluated':0,'emitterControlOrderChanged':False,'originalCallArmsRetained':10,'fullIdentityStillRequiresNative':True,'compilerNativeSSHCalls':0,'productEdits':False,'resourceDriverReady':False,'keyExclusionsApproved':[],'C2':False,'fixedpointQualified':False,'performanceQualified':False},indent=2)+'\n')
print('Authored copied SOURCE only; exact reverse/balance passed')
