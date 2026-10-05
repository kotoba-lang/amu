from pathlib import Path
import json,hashlib,tarfile,subprocess
r=Path('/Users/junkawasaki/github/wt/amu-seed17');w=Path('/private/tmp/amu-affine-read-direct-20261006');per=Path('/private/tmp/amu-affine-read-direct-permanent-20261006');i=Path('/private/tmp/amu-affine-read-direct-integrated-20261006');p=Path('/private/tmp/amu-affine-read-direct-integrated-20261006-parity');v1=Path('/private/tmp/amu-affine-read-20261006');d=r/'docs/evidence/coscientist-affine-read-direct-20261006';d.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();integ=load(w/'integrated-summary.json');tim=load(w/'timing-audit-matmult-int.json');assert tim['qualifies'] and integ['status']=='complete-3-generations-19-ports-and-per-case-corpus-parity';assert (r/'seed/41-a64gen.kotoba').read_bytes()==(w/'41-a64gen-prototype.kotoba').read_bytes();assert (w/'bootstrap-before.log').read_bytes()==(w/'bootstrap-after.log').read_bytes();gates=[]
for line in (w/'gate-build/gates/r6m/summary.tsv').read_text().splitlines():
 name,status,seconds,detail=line.split('\t',3);gates.append({'gate':name,'status':status,'seconds':float(seconds),'detail':detail})
assert len([x for x in gates if x['status']=='PASS'])==6 and not any(x['status']=='FAIL' for x in gates);assert all(next(x for x in gates if x['gate']==n)['status']=='PASS' for n in ['ERR','G1','G2','G3','G4','G5']);(w/'gate-summary.json').write_text(json.dumps(gates,indent=2)+'\n');assert 'PASS' in (w/'unit-final.log').read_text()
corrections=load(w/'authoring-corrections.json');corrections.update({'fixtureAuthoring':'Preserve copied loader executable mode; use existing gn-a-sreg (slot->register+1, zero=home) in new memory-slot refusal test. Initial failures retained. Original434/9339 test expectations unchanged.','prefixHarness':'Initial exec used separate globals/locals and could not resolve FIX; correct to one namespace. Original402 fixtures/7989 runs compared exactly; compiler/golden/expected semantics unchanged.','unitPath':'Initial standard unit lacked explicit temporary path allowance; set existing SEED_RESOURCES_35 for repo:/private/tmp. Then native unit differed only by new generated fixture image; independent9339 runs and real/test layouts pass before updating golden. Normal native unit passes after reviewed generated golden update.'})
s={'status':'qualified-native-direct-affine-index-checked-read','sourceCommit':integ['sourceCommit'],'baselineSourceCommit':load(w/'hypothesis.json')['sourceCommit'],'decision':'Adopt exact bounded affine-index/read composition: fresh30 accepted triples qualify13.12percent shorter originalmatmult. Other18 exactly previous product. Native4gen,8939 preflight fullstate comparisons,434/9339 permanent table preserving402/7989 original prefix,12 guards, normalunit, ERR/G1-G5, unchanged bootstrap inventory and committed-source integrated3gen/full per-case corpus output parity pass. C-or-better all19 remains unachieved.','hypothesis':load(w/'hypothesis.json'),'generations':load(w/'generations.json'),'codeChanges':load(w/'code-change.json'),'nativePreflight':load(w/'preflight-audit.json'),'nativeInstructionAudit':load(w/'instruction-audit.json'),'observerByteProof':load(w/'observer-byte-audit.json'),'permanent':load(w/'permanent-summary.json'),'permanentPrefixAudit':load(w/'permanent-prefix-audit.json'),'timing':tim,'timingArtifactPins':load(w/'timing-artifact-audit-matmult-int.json'),'gates':gates,'gateCompilerLineage':load(w/'gate-build-lineage.json'),'integration':integ,'fullCheckAndActualExportOutputAudit':{k:v for k,v in load(w/'per-case-output-audit.json').items() if k!='rows'},'authoringCorrections':corrections,'bootstrapProductInventoryUnchanged':True,'productChanged':True,'launcherSwitched':False,'rungRecordChanged':False,'wire20Granted':False,'officialEmbenchScore':False,'COrBetter':False,'freshAll19Aggregate':False}
for n,key in [('permanent-regression-proof.json','preTimingOriginalRegression'),('ports-state.json','original19State'),('read-proof.json','independentReadState'),('effect-proof.json','allocatingImportResourceState'),('effect-alias-proof.json','operandAndHandleAliasResourceState')]:s[key]={k:x for k,x in load(w/n).items() if k not in ['observations','runs']}
(d/'summary.json').write_text(json.dumps(s,indent=2)+'\n');(d/'archive.py').write_bytes(Path(__file__).read_bytes());(d/'timing-summary.json').write_text(json.dumps({'status':'complete-independent-fresh-timing-audit','entries':[tim]},indent=2)+'\n');(d/'next-hypothesis.json').write_bytes((w/'next-hypothesis.json').read_bytes());q=subprocess.run(['git','diff','--no-index',str(w/'baseline-41-a64gen.kotoba'),str(w/'41-a64gen-prototype.kotoba')],capture_output=True,text=True);assert q.returncode==1;(d/'prototype.diff').write_text(q.stdout)
with tarfile.open(d/'native-proof.tgz','w:gz') as a:
 for x in sorted(w.iterdir()):
  if x.name in ['__pycache__','collected','gate-build','timing-package','permanent-unit','permanent-unit-final','permanent-regression-run']:continue
  a.add(x,arcname=x.name)
 for x in sorted(per.iterdir()):
  if x.name in ['__pycache__','permanent-regression-run']:continue
  a.add(x,arcname='new-permanent/'+x.name)
 for n in ['seed/MANIFEST','seed/SIR','seed/HEADS','seed/MEMORY-MAP','AGENTS.md','scripts/seed/a64gen-fixtures.py','seed/tests/unit/41-a64gen.expected','seed/tests/unit/41-a64gen.fixtures.json','seed/tests/unit/41-a64gen_t.kotoba']:a.add(r/n,arcname='committed-source/'+n)
 for n in ['clobber-state-loader.c','clobber-state-loader']:a.add(Path('/private/tmp/amu-context-call-20261005')/n,arcname='diagnostic/'+n)
