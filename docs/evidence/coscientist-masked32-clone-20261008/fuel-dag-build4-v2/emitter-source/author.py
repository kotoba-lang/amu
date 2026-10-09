from pathlib import Path
import json,hashlib,re
D=Path(__file__).parent;P=D.parent/'vector-masked32-shift-orr-emitter-source-v1-native-controls'
def h(b):return hashlib.sha256(b).hexdigest()
def forms(s):
 out=[];stack=[];start=None;string=False;comment=False;escape=False
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
   assert stack and stack.pop()=={')':'(',']':'[','}':'{'}[c],(i,s[max(0,i-80):i+80])
   if not stack:out.append((start,i+1,s[start:i+1]))
 assert not stack and not string;return out
def defn(s,n):
 q=[x for x in forms(s)if re.match(r'\(defn-?\s+'+re.escape(n)+r'\s',x[2])];assert len(q)==1;return q[0]
def main():
 base=(P/'unity-sr-on.kotoba').read_bytes();assert h(base)=='2b00f83cf91e4215882530893281a22d9eb23168e97aff59221867937fe7a207'
 helper=(D/'helpers.kotoba').read_text();forms(helper);reversal={}
 for name,parent in [('unity','unity-sr-on.kotoba'),('41','41-sr-on.kotoba')]:
  old=(P/parent).read_text();a,b,t=defn(old,'gn-op-call');new=t.replace('aes (as-admit M i f t n)]','aes (as-admit M i f t n) charged-dag (if (= df-feature 1) (df-admit M i f t n) 0)]').replace('         :else (gn-call-generic M i f t n))))','         (> charged-dag 0) (df-call M i f t n charged-dag)\n         :else (gn-call-generic M i f t n))))');assert new!=t and 'charged-dag'in new
  for feature in ['off','on']:
   hs=helper.replace('(def df-feature 0)','(def df-feature '+('1'if feature=='on'else'0')+')');s=old[:a]+hs+'\n'+new+old[b:];forms(s);reverse=s.replace(hs+'\n','',1).replace(new,t,1);assert reverse==old
   dst=D/(name+'-df-'+feature+'.kotoba');dst.write_text(s);reversal[dst.name]={'parent':str(P/parent),'parentSHA256':h(old.encode()),'exactReverse':True,'sha256':h(s.encode())}
 (D/'reversal.json').write_text(json.dumps(reversal,indent=2)+'\n')
if __name__=='__main__':main()
