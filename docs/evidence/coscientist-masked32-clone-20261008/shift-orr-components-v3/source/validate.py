import re

def need(v,s):
 if not v:raise AssertionError(s)

def validate(raw,c):
 widths={'ALLOC':6,'PIPELINE':3,'OWNER':7,'ROOT':22,'SIR':5,'STATE':14,'GUARD':4,'END':2};rows={k:[]for k in widths}
 for line in raw.decode('ascii').splitlines():
  v=line.split();need(v and v[0]in widths and len(v)==widths[v[0]]+1,'exact record schema');need(all(re.fullmatch(r'-?[0-9]{1,20}',z)for z in v[1:]),'bounded decimal');xs=list(map(int,v[1:]));need(all(-(1<<63)<=z<(1<<64)for z in xs),'scalar range');rows[v[0]].append(xs)
 for k in ['ALLOC','PIPELINE','OWNER','ROOT','END']:need(len(rows[k])==1,'exact one '+k)
 k=c%17;orient=int(c<17);a=rows['ALLOC'][0];r=rows['ROOT'][0];owner=rows['OWNER'][0]
 need(rows['PIPELINE'][0][0]==0,'checked lowered source accepted')
 need(a[0]>0 and a[1]>0 and a[2]==a[0] and a[3]==a[0]+a[1] and a[4:]==[1,0],'original successfulG allocation')
 need(r[:3]==[c,k,orient]and r[3]>0 and r[4]==8388608 and r[5:7]==a[2:4]and r[7]==524288 and 0<r[5]<r[6]<=r[4],'full physical scalarM/G')
 need(0<=r[8]<=1 and r[9]==0 and r[10]>0 and r[11]>0 and 19<=r[12]<=28 and 1<=r[13]<=31,'genuine resident original prestate')
 need(r[14:20]==([8,9,0,1,1,1]if orient else[9,8,0,1,1,1]),'original orientation/coalescing/kills')
 pre=rows['PIPELINE'][0]
 need(0<pre[1]<r[20]<=196608 and 0<pre[2]<r[21]<=8192 and r[20]-pre[1]==15*(r[21]-pre[2]),'explicit postclonecounts bound to originalmc-add15rows')
 need(pre[2]<=owner[0]<r[21] and pre[1]<=owner[1]<r[3],'owner belongs appended clone domain')
 need(owner[0]>0 and 0<owner[1]<r[3] and owner[2]==r[11] and r[3]+9<owner[4]<r[20] and owner[5:]==[1,owner[0]],'genuine same FN/END owner')
 need(len(rows['SIR'])==10 and [x[0]for x in rows['SIR']]==list(range(r[3],r[3]+10)),'all ten source rows')
 q=[x[1:]for x in rows['SIR']];slot=q[0][2];n=r[13];f=q[9][1]
 need(0<slot<=r[11] and 0<f<r[21],'source slot/callee bounded')
 expect=[[4,0,slot,0],[3,1,n,0],[6,8 if orient else 9,0,0],[4,1,slot,0],[3,2,32,0],[3,3,n,0],[6,2,2,0],[6,9 if orient else 8,1,0],[6,6,0,0],[13,f,0,1]]
 need(q==expect,'exact genuine nine SIR plusCALL')
 need(rows['END']==[[c,777]],'intercepted diagnostic success')
 if 7<=k<16:need(rows['GUARD']==[[c,0,1,1]]and not rows['STATE'],'read-only readiness refusal completeM/G unchanged')
 else:
  need(not rows['GUARD']and len(rows['STATE'])==1,'one state receipt');v=rows['STATE'][0]
  need(v[0]==c and 0<=v[1]<=r[7] and v[2]==v[3]and v[4]==v[5]and v[7]==v[8]and v[9:12]==[1,1,1]and v[13]==1,'complete scalarM/G andcode')
  if 1<=k<=3:need(v[4]==v[6]and v[12]==0 and v[2]==r[7],'original capacity error at cap')
  elif k==6:need(v[4]==901 and v[2]==v[1]and v[12]==0 and v[7]==0,'dirty MMERR preserves completeM/G')
  else:need(v[4]==0 and v[2]==v[1]+3 and v[7]==8 and v[12]==3,'exact threeword replacement/skip8')
 return {'case':c,'localCase':k,'orientation':'left'if orient else'right','scope':'readonly-guard-fullM/G'if 7<=k<16 else'fullM/G-except-three-registeredCODEwords','records':rows}
