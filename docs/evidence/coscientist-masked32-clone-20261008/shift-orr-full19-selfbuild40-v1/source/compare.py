"""Finite aligned word-pattern delta diagnostic, not owner/domain proof."""
import struct

def need(c,s):
 if not c:raise AssertionError(s)
def lsl(d,x,s):return 0xd3400000+((64-s)&63)*65536+(63-s)*1024+x*32+d
def lsr(d,x,s):return 0xd3400000+s*65536+63*1024+x*32+d
def orr(d,n,m,s=0):return 0xaa000000+m*65536+s*1024+n*32+d
def compare(old,new):
 need(len(old)==len(new),'unchanged wholepayload length');patterns={}
 for x in range(19,29):
  for left in range(1,32):
   right=32-left;replacement=struct.pack('<III',lsr(10,x,right),orr(9,10,x,left),0xd503201f)
   for orient,words in [('left',[lsl(9,x,left),lsr(10,x,right),orr(9,9,10)]),('right',[lsr(9,x,right),lsl(10,x,left),orr(9,9,10)])]:patterns[(struct.pack('<III',*words),replacement)]={'resident':x,'left':left,'right':right,'orientation':orient}
 spans=[];i=0
 while i<len(old):
  if old[i]==new[i]:i+=1;continue
  start=(i//4)*4;key=(old[start:start+12],new[start:start+12]);need(start>=i-3 and start+12<=len(old)and key in patterns,'only exact aligned registeredthreeword substitution')
  need(not spans or start>=spans[-1]['byteOffset']+12,'nonoverlapping changes');spans.append({'byteOffset':start,**patterns[key],'oldWords':[hex(x)for x in struct.unpack('<III',key[0])],'newWords':[hex(x)for x in struct.unpack('<III',key[1])]});i=start+12
 need(spans,'nonzero patch observation; zero is hypothesis failure/no fallback')
 return {'observedAlignedThreeWordPatterns':len(spans),'spans':spans,'allOtherPayloadBytesExact':True,'tailExact':True,'typedSIROwnerDomainQualified':False}
