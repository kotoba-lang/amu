from pathlib import Path
import json,stat,hashlib,io,contextlib
D=Path('/Users/junkawasaki/github/workspaces/codex/tc-homogeneous-tail-frame-candidate-source-v2-20261009');O=Path(__file__).resolve().parent
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes())
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for n,r in sp.items():assert rec(D/n)=={k:r[k]for k in ['bytes','sha256']}
for p,r in ip.items():assert rec(p)=={k:r[k]for k in ['bytes','sha256']}
assert rec(D/'source-pins.json')['sha256']=='7c7ce2f314eeffdfaef892b710a9ad089f05cd2cc22a7aa5ac5c73cf34008192'
base=Path('/Users/junkawasaki/github/workspaces/codex/crc-table-decision-collapse-v2-20261008/41-a64gen-candidate.kotoba').read_text();candidate=(D/'41-a64gen-candidate.kotoba').read_text();rule=(D/'rule.kotoba').read_text()
oldwrap='(defn- gn-run [M :vector-i64] :vector-i64 (gn-run-open M 0 0))'
assert candidate==base.replace(oldwrap,rule+'\n(defn- gn-run [M :vector-i64] :vector-i64 (sf-collapse (gn-run-open M 0 0)))')
# Execute source-only saved controls without their author output writer.
s=(D/'saved-controls.py').read_text();s=s[:s.index("(D/'saved-controls-result.json').write_text")];g={'__file__':str(D/'saved-controls.py'),'__name__':'pure_controls_no_writer'};exec(compile(s,str(D/'saved-controls.py'),'exec'),g);assert g['result']==json.loads((D/'saved-controls-result.json').read_bytes())
s=(D/'model.py').read_text().replace("(D/'model-result.json').write_text(json.dumps(out,indent=2)+'\\n');print(out['status'])","globals()['pure_model_output']=out")
gm={'__file__':str(D/'model.py'),'__name__':'pure_model_no_writer'};exec(compile(s,str(D/'model.py'),'exec'),gm);gm['main']();assert gm['pure_model_output']==json.loads((D/'model-result.json').read_bytes())
summary={'sourceFiles':len(sp),'sourceLogicalBytes':sum(r['bytes']for r in sp.values()),'inputFiles':len(ip),'inputLogicalBytes':sum(r['bytes']for r in ip.values()),'sourcePins':rec(D/'source-pins.json'),'candidate':rec(D/'41-a64gen-candidate.kotoba'),'preregistration':rec(D/'preregistration.json'),'freeze':rec(D/'freeze.json'),'savedControlsRecomputed':g['result'],'modelRecomputed':gm['pure_model_output']}
(O/'checks.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k not in ['modelRecomputed','savedControlsRecomputed']}));print(g['result']['negatives'])