with tarfile.open(d/'initial-untimed-variant.tgz','w:gz') as a:
 for x in sorted(v1.iterdir()):
  if x.name in ['__pycache__','permanent-regression-run']:continue
  a.add(x,arcname=x.name)
with tarfile.open(d/'timing.tgz','w:gz') as a:
 for n in ['remote-timing.py','timing-package','audit-workload.py','timing-artifact-audit.py','timing-audit-matmult-int.json','timing-artifact-audit-matmult-int.json','batch-status.json']:a.add(w/n,arcname=n)
with tarfile.open(d/'integrated-proof.tgz','w:gz') as a:
 for n in ['gate-summary.json','gates.log','gate-build/gates/r6m','integrated-ports.py','integrated-proof.py','integrated-summary.json','per-case-output-audit.py','per-case-output-audit.json','integrated-parity.log','integrated-ports.log','integrated-build.log']:a.add(w/n,arcname=n)
 for n in ['check.tsv','compile.tsv','exports.tsv']:a.add(p/n,arcname='parity/'+n)
 for x in sorted((p/'run').rglob('*')):
  if x.is_file() and x.suffix in ['.out','.err','.st','.raw']:a.add(x,arcname='parity/'+str(x.relative_to(p)))
 for n in ['inputs','inputs.sha256','input-check.log','objects1.sha','objects2.sha','objects3.sha','ports.json','front1.out','front2.out','front3.out','g1.out','g2.out','g3.out','g3/amu','g3/amu.bin','g3/amu.kseed','g3/tree']:a.add(i/n,arcname='integrated/'+n)
