"""Pure original-source recurrence; no native/process/network operations."""
from pathlib import Path
import re,json,struct,hashlib
D=Path(__file__).resolve().parent
R=json.loads((D/'report.json').read_text());P=Path(R['source']['path']);b=P.read_bytes();assert len(b)==R['source']['bytes'] and hashlib.sha256(b).hexdigest()==R['source']['sha256']
leaves=re.findall(r'\(vector-at \[([0-9 ]+)\] \(- i ([0-9]+)\)\)',b.decode());assert len(leaves)==16
T=[]
for j,(v,offset)in enumerate(leaves):
 a=list(map(int,v.split()));assert len(a)==16 and int(offset)==16*j;T.extend(a)
assert T==R['sourceTableValues']
seed=0;crc=4294967295;first={};tr=[];allStop=None
for i in range(R['maximumTraceSteps']):
 seed=(seed*1103515245+12345)&2147483647;index=(crc^(seed>>16))&255;first.setdefault(index,i+1);crc=T[index]^(crc>>8)
 if len(first)==256 and allStop is None:allStop=i+1
 if i+1 in [1,2,1024] or i+1==allStop:tr.append({'prefix':i+1,'CRC':(~crc)&4294967295,'distinctIndices':len(first),'missingIndices':[n for n in range(256)if n not in first]})
assert tr==R['traces'] and allStop==R['all256FirstPrefix'] and [first.get(n)for n in range(256)]==R['firstVisitByIndex']
N=Path('/Users/junkawasaki/github/workspaces/codex/crc-table-decision-collapse-tc-remaining-extract1-source-v2-20261009/run-outputs/observed-on-input.bin');nb=N.read_bytes();assert len(nb)==3680 and hashlib.sha256(nb).hexdigest()=='5187d8338730957bf4611f294117c811099af65c9d1117492dd57430e8fa8999';assert list(struct.unpack_from('<256Q',nb,1632))==T
print(json.dumps({'status':'PASS_SOURCE_TRACE_AND_LITERAL_BYTES_ONLY','original1024Distinct':tr[2]['distinctIndices'],'missing':tr[2]['missingIndices'],'full256FirstPrefix':allStop,'nativeCalls':0}))
