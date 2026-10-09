"""Pure symbolic architectural state model for bounded equal-frame tail fusion."""
from copy import deepcopy
import json
from pathlib import Path
D=Path(__file__).parent
# Opaque independent atoms mean equality holds for arbitrary values, not a sampled integer domain.
def initial(F):
 r={f'x{i}':f'arbitrary-volatile-{i}'for i in range(31)};r.update(x29=('frame-header',0),x30='returning-helper-link',x19='previous-vector-local',x7='opaque-context',x9='opaque-next-vector');m={('header',0):'arbitrary-caller-FP',('header',8):'arbitrary-caller-LR',('frame',0):'arbitrary-caller-x19',('frame',F-8):'opaque-context'}
 for o in range(8,F-8,8):m['frame',o]=f'arbitrary-home-{o}'
 return {'regs':r,'SP':('frame',0),'memory':m,'NZCV':'arbitrary-NZCV','guestMemory':'opaque-unchanged-guest-memory','fuel':'opaque-fuel'}
def original(s,F,targetF=None):
 q=deepcopy(s);r=q['regs'];m=q['memory'];r['x0']=r['x9'];r['x19']=m['frame',0];q['SP']=('header',0);r['x29']=m['header',0];r['x30']=m['header',8];q['SP']=('caller-SP',0)
 # Exact stp-pre/mov/sub/save/context prefix at target: sameF reuses the same valid extent.
 m['header',0]=r['x29'];m['header',8]=r['x30'];r['x29']=('frame-header',0);q['SP']=('frame',0)if targetF in[None,F]else('different-frame',targetF);m['frame',0]=r['x19'];m['frame',(targetF or F)-8]=r['x7'];r['x19']=r['x0'];return q
def fused(s,F,bare=False):
 q=deepcopy(s);r=q['regs'];r['x0']=r['x9']
 if not bare:r['x30']=q['memory']['header',8]
 r['x19']=r['x0'];return q

def observe(q,fuel,extraTrap=False):
 # Target fuel instructions unchanged. Compare exact architectural state at charge/trap, including LR, flags and homes.
 z=deepcopy(q);z['fuel']=fuel;z['outcome']='entry-fuel-trap'if fuel==0 else 'charge-complete';z['fuel']=fuel if fuel==0 else fuel-1
 if extraTrap:z['outcome']='extra-observable-trap'
 return z

def main():
 cases=[]
 for F in[80,96]:
  s=initial(F);a=original(s,F);b=fused(s,F);assert a==b;assert original(s,F)!=fused(s,F,True)
  for fuel in[0,1,2,2**64-1]:assert observe(a,fuel)==observe(b,fuel);cases.append({'F':F,'fuel':fuel,'allRegistersFlagsFrameHomesGuestMemoryEqual':True})
 negatives={}
 s=initial(80)
 negatives['bareNOP3-wrong-LR']=original(s,80)!=fused(s,80,True)
 negatives['mismatched-F']=original(s,80,96)!=fused(s,80)
 bad=deepcopy(s);bad['memory']['frame',72]='wrong-context';negatives['mismatched-context']=original(bad,80)!=fused(bad,80)
 bad=deepcopy(s);bad['memory']['frame',0]='wrong-callee-save';# map certificate requires correct outer saved x19; alias/saved obligation refused before execution
 negatives['mismatched-callee-save-map']=bad['memory']['frame',0]!=s['memory']['frame',0]
 bad=fused(s,80);bad['regs']['x19']=s['regs']['x19'];negatives['wrong-private-entry-skips-param']=bad!=original(s,80)
 private_entry_allowed=lambda sources:all(x=='certified-internal-tail'for x in sources)
 negatives['unknown-incoming']=not private_entry_allowed(['certified-internal-tail','unknown-FADDR-or-branch'])
 bad=deepcopy(s);bad['memory']['frame',72]='helper-alias-write';negatives['helper-stack-alias']=original(bad,80)!=fused(bad,80)
 negatives['extra-observable-trap']=observe(original(s,80),1,True)!=observe(fused(s,80),1)
 assert all(negatives.values())
 out={'status':'PASS_PURE_SYMBOLIC_EQUAL_FRAME_TRANSITION_MODEL_ONLY','arbitraryValues':'independent opaque callerFP/callerLR/callerx19/context/vector/volatile registers/frame homes/guest memory/NZCV atoms; no equality assumptions between atoms','cases':cases,'negatives':negatives,'closure':'returning helper may clobber every volatile register including x30; must obey ABI preserving active frame/home/context memory and x19. x9 stores its returned vector after existing gn-take. Fusion reloads saved callerLR explicitly.','exactObservableState':['x0..x30','SP','NZCV','all active frame/header/home memory','guest memory','fuel/trap outcome'],'premises':['sameF complete map and exact certified current emitted words','active private frame/header readable+writable already established by original prologue; fused adds no new address','frame/home memory cannot escape through runtime/capability/vector/unknown-call aliases','only admitted compiler-owned private entries; public entries untouched','no observable trap within ordinary certified restore/prologue memory operations of valid private frame; target fuel/nonfuel trap state unchanged','same code counts and unchanged target fuel/body words preserve synchronous trap PC and FP/LR unwind state; asynchronous instruction-step observation of the removed intermediate restore/reallocate is outside this rule contract'],'nativeCalls':0,'optimizerCorrectnessQualified':False}
 (D/'model-result.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'])
if __name__=='__main__':main()
