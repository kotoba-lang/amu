"""Finite scalar-state receipts only; no generated machine execution proof."""
WIDTH={'PIPELINE':3,'ALLOC':6,'ROOT':17,'SIR':5,'FREC':3,'INNER':5,'IFREC':3,'GUARD':4,'STATE':14,'FUELWORD':2,'FUELMODEL':4,'END':2}
FUEL=[0xf94004f0,0xf1000610,0x54000042,0xd4200000,0xf90004f0]
def verify(raw,case):
 assert isinstance(raw,bytes)and len(raw)<=1048576 and 0<=case<16;rows={k:[]for k in WIDTH};order=[]
 for line in raw.decode('ascii').splitlines():
  f=line.split();assert f and f[0]in WIDTH and len(f)==WIDTH[f[0]]+1;z=list(map(int,f[1:]));assert all(-(1<<63)<=v<(1<<63)for v in z);rows[f[0]].append(z);order.append(f[0])
 for tag in ['PIPELINE','ALLOC','ROOT','END']:assert len(rows[tag])==1
 assert order[0]=='PIPELINE'and order[-1]=='END'and rows['PIPELINE'][0][0]==0 and rows['END']==[[case,777]]
 r=rows['ROOT'][0];c,i,f,t,n,end,p,base,top,count,sirn,fnn,h,dp,fb,leaf,freg=r
 assert c==case and 0<p<i<sirn and 0<f<fnn and 0<=t<=6 and 1<=n<=5 and t+n<=min(7,h,dp)and fb>0 and leaf==freg==0 and 0<base<top<=count and p<end<sirn and end-p+1<=32
 al=rows['ALLOC'][0];assert al[0]==al[2]==base and al[0]+al[1]==al[3]==top and al[4:]==[0,0]
 assert len(rows['FREC'])==16 and [z[:2]for z in rows['FREC']]==[[f,k]for k in range(16)];ff=[z[2]for z in rows['FREC']];assert ff[12]==p and ff[14]==1
 body=rows['SIR'];assert [z[0]for z in body]==list(range(p,end+1));sir=[z[1:]for z in body];assert sir[:2]==[[1,f,n,ff[10]],[18,0,0,0]]and sir[2][0]==9 and sir[-2:]==[[19,0,0,0],[2,f,0,0]]
 g=sir[-3][1];assert sir[-3]==[13,g,0,1]and 0<g<fnn and g!=f;assert len(rows['IFREC'])==16 and [z[:2]for z in rows['IFREC']]==[[g,k]for k in range(16)];gf=[z[2]for z in rows['IFREC']];assert gf[14]==0 and gf[11]==0
 inner=rows['INNER'];mp=gf[12];assert [z[0]for z in inner]==list(range(mp,mp+7));ins=[z[1:]for z in inner];assert ins[0]==[1,g,1,1]and ins[1][0]==9 and ins[2]==[4,0,1,0]and ins[3][0]==3 and ins[3][1]==1 and ins[3][3]==0 and ins[3][2]>0 and ins[3][2]&(ins[3][2]+1)==0 and ins[4:]==[[6,5,0,0],[19,0,0,0],[2,g,0,0]]
 if case>=6:
  assert len(rows['GUARD'])==1 and not rows['STATE']and not rows['FUELWORD']and not rows['FUELMODEL'];assert rows['GUARD'][0]==[case,0,901 if case==9 else 0,1]
 else:
  assert len(rows['STATE'])==1 and not rows['GUARD'];z=rows['STATE'][0];assert z[0]==case and z[1]==end and z[8:12]==[0,0,1,1]and z[-1]==1 and 0<z[12]<=192 and z[3]-z[2]==z[12]and z[6]==z[5]and z[7]==z[5]+1
  assert len(rows['FUELWORD'])==5 and [x[0]for x in rows['FUELWORD']]==list(range(rows['FUELWORD'][0][0],rows['FUELWORD'][0][0]+5))and [x[1]for x in rows['FUELWORD']]==FUEL
  assert rows['FUELMODEL']==([[case,1 if case==0 else 0,0 if case==0 else case-1,0]]if case<3 else [])
 return {'status':'PASS_FINITE_FUEL_DAG_COMPONENT_STATE_RECEIPT_ONLY','case':case,'sourceBoundFullStatePredicate':True,'emittedFuelFiveWords':case<6,'abstractFuelModelOnly':case<3,'actualGeneratedCodeExecution':False,'actualNonresumingTrapQualified':False,'performanceQualified':False}
