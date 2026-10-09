"""Executable pure qualification registration; deliberately no launch authority."""
from pathlib import Path
import hashlib,json
from qualification import cases,native_raw,parse
D=Path(__file__).resolve().parent
R=Path('/Users/junkawasaki/github/workspaces/codex/tc-hft-g4-held-v6-original19-runtime190-source-v1-20261009-dense/run-outputs')
def registration(rows):
 out=cases(rows)
 for q in out:
  q['argvRelative']=['consumers/'+q['workload'],q['arm'],str(q['n']),str(q['calls']),'1']
  sourceArm='ON' if q['arm']=='ON' else 'OFF'
  stem=f'{q["workload"]}-{sourceArm}-n{q["n"]}'
  q['expected']=native_raw((R/(stem+'.stdout')).read_bytes(),(R/(stem+'.stderr')).read_bytes())
 return out
def verify_saved(root,rows):
 """Requires complete explicit child closure receipts; does not confer resource qualification."""
 root=Path(root);answers=[]
 for i,q in enumerate(registration(rows),1):
  p=root/f'{i:03d}';r=json.loads((p/'closure.json').read_text())
  assert set(r)=={'index','argvRelative','returncode','directWaitCount','reaped','ownershipAndResourcesProof'}
  assert r['index']==i and r['argvRelative']==q['argvRelative'] and r['directWaitCount']==1 and r['reaped'] is True
  # Fresh independently reviewed execution adapter must supply a bound proof; source alone never claims it.
  pin=r['ownershipAndResourcesProof'];assert set(pin)=={'path','bytes','sha256'}
  proofRaw=Path(pin['path']).read_bytes();assert len(proofRaw)==pin['bytes'] and hashlib.sha256(proofRaw).hexdigest()==pin['sha256']
  proof=json.loads(proofRaw);assert proof['status']=='PASS_INDEPENDENT_CURRENT17_CONSUMER_QUALIFICATION_CHILD_CLOSURE_ONLY' and proof['index']==i and proof['argvRelative']==q['argvRelative'] and proof['reaped'] is True and proof['returncode']==0
  answers.append(parse((p/'stdout').read_bytes(),(p/'stderr').read_bytes(),q,q['expected'],r['returncode']))
 assert len(answers)==342
 return {'status':'PASS_SAVED_CURRENT17_CONSUMER_RESULT_FUEL_COUNTER_REPEAT_RESET_ONLY','closedConsumerCalls':342,'freshCalls':285,'repeatResetCalls':57,'elapsedPerformanceQualified':False,'officialEmbenchQualified':False}
if __name__=='__main__':
 print(json.dumps(registration(json.loads((D/'packet.json').read_text())['entries']),indent=2))
