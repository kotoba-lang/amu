"""Independent stdlib finite shadow receipt decoder; no native execution."""
from pathlib import Path
import re,json,hashlib,base64
D=Path(__file__).resolve().parent
H=lambda s:hashlib.sha256(s.encode('ascii')).hexdigest()
def cid(h):return 'b'+base64.b32encode(bytes([1,85,18,32])+bytes.fromhex(h)).decode().lower().rstrip('=')
def decode(domain,scope,s,n,cap):
 assert isinstance(s,str)and s.isascii()and len(s)<=cap
 p=domain+'|'+scope+'|';assert s.startswith(p)and s.endswith('|END');b=s[len(p):-4];assert re.fullmatch('[0-9a-f]+',b)and len(b)==16*(n+1)and int(b[:16],16)==n
 v=[int(b[16+i*16:32+i*16],16)for i in range(n)];return [x-(1<<64)if x>=1<<63 else x for x in v]
def validate(raw,c,family):
 assert type(raw)is bytes and len(raw)<=1048576 and raw.endswith(b'\n');tags=['SHADOW-CONTEXT','SHADOW-REQUEST','SHADOW-RESULT','SHADOW-TRANSITION','SNAPSHOT-CID','COMPUTE-CID','RESULT-CID','TRANSITION-CID','SHADOW','MUTATION','SHADOW-CLEANUP'];found={}
 for line in raw.splitlines():
  tag=line.split(b' ',1)[0].decode('ascii');assert tag in tags or tag in ['PIPELINE','ALLOC']
  if tag in tags:assert tag not in found;found[tag]=line[len(tag)+1:].decode('ascii')
 assert set(found)==set(tags);s=(D/'unity-shadow.kotoba').read_text();sc={k:re.search(r'\(def '+k+r' "([0-9a-f]{64})"\)',s)[1]for k in ['cc-evaluator','cc-rules','cc-contract','cc-output-contract','cs-adapter']};scope=H(sc['cc-evaluator']+sc['cc-rules']+sc['cc-contract']+sc['cs-adapter']);X=decode('shape-context/v1',scope,found['SHADOW-CONTEXT'],12643,393216);snap=H(found['SHADOW-CONTEXT']);Q=decode('shape-compute/v1',snap,found['SHADOW-REQUEST'],3024,131072);compute=H(found['SHADOW-REQUEST']);outputscope=H(snap+sc['cc-output-contract']);R=decode('shape-result/v2',outputscope,found['SHADOW-RESULT'],512,131072);T=decode('shape-transition/v2',compute,found['SHADOW-TRANSITION'],512,131072)
 for name,encoded in [('SNAPSHOT-CID','SHADOW-CONTEXT'),('COMPUTE-CID','SHADOW-REQUEST'),('RESULT-CID','SHADOW-RESULT'),('TRANSITION-CID','SHADOW-TRANSITION')]:assert found[name]==cid(H(found[encoded]))
 projected=T.copy()
 for i in range(512):
  if i in[7,8,208]or 32<=i<80 and(i-32)%6<4:projected[i]=0
 assert R==projected
 row=list(map(int,found['SHADOW'].split(' ')));assert len(row)==19 and row[:2]==[c,family]and row[2]==[5,4,3][c]and row[3:6]==[1,1,1]and 0<=row[12]<=536870912 and row[13]==0
 assert Q[1]==row[2]and Q[4]==c and T[1]==row[2]and T[4:7]==row[16:19]and T[7:9]==row[14:16]and T[9]==row[15]-row[14]
 assert list(map(int,found['SHADOW-CLEANUP'].split(' ')))==[c,family,1]
 mutation=list(map(int,found['MUTATION'].split(' ')));assert len(mutation)==6 and mutation[:3]==[c,family,row[2]]
 if family==0:assert mutation[3:]==[-1,0,0]and row[6:12]==[1]*6
 else:
  assert row[11]==0 and mutation[3]>=0
  old,new=mutation[4:];assert new==(old+128 if family==1 else 0 if family==2 and old<0 else old+1 if family==2 else old^1 if family==3 else 1)
  if family==1:assert Q[80]==new
  if family==3:assert Q[100]==new
  if family==4:assert Q[2896+row[2]]==1 and row[8]==0
 # Independently ordered contributions; -1 neutral and0 a real lowerbound.
 n=X[1];ec=X[3];assert 2<=n<=8 and 0<=ec<=16
 def replay(fresh):
  acc=[0 if fn==0 else -1 if fresh else Q[32+fn*6+k]for fn in range(n)for k in range(4)]
  for e in range(ec):
   edge=R[80+8*e:88+8*e];assert edge[:4]==X[10531+4*e:10535+4*e];target=edge[2];assert 0<target<n
   for k,x in enumerate(edge[4:]):
    assert x>=-1
    if edge[0]!=row[2]:assert x==-1;continue
    if x!=-1:
     at=4*target+k;acc[at]=x if acc[at]<0 else min(acc[at],x)
  return acc
 saved=replay(False);fresh=replay(True)
 if row[9]==1:assert saved==[0 if fn==0 else T[32+fn*6+k]for fn in range(n)for k in range(4)]
 return {'case':5*c+family,'subject':row[2],'family':family,'computeCID':found['COMPUTE-CID'],'resultCID':found['RESULT-CID'],'transitionCID':found['TRANSITION-CID'],'snapshotCID':found['SNAPSHOT-CID'],'physicalLedger':row[12],'complete':bool(row[8]),'roleProven':bool(row[6]),'published':bool(row[11]),'savedReplay':saved,'freshReplay':fresh,'directStatePairExact':True,'nativeTimingQualified':False,'keyExclusions':[]}
