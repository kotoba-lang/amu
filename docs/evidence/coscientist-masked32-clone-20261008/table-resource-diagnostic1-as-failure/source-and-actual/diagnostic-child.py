"""Resource installation diagnostic only. No subprocess/exec/loader/compiler path."""
import os,sys,json,resource

def desired(before,budget,infinity):
 soft,hard=before
 assert soft==infinity or soft>=0
 assert hard==infinity or hard>=0
 h=budget if hard==infinity else min(hard,budget)
 s=h if soft==infinity else min(soft,h,budget)
 return (s,h)

def main(fd):
 total=0
 def emit(q):
  nonlocal total
  b=(json.dumps(q,sort_keys=True)+'\n').encode();assert total+len(b)<=65536
  view=memoryview(b)
  while view:
   n=os.write(fd,view);assert n>0;view=view[n:]
  os.fsync(fd);total+=len(b)
  sys.stdout.buffer.write(b);sys.stdout.buffer.flush()
 for index,(name,budget)in enumerate([('RLIMIT_FSIZE',67108864),('RLIMIT_CPU',1800),('RLIMIT_AS',4294967296)],1):
  before=None;target=None
  try:
   limit=getattr(resource,name);before=resource.getrlimit(limit);target=desired(before,budget,resource.RLIM_INFINITY)
   emit({'stage':'before','index':index,'limit':name,'before':before,'desired':target,'infinity':resource.RLIM_INFINITY})
   resource.setrlimit(limit,target)
   after=resource.getrlimit(limit)
   if tuple(after)!=target:raise AssertionError('exact resource readback mismatch')
   emit({'stage':'outcome','index':index,'limit':name,'outcome':'installed','readback':after})
  except BaseException as ex:
   if target is None:emit({'stage':'before','index':index,'limit':name,'before':before,'desired':None,'infinity':resource.RLIM_INFINITY,'readException':repr(ex)})
   try:after=resource.getrlimit(getattr(resource,name))
   except BaseException as read_ex:after={'readbackException':repr(read_ex)}
   emit({'stage':'outcome','index':index,'limit':name,'outcome':'failure','before':before,'desired':target,'readback':after,'exception':repr(ex),'exceptionType':type(ex).__name__})
   return 78
 emit({'stage':'terminal','status':'ALL_THREE_INSTALLED_EXACT_READBACK','nativeLoaderCalls':0,'compilerCalls':0})
 return 0
if __name__=='__main__':
 assert len(sys.argv)==3 and sys.argv[1]=='--journal-fd'
 sys.exit(main(int(sys.argv[2])))
