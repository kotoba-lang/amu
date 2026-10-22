from pathlib import Path
import json,hashlib,tarfile,subprocess
r=Path('/Users/junkawasaki/github/wt/amu-seed17');w=Path('/private/tmp/amu-loop-temp-registers-20261006');d=r/'docs/evidence/coscientist-loop-temp-registers-20261006';d.mkdir(parents=True);load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();t=load(w/'timing-summary.json');assert len(t['entries'])==1 and not t['entries'][0]['qualifies'];assert (r/'seed/41-a64gen.kotoba').read_bytes()==(w/'baseline-41-a64gen.kotoba').read_bytes();o=load(w/'register-observation.json');mapped=[(e['workload'],f) for e in o['entries'] for f in e['functions'] if f['additionalTempRegisters']];assert len(mapped)==1 and mapped[0][1]['additionalTempRegisters']==2
s={'status':'rejected-loop-produced-high-temp-register-allocation-after-fresh-timing','baselineSourceCommit':load(w/'hypothesis.json')['sourceCommit'],'decision':'Only originalmatmult changes; other18 byte-equal current product. New2register machine differs from previous3register machine. Fresh30accepted triples fail unchanged ratio+summedSD rule. Reject prototype, do not retime identical machine.','hypothesis':load(w/'hypothesis.json'),'generations':load(w/'generations.json'),'codeChanges':load(w/'code-change.json'),'preflight':load(w/'preflight-audit.json'),'nativeAllocationObservation':o,'instructionAudit':load(w/'instruction-audit.json'),'guardProof':load(w/'guard-proof.json'),'authoringCorrections':load(w/'authoring-corrections.json'),'timing':t,'productChanged':False,'officialEmbenchScore':False,'COrBetter':False,'productGatesAndIntegration':'Not rerun after performance rejection; current qualified loop-high-temp product remains unchanged.'}
for n,key in [('permanent-regression-proof.json','permanentRegression'),('ports-state.json','original19State'),('callee-proof.json','additionalLoopCalleeProof'),('import-proof.json','actualAllocatingOpenImportProof'),('resource-proof.json','resourcePartialWrites')]:v=load(w/n);s[key]={k:x for k,x in v.items() if k not in ['runs','observations']}
(d/'summary.json').write_text(json.dumps(s,indent=2)+'\n');(d/'archive.py').write_bytes(Path(__file__).read_bytes());(d/'timing-summary.json').write_bytes((w/'timing-summary.json').read_bytes());q=subprocess.run(['git','diff','--no-index',str(w/'baseline-41-a64gen.kotoba'),str(w/'41-a64gen-prototype.kotoba')],capture_output=True,text=True);assert q.returncode==1;(d/'prototype.diff').write_text(q.stdout)
next={'status':'registered-not-implemented-or-measured','hypothesis':'Compose a closed high-depth affine expression: exact LGET t localA; CONST t+1 c; integer MUL t; LGET t+1 localB; integer ADD t; integer ADD t-1 with a known small constant prefix. Emit existing enc-madd plus immediate prefix add directly to original final destination, eliminating intermediate high homes and redundant reloads. Keep original frame/local assignment/no new callee registers.','nativeStructuralCensus':load(w/'next-fusion-census.json'),'generalAdmission':'No workload names. Same-function validated loop, high temp>=7, exact integer opcode/operand records, register-resident valid local slots, known prefix descriptor and immediate range, proof that consumed high temps are killed before later reads with bounded scan, original alias/coalescing bookkeeping and final folded LSET skip count. Unknown shapes/labels/liveness/resources refuse to original path. Preserve existing scalar-tree state14.','evidence':'Current quiet native census identifies two structural sequences in originalmatmult FN5 SIR3291/3300 with factors20/prefix800/1200. Structural match is not compiler admission or timing. Existing enc-madd is available in seed/40-a64enc.','requiredProof':'Independent i64 modular overflow/negative/zero/extreme arguments; live prefix homes/registers; local aliases/coalescing; RET2/future temp reads causing refusal; call/branch/loop imports/resources/fuel/traps; native fixedpoint; current402/7989 regressions; all19source/result/fuel/actual-byte admission beforefresh prospective timing. No result cache/check hoisting/benchmark changes.','measurement':'Each changed original guest new quiet30triples, RSD<=10%, ratio>=1.05 and gap>sumSD. New machine must differ from rejected2reg/3reg machines. Performance pass thenpermanent guards/gates/integrated3gen/percasecorpus beforepromotion.','goal':'C-or-better remains all19 original aligned workloads, not officialscores.'};(d/'next-hypothesis.json').write_text(json.dumps(next,indent=2)+'\n')
with tarfile.open(d/'native-proof.tgz','w:gz') as a:
 for x in sorted(w.iterdir()):
  if x.name in ['__pycache__','collected','timing-package','permanent-regression-run','batch-status.json','remote-timing.log']:continue
  if x.name.startswith('timing-audit-') or x.name.startswith('timing-artifact-audit-'):continue
  a.add(x,arcname=x.name)
 for n in ['seed/MANIFEST','seed/SIR','seed/HEADS','seed/MEMORY-MAP','AGENTS.md','seed/41-a64gen.kotoba','seed/40-a64enc.kotoba','tools/kexe_loader.c','scripts/seed/a64gen-fixtures.py','seed/tests/unit/41-a64gen.expected']:a.add(r/n,arcname='baseline-source/'+n)
 for n in ['clobber-state-loader.c','clobber-state-loader']:a.add(Path('/private/tmp/amu-context-call-20261005')/n,arcname='diagnostic/'+n)
