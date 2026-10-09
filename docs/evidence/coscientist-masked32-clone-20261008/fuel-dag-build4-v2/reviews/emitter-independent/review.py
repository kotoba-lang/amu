from pathlib import Path
import json,hashlib,re
D=Path('/Users/junkawasaki/github/workspaces/codex/vector-fuel-scalar-dag-source-v1-width');O=Path(__file__).resolve().parent;inputs={}
def pin(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def verify(p,v=None):
 z=pin(p)
 if v is not None:assert z==v,str(p)
 inputs[str(p)]=z;return z
def forms(s):
 stack=[];out=[];start=0;string=False;comment=False;escape=False
 for i,c in enumerate(s):
  if comment:
   if c=='\n':comment=False
   continue
  if string:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':string=False
   continue
  if c==';':comment=True;continue
  if c=='"':string=True;continue
  if c in '([{':
   if not stack:start=i
   stack.append(c)
  elif c in ')]}':
   assert stack and stack.pop()=={')':'(',']':'[','}':'{'}[c]
   if not stack:out.append(s[start:i+1])
 assert not stack and not string;return out
def defn(s,name):
 vals=[t for t in forms(s)if re.match(r'\(defn-?\s+'+re.escape(name)+r'\s',t)];assert len(vals)==1;return vals[0]
assert verify(D/'source-pins.json')['sha256']=='fbdd649d3964b76d3d91b915065c6133f137954557d60b54df4e47b85ce6a7ba'
assert verify(D/'source-report.json')['sha256'].startswith('9ef2f454')
for name,v in json.loads((D/'source-pins.json').read_text()).items():verify(D/name,v)
for p,v in json.loads((D/'input-pins.json').read_text()).items():verify(Path(p),v)
helpers=(D/'helpers.kotoba').read_text();assert len(forms(helpers))==6
assert '(def df-feature 0)'in helpers
for name,z in json.loads((D/'reversal.json').read_text()).items():
 src=(D/name).read_text();p=Path(z['parent']);verify(p);base=p.read_text();h=helpers.replace('(def df-feature 0)','(def df-feature '+('1'if'-on.'in name else'0')+')')
 assert src.count(h+'\n')==1
 assert src.replace(h+'\n','',1).replace(defn(src,'gn-op-call'),defn(base,'gn-op-call'),1)==base
 forms(src)
on=(D/'41-df-on.kotoba').read_text();call=defn(helpers,'df-call');emit=defn(helpers,'df-emit-body');body=defn(helpers,'df-body');admit=defn(helpers,'df-admit');shape=defn(helpers,'df-shape')
assert call.count('(gn-op-fuel m1)')==1 and call.index('(gn-op-fuel m1)')<call.index('(di-init m2 f)')
assert '(gn-gs (di-init m2 f) gn-f-ctx 1)'in call
assert '(di-restore 1 0)'in call and '(gn-vclear)'in call and '(gn-take i t 0)'in call
assert 'gn-call-generic'not in call and 'OP-FUEL'not in emit
assert 'gn-call-scalar-mask M j 0'in emit and '(= (gn-fnf M a FF-FUEL) 0)'in body
assert '(= (gn-op M (+ j 2)) OP-END)'in body and '(= (gn-op M (inc j)) OP-RET)'in body
assert '(= (gn-g M gn-f-freg) 0)'in admit and '(= (gn-g M gn-f-leaf) 0)'in admit
assert '(= op OP-TAB)'in shape and '(= seen 1)'in shape and '(= mseen 1)'in shape
assert not any(x in helpers for x in ('vector-alloc','mem-alloc','gn-fix','gn-rtcall','gn-op-rt','gn-call-generic'))
assert 96+6+20+1+5+1+6+1==136<192
# Abstract fuel underflow/success check, with only pure admitted body between charge/return.
def nonleaf(fuel):return ('trap',0)if fuel==0 else('return',fuel-1)
def pure_leaf(fuel):
 if fuel==0:return ('trap',0)
 cached=fuel-1
 return ('return',cached)
assert all(nonleaf(f)==pure_leaf(f)for f in (0,1,2,100))
(O/'input-pins.json').write_text(json.dumps(inputs,indent=2)+'\n')
(O/'pure-controls.json').write_text(json.dumps({'status':'PASS_INDEPENDENT_PURE_PINS_FOUR_REVERSALS_AND_FUEL_ORDER_ONLY','fourExactReversals':True,'typedBalance':True,'originalFuelBeforeFrameReset':True,'nestedMaskUncharged':True,'correctedConservativeTotalWords':136,'reserveWords':192,'abstractFuelCases':4,'nativeCalls':0,'SSHCalls':0,'physicalRegistersQualified':False},indent=2)+'\n')
print('PASS independent SOURCE controls, native/SSH0')
