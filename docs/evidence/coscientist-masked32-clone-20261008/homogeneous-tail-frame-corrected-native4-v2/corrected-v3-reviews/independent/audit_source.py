from pathlib import Path
import json,hashlib,stat,sys
D=Path('/Users/junkawasaki/github/workspaces/codex/tc-homogeneous-tail-frame-candidate-source-v3-20261009');V2=Path(str(D).replace('-v3-','-v2-'));O=Path(__file__).resolve().parent;sys.dont_write_bytecode=True
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes())
def rec(p):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode)and not p.is_symlink();b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for n,r in sp.items():assert rec(D/n)=={k:r[k]for k in ['bytes','sha256']}
for p,r in ip.items():assert rec(p)=={k:r[k]for k in ['bytes','sha256']}
for n in ['rule.kotoba','41-a64gen-candidate.kotoba']:
 old=(V2/n).read_bytes();new=(D/n).read_bytes();assert old.count(b'(enc-mov ')==2 and new==old.replace(b'(enc-mov ',b'(enc-mov-r ')
assert (D/'model.py').read_bytes()==(V2/'model.py').read_bytes()and (D/'model-result.json').read_bytes()==(V2/'model-result.json').read_bytes()
assert (D/'saved-controls.py').read_bytes()==(V2/'saved-controls.py').read_bytes()and (D/'saved-controls-result.json').read_bytes()==(V2/'saved-controls-result.json').read_bytes()
s=(D/'helper-heads.py').read_text();s=s[:s.index("(D/'helper-heads-result.json').write_text")];g={'__file__':str(D/'helper-heads.py'),'__name__':'pure_helper_no_writer'};exec(compile(s,str(D/'helper-heads.py'),'exec'),g);assert g['result']==json.loads((D/'helper-heads-result.json').read_bytes())
summary={'sourceFiles':len(sp),'sourceLogicalBytes':sum(x['bytes']for x in sp.values()),'inputFiles':len(ip),'inputLogicalBytes':sum(x['bytes']for x in ip.values()),'sourcePins':rec(D/'source-pins.json'),'candidate':rec(D/'41-a64gen-candidate.kotoba'),'preregistration':rec(D/'preregistration.json'),'freeze':rec(D/'freeze.json'),'helperClosure':g['result'],'exactDeltaOnlyTwoHelperNames':True,'modelAndControlsByteExactV2':True};(O/'checks.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k!='helperClosure'}));print(len(g['result']['calls']),len(g['result']['uniqueHeads']))
