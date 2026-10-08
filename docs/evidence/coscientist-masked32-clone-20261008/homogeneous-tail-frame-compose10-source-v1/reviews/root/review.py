from pathlib import Path
import json,hashlib,subprocess
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'tc-homogeneous-tail-frame-compose10-source-v1-20261009';D=Path(__file__).resolve().parent
sp=json.loads((S/'source-pins.json').read_bytes());ip=json.loads((S/'input-pins.json').read_bytes());pr=json.loads((S/'preregistration.json').read_bytes())
def rec(p):
 p=Path(p);assert p.is_file()and not p.is_symlink();b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for n,r in sp.items():assert rec(S/n)=={k:r[k]for k in ['bytes','sha256']}
for f,r in ip.items():assert rec(f)=={k:r[k]for k in ['bytes','sha256']}
assert len(sp)==18 and len(ip)==44 and sum(r['bytes']for r in ip.values())==2972160
old=Path(pr['singleEdgeCandidate']['path']).read_text();new=(S/'41-a64gen-candidate.kotoba').read_text()
def form(s):
 a=s.index('(defn- sf-collapse');depth=0;comment=False;string=False;escape=False
 for i in range(a,len(s)):
  c=s[i]
  if comment:
   if c=='\n':comment=False
   continue
  if string:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':string=False
   continue
  if c==';':comment=True
  elif c=='"':string=True
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if depth==0:return a,i+1,s[a:i+1]
 raise AssertionError('incomplete source form')
a,b,x=form(old);aa,bb,y=form(new);assert old[:a]==new[:aa]and old[b:]==new[bb:];assert new.count('(defn')==old.count('(defn');assert '(>= used 10)'in y and '(<= fnn 512)'in y and '(sf-old-fix current 1)'in y
controls=[]
for n in ['helper-heads.py','model.py','compose-model.py','compose-controls.py']:
 r=subprocess.run(['/opt/homebrew/Cellar/python@3.14/3.14.6/Frameworks/Python.framework/Versions/3.14/bin/python3.14',str(S/n)],cwd=S,capture_output=True,check=True);(D/(n+'.stdout')).write_bytes(r.stdout);(D/(n+'.stderr')).write_bytes(r.stderr);controls.append(dict(script=n,returncode=r.returncode))
for n,r in sp.items():assert rec(S/n)=={k:r[k]for k in ['bytes','sha256']}
c=json.loads((S/'compose-controls-result.json').read_bytes());assert len(c['pairs'])==10 and len(c['changes'])==40 and c['expectedNativeSHA256']=='c6d22d3f547832430d7263892e8ddd9697f04317ddc16f76edddde2baf548af2';assert all(c['negatives'].values())
q=dict(status='PASS_ROOT_SOURCE_ONLY_HFT_COMPOSE10_CONDITIONAL_ABI_PREMISES',sourcePinsSHA256=rec(S/'source-pins.json')['sha256'],inputPinsSHA256=rec(S/'input-pins.json')['sha256'],preregistrationSHA256=rec(S/'preregistration.json')['sha256'],candidateSHA256=rec(S/'41-a64gen-candidate.kotoba')['sha256'],sourceFiles=18,inputFiles=44,inputBytes=2972160,onlySfCollapseChanged=True,controls=controls,prospectiveEdges=10,prospectiveWordChanges=40,nativeCalls=0,fullMachineSemanticsQualified=False,generalPrivateABIQualified=False,performanceQualified=False,productAdoptionQualified=False,C2=False,notes=['Current FIX/label closure checked before each mutation; new target is compiler-owned param entry.','SameF/prologue/CODE/FIX/FN counts/publicexports and original fuel words retained.','Symbolic helper opaque composition retains initial shared frame and reloads saved LR each edge.','Current private-stack ownership/helperABI and absence of observable removed stack steps remain premises.','Complete native build/emission/runtime/fixedpoint/performance require fresh separate evidence.'])
(D/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
