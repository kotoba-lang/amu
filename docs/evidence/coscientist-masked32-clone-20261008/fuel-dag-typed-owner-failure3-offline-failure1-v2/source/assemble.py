"""SOURCE assembly only, parent bytes pinned. No compiler execution."""
from pathlib import Path
import json,hashlib,importlib.util,sys
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;W=D.parent;P=W/'vector-fuel-scalar-dag-source-v1-width/unity-df-on.kotoba';old=P.read_text();assert hashlib.sha256(P.read_bytes()).hexdigest()=='5fde80c8d567b6ce73ec0ce56e3766aef5e37484080a16be4da28923b2be5053'
ns={'__file__':str(W/'vector-fuel-scalar-dag-source-v1-width/author.py'),'__name__':'pinned_parent_source_parser'};parser_bytes=(W/'vector-fuel-scalar-dag-source-v1-width/author.py').read_bytes();assert hashlib.sha256(parser_bytes).hexdigest()=='fdad4af69b606d8e5360875c18839af46ea2f0b3e2d2417f6b0152f6376cabb5';exec(compile(parser_bytes,ns['__file__'],'exec'),ns)
h=(D/'helpers.kotoba').read_text();ns['forms'](h);s=old;replacements=[]
a,b,t=ns['defn'](s,'gn-op-call');new=t.replace('(defn- gn-op-call','(defn- fo-original-call',1)+'\n(defn- gn-op-call [M :vector-i64 i :i64 f :i64 t :i64 n :i64] :vector-i64 (fo-call M i f t n))';s=s[:a]+h+'\n'+new+s[b:];replacements.append((h+'\n'+new,t))
a,b,t=ns['defn'](s,'drv-c5');new=t.replace('(defn- drv-c5','(defn- fo-original-c5',1)+'\n(defn- drv-c5 [M :vector-i64 S :string path :string out :string] :i64\n (let [w (if (fo-enabled) (fo-pre M) 0)] (fo-original-c5 M S path out)))';s=s[:a]+new+s[b:];replacements.append((new,t))
a,b,t=ns['defn'](s,'out-build');new=t.replace('(defn- out-build','(defn- fo-original-build',1)+'\n(defn- out-build [M :vector-i64 S :string] :vector-i64\n (let [result (fo-original-build M S) w (if (fo-enabled) (fo-final result) 0)] result))';s=s[:a]+new+s[b:];replacements.append((new,t))
ns['forms'](s);(D/'unity-observer.kotoba').write_text(s);rev=s
for new,prior in reversed(replacements):assert rev.count(new)==1;rev=rev.replace(new,prior,1)
assert rev==old;(D/'reversal.json').write_text(json.dumps({'exactReverseParent':True,'parentSHA256':hashlib.sha256(old.encode()).hexdigest(),'changedDefinitions':['gn-op-call','drv-c5','out-build'],'helperM_GWrites':0,'ordinaryOriginalCallOnce':True,'newSourceSHA256':hashlib.sha256(s.encode()).hexdigest()},indent=2)+'\n')
