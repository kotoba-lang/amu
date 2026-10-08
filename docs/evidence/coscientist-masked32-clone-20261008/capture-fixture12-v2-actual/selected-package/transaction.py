"""Explicit parent-to-worker lease. Thread start exceptions never establish absence."""
class SetupFailure(Exception):
 def __init__(self,cause,capture,readOwnership):
  super().__init__(repr(cause));self.capture=capture;self.readOwnership=readOwnership
def setup(pipe,close,construct,start):
 reads={};writes={};cap=None
 try:
  for name in ['stdout','stderr']:
   r,w=pipe();reads[name]=r;writes[name]=w
  cap=construct(reads);start(cap)
  # Grant is an explicit one-way decision, not inferred from thread ident or start return.
  cap.grant();return cap,writes
 except BaseException as ex:
  parentOwns=cap is None or cap.deny_pending()
  errors=[]
  for fd in writes.values():
   try:close(fd)
   except BaseException as err:errors.append(repr(err))
  if parentOwns:
   for fd in reads.values():
    try:close(fd)
    except BaseException as err:errors.append(repr(err))
  # A denied late-starting worker can acknowledge later but can never touch reads.
  if cap is not None:cap.refuse('setup-failure')
  failure=SetupFailure(ex,cap,'parent-denied'if parentOwns else'worker-granted')
  failure.cleanupErrors=errors;raise failure from ex
