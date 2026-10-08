"""Pure metadata model only. No saved artifact execution or native calls."""
from pathlib import Path
import json,ast,hashlib
D=Path(__file__).resolve().parent;W=D.parent
ns={'__file__':str(D/'validate.py'),'__name__':'pure_observer_validator'};exec(compile((D/'validate.py').read_bytes(),str(D/'validate.py'),'exec'),ns)
source=(W/'vector-fuel-scalar-dag-emitted18-source-v1-width/positive.kotoba').read_bytes();names=['mask','mix','extra','bench'];F={};body={};offsets={'mask':0,'mix':5,'extra':25,'bench':35}
def append(f,p,rows):
 for j,z in enumerate(rows):body[p+j]=z
append(1,1,[[1,1,1,1],[9,1,0,0],[4,0,1,0],[3,1,4294967295,0],[6,5,0,0],[19,0,0,0],[2,1,0,0]])
append(2,8,[[1,2,2,2],[18,0,0,0],[9,2,0,0],[4,0,1,0],[3,1,1,0],[6,8,0,0],[4,1,2,0],[6,7,0,0],[13,1,0,1],[19,0,0,0],[2,2,0,0]])
append(3,19,[[1,3,1,1],[18,0,0,0],[9,3,0,0],[4,0,1,0],[13,1,0,1],[19,0,0,0],[2,3,0,0]])
append(4,26,[[1,4,1,1],[18,0,0,0],[9,4,0,0],[4,0,1,0],[3,1,7,0],[13,2,0,2],[4,1,1,0],[6,1,0,0],[19,0,0,0],[2,4,0,0]])
lines=[]
def add(tag,z):lines.append(tag+' '+' '.join(map(str,z)))
for phase in [0,1]:
 add('FH',[phase,0,36,5,100,100,100])
 for i,z in body.items():add('FSIR',[phase,i,*z])
 for f,name in enumerate(names,1):
  start=source.index(name.encode());end=start+len(name);r=[f,f,2,2 if f==2 else 1,1,1,1 if f==2 else 0,0,0,0,2 if f==2 else 1,1 if f==4 else 0,{1:1,2:8,3:19,4:26}[f],offsets[name]if phase else 0,0 if f==1 else 1,3];F[f]=r
  for k,v in enumerate(r):add('FF',[phase,f,k,v])
  for k,v in enumerate([1,0,0,f,0,f,1,0]):add('FNODE',[phase,f,f,k,v])
  for k,v in enumerate([start,end,0,0,f,0,0,0]):add('FSYM',[phase,f,f,k,v])
  for k,v in enumerate([1,start,end,0]):add('FTOK',[phase,f,f,k,v])
for i,owner,f,t,n,end,site in [(16,2,1,0,1,0,0),(23,3,1,0,1,0,0),(31,4,2,0,2,18,1)]:
 for phase in [0,1]:
  values=[0,1,0,64,1,3,2,1,0,0,0,0,0,0,0,0]
  for k,v in enumerate(values):add('FG',[i,phase,k,v])
 add('FCALL',[i,owner,f,t,n,end,end,40,55,0,site,1,1,0,0,0,0])
add('FOUT',[68,272,5,1,1,1,2])
for j in range(68):add('FCODE',[j,0])
for j in range(1,5):add('FLABEL',[j,j])
add('FEXP',[1,4,140,1,0]);add('FEND',[1,0]);lines.append('{:ok true, :target :aarch64-macos, :output "synthetic.kseed", :bytes 298}')
raw=('\n'.join(lines)+'\n').encode();ns['verify'](raw,source,bytes(272),140)
mutants=[raw.replace(b'FCALL 31 4 2 0 2 18 18',b'FCALL 31 3 2 0 2 18 18'),raw.replace(b'FSIR 0 23 13 1 0 1',b'FSIR 0 23 13 2 0 1'),raw.replace(b'FF 0 2 5 1',b'FF 0 2 5 2'),raw.replace(b'FCALL 31 4 2 0 2 18 18 40 55 0 1',b'FCALL 31 4 2 0 2 18 18 40 55 0 0'),raw.replace(b'FG 31 0 7 1',b'FG 31 0 7 0'),raw.replace(b'FSIR 0 27 18 0 0 0',b'FSIR 0 27 18 1 0 0'),raw.replace(b'FEXP 1 4 140 1 0',b'FEXP 1 4 144 1 0')]
for b in mutants:
 try:ns['verify'](b,source,bytes(272),140)
 except (AssertionError,StopIteration):pass
 else:raise AssertionError('accepted mutation')
for n in ['assemble.py','run.py','validate.py','source-controls.py']:ast.parse((D/n).read_text())
h=(D/'helpers.kotoba').read_text();assert 'gn-put'not in h and 'gn-gs'not in h and 'vector-assoc'not in h and 'fo-original-call M i f t n'in h
assert json.loads((D/'reversal.json').read_bytes())['exactReverseParent']
(D/'pure-controls.json').write_text(json.dumps({'status':'PASS_PURE_TYPED_OWNER_MODEL_AND_SOURCE_ONLY','acceptedSyntheticOwnerModel':1,'rejectedMutants':len(mutants),'syntaxFiles':4,'exactParentReversal':True,'helperM_GWrites':0,'nativeCalls':0,'actualTypedOwnerQualified':False},indent=2)+'\n')
