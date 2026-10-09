"""Pure parser/selection controls only. Synthetic witness is not current typed evidence."""
import json,struct,copy
from validate_observer import validate,selection,split

def fixture(empty=False):
 fn=[[0]*16 for _ in range(16)];sir=[[0]*4];ranges={}
 for f in range(1,13):
  p=len(sir);h=13 if f<=6 else 14;n=4 if f<=6 else 7
  body=[[1,f,1,1],[18,0,0,0],[9,f,0,0],[4,0,1,0]]+[[3,k,k,0]for k in range(1,n)]+[[13,h,0,n],[13,f+1 if f<12 else 15,0,1],[19,0,0,0],[2,f,0,0]]
  sir+=body;fn[f]=[f,f,2,1,4,4,0,0,0,0,1,0,p,0,1,7];ranges[f]=(p,len(sir),p+4+n-1)
 for f,n in [(13,4),(14,7),(15,1)]:
  p=len(sir);sir.extend([[1,f,n,1],[18,0,0,0],[19,0,0,0],[2,f,0,0]]);fn[f]=[f,f,2,n,4,4,0,0,0,0,1,0,p,0,1,7]
 if empty:
  for f in range(1,13):sir[fn[f][12]+3][0]=5
 q=selection(fn,sir);code=[[0]for _ in range(801)];fix=[[0]*4];labels=[[0]for _ in range(16)];fn1=copy.deepcopy(fn)
 for f in range(1,16):fn1[f][13]=1+f*40
 rows=[]
 def row(t,v):rows.append((t,v))
 def table(t,phase,rs):
  for i,v in enumerate(rs):row(t,[phase,i,*v])
 def header(phase,exp):return [phase,0,16,len(sir),16,1,16,801,len(fix),16,exp]
 row('SH',header(0,1));row('SQ',q);table('SF',0,fn);table('SN',0,[[0]*8 for _ in range(16)]);table('ST',0,[[0]*4]);syms=[[0]*8 for _ in range(16)]
 for f in range(1,16):syms[f][4]=f
 table('SY',0,syms);table('SS',0,sir);row('SZ',[0])
 def state(i,phase):
  G=[0,1,1,80,1,7,0,1,0,0,0,0,0,0,0,0];row('SG',[phase,i,*G])
  for k in range(2):row('SL',[phase,i,k,20 if k else 0,1])
  for k in range(7):row('SD',[phase,i,k,0,0])
 for f in q[4:4+q[0]]:
  p,end,h=ranges[f];pos=fn1[f][13]
  for i in range(p,end):
   op=sir[i][0]
   if op==13:
    state(i,0);code[pos][0]=0x14000000 if sir[i+1][0]==19 else 0x94000000;fix.append([pos,4,sir[i][1],0])
   after=pos+(5 if op==18 else 1 if op in [1,13]else 0)
   row('SI',[i,pos,after,0,op,0])
   if op in [1,13]:state(i,1)
   pos=after
 for phase in [1,2]:
  row('SH',header(phase,1));row('SQ',q);table('SF',phase,fn1);projected=copy.deepcopy(code)
  if phase==2:
   for pc,kind,target,aux in fix[1:]:projected[pc][0]=(projected[pc][0]&0xfc000000)|((fn1[target][13]-pc)&0x3ffffff)
  table('SC',phase,projected);table('SX',phase,fix);table('SB',phase,labels)
  if phase==2:table('SE',phase,[[0]*4])
  row('SZ',[phase])
 return rows,b''.join(struct.pack('<I',v[2])for t,v in rows if t=='SC'and v[0]==2 and v[1]>0)

def encode(rs):return [(t+' '+' '.join(map(str,v))+'\n').encode()for t,v in rs]
def controls():
 rs,p=fixture();q=validate(encode(rs),p,b'');assert len(q['selectedOwners'])==12 and q['selectedEdges']==24 and not q['safeRewriteQualified']
 zero,zp=fixture(True);z=validate(encode(zero),zp,b'');assert z['status'].startswith('REJECTED_')
 negatives=[]
 def refuse(name,mutate):
  r=copy.deepcopy(rs);payload=p;mutate(r)
  try:validate(encode(r),payload,b'')
  except (AssertionError,IndexError,ValueError,KeyError):negatives.append(name);return
  raise AssertionError('mutant admitted:'+name)
 refuse('missing-footer',lambda r:r.pop())
 refuse('missing-node',lambda r:r.pop(next(i for i,x in enumerate(r)if x[0]=='SN')))
 refuse('missing-token',lambda r:r.pop(next(i for i,x in enumerate(r)if x[0]=='ST')))
 refuse('duplicate-owner',lambda r:next(v for t,v in r if t=='SQ').__setitem__(5,1))
 refuse('missing-post-FN',lambda r:r.pop(next(i for i,x in enumerate(r)if x[0]=='SG')))
 refuse('missing-gnins',lambda r:r.pop(next(i for i,x in enumerate(r)if x[0]=='SI')))
 refuse('unknown-callee',lambda r:next(v for t,v in r if t=='SS'and v[2]==13).__setitem__(3,999))
 refuse('node-reference-overflow',lambda r:next(v for t,v in r if t=='SN').__setitem__(3,999))
 refuse('token-source-overflow',lambda r:next(v for t,v in r if t=='ST').__setitem__(4,999))
 refuse('layout-native-mismatch',lambda r:next(v for t,v in r if t=='SC'and v[0]==2 and v[1]==1).__setitem__(2,1))
 refuse('frame-slot-overflow',lambda r:next(v for t,v in r if t=='SG').__setitem__(6,17))
 refuse('SIR-cap-plus1',lambda r:next(v for t,v in r if t=='SQ').__setitem__(1,257))
 refuse('FN-cap-plus1',lambda r:next(v for t,v in r if t=='SQ').__setitem__(0,17))
 refuse('edge-cap-plus1',lambda r:next(v for t,v in r if t=='SQ').__setitem__(2,65))
 refuse('fix-target-overflow',lambda r:next(v for t,v in r if t=='SX'and v[0]==1 and v[1]==1).__setitem__(4,999))
 refuse('fix-aux-invalid',lambda r:next(v for t,v in r if t=='SX'and v[0]==1 and v[1]==1).__setitem__(5,2))
 refuse('missing-FIX',lambda r:r.pop(next(i for i,x in enumerate(r)if x[0]=='SX')))
 refuse('missing-CODE',lambda r:r.pop(next(i for i,x in enumerate(r)if x[0]=='SC')))
 refuse('missing-export',lambda r:r.pop(next(i for i,x in enumerate(r)if x[0]=='SE')))
 for name,raw in [('empty',b''),('trap',b'KEXE_TRAP {}\n'),('partial',b'SH 0'),('extra',b'SREFUSE 0\n{:ok true, x}\n')]:
  try:
   ls,suf=split(raw);validate(ls,p,b'')
  except AssertionError:negatives.append(name);continue
  raise AssertionError(name)
 return {'status':'PASS_PURE_SYNTHETIC_SHARED_FRAME_OBSERVER_SELECTION_PARSER_ONLY','positiveOwners':q['selectedOwners'],'positiveSIR':q['selectedSIR'],'positiveEdges':24,'zeroSelectionRejected':True,'negativeControls':negatives,'actualTypedEvidence':False,'actualNativeThreadProcessFDPipeCalls':0,'safeRewriteQualified':False}
if __name__=='__main__':print(json.dumps(controls(),indent=2))
