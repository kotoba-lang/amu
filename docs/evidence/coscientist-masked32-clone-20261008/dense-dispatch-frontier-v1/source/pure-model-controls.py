"""Finite mathematical counterexamples only, never evaluates a benchmark."""
import json,pathlib
vals=[-(1<<63),-(1<<63)+1,-2,-1,0,1,2,(1<<63)-2,(1<<63)-1]
def quadrant(a,b): return (a<b if b<0 else False) if a<0 else (True if b<0 else a<b)
assert all(quadrant(a,b)==((a&((1<<64)-1))<(b&((1<<64)-1))) for a in vals for b in vals)
# Abstract two transition steps: the first updates state before limit comparison.
ordered_state=0
for step in [1,2]:
    ordered_state+=step
    if step==2:break
unsafe_jump_state=2
assert ordered_state==3 and ordered_state!=unsafe_jump_state
# Two original logical frames: first entry succeeds, a write happens, then next
# entry exhausts. A bulk charge before the first write changes the failure prefix.
fuel=1;state=0
fuel-=1;state=7
second_entry_exhausts=(fuel==0)
eager_bulk_exhausts=(1<2);eager_state=0
assert second_entry_exhausts and eager_bulk_exhausts and state!=eager_state
r={'schema':'DENSE_DISPATCH_FINITE_MODEL_CONTROLS/v1','nativeExecution':False,
   'unsignedComparisonBoundaryPairs':81,'unsignedComparisonPairsPass':True,
   'unsafeStepJumpCounterexample':{'orderedState':ordered_state,'jumpState':unsafe_jump_state},
   'unsafeBulkFuelCounterexample':{'orderedFailureState':state,'eagerFailureState':eager_state},
   'claim':'Mathematical/source models only; not full-domain proof or actual native failure evidence'}
(pathlib.Path(__file__).parent/'pure-model-controls.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
