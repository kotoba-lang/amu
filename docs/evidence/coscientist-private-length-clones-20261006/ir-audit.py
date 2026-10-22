"""Independent actual pre/post-SIR, all16 FN fields, final proof facts and guard map audit."""
from pathlib import Path
import importlib.util,json,hashlib
W=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('length_oracle',W/'length-oracle.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v);O=v.O;C=v.C

def audit(p):
 phases={};jobs={};facts=[];safe=set();phase=None
 for line in p.read_text().splitlines():
  q=line.split()
  if not q:continue
  if q[0]=='PCPHASE':
   phase=int(q[1]);assert phase not in phases;phases[phase]={'head':tuple(map(int,q[2:])),'sir':{},'meta':{},'ff':{}}
  elif phase is not None:
   if q[0]=='SIR':phases[phase]['sir'][int(q[1])]=tuple(map(int,q[2:]))
   if q[0]=='META':phases[phase]['meta'][int(q[1])]=tuple(map(int,q[2:]))
   if q[0]=='PCFF':phases[phase]['ff'][(int(q[1]),int(q[2]))]=int(q[3])
   if q[0]=='PCJOB':assert phase==0;jobs[int(q[1])]=tuple(map(int,q[2:]))
   if q[0]=='PCFACT':assert phase==0;facts.append(tuple(map(int,q[2:])))
   if q[0]=='PCSAFE':assert phase==1;safe.add(int(q[1]))
 assert set(phases)=={0,1};a,b=phases[0],phases[1];fnN,sirN,labelN,e1,e2=a['head'];assert e1==e2==0
 assert set(a['sir'])==set(range(1,sirN)) and set(a['meta'])==set(range(1,fnN));assert len(a['ff'])==(fnN-1)*16
 flags,_=v.shape.infer(a['sir'],a['meta']);contexts,calls,accesses,status=v.inference(a['sir'],a['meta'],flags)
 ctxMap={c:j for j,c in enumerate(contexts,1)};chosen=[];cloneMap={};pos=sirN;fid=fnN;labels=labelN
 for j,(f,n) in enumerate(contexts,1):
  good=status[j-1][0]=='LENGTH-CONTEXT';clone=0
  if n>=0 and good:
   assert flags[f][0]==1 and a['meta'][f][5]==4
   start=a['meta'][f][0];end=next(i for i in range(start+1,sirN) if a['sir'][i][0]==O('END'))
   clone=fid;chosen.append((j,f,n,fid,start,end,pos));cloneMap[j]=fid;pos+=end-start+1;fid+=1
   labels+=sum(a['sir'][i][0]==O('LABEL') for i in range(start,end+1))
  assert jobs[j]==(f,n,1 if good else 2,clone),(j,jobs[j],(f,n,good,clone))
 assert len(jobs)==len(contexts)
 # Final actual facts must match the oracle before they can justify any changed edge/check.
 bysite={}
 for f,n,i,len_,idx in accesses:
  if n>=0 and 0<=idx<len_:bysite.setdefault((ctxMap[(f,n)],i),[]).append((2,len_,idx))
 for f,n,i,c,len_ in calls:bysite.setdefault((ctxMap[(f,n)],i),[]).append((1,ctxMap[(c,len_)],0))
 wanted=[]
 for (j,i),entries in sorted(bysite.items()):
  for kind,target,index in sorted(entries,key=lambda x:-x[0]):wanted.append((j,i,kind,target,index))
 assert facts==wanted,('facts',set(facts)^set(wanted))
 callEdges={(j,i):cloneMap[target] for j,i,kind,target,index in facts if kind==1 and target in cloneMap}
 safeOriginal={(j,i) for j,i,kind,target,index in facts if kind==2}
 predicted=dict(a['sir']);meta=dict(a['meta']);ff=dict(a['ff']);expectedSafe=set();newLabel=labelN
 genericEdges=0
 for j,(f,n) in enumerate(contexts,1):
  if n==-1:
   for (ctx,i),target in callEdges.items():
    if ctx==j:op,a0,b0,c0=predicted[i];assert op==O('CALL');predicted[i]=(op,target,b0,c0);genericEdges+=1
 for j,f,n,fid,start,end,dest in chosen:
  labmap={}
  for i in range(start,end+1):
   if a['sir'][i][0]==O('LABEL'):labmap[a['sir'][i][1]]=newLabel;newLabel+=1
  for i in range(start,end+1):
   op,aa,bb,cc=a['sir'][i]
   if op in (O('FN'),O('END')):aa=fid
   elif op in (O('LABEL'),O('BR')):aa=labmap[aa]
   elif op==O('CALL'):aa=callEdges.get((j,i),aa)
   if op in (O('BRZ'),O('BRNZ')):bb=labmap[bb]
   at=dest+i-start;predicted[at]=(op,aa,bb,cc)
   if (j,i) in safeOriginal:expectedSafe.add(at)
  old=a['meta'][f];meta[fid]=(dest,*old[1:])
  for k in range(16):
   value=dest if k==C['FF-SIR'] else 0 if k in [C[x] for x in ['FF-CODE','FF-EXPORT','FF-SYM','FF-NODE']] else C['FK-PRIV'] if k==C['FF-KIND'] else a['ff'][(f,k)]
   ff[(fid,k)]=value
 assert b['head']==(fnN+len(chosen),pos,labels,0,0) and newLabel==labels,(p.parent.name,b['head'],(fnN+len(chosen),pos,labels,0,0),newLabel)
 assert b['sir']==predicted,('sir',[(i,b['sir'].get(i),predicted[i]) for i in predicted if b['sir'].get(i)!=predicted[i]][:8])
 assert b['meta']==meta and b['ff']==ff
 assert safe==expectedSafe and all(i>=sirN for i in safe)
 # Original public definitions retain all metadata; only explicitly proved call targets change.
 assert all(b['ff'][(f,k)]==a['ff'][(f,k)] for f in range(1,fnN) for k in range(16))
 return {'originalFunctions':fnN-1,'contexts':len(contexts),'clones':len(chosen),'genericProvedCallRedirects':genericEdges,'guardMapSites':len(safe),'sourceRecords':sirN-1,'newSourceRecords':pos-1,'newLabels':labels-labelN,'all16FnFieldsVerified':True,'allSourceInstructionsVerified':True,'publicAccessGuardFlags':0}
if __name__=='__main__':
 rows=[]
 for p in sorted((W/'observer/ports').glob('*/compile.log')):
  row={'workload':p.parent.name,**audit(p),'nativeLogSha256':hashlib.sha256(p.read_bytes()).hexdigest()};rows.append(row);print(row,flush=True)
 assert len(rows)==19
 (W/'ir-audit.json').write_text(json.dumps({'status':'PASS independent complete pre/post native SIR/FN/label/context/fact/guard-map audit','entries':rows,'machineAuditComplete':False,'performanceClaim':False,'COrBetterAchieved':False},indent=2)+'\n')
