from pathlib import Path
import json,signal
signal.alarm(15)
r=Path('/Users/zebulun/github/workspaces/codex/vector-leaf-straight-read-cache-current19-timing-v2-root/timing')
folders=sorted(p for p in (r/'children').iterdir() if p.is_dir()) if (r/'children').exists() else []
latest=[]
for p in folders[-4:]:
 try:
  q=json.loads((p/'receipt.json').read_bytes());latest.append({k:q.get(k) for k in ('index','label','kind','state','returncode')})
 except (FileNotFoundError,json.JSONDecodeError):latest.append({'folder':p.name,'state':'receipt-transition'})
states=[]
for p in sorted(r.glob('*-state.json')):
 q=json.loads(p.read_bytes());states.append({'workload':q['workload'],'status':q.get('status'),'calibrations':len(q['calibration']),'triples':len(q['triples']),'accepted':len(q['accepted'])})
q={'scope':'readonly saved progress, no timing qualification','receiptFolders':len(folders),'latest':latest,'states':states,'terminalPresent':(r/'terminal.json').exists(),'failurePresent':(r/'failure.json').exists()}
b=(json.dumps(q)+'\n').encode();assert len(b)<=65536
import sys
sys.stdout.buffer.write(b)
