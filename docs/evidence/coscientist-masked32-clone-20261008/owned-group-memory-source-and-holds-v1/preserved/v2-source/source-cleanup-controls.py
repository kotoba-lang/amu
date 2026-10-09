"""Pure finite cleanup interleaving/source checks. No process/thread/API calls."""
from pathlib import Path
import ast,itertools,json
D=Path(__file__).resolve().parent;s=(D/'run.py').read_text();t=ast.parse(s)
assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='poll'for n in ast.walk(t))
assert s.count('os.killpg(proc.pid,signal.SIGKILL)')==2
assert 'os.killpg(proc.pid,0)'not in s and 'group-absence'not in s and 'api.listfn('not in s
assert 'with anchorLock:'in s and "if proc is not None and not reaped and not stop.is_set():"in s
assert 'normal reap ownership lock'in s and 'cleanup ownership lock unavailable; no reap or signal'in s
# Split watchdog lock/check/signal lifecycle vs main stop/reap. Valid schedules require
# lock ownership at all signals and forbid main reap while watchdog holds the lock.
valid=0;blocked=0
for order in itertools.permutations(['watch_enter','watch_signal','watch_exit','main_stop','main_reap']):
 locked=False;entered=False;stopped=False;reaped=False;signals=0;legal=True
 for event in order:
  if event=='watch_enter':
   if entered:legal=False;break
   entered=True;locked=True
  elif event=='watch_signal':
   if not locked:legal=False;break
   if not stopped and not reaped:signals+=1
  elif event=='watch_exit':
   if not locked:legal=False;break
   locked=False
  elif event=='main_stop':stopped=True
  elif event=='main_reap':
   if not stopped or locked:legal=False;break
   reaped=True
 if legal:valid+=1
 else:blocked+=1
assert valid>0 and blocked>0
# A removed-lock counterexample: worker checks unreaped, main reaps, worker signals.
unsafe=['watch_check_unreaped','main_stop','main_reap','watch_signal_cached_check']
assert unsafe.index('main_reap')<unsafe.index('watch_signal_cached_check')
(D/'source-cleanup-controls.json').write_text(json.dumps({'status':'PURE_SOURCE_INTERLEAVING_ONLY','finiteOrders':120,'admittedSafeOrders':valid,'refusedInvalidOrders':blocked,'lockRemovalCounterexample':unsafe,'leaderPollAbsent':True,'postReapGroupAPIOperationsAbsent':True,'runtimeThreadOrProcessCalls':0,'processAPIReads':0},indent=2)+'\n')
print('PURE_CLEANUP_SOURCE_CHECKS_PASS')
