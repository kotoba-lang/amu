"""One-off diagnostic Kotoba SOURCE assembly only; no compiler invocation."""
from pathlib import Path
import re,json,hashlib,difflib
D=Path(__file__).parent;B=Path('/Users/junkawasaki/github/workspaces/codex/tc-homogeneous-tail-frame-compose511-bound-hoist-source-v2-20261009');base=(B/'41-a64gen-candidate.kotoba').read_text();assert hashlib.sha256(base.encode()).hexdigest()=='62644967b69517b11936163a958b70e3ae3f8faeb21be185274aa2a57595f765'
def form(s,name):
 start=s.index('(defn- '+name+' ');tokens=list(re.finditer(r'"(?:\\.|[^"\\])*"|;[^\n]*|[()\[\]]|[^\s()\[\]]+',s[start:]));depth=0
 for t in tokens:
  v=t.group()
  if v.startswith(';'):continue
  if v=='(':depth+=1
  if v==')':
   depth-=1
   if depth==0:return start,start+t.end()
 raise AssertionError('unclosed')
def wrap(s,name,notice):
 a,b=form(s,name);f=s[a:b];body=f.index(' :i64\n')+len(' :i64\n');return s[:a]+f[:body]+' (let [qo-observation '+notice+']\n '+f[body:-1]+')'+')'+s[b:]
s=base
assert s.count("(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 80))")==1
s=s.replace("(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 80))","(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 88))")
s=wrap(s,'gn-ctx-safe','(qo-safe-note M f n depth work)');s=wrap(s,'gn-ctx-scan','(qo-scan-note M j f depth work)')
needle='(gn-gs gn-f-ctx (if (>= (gn-ctx-safe M f n 8 512) 0) 1 0))';assert s.count(needle)==1;s=s.replace(needle,'(qo-top M i f n)')
a,b=form(s,'gn-run-open');old=s[a:b];new=old.replace('        M3 (if (= (vector-at M2 MM-ERR) 0) (gn-loop M2 1) M2)\n        n (vector-at M3 MM-CODE-N)]\n    (gn-put M3 MM-R0 (- n 1)))','        qo-active (= (vector-at M2 MM-ERR) 0)\n        M2q (if qo-active (qo-init M2) M2)\n        M3 (if qo-active (gn-loop M2q 1) M2q)\n        M4 (if qo-active (qo-clean M3) M3)\n        n (vector-at M4 MM-CODE-N)]\n    (gn-put M4 MM-R0 (- n 1)))');assert new!=old;s=s[:a]+new+s[b:]
a=s.index('(defn- gn-ctx-safe ');s=s[:a]+(D/'helpers.kotoba').read_text()+'\n'+s[a:]
(D/'41-observer.kotoba').write_text(s);(D/'observer.patch').write_text(''.join(difflib.unified_diff(base.splitlines(True),s.splitlines(True),fromfile='current62644967',tofile='diagnostic-observer')))
assembly=json.loads((B/'source-assembly.json').read_bytes());parts=[];pins=[]
for r in assembly['modulePins']:
 p=D/'41-observer.kotoba'if r['module']=='seed/41-a64gen.kotoba'else Path(r['path']);b=p.read_bytes();parts.append(b+b'\n');pins.append({'module':r['module'],'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
u=b''.join(parts);(D/'unity-observer.kotoba').write_bytes(u);assert b''.join(Path(r['path']).read_bytes()+b'\n'for r in assembly['modulePins'])==(B/'unity-candidate.kotoba').read_bytes();assembly['modulePins']=pins;assembly['unity']={'path':str(D/'unity-observer.kotoba'),'bytes':len(u),'sha256':hashlib.sha256(u).hexdigest()};assembly['baseUnity']={'path':str(B/'unity-candidate.kotoba'),'bytes':(B/'unity-candidate.kotoba').stat().st_size,'sha256':hashlib.sha256((B/'unity-candidate.kotoba').read_bytes()).hexdigest()};assembly['nativeCalls']=0;(D/'source-assembly.json').write_text(json.dumps(assembly,indent=2)+'\n')
print('observerSOURCE',len(s.encode()),'unity',len(u))
