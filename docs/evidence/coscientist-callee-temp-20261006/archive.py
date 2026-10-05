from pathlib import Path
import json,hashlib,tarfile,subprocess
r=Path('/Users/junkawasaki/github/wt/amu-seed17');w=Path('/private/tmp/amu-callee-temp-20261006');d=r/'docs/evidence/coscientist-callee-temp-20261006';d.mkdir(parents=True,exist_ok=True);load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();t=load(w/'timing-summary.json');assert len(t['entries'])==6 and all(not x['qualifies'] for x in t['entries']);assert (r/'seed/41-a64gen.kotoba').read_bytes()==(w/'baseline-41-a64gen.kotoba').read_bytes()
s={'status':'rejected-unused-callee-register-allocation-for-high-temps','baselineSourceCommit':load(w/'hypothesis.json')['sourceCommit'],'decision':'All six changed original guests freshly measured; none meets unchanged ratio>=1.05 and meanGap>sumSD. Reject prototype and keep current qualified loop-high-temp product. No identical-machine retiming.','hypothesis':load(w/'hypothesis.json'),'generations':load(w/'generations.json'),'codeChanges':load(w/'code-change.json'),'preflight':load(w/'preflight-audit.json'),'nativeAllocationObservation':load(w/'register-observation.json'),'timing':t,'productChanged':False,'officialEmbenchScore':False,'COrBetter':False,'productGatesAndIntegratedProof':'Not rerun after performance rejection; experimental compiler not promoted.','authoringCorrection':'Callee backup audit initially demanded offset>=16 for every function. For leaf functions with zero callee locals the original save region has zero bytes. Corrected independent non-overlap condition to offset>=8*localnsv; verified exact save/restore instructions and original frame. Compiler and execution oracles unchanged. Initial script/log retained.','depthHypothesisCorrection':'Historical native SIR matched to fresh allocation metadata shows all declared high depths actually named. No unnecessary declared-depth-only capacity found. Instead MD5 two and SHA two vector initializer functions have only constant definitions plus VEC/RET: original descriptors avoid materializing high values; new callee save/restore adds cost without replacing expression spills.'}
for n,key in [('permanent-regression-proof.json','permanentRegression'),('ports-state.json','original19FullState'),('callee-proof.json','additionalCalleeProof'),('import-proof.json','allocatingOpenImportProof'),('resource-proof.json','resourcePartialWriteProof')]:v=load(w/n);s[key]={k:x for k,x in v.items() if k not in ['runs','observations']}
(d/'summary.json').write_text(json.dumps(s,indent=2)+'\n');(d/'timing-summary.json').write_bytes((w/'timing-summary.json').read_bytes());(d/'archive.py').write_bytes(Path(__file__).read_bytes());q=subprocess.run(['git','diff','--no-index',str(w/'baseline-41-a64gen.kotoba'),str(w/'41-a64gen-prototype.kotoba')],capture_output=True,text=True);assert q.returncode==1;(d/'prototype.diff').write_text(q.stdout)
next={'status':'registered-not-implemented-or-measured','hypothesis':'Select additional callee registers using actual canonical high-temp materialization/read counts and validated loop weights, rather than named depth alone. Preserve original local allocation and frame. Exclude proven straight-line constant-only vector initializer temps that remain deferred constants and never replace a spill. A bounded compiler census must establish actual emitting paths/descriptor transitions before defining a profitability gate.','evidence':load(w/'actual-depth-analysis.json'),'negativeTiming':[{k:v for k,v in x.items() if k!='summary'} for x in t['entries']],'requiredNextEvidence':'Fresh native observation of high-temp gn-mat/gn-fin/gn-sr and original load/store emission, SIR position, descriptor/coalescing/branch/call and loop membership. Observer guest bytes equal current product; counts are not runtime shares. Then register a general admission policy and independently prove canonical homes/register backups/aliases/joins/calls/indirect/tail/RET2/imports/resources/fuel/traps.','measurement':'Every changed original guest requires fresh prospective30triples, stable ratio>=1.05 and meanGap>sumSD; no repeats of identical machines to seek a pass. Current product baseline is loop-high-temp seed/image.','goal':'C-or-better across all19 original aligned workloads, unchanged scope, not official scores.'};(d/'next-hypothesis.json').write_text(json.dumps(next,indent=2)+'\n')
with tarfile.open(d/'native-proof.tgz','w:gz') as a:
 for x in sorted(w.iterdir()):
  if x.name in ['__pycache__','collected','timing-package','permanent-regression-run','batch-status.json','remote-timing.log']:continue
  if x.name.startswith('timing-audit-') or x.name.startswith('timing-artifact-audit-'):continue
  a.add(x,arcname=x.name)
 for n in ['seed/MANIFEST','seed/SIR','seed/HEADS','seed/MEMORY-MAP','AGENTS.md','seed/41-a64gen.kotoba','tools/kexe_loader.c','scripts/seed/a64gen-fixtures.py','seed/tests/unit/41-a64gen.expected']:a.add(r/n,arcname='baseline-source/'+n)
 for n in ['clobber-state-loader.c','clobber-state-loader']:a.add(Path('/private/tmp/amu-context-call-20261005')/n,arcname='diagnostic/'+n)
 for e in load(w/'actual-depth-analysis.json')['entries']:
  name=e['workload'];a.add(Path('/private/tmp/amu-loop-region-census-20261006/meta-ports')/name/'compile.log',arcname='historical-native-SIR/'+name+'.log')
