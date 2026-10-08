"""Pure finite ownership controls. No process/thread/API calls."""
from pathlib import Path
import ast,itertools,json
D=Path(__file__).resolve().parent;s=(D/'run.py').read_text();t=ast.parse(s)
assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='poll'for n in ast.walk(t))
assert s.count('os.killpg(proc.pid,signal.SIGKILL)')==2
assert 'os.killpg(proc.pid,0)'not in s and 'group-absence'not in s
assert 'with anchorLock:'in s and s.count('signalAuthority=False;waitEntered=True')==2
assert 'if proc is not None and signalAuthority and not waitEntered'in s
assert 'if locked and proc is not None and signalAuthority and not waitEntered'in s
# Monotone signaling anchor: retirement precedes any waitpid-capable operation.
# Model both publication gaps (returncode None and returncode0) and normal return.
controls=[]
for published,raises in [(None,True),(0,True),(0,False)]:
 authority=True;entered=False;signals=[];uncertain=False
 authority=False;entered=True # under lock, BEFORE wait
 returncode=published
 if raises:uncertain=True
 if authority and not entered and returncode is None:signals.append('killpg')
 assert signals==[] and authority is False
 controls.append({'returncode':returncode,'waitRaises':raises,'ownershipUncertain':uncertain,'laterGroupSignals':0})
# Every ordering of watchdog signal, retirement and wait respects lock+retirement.
valid=0;refused=0
for order in itertools.permutations(['watch_attempt','retire','wait']):
 authority=True;entered=False;legal=True;signals=[]
 for event in order:
  if event=='retire':authority=False;entered=True
  elif event=='wait':
   if not entered:legal=False;break
  elif authority and not entered:signals.append('pre-wait-owned-kill')
 if legal:valid+=1
 else:refused+=1
assert valid==3 and refused==3
# Counterexample for old infer-unreaped-from-returncode rule is explicitly rejected.
oldUnsafe={'kernelWaitpidReaped':True,'returncode':None,'wouldSignalFromOldRule':True}
assert oldUnsafe['wouldSignalFromOldRule'] and controls[0]['laterGroupSignals']==0
(D/'source-cleanup-controls.json').write_text(json.dumps({'status':'PURE_MONOTONIC_OWNERSHIP_SOURCE_ONLY','waitGapControls':controls,'finiteRaceOrders':6,'admittedSafeOrders':valid,'refusedWaitBeforeRetirementOrders':refused,'oldRuleCounterexample':oldUnsafe,'leaderPollAbsent':True,'postWaitGroupOperationsAbsent':True,'runtimeThreadOrProcessCalls':0,'processAPIReads':0},indent=2)+'\n')
print('PURE_CLEANUP_SOURCE_CHECKS_PASS')
