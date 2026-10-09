from pathlib import Path
import json,hashlib,sys,importlib.util
sys.dont_write_bytecode=True
D=Path(__file__).parent;W=D.parent;P=W/'vector-fuel-scalar-dag-source-v1-width/unity-df-on.kotoba';s=P.read_text();old=s;assert hashlib.sha256(P.read_bytes()).hexdigest()=='5fde80c8d567b6ce73ec0ce56e3766aef5e37484080a16be4da28923b2be5053'
spec=importlib.util.spec_from_file_location('parent_author',W/'vector-fuel-scalar-dag-source-v1-width/author.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
h=(D/'control-helpers.kotoba').read_text();a.forms(h);lo,hi,t=a.defn(s,'gn-op-call');renamed=t.replace('(defn- gn-op-call','(defn- dc-original-call',1);wrapper='(defn- gn-op-call [M :vector-i64 i :i64 f :i64 t :i64 n :i64] :vector-i64\n (if (and (dc-enabled) (> (df-admit M i f t n) 0)) (dc-check M i f t n) (dc-original-call M i f t n)))';s=s[:lo]+h+'\n'+renamed+'\n'+wrapper+s[hi:]
replacements=[('m1 (mem-alloc m0 (if enlarged newneed oldneed))]','m1 (mem-alloc m0 (if enlarged newneed oldneed))\n       receipt (if (dc-enabled) (dc-print "ALLOC" [b (if enlarged newneed oldneed) (vector-at m1 MM-R0) (vector-at m1 MM-HEAP-TOP) (vector-at m1 MM-R1) (vector-at m1 MM-ERR)]) 0)]'),('(defn- seed-main [] :i64 (drv-main))','(defn- seed-main [] :i64 (if (dc-enabled) (dc-main) (drv-main)))'),('(defn- drv-c5 [M :vector-i64 S :string path :string out :string] :i64\n  (if (= (vector-at M MM-ERR) 0) (drv-c6 (gn-run M) S path out) (drv-fail M path)))','(defn- drv-c5 [M :vector-i64 S :string path :string out :string] :i64\n  (if (dc-enabled) (dc-finish M) (if (= (vector-at M MM-ERR) 0) (drv-c6 (gn-run M) S path out) (drv-fail M path))))')]
patch=json.loads((W/'vector-masked32-shift-orr-native-controls-source-v3-native-controls/mc-diagnostic-return-patch.json').read_bytes());replacements.append((patch['old'],patch['new'].replace('sx-enabled','dc-enabled')))
for x,y in replacements:assert s.count(x)==1;s=s.replace(x,y)
a.forms(s);(D/'unity-component.kotoba').write_text(s)
r=s
for x,y in reversed(replacements):r=r.replace(y,x,1)
r=r.replace(h+'\n'+renamed+'\n'+wrapper,t,1);assert r==old
(D/'reversal.json').write_text(json.dumps({'exactReverseParent':True,'parentSHA256':hashlib.sha256(old.encode()).hexdigest(),'wrappedDefinitions':['gn-op-call','gn-run-open allocation receipt','seed-main','drv-c5','mc-generate sentinel preservation'],'ordinaryPipelineUnchanged':True,'helperInterceptionOnlyOriginalEligibleCall':True,'sentinelNoSecondFallback':True},indent=2)+'\n');print('source assembled')
