"""Independent pure mocks/source checks; zero thread/FD/kernel/native operations."""
from pathlib import Path
import importlib.util,json
D=Path(__file__).parent;S=D/'pure-copy'
spec=importlib.util.spec_from_file_location('own',S/'ownership.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Stream:
 def __init__(self):self.closed=False
 def close(self):self.closed=True
class Worker:
 def __init__(self):self.joined=[]
 def join(self,t):self.joined.append(t)
 def is_alive(self):return True
stream=Stream();p=m.HeldProtocol(stream,100,0,'a'*64,'b'*64,lambda row:True);p.worker=Worker()
try:p.close()
except m.Refusal as ex:assert str(ex)=='ownership worker stopped'
else:raise AssertionError('unacked close unexpectedly accepted')
assert stream.closed and p.worker.is_alive() and p.worker.joined==[0]
# The real caller catches close refusal then continues to fsync/close/hash journal.
s=(S/'native-call.py').read_text();a=s.index('if protocol is not None:protocol.close()');b=s.index("r['ownershipJournal']=hfile(oj,65536)")
assert "except BaseException as ex:failure=failure or'ownership-cleanup:'" in s[a:b]
assert 'for file in [limitFile,memoryFile,ownershipFile]'in s[a:b]
assert 'ownershipStopAcknowledged'not in s
c=(S/'kexe_loader_diagnostic.c').read_text();supervise=c[c.index('static int supervise(pid_t child)'):c.index('static int supervise(pid_t child)')+10000]
assert 'if (oh_arm_deadline(0) != 0) return 78;'in supervise and 'if (oh_exit_held(child) != 0) return 78;'in supervise
assert 'oh_abort_unwaited'in c and 'oh_abort_unwaited'not in supervise
# Normal successful path retirement is correctly ordered before reaping.
assert supervise.index('supervised_pid = -1;')<supervise.index('pid_t result=waitpid(child,&status,0)')
assert supervise.index('oh_exit_held(child)')<supervise.index('supervised_pid = -1;')
# Parent control handle is not durably recorded before a possibly failing peer close.
assert s.index('peer.close();peer=None;r[\'pid\']=proc.pid')>s.index('proc=subprocess.Popen(')
result={'status':'PASS_PURE_INDEPENDENT_FAILURE_BRANCH_REPRODUCTION_ONLY','unackedReceiptWorkerCloseRefused':True,'socketClosedBeforeUnackedJoin':True,'callerStillClosesAndHashesReceiptJournal':True,'CExitHeldAndArmFailuresHaveNoExactChildCleanupInSupervise':True,'normalSignalRetirementBeforeReapOrdered':True,'PopenPIDPublicationAfterFalliblePeerClose':True,'actualOperations':0}
(D/'injected-controls-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
