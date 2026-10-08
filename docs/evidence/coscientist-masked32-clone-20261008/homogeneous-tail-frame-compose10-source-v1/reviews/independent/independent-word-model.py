"""Independent bounded interpreter for actual saved restore/entry words only."""
from pathlib import Path
import json,copy,hashlib
D=Path(__file__).parent;S=D.parent/'tc-homogeneous-tail-frame-compose10-source-v1-20261009';r=json.loads((S/'compose-controls-result.json').read_bytes());before=Path(r['originalNative']['path']).read_bytes();after=bytearray(before)
for c in r['changes']:
 at=c['physicalByteOffset'];assert int.from_bytes(before[at:at+4],'little')==c['before'];after[at:at+4]=c['after'].to_bytes(4,'little')
assert hashlib.sha256(after).hexdigest()==r['expectedNativeSHA256']
def word(blob,i):return int.from_bytes(blob[(i-1)*4:i*4],'little')
def step(q,w,pc):
 x=q['x'];m=q['m'];sp=q['sp'];n=pc+1
 if w==0xaa0903e0:x[0]=x[9]
 elif w==0xf94003f3:x[19]=m[sp]
 elif w==0x910003bf:q['sp']=x[29]
 elif w==0xa8c17bfd:x[29],x[30]=m[sp],m[sp+8];q['sp']=sp+16
 elif w==0xa9bf7bfd:q['sp']=sp-16;m[sp-16]=x[29];m[sp-8]=x[30]
 elif w==0x910003fd:x[29]=sp
 elif w&0xffc003ff==0xd10003ff:q['sp']=sp-((w>>10)&4095)
 elif w==0xf90003f3:m[sp]=x[19]
 elif w&0xffc003ff==0xf90003e7:m[sp+8*((w>>10)&4095)]=x[7]
 elif w==0xaa0003f3:x[19]=x[0]
 elif w==0xf94007be:x[30]=m[x[29]+8]
 elif w==0xd503201f:pass
 elif w&0xfc000000==0x14000000:
  delta=w&0x3ffffff;delta=delta-(1<<26)if delta&(1<<25)else delta;n=pc+delta
 else:raise AssertionError('unknown instruction '+hex(w))
 return n
cases=[]
for p in r['pairs']:
 F=p['F'];start=p['tailWord']-4;end=p['privateEntryWord']+1
 oldBranch=word(before,p['tailWord']);newBranch=word(after,p['tailWord']);assert p['tailWord']+(oldBranch&0x3ffffff)==p['privateEntryWord']-5 and p['tailWord']+(newBranch&0x3ffffff)==p['privateEntryWord']
 for seed in range(8):
  header=0x100000+seed*0x1000;m={a:(a*31+seed)&((1<<64)-1)for a in range(header-F,header+16,8)};x=[i*0x12345+seed for i in range(31)];x[29]=header;x[30]=0xaaaa+seed;x[7]=m[header-8];x[9]=0xf000+seed
  q=dict(x=x,sp=header-F,m=m,NZCV=seed%16,guestMemory=[seed,1,2,3],fuel=seed);a=copy.deepcopy(q);b=copy.deepcopy(q)
  for blob,state in [(before,a),(after,b)]:
   pc=start
   for budget in range(20):
    if pc==end:break
    pc=step(state,word(blob,pc),pc)
   assert pc==end
  assert a==b;cases.append(dict(owner=p['owner'],F=F,seed=seed,all31GPR_SP_NZCV_FrameGuestFuelEqual=True))
# Meaningful LR mutant: NOP at the new LR reload cannot preserve arbitrary helper LR.
p=r['pairs'][0];F=p['F'];header=0x80000;x=[i+100 for i in range(31)];x[29]=header;x[30]=77;x[7]=333;x[9]=444;m={a:9 for a in range(header-F,header+16,8)};m[header]=222;m[header+8]=888;m[header-F]=999;m[header-8]=333;q=dict(x=x,sp=header-F,m=m,NZCV=5,guestMemory=[],fuel=0)
mut=bytearray(after);at=(p['tailWord']-3-1)*4;mut[at:at+4]=(0xd503201f).to_bytes(4,'little');states=[]
for blob in [before,mut]:
 st=copy.deepcopy(q);pc=p['tailWord']-4
 for _ in range(20):
  if pc==p['privateEntryWord']+1:break
  pc=step(st,word(blob,pc),pc)
 states.append(st)
assert states[0]!=states[1]
out=dict(status='PASS_INDEPENDENT_BOUNDED_SAVED_WORD_FRAME_TRANSITION_MODEL_ONLY',cases=cases,caseCount=len(cases),savedWordChanges=40,bareNopLRMutantRefused=True,expectedNativeSHA256=r['expectedNativeSHA256'],scope='saved actual OFF/prospective SOURCE40 words, active valid private equal frame and restored context premises; no candidate native emission/generalABI qualification',nativeCalls=0)
(D/'independent-word-model-result.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],len(cases))