with tarfile.open(d/'timing.tgz','w:gz') as a:
 for n in ['remote-timing.py','timing-package','audit-workload.py','timing-artifact-audit.py','timing-summary.json','batch-status.json','remote-timing.log']:a.add(w/n,arcname=n)
 for x in sorted(w.iterdir()):
  if x.name.startswith('timing-audit-') or x.name.startswith('timing-artifact-audit-'):a.add(x,arcname=x.name)
(d/'checksums.sha256').write_text(''.join(sha(x)+'  '+x.name+'\n' for x in sorted(d.iterdir()) if x.is_file() and x.name!='checksums.sha256'));v=t['entries'][0];z=v['summary']
report='''# Loop-produced high-temp registers: rejected experiment

Native materialization evidence narrows register allocation to dynamic arithmetic
inside actual backward regions. Only1 original function/2 temps are admitted;
other18 guests equal current product. The new machine passes semantics but its
fresh30-triple timing still fails the unchanged variation criterion. Reject it;
current qualified product stays at `affb9855665f6cb0cbe1d97a5803ac6efdb50b65`.
C-or-better across all19 remains unachieved. These are not official Embench scores.

[Summary](evidence/coscientist-loop-temp-registers-20261006/summary.json),
[raw timing summary](evidence/coscientist-loop-temp-registers-20261006/timing-summary.json),
[checksums](evidence/coscientist-loop-temp-registers-20261006/checksums.sha256).
Archives preserve actual source/unity, native generations, observations/guest
machines, guard failure repairs, independent state oracles, pinned C/runner/spec
and all accepted/rejected measurement rows.

## Native implementation and proof

A bounded function scan accepts a non-coalesced high integer ADD/MUL result from
adjacent LGET/CONST producers only within a validated same-function backward
region. Trivial constants0/1/-1 refuse. Highest admitted temp bounds a contiguous
mapped range; original local allocation/frame/outgoing area remain unchanged.
Added callee registers save/restore in the original mapped temp homes. Existing
state14 tree flag is untouched. There are no source/workload names or result
caches. Experimental Kotoba algorithm and independent hand-fixture authoring are
one-off exceptions to mechanical refactoring; product source stays unchanged.

Generation1 is813824B. Native generations2/3/4 are byte-identical813816B, SHA-256
`74ee0950a44723c45266e3ccca51326c7b658d8a28d0b04c4d9a813c0829bfb4`.
Actual native observation and exact guest/entry equality admit only matmult FN5,
temps7/8 in x24/x25. Independent instruction audit verifies original frame and
one exact save/restore each at disjoint backup offsets80/72. Candidate10308B
machine differs from rejected10316B three-register machine; no identical-code
retiming. All18 other guest bytes equal current product.

All402 permanent fixtures/7989 native runs pass unchanged expectations/golden,
with real/test code/literals/function offsets equal.750 independent deep-expression
full-state comparisons now explicitly enclose producers in one-iteration loops,
including extra backedge fuel in the oracle. Depths8/10/17/31/63, caller locals
occupying all10 callee registers, nested calls, tail calls, RET2/RES2, joins, leaf
bodies, allocating calls and partial fuel pass with actual added save/restores
independently verified for all30 new cases.96 real allocating open imports,
40 resource exhaustion/partial-write comparisons and209 full/partial-fuel states
of original19 pass:1095 additional state comparisons before timing.

Nine fresh native guard checks cover actual hot admission, cold/constant/trivial/
coalesced refusal, zero budget, wrong label record, foreign label position and
wrong function start. Failure sum is bounded0..9; command exit0 proves all pass.
Initial proof authoring duplicated the standard main wrapper, then expected
scalar stdout from command mode. Correct the proof to define seed-main and use
its bounded failure exit; compiler/guard expectations unchanged. Initial scripts
and failures remain archived. Source/goldens/launcher/rung/wire grants unchanged.

## Fresh timing and rejection

Apple M4 zebulun, original matrix/source and pinned C/runner/spec.30 accepted
rotating current-product/new-candidate/C triples of33 attempts. Independent audit
recomputes every mean/SD/order/rejection and verifies source/machine/offset/C/
runner/native preflight pins. Load<=4, background idle>=90%, intervals sufficient,
allRSD<=10%. Promotion also needs ratio>=1.05 and meanGap>summedSD.

|Original workload|Product ns/body|Candidate ns/body|C ns/body|Shorter time|Qualifies|
|---|---:|---:|---:|---:|---|
'''
report+=f"|matmult-int|{z['baseline']['meanNsPerBody']:.2f}|{z['candidate']['meanNsPerBody']:.2f}|{z['C']['meanNsPerBody']:.2f}|{v['savedTimeFraction']*100:.2f}%|No|\n"
report+=f"\nMean gap{v['meanGapNs']:.2f}ns is below summedSD{v['summedSdNs']:.2f}ns.\nCandidate/C execution-time ratio is{z['candidateOverC']:.2f}. No speedup adopted,\nno freshall19 aggregate, no gates/integration rerun for rejected source.\n"
report+='''
## Next registered hypothesis

Current native SIR has two closed high-depth affine expressions with known prefix:
local*constant+local+prefix. Existing enc-madd can compose their arithmetic and
avoid intermediate homes without extra callee saves. Validate exact integer
shape, local mappings, actual prefix descriptor, same-function loop, bounded
liveness (including future RET2/read refusal), aliases/coalescing and final skip
bookkeeping before a new machine. Structural matches are not admission or
measured time shares. [Next hypothesis](evidence/coscientist-loop-temp-registers-20261006/next-hypothesis.json).
''';(r/'docs/coscientist-loop-temp-registers-20261006.md').write_text(report)
p=r/'docs/coscientist-content-address-20261005.md';text=p.read_text();head='''Latest experimental follow-up: [loop-produced high-temp registers](coscientist-loop-temp-registers-20261006.md)
uses [fresh native spill census](coscientist-temp-materialization-census-20261006.md)
to admit only1 originalfunction/2temps. Native fixedpoint,7989 regressions,
1095 extra state comparisons and9 guard checks pass. Fresh30triples show9.96%
shorter mean but fail unchanged summed-variation criterion; product unchanged.
Next compose closed affine expression arithmetic and intermediate homes, without
new callee saves, after exact shape/liveness/alias proofs.

''';p.write_text(text.replace('# Content identity, computation identity, and native performance\n\n','# Content identity, computation identity, and native performance\n\n'+head,1));print('PASS rejected new-machine experiment, raw evidence and next affine-fusion hypothesis archived')
