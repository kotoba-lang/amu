from pathlib import Path
import collections,copy,hashlib,json
T=Path(__file__).resolve().parent
ns={'__file__':str(T/'read-machine.py')};exec(compile((T/'read-machine.py').read_text(),str(T/'read-machine.py'),'exec'),ns)
parse=ns['parse'];branch=ns['branch']
def spans(a):
 starts=sorted((v,f) for f,v in a['fns'].items() if v>0)
 assert len({v for v,f in starts})==len(starts)
 return {f:(v,starts[k+1][0] if k+1<len(starts) else a['n']) for k,(v,f) in enumerate(starts)}
def audit(a,b):
 assert a['records']==b['records'] and a['post']==b['post']
 assert a['fns'].keys()==b['fns'].keys() and a['n']==b['n']
 sa=spans(a);sb=spans(b);assert sa.keys()==sb.keys()
 mapping={};ends={};total=collections.Counter()
 for f,(st,en) in sa.items():
  bt,be=sb[f];assert en-st==be-bt,(f,'changed body size')
  ends[f]=(en,be)
  for i in range(st,en):assert i not in mapping;mapping[i]=bt+i-st
 assert set(mapping)==set(range(1,a['n']))
 assert set(mapping.values())==set(range(1,b['n']))
 mapping[a['n']]=b['n']
 for f in a['fns']:assert (a['fns'][f]==0)==(b['fns'][f]==0)
 for i,j in mapping.items():
  if i==a['n']:continue
  z=a['words'][i-1];v=b['words'][j-1];q=branch(z);r=branch(v)
  if q is None:assert z==v,(i,j,'ordinary opcode/constant');total['exactWords']+=1
  else:
   assert r and q[0]==r[0] and mapping[i+q[1]]==j+r[1],(i,j,'branch opcode/destination')
   total['branches']+=1
 fa=collections.Counter((mapping[at],kind,target,aux) for _,at,kind,target,aux in a['fix'])
 fb=collections.Counter((at,kind,target,aux) for _,at,kind,target,aux in b['fix'])
 assert fa==fb,'exact projected fixup records'
 # Source execution order changes; compare each emitted source interval by source index.
 ea={e[0]:e for e in a['events']};eb={e[0]:e for e in b['events']}
 assert len(ea)==len(a['events']) and len(eb)==len(b['events']) and ea.keys()==eb.keys()
 sir={x[2]:x[3:] for x in a['post'] if x[:2]==(1,'SIR')};owner={};f=0
 for i,v in sorted(sir.items()):
  if v[0]==1:f=v[1]
  owner[i]=f
 for si,(i,st,en,safe,mode,skip) in ea.items():
  j,bt,be,bsafe,bmode,bskip=eb[si]
  assert (si,safe,mode,skip)==(j,bsafe,bmode,bskip)
  f=owner[si]
  if f not in sa:assert st==en and bt==be
  else:
   ast,aen=sa[f];bst,ben=sb[f]
   assert ast<=st<=en<=aen and bst<=bt<=be<=ben
   assert (st-ast,en-ast)==(bt-bst,be-bst),(si,'fusion/source interval')
 total['sourceIntervals']=len(ea);total['functions']=len(a['fns']);total['fixups']=len(a['fix'])
 for _,at,kind,target,aux in b['fix']:
  if kind==4 and aux==1:
   assert b['words'][b['fns'][target]-1]==0xd2800005
   q=branch(b['words'][at-1]);assert q and at+q[1]==b['fns'][target]+1;total['privateEntries']+=1
 pool=((a['n']-1)*4+7)//8*8
 assert a['raw'][pool:]==b['raw'][pool:] and set(a['raw'][4*(a['n']-1):pool])<={0} and set(b['raw'][4*(b['n']-1):pool])<={0}
 return dict(total)
if __name__=='__main__':
 rows=[];tot=collections.Counter()
 for p in sorted((T/'baseline/ports').iterdir()):
  a=parse(p);b=parse(T/'candidate/ports'/p.name);z=audit(a,b);tot.update(z);rows.append({'workload':p.name,**z});print('PASS',p.name,z,flush=True)
 # Actual code/branch/fixup mutations must be rejected by this independent comparator.
 a=parse(T/'baseline/ports/statemate');b=parse(T/'candidate/ports/statemate');controls=[]
 for kind in ['ordinary','branch','entry','fixup','source']:
  x=copy.deepcopy(b)
  if kind in ('ordinary','branch'):
   i=next(i for i,v in enumerate(x['words']) if (branch(v) is None)==(kind=='ordinary'))
   x['words'][i]^=1 if kind=='ordinary' or x['words'][i]&0x7c000000==0x14000000 else 32
  elif kind=='entry':x['fns'][next(f for f,v in x['fns'].items() if v>0)]+=1
  elif kind=='fixup':x['fix'][0]=(*x['fix'][0][:4],99)
  else:
   e=x['events'][0];x['events'][0]=(*e[:3],99,*e[4:])
  try:audit(a,x)
  except (AssertionError,KeyError,IndexError):controls.append({'fault':kind,'status':'REFUSED'})
  else:raise AssertionError('fault accepted '+kind)
 result={'status':'PASS independent all19 isolated native layout translation audit','totals':dict(tot),'rows':rows,'controls':controls,'instructionsRemoved':0,'instructionsAdded':0,'performanceClaim':False}
 (T/'layout-audit.json').write_text(json.dumps(result,indent=2)+'\n')