with tarfile.open(d/'timing.tgz','w:gz') as a:
 for n in ['remote-timing.py','timing-package','audit-workload.py','timing-artifact-audit.py','timing-summary.json','batch-status.json','remote-timing.log']:a.add(w/n,arcname=n)
 for x in sorted(w.iterdir()):
  if x.name.startswith('timing-audit-') or x.name.startswith('timing-artifact-audit-'):a.add(x,arcname=x.name)
(d/'checksums.sha256').write_text(''.join(sha(x)+'  '+x.name+'\n' for x in sorted(d.iterdir()) if x.is_file() and x.name!='checksums.sha256'))
report='''# Unused callee registers for high expression temps: rejected experiment

All six changed original Embench guests fail the unchanged prospective promotion
rule. Keep the qualified loop-contained high-read product at source commit
`affb9855665f6cb0cbe1d97a5803ac6efdb50b65`; no product algorithm/golden/launcher
change. C-or-better across all19 originals remains unachieved. These are aligned
native body timings, not official Embench scores.

[Summary](evidence/coscientist-callee-temp-20261006/summary.json),
[raw timing summary](evidence/coscientist-callee-temp-20261006/timing-summary.json),
[checksums](evidence/coscientist-callee-temp-20261006/checksums.sha256).
Native/timing archives contain scripts, source/unity, four native generations,
actual machines, full observations, per-case outputs, C artifacts, original
source/runner/spec pins and all accepted/rejected timing rows.

## Hypothesis and native proof

Use x19..x28 left unused by original local allocation for canonical expression
temps7+, keeping the original frame and local allocation. Save/restore added
registers in their original temp home slots; those mapped homes hold caller
backups and cease to store expression values. Low caller-register call saves
stay unchanged. New experimental Kotoba algorithm authoring is a one-off hand
exception; no mechanical refactor rule covers it. Product source is unchanged.

Generation1 is812776B. Generations2/3/4 are byte-identical813176B, SHA-256
`a9dfcc6c1dce58679782baf40b5d73d88126c5ffef008b60a5038187aee8aa82`.
Fresh native observation on all19 compiles identifies14 admitted functions across
six workloads and proves observer/quiet guest bytes/entry offsets equal. Every
register backup offset is disjoint from original callee saves; original frame
sizes stay unchanged. Independent native instruction audits check exact added
save/restore instructions on30 new deep-expression cases.

All402 permanent fixtures/7989 runs pass with existing expectations/golden
unchanged and real/test code/literal/entry layout equal. Additional750 independent
full-state comparisons cover depths8/10/17/31/63, caller locals occupying all10
callee registers, nested calls, joins, leaf bodies, allocations, tail calls, RET2/
RES2 and partial fuel.96 actual allocating replacement-import comparisons and40
resource exhaustion/partial-write comparisons pass.209 full/partial-fuel states
of all19 original workloads equal current qualified product, with canonical
source hashes and original results/fuel unchanged. Thus1095 additional full-state
comparisons were sealed along with7989 regressions before timing.

The authoring audit initially required offset>=16 for every function. Leaf
functions with no callee locals have no original callee-save region. Corrected
non-overlap bound is offset>=8*localnsv; actual instructions and original frames
are checked. Initial failure/script remain archived; compiler and execution
expectations were not changed.

## Fresh prospective timing

Apple M4 zebulun, same pinned runner/C/original sources/spec.30 accepted rotating
product/candidate/C triples per changed guest;180 accepted of188 attempts total.
Rows independently audited for rotating order, load<=4, idle>=90%, interval,
RSD<=10%, source/guest/offset/C/runner/proof pins. Qualification requires both
baseline/candidate>=1.05 and mean gap>summed SD. No retiming of identical machines.

|Original workload|Product ns/body|Candidate ns/body|C ns/body|Shorter time|Qualifies|
|---|---:|---:|---:|---:|---|
'''
for x in t['entries']:
 z=x['summary'];report+=f"|{x['workload']}|{z['baseline']['meanNsPerBody']:.2f}|{z['candidate']['meanNsPerBody']:.2f}|{z['C']['meanNsPerBody']:.2f}|{100*x['savedTimeFraction']:.2f}%|No|\n"
