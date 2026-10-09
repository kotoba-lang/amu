"""Pure finite instruction/fuel contract controls, no machine execution."""
from pathlib import Path
import json
MASK=(1<<64)-1
PUBLISHED=[0xf1000508,0x54000042,0xd4200000,0xf90004e8]
INIT=0xf94004e8
# Instruction models restrict only this SUBS/BHS/BRK/STR sequence.
def generic(ctx):
 x=(ctx-1)&MASK;carry=ctx>=1
 return {'trap':not carry,'ctx':x if carry else ctx,'debit':1 if carry else 0}
def cached(x8,ctx,branchWords=2):
 x=(x8-1)&MASK;carry=x8>=1
 assert branchWords==2,'BHS must land on STR, not past publication'
 if not carry:return {'trap':True,'ctx':ctx,'x8':x,'debit':0}
 return {'trap':False,'ctx':x,'x8':x,'debit':1}
def controls():
 cases=0
 for fuel in [0,1,2,3,7,2**63-1,2**63,2**64-1]:
  for ticks in range(9):
   x8=fuel;ctx=fuel;off=fuel
   for _ in range(ticks):
    a=generic(off);b=cached(x8,ctx);assert all(a[k]==b[k]for k in ['trap','ctx','debit']);cases+=1
    if a['trap']:break
    off=a['ctx'];ctx=b['ctx'];x8=b['x8']
    # Any original nonfuel trap after this prefix observes same published context.
    assert off==ctx
 # Invalid cache/context certificates have concrete counterexamples, not acceptance.
 assert cached(5,0)['ctx']!=generic(0)['ctx'] # unknown external context write, stale x8.
 assert cached(99,5)['ctx']!=generic(5)['ctx'] # unclosed x8 writer.
 try:cached(1,1,3)
 except AssertionError:pass
 else:raise AssertionError('missing publication accepted')
 assert cached(0,0)['trap']and cached(0,0)['ctx']==0
 # Original freg1 private protocol remains byte-expression exact in copied source.
 D=Path(__file__).parent;s=(D/'41-a64gen-candidate.kotoba').read_text();offsrc=(D/'41-a64gen-off.kotoba').read_text()
 private='(-> M (gn-emit (enc-subs-i 8 8 1)) (gn-emit (enc-bcond (enc-cond-hs) 3)) (gn-emit (enc-str 31 7 CTX-FUEL)) (gn-emit (enc-brk 0)))'
 assert private in s and private in offsrc
 assert '(cond-> (= (gn-g M gn-f-freg) 1) (gn-emit (enc-str 8 7 CTX-FUEL)))'in s and '(cond-> (= (gn-g M gn-f-freg) 1) (gn-emit (enc-str 8 7 CTX-FUEL)))'in offsrc
 pro=s[s.index('(defn- gn-op-fn2'):s.index('(defn- gn-op-ret')]
 assert pro.index('(sl-clear)')<pro.index('(gn-gs gn-f-freg 2)') and '(and (= leaf 2) (= F 0) (= (gn-g M2 gn-f-fuel) 1))'in pro
 assert 'gn-chain-private'not in s # Actual current fixup is gn-chain-fix + ly-fix-one, not invented symbol.
 # Exact encoder constants are arithmetic witnesses only; actual emitted words still need independent review.
 assert INIT==0xf9400000+(1<<10)+(7<<5)+8
 assert PUBLISHED==[0xf1000000+(1<<10)+(8<<5)+8,0x54000000+(2<<5)+2,0xd4200000,0xf9000000+(1<<10)+(7<<5)+8]
 return {'status':'PASS_FINITE_PURE_FUEL_INSTRUCTION_MODEL_ONLY','finiteComparedTicks':cases,'fuelValues':8,'prefixNonfuelTrapContextParity':True,'zeroFuelTrapContextPreserved':True,'wrongBranchOffsetRefused':True,'staleContextAndX8WriterCounterexamplesFound':True,'privateFreg1AndEpilogueExpressionsUnchanged':True,'initAfterSlClear':True,'candidateInitWord':hex(INIT),'candidateFuelWords':[hex(w)for w in PUBLISHED],'actualEmissionOrClobberCertificateQualified':False,'nativeCompileOrGuestCalls':0,'performanceQualified':False,'C2':False}
if __name__=='__main__':print(json.dumps(controls(),indent=2))
