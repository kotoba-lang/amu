"""Pure inductive model: capacity-bounded generic equal-frame edges, arbitrary volatile helper results."""
import json,copy
from pathlib import Path
from model import initial,original,fused,observe
D=Path(__file__).parent
result=[]
for F in [80,96]:
 a=initial(F);b=copy.deepcopy(a)
 for edge in range(1,512):
  # Same opaque helper transformation on both equal inputs. ABI preserves x19/frame/header; arbitrary caller-clobbered regs/flags and guest effects allowed.
  for q in [a,b]:
   for r in range(19):q['regs'][f'x{r}']=f'arbitrary-helper-{edge}-r{r}'
   q['regs']['x7']='opaque-context';q['regs']['x9']=f'arbitrary-return-vector-{edge}';q['regs']['x30']=f'arbitrary-helper-LR-{edge}';q['NZCV']=f'arbitrary-helper-flags-{edge}';q['guestMemory']=f'arbitrary-identical-helper-effects-{edge}'
  a=original(a,F);b=fused(b,F);assert a==b
  for fuel in [0,1,2,2**64-1]:assert observe(a,fuel)==observe(b,fuel)
  result.append({'F':F,'edge':edge,'allRegistersFlagsFullMemoryFuelTrapEqual':True})
 # Each original public entry still runs unchanged and has identical original ABI, no alternative skip applies.
 assert b['memory']['header',8]=='arbitrary-caller-LR'and b['memory']['frame',0]=='arbitrary-caller-x19'
q={'status':'PASS_PURE_511_STEP_EQUAL_FRAME_MODEL_ONLY','edgesPerHomogeneousFrame':511,'cases':result,'induction':'equality at each target parameter instruction plus unchanged helper ABI transformation implies equality for the next transition; saved header callerLR and caller-x19 home persist; each fusion reloads LR even after helper clobber','crossFrameAllowed':False,'bareNOPAllowed':False,'observableState':'all31GPR/SP/NZCV/header/home/guestMemory/fuel and synchronous trap state remain exact under single-edge model privateframe/ABI premises','nativeCalls':0,'privateFrameUniversalABIQualified':False}
(D/'compose-model-result.json').write_text(json.dumps(q,indent=2)+'\n');print(q['status'])
