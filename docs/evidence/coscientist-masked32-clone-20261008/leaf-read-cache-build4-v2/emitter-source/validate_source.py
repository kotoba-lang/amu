"""Source-only lexical/exact-reversal plus bounded independent linear-origin/frame controls."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
P=json.loads((D/'preregistration.json').read_text());B=Path(P['inputPins'][0]['path']).parent
H=(D/'helpers.kotoba').read_text()
# Exact old graph construction, with only separate name and final backedge predicate different.
a=H.index('(defn- lc-build ');b=H.index('\n(defn- lc-assign ',a)
original=(B/'41-sr-on.kotoba').read_text();x=original.index('(defn- sc-build ');y=original.index('\n;; Iterative DFS',x)
assert H[a:b].replace('(defn- lc-build ','(defn- sc-build ').replace('(if (>= reads 2) S (sc-fail S))','(if (and (>= reads 2) (> backs 0)) S (sc-fail S))').strip()==original[x:y].strip()
def balanced(t):
 stack=[];q=False;e=False
 for line in t.splitlines():
  for c in line:
   if q:
    if e:e=False
    elif c=='\\':e=True
    elif c=='"':q=False
    continue
   if c==';':break
   if c=='"':q=True
   elif c in '([{':stack.append(c)
   elif c in ')]}':assert stack and stack.pop()==dict(zip(')]}','([{'))[c]
 assert not stack and not q
for r in json.loads((D/'reversal.json').read_text())['variants']:
 p=D/r['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'];balanced(p.read_text())
balanced(H)
# Independent reference on this deliberately linear subset: every handle producer
# must be most recent LGET of chosen slot; selected writes must copy that same root.
def origin_ok(body,slot=1,budget=131072):
 temps={};reads=0
 for op,a,b,c in body:
  budget-=1
  if budget<0:return False
  if op==4:temps[a]=b if b==slot else None
  elif op==3:temps[a]=None
  elif op in (6,7,8):
   valid=(op==6 and 1<=a<=10)or(op==7 and 1<=a<=5)or(op==8 and 1<=a<=2)
   if not valid:return False
   temps[b]=None
  elif op==5:
   if a==slot and temps.get(b)!=slot:return False
  elif op==14:
   if a!=176 or c!=2 or not 0<=b<=5 or temps.get(b)!=slot:return False
   reads+=1;temps[b]=None
  elif op in (18,19):pass
  else:return False
 return reads>=2
positive=[(18,0,0,0),(4,0,1,0),(3,1,0,0),(14,176,0,2),(4,1,1,0),(3,2,1,0),(14,176,1,2),(6,1,0,0),(19,0,0,0)]
assert origin_ok(positive);checks=1
copy=[(4,0,1,0),(5,1,0,0)]+positive
assert origin_ok(copy);checks+=1
single=positive[:4]+[(19,0,0,0)];assert not origin_ok(single);checks+=1
changed=[(3,0,123,0),(5,1,0,0)]+positive;assert not origin_ok(changed);checks+=1
for bad in [(13,1,0,1),(23,1,0,1),(15,1,0,0),(17,0,0,0),(14,177,0,2),(14,208,0,2),(9,2,0,0),(10,2,0,0),(11,0,2,0),(12,0,2,0),(6,16,0,0),(6,11,0,0),(7,8,0,0),(8,16,0,0)]:
 assert not origin_ok(positive[:1]+[bad]+positive[1:]);checks+=1
wrong=positive[:];wrong[1]=(4,0,2,0);assert not origin_ok(wrong);checks+=1
assert not origin_ok(positive,budget=1);checks+=1
# Entry label uniqueness/no-ingress qualification independent of physical CODE.
def entry_ok(rows,label):
 return sum(op==9 and a==label for op,a,b,c in rows)==1 and not any(op in (10,11,12) and (a if op==10 else b)==label for op,a,b,c in rows)
assert entry_ok([(9,3,0,0)]+positive,3);checks+=1
for rows in ([(9,3,0,0),(10,3,0,0)],[(9,3,0,0),(11,0,3,0)],[(9,3,0,0),(12,0,3,0)],[(9,3,0,0),(9,3,0,0)]):assert not entry_ok(rows,3);checks+=1
# Frame/saved-register ABI invariant: low locals remain r0..6, cache19..21 disjoint;
# saved high regs are restored after arbitrary cache values before caller return.
for ns in range(1,8):
 for dp in range(8):
  frame=((8*(ns+dp+2)+15)//16)*16+32
  assert frame%16==0 and 0<frame<=160 and frame+16<=176
  offsets=[0,8,16];assert max(offsets)+8<=32<=frame
  old={19:0x1234,20:-7,21:2**63-1};stack={o:old[r]for r,o in zip(old,offsets)}
  changed={19:4,20:0x1000,21:1};restored={r:stack[o]for r,o in zip(changed,offsets)}
  assert restored==old and set(range(ns)).isdisjoint(changed);checks+=1
# Source guard/code mapping obligations stay explicit; these are no native claims.
assert '(sc-queries M1 (lc-build M1 i end slot))' in H
assert '(let [M1 (sl-assign M i f np)]' in H
assert '(if (= lc-feature 0) M1' in H
assert '(lc-ingress? M 1 (vector-at M MM-SIR-N) label 0)' in H
(D/'pure-controls.json').write_text(json.dumps({'status':'PASS_BOUNDED_PURE_SOURCE_ORIGIN_AND_FRAME_CONTROLS_ONLY','checks':checks,'exactReverseVariants':4,'lcBuildExactOriginalOtherThanNameAndBackedgePredicate':True,'nativeCalls':0,'limits':'Reference is independent linear-origin model, not executing native sc graph or candidate. Saved-register model is source ABI check, not emitted machine roundtrip. Lexical delimiter check does not establish Kotoba compiler admission.'},indent=2)+'\n')