report+='''
Matmult's9.16% shorter mean does not qualify:1683.27ns mean gap is below1823.65ns
summed SD. SHA and UD are slower. The unrestricted prototype is rejected, so
product gates/integrated rebuilding are not rerun for this rejected algorithm.
Other13 original guest binaries equal current product; no fresh19 aggregate.

## Evidence changes the next action

Named capacity is not the problem: historical native SIR matched to fresh
allocation metadata shows the high depths are actually named. MD5's two high
functions and two SHA setup functions each build vectors from only constants
plus VEC/RET (with an entry label). Deferred constant descriptors already avoid
high expression spills, so adding callee saves/restores does not replace that
work. All64/56 named temps are present; the earlier unused-declared-capacity
hypothesis is falsified.

Next observe actual high-temp materialization/reads, descriptor transitions,
coalescing and loop membership before choosing a general profitability policy.
Counts are not measured time shares. A later changed machine needs independent
semantics and fresh prospective timing, then permanent gates/integrated3gen/
per-case corpus proof before promotion. See [registered next hypothesis](evidence/coscientist-callee-temp-20261006/next-hypothesis.json).
'''
(r/'docs/coscientist-callee-temp-20261006.md').write_text(report)
p=r/'docs/coscientist-content-address-20261005.md';text=p.read_text();head='''Latest experimental follow-up: [unused callee registers for high temps](coscientist-callee-temp-20261006.md)
passes native3-generation fixedpoint,7989 existing regressions and1095 additional
full-state comparisons. Allsix fresh30-triple comparisons fail promotion;
matmult's9.16% shorter mean is below summed variation, SHA/UD slower. Product
unchanged. Native SIR falsifies unused declared capacity; constant-only vector
initializers add callee preservation without replacing spills. Observe actual
materialization/loop-weighted use before another allocation policy.

''';p.write_text(text if head in text else text.replace('# Content identity, computation identity, and native performance\n\n','# Content identity, computation identity, and native performance\n\n'+head,1));print('PASS rejected six-guest experiment and raw evidence archived')
