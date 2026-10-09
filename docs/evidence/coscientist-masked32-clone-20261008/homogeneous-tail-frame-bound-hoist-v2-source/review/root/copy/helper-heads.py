"""Pure current16 additional-helper head/arity closure; no compiler/operational execution."""
from pathlib import Path
import json,re,hashlib,importlib.util
D=Path(__file__).parent;W=D.parent;R=Path('/Users/junkawasaki/github/wt/amu-seed17')
spec=importlib.util.spec_from_file_location('scanner',W/'shared-frame-currenttyped-observer3-library-closure-author-v1-20261009/diagnose.py');scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
def parse(s):
 ts=re.findall(r';[^\n]*|"(?:\\.|[^"\\])*"|[()\[\]{}]|[^\s()\[\]{};]+',s);ts=[t for t in ts if not t.startswith(';')];i=0
 def one():
  nonlocal i
  t=ts[i];i+=1
  if t in['(','[','{']:
   close={'(':')','[':']','{':'}'}[t];a=[]
   while ts[i]!=close:a.append(one())
   i+=1;return a if t=='('else('vector',a)
  return int(t,0)if re.fullmatch(r'-?[0-9]+|0x[0-9a-fA-F]+',t)else t
 forms=[]
 while i<len(ts):forms.append(one())
 return forms
names=(R/'seed/20-names.kotoba').read_text();table=parse(scanner.form(names,'nm-head-code'))[0][4]
def head(t):
 b=t.encode('ascii');ws=[int.from_bytes(b[k:k+8].ljust(8,b'\0'),'little')for k in[0,8,16]];ws=[x-(1<<64)if x>=1<<63 else x for x in ws];env=dict(zip(['w0','w1','w2'],ws))
 def ev(e):
  if isinstance(e,list):
   assert e[0]=='case',e[0];key=ev(e[1]);a=e[2:]
   for j in range(0,len(a)-1,2):
    keys=a[j]if isinstance(a[j],list)else[a[j]]
    if key in keys:return ev(a[j+1])
   return ev(a[-1])
  return env[e]if e in env else e
 return ev(table)
a=json.loads((W/'tc-original19-remaining10-fixedpoint-source-v4-20261009/source-assembly.json').read_bytes());source=b''.join(Path(D/'41-a64gen-candidate.kotoba'if n=='seed/41-a64gen.kotoba'else p['path']).read_bytes()+b'\n'for n,p in zip(a['modules'],a['modulePins'])).decode()
# Function definitions/parameter counts from actual forms, including source docstrings.
fn={}
for form in parse(source):
 if isinstance(form,list)and form and form[0]in['defn','defn-']:
  ps=[x for x in form[2:]if isinstance(x,tuple)and x[0]=='vector'][:1]
  if not ps:ps=[clause[0]for clause in form[2:]if isinstance(clause,list)and clause and isinstance(clause[0],tuple)and clause[0][0]=='vector']
  assert ps,form[1]
  counts=set()
  for param in ps:
   params=param[1];j=argc=0
   while j<len(params):
    assert isinstance(params[j],str)and not params[j].startswith(':'),(form[1],params);argc+=1;j+=1
    if j<len(params)and(isinstance(params[j],tuple)or isinstance(params[j],str)and params[j].startswith(':')):j+=1
   counts.add(argc)
  fn[form[1]]=counts
rule=(D/'rule.kotoba').read_text();calls=[]
def walk(e,threaded=False):
 if isinstance(e,tuple):
  for x in e[1]:walk(x)
 elif isinstance(e,list)and e:
  h=e[0];assert isinstance(h,str)
  if h in['defn','defn-']:
   for x in e[4:]:walk(x)
   return
  if h in fn:
   argc=len(e)-1+int(threaded);assert argc in fn[h],(h,argc,fn[h]);calls.append({'head':h,'kind':'current16defn','arity':argc})
  else:
   code=head(h);assert code!=0,('unknownhead',h);calls.append({'head':h,'kind':'primary-nm-head-code','code':code})
  if h=='->':
   walk(e[1])
   for x in e[2:]:walk(x,True)
  else:
   for x in e[1:]:walk(x)
for f in parse(rule):walk(f)
assert head('enc-mov')==0 and 'enc-mov'not in fn
assert fn['enc-mov-r']=={2}
# OriginalV2 introduced undefined helper must be detected by the same closed set.
old=(W/'tc-homogeneous-tail-frame-candidate-source-v2-20261009/rule.kotoba').read_text();assert old.count('(enc-mov ')==2
unknown=[]
for h in re.findall(r'\(\s*([A-Za-z0-9!?+*/<>=_.-]+)',old):
 if h not in fn and head(h)==0:unknown.append(h)
assert unknown==['enc-mov','enc-mov']
result={'status':'PASS_PURE_CURRENT16_ADDED_HELPER_HEAD_ARITY_CLOSURE_ONLY','current16DefinitionCount':len(fn),'additionalRuleCallOccurrences':len(calls),'uniqueHeads':sorted({x['head']for x in calls}),'calls':calls,'implicitLibraryHeadsNeeded':[],'unknownHeads':[],'V2UnknownHelperCounterexample':unknown,'primarySources':{str(R/'seed/20-names.kotoba'):hashlib.sha256(names.encode()).hexdigest(),str(R/'seed/40-a64enc.kotoba'):hashlib.sha256((R/'seed/40-a64enc.kotoba').read_bytes()).hexdigest()},'nativeCalls':0,'typeAndLinearityBindingPending':True}
(D/'helper-heads-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'calls':len(calls),'unique':len(result['uniqueHeads']),'unknown':0,'V2counterexample':unknown}))
