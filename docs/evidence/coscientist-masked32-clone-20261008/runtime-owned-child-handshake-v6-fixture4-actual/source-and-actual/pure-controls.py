"""Read-only/source AST and injected Python models. No operational APIs."""
from pathlib import Path
import json,importlib.util,ast,types
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fixture_pure_module',D/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
pr=json.loads((D/'preregistration.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());m.source_scope(pr)
neg=[]
def refuse(n,fn):
 try:fn()
 except (AssertionError,KeyError,TypeError,IndexError):neg.append(n)
 else:raise AssertionError('admitted mutant:'+n)
g={k:None for k in m.GO_KEYS};g.update(status=pr['rootGOStatus'],maximumDirectStarts=4,outputRoot=pr['freshOutputRoot'],noRetry=True,timingAuthorized=False,C2=False,outerHostLaunchRequiresEscalation=True);assert m.go_header(g,pr)
for n,k,v in [('fifth-start','maximumDirectStarts',5),('retry','noRetry',False),('C2','C2',True),('timing','timingAuthorized',True),('no-host','outerHostLaunchRequiresEscalation',False),('extra','extra',1)]:q=dict(g);q[k]=v;refuse(n,lambda:m.go_header(q,pr))
C=Path(pr['cases'][0]['capsule']);fake=types.SimpleNamespace(__file__=str(C/'native-call.py'))
f=types.SimpleNamespace(closed=False);q=m.journal_guard(fake,f,Path('/pure/journal'));assert q['status']=='UNHASHED_UNCLOSED_WRITER_OWNERSHIP_RETAINED'
# Actual source AST of positive guard also invokes hfile only once ACK+closed.
tree=ast.parse((C/'native-call.py').read_bytes());node=next(n.value for n in ast.walk(tree)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Subscript)and isinstance(t.slice,ast.Constant)and t.slice.value=='ownershipJournal'for t in n.targets));expr=compile(ast.fix_missing_locations(ast.Expression(node)),'sourcejournal','eval');hashes=[]
for ack,closed in [(False,False),(False,True),(True,False)]:
 r=eval(expr,dict(hfile=lambda *a:hashes.append(a),oj=Path('/pure/journal'),ownershipAck=ack,ownershipFile=types.SimpleNamespace(closed=closed)));assert r['status']=='UNHASHED_UNCLOSED_WRITER_OWNERSHIP_RETAINED'and hashes==[]
assert eval(expr,dict(hfile=lambda *a:'closed-hash',oj=Path('/pure/journal'),ownershipAck=True,ownershipFile=types.SimpleNamespace(closed=True)))=='closed-hash'
class FakeOS:
 def dup(self,fd):return fd+10
 def kill(self,*a):return None
 def killpg(self,*a):return None
trace=[];o=m.OSProxy(FakeOS(),'dup2',trace);assert o.dup(1)==11
try:o.dup(2)
except OSError as ex:assert ex.errno==24
else:raise AssertionError('dup2 did not refuse')
o.waitEntered=True;refuse('signal-after-wait',lambda:o.kill(1,9));refuse('group-after-wait',lambda:o.killpg(1,9))
# No proof is synthesized for future build/fixture; exact runtime proof required.
assert pr['actualLoaderBuildPending']is True and not Path(pr['loader']).exists()
assert len(ip)==pr['exactInputFiles']==79 and sum(r['bytes']for r in ip.values())==pr['exactInputLogicalBytes']==2454696
assert len(pr['cases'])==4 and pr['maximumGuestForks']==3 and pr['maximumThreadStarts']==10
for p in D.rglob('*.py'):ast.parse(p.read_bytes())
s=(D/'run.py').read_text();assert 'entered.wait(5)'in s and 'release.wait(max(0,self.deadline-time.monotonic()))'in s and 'self.worker.is_alive()and not self.writer_stop_acknowledged()and not file.closed'in s
assert 'UNACKNOWLEDGED_OWNERSHIP_JOURNALS' in s and 'journal_guard(m,file' in s and 'coord.join(timeout=5)'in s
assert s.index("save(O/'terminal.json'")<s.index("save(O/'report.json'")
print(json.dumps(dict(status='PASS_PURE_HELD_V6_FIXTURE4_SOURCE_ONLY',actualOperations=0,fixedCases=4,refusedMutants=neg,actualJournalASTGuardBranches=4,original30Deadline=True,sourceCapsuleMechanismsChecked=4,futureBuildNotInvented=True),indent=2))
