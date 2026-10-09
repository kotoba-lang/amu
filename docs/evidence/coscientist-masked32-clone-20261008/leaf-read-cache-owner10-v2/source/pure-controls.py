from pathlib import Path
import sys,json,importlib.util,hashlib
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('offline_only_decoder',D/'decode.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
ff=[0]*16;ff[2]=2;ff[3]=1;ff[10]=1;ff[12]=1;ff[13]=1
beforeff=ff[:];beforeff[13]=0
bg=[0]*16;bg[0]=1;bg[4]=bg[5]=1;ag=bg[:];ag[2]=3;ag[3]=64;ag[8]=3;ag[15]=1
lines=[]
for phase,g in[(0,bg),(1,ag)]:
 lines.append('LA '+' '.join(map(str,[phase,1,1,1,0,7,2,1,1])))
 for tag,vals in[('LG',g),('LF',beforeff),('LS',[0]*7)]:
  for k,x in enumerate(vals,1 if tag=='LS'else 0):lines.append(' '.join(map(str,[tag,phase,1,1,k,x])))
lines+=['LP 1 1 1 2 64 3 3 1 0 1 0','LR 4 0 3 2 3 0','LR 5 0 3 3 4 0']
sir=[[1,1,1,1],[18,0,0,0],[9,1,0,0],[14,176,0,2],[14,176,0,2],[2,1,0,0]]
for phase in(3,4):
 rows={'HEADER':{0:[0,2,7,2,6,1,1,0,20,20,2]},'SIR':{i+1:z for i,z in enumerate(sir)},'FREC':{1:ff},'CODE':{i:[i]for i in range(1,6)},'FIX':{},'LIT':{},'LITB':{},'EXP':{1:[1,0,1,0]},'LABEL':{1:[2]},'END':{0:[]}}
 for tag,rs in rows.items():
  for i,z in rs.items():lines.append(' '.join(map(str,['LO',phase,tag,i,*z])))
raw=('\n'.join(lines)+'\n').encode();payload=b''.join(i.to_bytes(4,'little')for i in range(1,6));v=d.parse(raw,payload);assert v['eligibleOwners']==1
mutants=[raw.replace(b'LF 1 1 1 12 1',b'LF 1 1 1 12 0'),raw.replace(b'LR 5 0 3',b'LR 5 0 0'),raw.replace(b'LP 1 1 1 2 64 3',b'LP 1 1 1 2 64 2'),raw.replace(b'LO 4 CODE 1 1',b'LO 4 CODE 1 9'),raw.replace(b'LO 3 SIR 6 2 1 0 0',b'LO 3 SIR 6 2 2 0 0'),raw.replace(b'LO 4 LABEL 1 2\n',b'')]
for m in mutants:
 try:d.parse(m,payload)
 except(AssertionError,ValueError):pass
 else:raise AssertionError('accepted invalid metadata')
for n in ['run.py','prepare.py','decode.py']:compile((D/n).read_text(),str(D/n),'exec')
# Structural parentheses/string balance only; no checker/compiler claim.
for n in ['41-observer-on.kotoba','unity-observer-on.kotoba']:
 s=(D/n).read_text();depth=0;quoted=comment=esc=False
 for c in s:
  if comment:
   if c=='\n':comment=False
   continue
  if quoted:
   if esc:esc=False
   elif c=='\\':esc=True
   elif c=='"':quoted=False
   continue
  if c==';':comment=True
  elif c=='"':quoted=True
  elif c in'([{':depth+=1
  elif c in')]}':depth-=1;assert depth>=0
 assert depth==0 and not quoted
rev=json.loads((D/'reversal.json').read_text())
for z in rev:
 s=(D/z['path']).read_text()
 for patch in reversed(z['patches']):assert s.count(patch['new'])==1;s=s.replace(patch['new'],patch['old'],1)
 assert s.encode()==Path(z['parent']).read_bytes()
r={'status':'PASS_PURE_OWNER_LAYOUT_ONE_POSITIVE_SIX_REJECT_AND_SOURCE_REVERSAL_ONLY','syntheticMetadataOnly':True,'nativeCompilerSSHCalls':0,'lexicalBalanceOnly':True,'actualOwnerAdmission':False};(D/'pure-controls.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
