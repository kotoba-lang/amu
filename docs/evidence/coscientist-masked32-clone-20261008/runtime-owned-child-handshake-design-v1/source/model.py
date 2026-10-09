"""Pure proposed held-launch ownership machine. No OS, FD, thread, process API."""
class Refuse(Exception):pass
def need(q,m):
 if not q:raise Refuse(m)
class Ownership:
 def __init__(self,go,nonce,leader):
  need(type(leader)is int and leader>0,'root leader PID');self.go=go;self.nonce=nonce;self.leader=leader;self.bound={};self.held={leader};self.released=set();self.waited={};self.retired=False;self.waitEntered=False;self.events=0;self.samples=0;self.gap=None
 def event(self):self.events+=1;need(self.events<=16,'finite protocol')
 def bind(self,pid,birth,pgid,parent,go,nonce,durable,kernelBirth,childForkResult=None):
  self.event();need(not self.retired and not self.waitEntered,'retired ownership');need(go==self.go and nonce==self.nonce,'current invocation');need(pid in self.held and pid not in self.bound,'held unreleased PID');need(pgid==self.leader and type(birth)is int and birth>0 and birth==kernelBirth,'live birth/group correlation');need(durable is True,'fsynced witness before release')
  if pid==self.leader:need(parent==0,'direct Popen anchor')
  else:need(parent==self.leader and childForkResult==pid and len(self.bound)==1,'exact loader fork child')
  self.bound[pid]=birth
 def release(self,pid):
  self.event();need(pid in self.held and pid in self.bound and not self.retired,'no unbound release');self.held.remove(pid);self.released.add(pid)
 def child(self,pid,guestGate,guestHasJournalFD):
  self.event();need(self.leader in self.released and len(self.bound)==1 and not self.held and pid!=self.leader and pid>0,'exact one child');need(guestGate is True and guestHasJournalFD is False,'private host-owned gate/channel');self.held.add(pid)
 def sample(self,members):
  self.event();need(not self.retired and not self.waitEntered and self.samples<8,'finite anchored sample');need(1<=len(members)<=2 and len({q[0]for q in members})==len(members),'finite unique census');need(self.leader in {q[0]for q in members},'leader census')
  for pid,birth,pgid,memory in members:
   need(pid in self.bound and self.bound[pid]==birth and pgid==self.leader and pid not in self.waited,'unknown/reused/exited member');need(type(memory)is int and 0<=memory<2**64,'memory width')
  need(sum(q[3]for q in members)<=4294967296,'soft threshold');self.samples+=1
 def error(self,pid,stage,errno):
  self.event();need(not self.retired and not self.waitEntered,'anchor retired');need(pid in self.bound and stage in {'member-getpgid','member-rusage','leader-getpgid'}and errno==3,'unknown/error refused');self.gap={'pid':pid,'birth':self.bound[pid],'stage':stage,'errno':errno,'missingFootprint':None};self.retired=True
 def child_wait(self,pid,birth,rc,durable):
  self.event();need(pid!=self.leader and self.bound.get(pid)==birth and pid in self.released and pid not in self.waited and rc==0 and durable is True,'exact durable loader wait0');self.waited[pid]=birth
 def before_wait(self):self.event();self.retired=True;self.waitEntered=True
 def finish(self,rc,uncertain,raw,resources):
  self.event();need(self.retired and self.waitEntered and rc==0 and uncertain is False and raw is True and resources is True and self.samples>=1,'closed validated original budget');need(len(self.bound)==2 and all(p==self.leader or p in self.waited for p in self.bound),'exact child closure')
  return {'ownershipDiagnosticQualified':True,'strictMemoryQualified':self.gap is None,'gap':self.gap,'hardPeakQualified':False,'zeroSynthesized':False}
