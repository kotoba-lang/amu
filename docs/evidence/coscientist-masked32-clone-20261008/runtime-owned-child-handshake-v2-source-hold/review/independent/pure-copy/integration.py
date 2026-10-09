"""Inert integration hooks. No native/process/group invocation or runnable pilot."""
class TransferFailure(Exception):
 def __init__(self,cause,capture,readOwnership,cleanup):
  super().__init__(repr(cause));self.capture=capture;self.readOwnership=readOwnership;self.cleanup=cleanup
def transfer_popen_reads(streams,duplicate,close_fd,construct,start,cleanup_deadline,clock):
 """Caller exclusively owns unbuffered Popen streams; worker receives duplicates only."""
 assert set(streams)=={'stdout','stderr'}
 reads={};cap=None;cleanup=[]
 try:
  for name in ['stdout','stderr']:
   assert not streams[name].closed
   reads[name]=duplicate(streams[name].fileno())
  # Close original Python wrappers before grant. Their later close is idempotent;
  # they never retain an owning reference to a worker readFD number.
  for s in streams.values():s.close();assert s.closed
  cap=construct(reads);start(cap);cap.grant();return cap
 except BaseException as ex:
  parentOwns=cap is None or cap.deny_pending()
  for s in streams.values():
   if not s.closed:
    try:s.close()
    except BaseException as err:cleanup.append('original-close:'+repr(err))
  if parentOwns:
   for fd in reads.values():
    try:close_fd(fd)
    except BaseException as err:cleanup.append('duplicate-close:'+repr(err))
  if cap is not None:
   cap.refuse('pipe-transfer-failure')
   if not parentOwns:
    # Grant may have completed before KeyboardInterrupt. Only worker closes reads.
    try:
     if not cap.join_once(max(0,cleanup_deadline-clock())):cleanup.append('worker-stop-ack-unavailable')
    except BaseException as err:cleanup.append('worker-stop-ack:'+repr(err))
  raise TransferFailure(ex,cap,'parent-denied'if parentOwns else'worker-granted',cleanup)from ex

from ownership import POLICY
MEMORY_POLICY=POLICY
ALLOWED_ESRCH_STAGES={'leader-getpgid','member-getpgid','member-rusage'}
def classify_memory(record):
 assert record['policy']==MEMORY_POLICY
 owned=(record['heldOwnershipQualified']is True and record['exactHeldChildWait0']is True and record['initialHeldSamples']==2 and record['acceptedLeaderBirthBound']is True and record['acceptedSamples']>=2 and record['otherRefusals']==[] and record['completePipeEOF']is True and record['stoppedClosedCapture']is True and record['rawTruncated']is False and record['captureErrors']==[] and record['exactDirectChildWait']=='closed0'and record['waitUncertain']is False and record['withinOriginalDeadline']is True and record['groupAuthorityRetired']is True and record['groupOperationsAfterWait']==record['groupOperationsAfterUncertainty']==0 and record['loaderWaitProtocolPinned']is True)
 if not owned:return {'status':'refused','hardPeakQualified':False}
 if record['failure']is None:return {'status':'held-launch-sampled-observations-only','hardPeakQualified':False,'sampleCompleteness':'finite-samples-only'}
 if record['freshKnownFailureVerified']is True:return {'status':'held-launch-owned-termination-gap','missingFootprint':None,'zeroSynthesized':False,'hardPeakQualified':False,'sampleCompleteness':'gap-unavailable'}
 return {'status':'refused','hardPeakQualified':False}
