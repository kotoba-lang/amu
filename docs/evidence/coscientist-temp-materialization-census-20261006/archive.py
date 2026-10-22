from pathlib import Path
import json,hashlib,tarfile,subprocess
r=Path('/Users/junkawasaki/github/wt/amu-seed17');w=Path('/private/tmp/amu-temp-materialization-census-20261006');d=r/'docs/evidence/coscientist-temp-materialization-census-20261006';d.mkdir(parents=True);load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();c=load(w/'materialization-census.json');a=load(w/'instruction-audit.json');ob=load(w/'observer-byte-audit.json');assert len(ob['entries'])==19 and c['events']==a['events']==81;assert all(x['diagnosticTargetByteIdentical'] for x in ob['entries']);assert (r/'seed/41-a64gen.kotoba').read_bytes()==(w/'baseline-41-a64gen.kotoba').read_bytes();mapped=[(e['workload'],f) for e in c['entries'] for f in e['mappedFunctions']];assert len(mapped)==14;assert sum(f['potentialReplacedStores']>0 for n,f in mapped)==2;assert sum(f['potentialLoopStores']>0 for n,f in mapped)==1
s={'status':'complete-current-native-materialization-census-changes-next-allocation-policy','hypothesis':load(w/'hypothesis.json'),'observation':ob,'census':c,'instructionAudit':{'status':a['status'],'events':a['events'],'all19GuestBytesEqualCurrentProduct':True},'diagnosticCorrection':load(w/'diagnostic-correction.json'),'productChanged':False,'performanceMeasured':False,'officialEmbenchScore':False,'COrBetter':False};(d/'summary.json').write_text(json.dumps(s,indent=2)+'\n');(d/'archive.py').write_bytes(Path(__file__).read_bytes());(d/'materialization-census.json').write_bytes((w/'materialization-census.json').read_bytes());(d/'instruction-audit.json').write_bytes((w/'instruction-audit.json').read_bytes())
next={'status':'registered-before-implementation-or-measurement','hypothesis':'Use original spare callee registers only for contiguous high temps7..max where a non-coalesced dynamic integer BIN inside a validated same-function backward region produces the high temp. Require adjacent LGET t local; CONST t+1 nontrivial value; BIN ADD/MUL t; no source/workload names. Highest admitted temp bounds mapped range, original frame/local allocation and call contracts retained. Bounded full-function scan refuses on budget/ownership uncertainty.','evidence':'Current native census verifies81 actual high-home machine words; only matmult FN5 temps7/8 have5stores+5loads in validated loops among14 formerly admitted functions. SHA FN21 high4temps have4stores+4loads outside loops;12 other functions havezero proposed-home events.','expectedCandidate':'Only2 additional registers for current originalmatmult, no unnecessary temp9 backup. Require fresh all19 bytes/canonicalsource/results/fuel to verify this expectation, not assume it.','semantics':'Independent disjoint register/home backup/local/outgoing/frame/callee save/restore/RET2/tail/indirect/alias/join/import/resource/fuel/trap proof and all7989 permanent runs. Guard tests must actually admit high loops and verify cold/constant/coalesced/foreign-label/budget refusals. Preserve literal state14 tree-skip flag.','measurement':'Every changed guest fresh30prospectivetriples, load<=4 idle>=90 RSD<=10 ratio>=1.05 and meanGap>sumSD. Previous3registermatmult failed variation rule; new2register machine must differ before any retiming.','promotion':'Only afterperformancequalification, append permanentguards/fixtures, normalunit/gates/integrated3generation/percasecorpus proof andunchanged bootstrapinventory.','goal':'C-or-better all19 originals, unchanged workloads/native selfhost, not officialscore.'};(d/'next-hypothesis.json').write_text(json.dumps(next,indent=2)+'\n')
with tarfile.open(d/'native-census.tgz','w:gz') as t:
 for x in sorted(w.iterdir()):t.add(x,arcname=x.name)
 for n in ['seed/MANIFEST','seed/SIR','seed/HEADS','seed/MEMORY-MAP','AGENTS.md','seed/41-a64gen.kotoba','seed/40-a64enc.kotoba','tools/kexe_loader.c','bench/embench/comparison-matrix.json']:t.add(r/n,arcname='product-source/'+n)
