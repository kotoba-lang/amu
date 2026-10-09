"""Finite saved text decoder only. Not a driver and never runs native code."""
import re
def decode(lines):
 assert len(lines)<=16931
 result=[];headers={};sir={};last=None;live=None;init=None;stop=None;clean=False
 widths={'QINIT':5,'QBEGIN':10,'QCALL':9,'QSCAN':10,'QEND':4,'QSTOP':3,'QCLEAN':8}
 for raw in lines:
  assert len(raw.encode())<=256 and raw.endswith('\n')
  xs=raw.split();tag=xs[0];assert tag in widths and len(xs)==widths[tag]+1
  assert all(re.fullmatch(r'(?:0|-?[1-9][0-9]*)',x)for x in xs[1:]);q=[int(x)for x in xs[1:]];assert all(-(1<<63)<=x<(1<<63)for x in q)
  if tag=='QINIT':assert init is None and q[:3]==[147552,147560,147560]and 0<q[3]<=65536 and 0<q[4]<=65536;init=q
  elif tag=='QBEGIN':
   assert init and stop is None and live is None and q[0]==len(result)+1<=256 and q[4:6]==[8,512]
   key=tuple(q[2:8]);assert q[8]==int(last is not None and key==last['key'])
   if q[8]:assert q[9]==last['answer']
   live={'id':q[0],'site':q[1],'key':key,'calls':[],'scans':[]}
  elif tag=='QCALL':
   assert live and q[0]==live['id']<=16;f,n,depth,work,p,op,a,b=q[1:]
   assert -1<=work<=512 and 0<=depth<=8
   assert (0<f<init[3]) or (p,op,a,b)==(-1,-1,0,0)
   assert (0<p<init[4]) or (op,a,b)==(-1,0,0)
   header=(p,op,a,b)
   if f in headers:assert headers[f]==header
   headers[f]=header;live['calls'].append(q)
  elif tag=='QSCAN':
   assert live and q[0]==live['id']<=16;j,f,depth,work,valid,op,a,b,c=q[1:]
   assert valid==int(0<j<init[4]and work>0)
   if valid:
    assert 0<=j<init[4];fields=(op,a,b,c)
    if j in sir:assert sir[j]==fields
    sir[j]=fields
   else:assert (op,a,b,c)==(-1,0,0,0)
   live['scans'].append(q)
  elif tag=='QEND':
   assert live and q[0]==live['id']and -1<=q[1]<=512 and 0<=q[2]<=513 and 1<=q[3]<=513
   if live['id']<=16:assert q[2]==len(live['scans'])and q[3]==len(live['calls'])
   live.update(answer=q[1],scanEntries=q[2],safeEntries=q[3]);result.append(live);last=live;live=None
  elif tag=='QSTOP':assert init and live is None and stop is None and q==[q[0],min(q[0],256),min(q[0],16)]and len(result)==min(q[0],256);stop=q
  elif tag=='QCLEAN':assert stop and not clean and q==[0]*8;clean=True
 assert init and stop and clean and live is None
 seen={};repeat=[]
 for row in result:
  key=row['key']
  if key in seen:
   assert seen[key]['answer']==row['answer'],'equal query changed answer within epoch'
   repeat.append(row)
  seen[key]=row
 return {'totalTopQueries':stop[0],'observedCompleteTopQueries':len(result),'fullRecursiveTraceQueries':min(stop[0],16),'completeWithinObservation':stop[0]<=256,'repeatedCompleteKeys':len(repeat),'hypotheticalAvoidableScanEntries':sum(r['scanEntries']for r in repeat),'hypotheticalAvoidableSafeEntries':sum(r['safeEntries']for r in repeat),'timingSavingsQualified':False,'cacheAdmissionQualified':False,'nativeObserverProof':False}
