"""Draft fixed wrapper: named limits then exact native-loader exec. Import inert."""
import os,sys,json,resource

def target(before,soft,hard):
 s,h=before;inf=resource.RLIM_INFINITY
 # Required loader CPU soft1800/hard1801 must not raise finite inherited limits.
 assert h==inf or h>=hard,'inherited hard below exact policy'
 assert s==inf or s>=soft,'inherited soft below exact policy'
 return (soft,hard)
def main(fd,argv):
 total=0
 def emit(q):
  nonlocal total
  b=(json.dumps(q,sort_keys=True)+'\n').encode();assert total+len(b)<=65536
  view=memoryview(b)
  while view:n=os.write(fd,view);assert n>0;view=view[n:]
  os.fsync(fd);total+=len(b)
 for idx,(name,soft,hard)in enumerate([('RLIMIT_FSIZE',67108864,67108864),('RLIMIT_CPU',1800,1801)],1):
  before=None;want=None
  try:
   kind=getattr(resource,name);before=resource.getrlimit(kind);want=target(before,soft,hard)
   emit({'index':idx,'limit':name,'stage':'before','before':before,'desired':want})
   resource.setrlimit(kind,want);after=resource.getrlimit(kind);assert after==want
   emit({'index':idx,'limit':name,'stage':'outcome','outcome':'installed','readback':after})
  except BaseException as ex:
   emit({'index':idx,'limit':name,'stage':'outcome','outcome':'failure','before':before,'desired':want,'exception':repr(ex)});return 78
 emit({'stage':'exec-ready','argv':argv,'ASSetterRequested':False,'CPUGraceHardSeconds':1801})
 os.set_inheritable(fd,False);os.execve(argv[0],argv,dict(os.environ))
 return 79
if __name__=='__main__':
 assert len(sys.argv)>=5 and sys.argv[1]=='--journal-fd'and sys.argv[3]=='--'
 sys.exit(main(int(sys.argv[2]),sys.argv[4:]))