(d/'checksums.sha256').write_text(''.join(sha(x)+'  '+x.name+'\n' for x in sorted(d.iterdir()) if x.is_file() and x.name!='checksums.sha256'))
(r/'docs/coscientist-temp-materialization-census-20261006.md').write_text('''# Current native high-temp materialization census

Observation changes the next allocation experiment:14 functions had spare callee
registers and named high temps, but only2 actually emitted loads/stores in the
proposed mapped homes. Only1 does so inside a validated loop. Current native
product and all19 original workloads stay unchanged; these counts are not timing
shares, speedups, or official Embench scores. C-or-better remains unachieved.

[Summary](evidence/coscientist-temp-materialization-census-20261006/summary.json),
[census](evidence/coscientist-temp-materialization-census-20261006/materialization-census.json),
[exact instruction audit](evidence/coscientist-temp-materialization-census-20261006/instruction-audit.json),
[checksums](evidence/coscientist-temp-materialization-census-20261006/checksums.sha256).
Archive contains full native compiler/source/input snapshots, logs, guest bytes,
original failed diagnostic and corrected observation, and reproducible scripts.

## Evidence

The current qualified812128B seed constructs the diagnostic compiler natively.
All19 canonical sources compile/extract with exactly current product guest bytes
and entry offsets. Diagnostic FN/SIR metadata occupies spare fields13/15;
original14 tree-skip flag stays intact. No optimization or result cache is added.
Fresh complete SIR snapshots include consumed/skipped instructions. All81 actual
high-temp home emissions are independently verified at exact native word offsets
against encoded LDR/STR addresses/registers. Each event belongs to its current
function, frame, temp and validated same-function backward-branch regions.

|Potential mapping|Actual stores|Actual loads|Loop stores|Loop loads|
|---|---:|---:|---:|---:|
|matmult FN5 temp7|3|3|3|3|
|matmult FN5 temp8|2|2|2|2|
|SHA FN21 temps7..10|4|4|0|0|
|Other12 formerly admitted functions|0|0|0|0|

These are compiler emission counts, not measured execution-frequency shares.
Other high-home events occur in functions with no spare callee registers. The
previous strategy added backups for homes which constant/local descriptors never
materialized. Matmult's formerly mapped temp9 also haszero events; reserving only
temps7/8 removes an unnecessary save/restore pair.

## Diagnostic failure retained

Initial observation used state14 for current SIR index. Exact guest/entry equality
caught Picojpeg drift:14 is an existing unnamed scalar-tree skip flag. Initial
records are invalid and excluded from analysis. Keep14 untouched, use15 for SIR,
then freshly verify all19 guests. This was an observation authoring error; no
product algorithm changed. A later rerun hit an existing output directory;
verified terminal failure, fixed directory reuse, and completed the same census.
Initial scripts/artifacts/logs are preserved. Diagnostic Kotoba instrumentation
is a one-off authoring exception, not a mechanical product refactor.

## Registered next experiment

Use spare callee registers for high temps produced by non-coalesced dynamic
integer arithmetic inside validated backward regions, with exact adjacent local/
constant producers and bounded ownership scans. Map only through the highest
admitted temp. Preserve original frame/local allocation and original temp-home
backups. No workload names; current evidence predicts2 registers in1 function,
but fresh all19 generated bytes must establish actual admission.

Require fresh native semantics/permanent regression, genuine high-loop guard
coverage and refusals, all19 source/result/fuel parity, and new machine hashes
before new prospective timing. Previous3register machine failed; never retime
identical code to seek another pass. Performance-qualified code then requires
normal permanent units, gates, integrated3generation/per-case corpus proof.
[Next hypothesis](evidence/coscientist-temp-materialization-census-20261006/next-hypothesis.json).
''');print('PASS current native census archived; next general allocation policy registered')
