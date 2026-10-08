from pathlib import Path
import json,hashlib,stat,sys,contextlib,io
D=Path('/Users/junkawasaki/github/workspaces/codex/published-mode2-x8-vector-statemate6-saved-emission-review-v1-20261009-dense');O=Path(__file__).resolve().parent;sys.dont_write_bytecode=True
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes())
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for n,r in sp.items():assert rec(D/n)=={k:r[k]for k in ['bytes','sha256']}
for p,r in ip.items():assert rec(p)=={k:r[k]for k in ['bytes','sha256']}
assert len(ip)==153 and sum(x['bytes']for x in ip.values())==11800185
s=(D/'compare.py').read_text().replace("(D/'report.json').write_text(json.dumps(out,indent=2)+'\\n');print", "globals()['independent_recomputed_output']=out;print")
g={'__file__':str(D/'compare.py'),'__name__':'pure_saved_no_writer'};exec(compile(s,str(D/'compare.py'),'exec'),g)
with contextlib.redirect_stdout(io.StringIO()):g['main']()
r=g['independent_recomputed_output'];assert r==json.loads((D/'report.json').read_bytes())
# Independently enumerate branch target positions relative to normalized token spans.
W=D.parent;A=W/'published-mode2-x8-vector-statemate6-source-v2-20261009/run-outputs';paths=[A/'off-vector.bin',A/'on-vector.bin',A/'on-statemate.bin'];targets=[]
for p in paths:
 norm=g['normalize'](p.read_bytes());inside=[]
 for b in norm['branches']:
  rid,tok=b['targetLocation'];t=norm['regions'][rid]['tokens'][tok]
  if b['target']!=t['pc'] and b['target'] not in norm['regions'][rid]['entryInitializationLoads']:inside.append(b)
 targets.append(dict(path=str(p),branchCount=len(norm['branches']),nonentryInteriorNormalizedTargets=inside))
summary={'sourceFiles':len(sp),'inputFiles':len(ip),'inputLogicalBytes':sum(x['bytes']for x in ip.values()),'subjectSourcePins':rec(D/'source-pins.json'),'subjectReport':rec(D/'report.json'),'subjectFreeze':rec(D/'freeze.json'),'recomputedExact':True,'vector':{k:r['vector'][k]for k in ['OFFbytes','ONbytes','deltaBytes','regions','changedRegions','sizeChangedRegions','ONprivatePlus1Branches','exports']},'statemate':{k:r['statemate'][k]for k in ['OFFbytes','ONbytes','deltaBytes','regions','changedRegions','sizeChangedRegions','ONprivatePlus1Branches','exports']},'finiteDebitCases':len(r['actualSavedChargeModelControls']),'structuralMutants':r['structuralMutantsRefused'],'branchTargetAudit':targets,'retainedHOLD':r['HOLD']};(O/'checks.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k in ['vector','statemate','branchTargetAudit']})[:5000])