(d/'checksums.sha256').write_text(''.join(sha(x)+'  '+x.name+'\n' for x in sorted(d.iterdir()) if x.is_file() and x.name!='checksums.sha256'))
b=tim['summary'];report=f'''# Direct affine-index checked read: qualified native improvement

The current native compiler composes an exact affine index and immediately
consuming vector read, eliminating intermediate homes and result copies while
retaining original handle/index checks. Original matmult time is13.12% shorter
in one fresh30-triple comparison, passing unchanged variation/profitability rules.
Other18 guest bytes equal the previous qualified product. C remains16.97x faster
than this candidate; all19 C-or-better goal is unachieved. These are aligned native
body measurements, not official Embench scores or a new suite aggregate.

Source `{integ['sourceCommit']}`; integrated command{integ['imageBytes']}B,
SHA-256 `{integ['imageGenerations']['amu']['3']}`.
[Summary](evidence/coscientist-affine-read-direct-20261006/summary.json),
[timing](evidence/coscientist-affine-read-direct-20261006/timing-summary.json),
[checksums](evidence/coscientist-affine-read-direct-20261006/checksums.sha256).
Archives retain raw measured rows/C/runner/spec, actual source/guest binaries,
all native generations, oracles/full-state receipts, initial untimed variant,
authoring failures/corrections, new permanent fixtures and committed-source
integrated rebuild/corpus actual outputs.

## Exact implementation and native proof

Admission uses six exact LGET/CONST/integer-MUL/LGET/integer-ADD/integer-ADD records,
then RT-VECTOR-AT at high-2 with two arguments. Require original nonleaf frame,
high>=7, valid resident local sources, prefix constant[-4095,4095], nontrivial
factor, validated same-function loop and bounded dead-intermediate/index proof.
Unknown structures, live index, absent loop and unknown ownership refuse.
No workload/function names, result cache, callee allocation or scalar-tree state14
changes. Existing gn-protect/gn-co/gn-dreg/gn-fin preserve aliases and final placement.
Every handle/index validation and fuel/allocating effect remains in original order.

All4 native generations byte-match814312B,
SHA-256 `a9cceee002d6365f3e68b740321b9e362635121bd575b613ac28d4b3da93372e`.
Actual observer/quiet guests and entry offsets equal for all19. Only2 actual sites,
original matmult SIR3291/3300, emit exact MADD/immediate arithmetic and read directly
into original x14/x15. Original192B frame and5-local prologue are byte-preserved.
Matmult machine10328→10280B. The initial10288B read-composition variant still moved
results from x0; it passed semantics but was never timed. Final direct variant
has independent native generations/proofs and differs from all rejected machines.

Original402 fixtures/7989 native runs pass unchanged expectations before timing.
4950 independent modular-arithmetic/index/alias/coalescing/live-index-RET2 refusal/
cold/nontrivial-factor/prefix-range/fuel states,1260 actual allocating-open-import/
invalid-handle/index/resource partial-write states,2520 additional source-operand
and handle-alias states, and209 complete original19 states pass. Total8939 sealed
before timing. Actual MADD admission/counts are audited for every new hand case.

Permanent fixture table grows to434/9339, preserving the exact402/7989 prefix.
New pure hand expectations cover integer extremes, invalid handles/indices,
partial fuel, source/handle aliases and refusal.12 independently constructed
native guard states cover admission, leaf/frame-slot/unknown-prefix/range refusal,
reserved fields, invalid locals, wrong read slot/depth/arity and wrong label.
Real/test layouts and normal unit stdout match independent fixture image; update
generated golden only after9339 actual runs pass, then normal native unit passes.
Initial loader-copy mode, test table-name, Python namespace and unit allowed-path
failures are corrected without changing program limits or prior expected results.
This is new Kotoba algorithm/hand-fixture authoring, not mechanical refactoring.

## Fresh timing and complete product checks

Apple M4 zebulun, pinned original source/C/runner/spec.30 accepted rotating triples
of31 attempts. Independent audit recomputes every rejection/order/mean/SD and
verifies source/machine/compiler/offset/C/runner/preflight pins. Load<=4,
background idle>=90%, allRSD<=10%, speedup>=1.05 and gap>summedSD.

|Original workload|Product µs/body|New µs/body|C µs/body|Shorter time|
|---|---:|---:|---:|---:|
|matmult-int|{b['baseline']['meanNsPerBody']/1000:.3f}|{b['candidate']['meanNsPerBody']/1000:.3f}|{b['C']['meanNsPerBody']/1000:.3f}|{tim['savedTimeFraction']*100:.2f}%|

Gap{tim['meanGapNs']:.2f}ns > summedSD{tim['summedSdNs']:.2f}ns; ratio{b['baselineOverCandidate']:.4f}.
No identical-machine retiming or result memoization. No newall19 geometric mean.

ERR/G1–G5 pass under explicit native-generation mapping; G2 retains its existing
one refused corpus case, with0 changed accepted outputs. Bootstrap inventory is
byte-identical. This is six gates, not all release gates. Commit-snapshot integrated
image/command/container/native code and all162objects match across3generations,
with117frontend objects and input content hashes verified. Generation3 checks and
compiles all19 canonical sources, yielding exact measured guest bytes/entry offsets.

All391 check classifications/messages and391 compile outcomes retain previous
qualified results; all891 export classifications retain875same,15existing closure
handle differences,0timeouts and1missing. All391 normalized actual check messages
and1780 native export output/status files equal previous product. Existing compile
counts remain300behavior-same,27Amu-only accepts,12Amu-only refusals,3differing
accepted behaviors,49shared refusals. These gaps remain explicit; no100%selfhost,
launcher switch, rung-record update, wire20 grant, merge/main or release claim.

## Next registered hypothesis

[Guarded descriptor reuse after elimination of the high-read C boundary](evidence/coscientist-affine-read-direct-20261006/next-hypothesis.json).
A prior descriptor cache was invalidated by the adjacent high-depth C helper.
Current qualified loop reads remove that boundary. Restrict a new experiment to
structurally witnessed high-inline loops, retaining all index checks and actual
call invalidation, then prove/measure a distinct machine. Native DefCID/result
caching remains unconnected; this local specialization uses exact SIR content.
'''
(r/'docs/coscientist-affine-read-direct-20261006.md').write_text(report)
f=r/'docs/coscientist-content-address-20261005.md';text=f.read_text();head='''Latest qualified follow-up: [direct affine-index checked read](coscientist-affine-read-direct-20261006.md)
passes4 native generations,8939 preflight state comparisons,434/9339 permanent
fixtures/runs preserving original402/7989,12 guards, ERR/G1-G5 and committed-source
integrated3gen/full actual-output corpus parity. Fresh30triples qualify13.12%
shorter originalmatmult time; other18 guests equal previous product. C remains
16.97x faster than candidate; all19 goal unachieved. Next guarded descriptor reuse
uses a new mechanism: adjacent high-depth reads no longer cross a C helper.

''';text=text.replace('# Content identity, computation identity, and native performance\n\n','# Content identity, computation identity, and native performance\n\n'+head,1);f.write_text(text);print('PASS qualified direct-affine-read product, full native/integrated evidence archived')
