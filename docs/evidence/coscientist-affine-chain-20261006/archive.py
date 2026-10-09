from pathlib import Path
import json,hashlib,tarfile,subprocess
r=Path('/Users/junkawasaki/github/wt/amu-seed17');w=Path('/private/tmp/amu-affine-chain-20261006');d=r/'docs/evidence/coscientist-affine-chain-20261006';d.mkdir(parents=True)
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t={'status':'complete-independent-fresh-timing-audit','entries':[load(w/'timing-audit-matmult-int.json')]};(w/'timing-summary.json').write_text(json.dumps(t,indent=2)+'\n');z=t['entries'][0];assert not z['qualifies'];assert (r/'seed/41-a64gen.kotoba').read_bytes()==(w/'baseline-41-a64gen.kotoba').read_bytes()
corrections={'compilerRegionCapacity':'Initial 330-case unit exceeded region4 (E101); partition into14 units of24, original capacity unchanged.','fixturePostGenerationState':'Existing hand-fixture guards read last-function state. Append clone of original cold-control sentinel to restore that state; no existing expectation or golden changed.','observerAuthoring':'Correct parenthesization of path expression. Initial diagnostic compile hit default1s loader CPU cap; diagnostic uses1800s matching native selfbuild. Program fuel/resource proofs unchanged.','remoteBeforeTiming':'Remote script root initially named prior experiment; preflight assertion stopped before any measurements. Correct new unique root, retain failed launch log. Exactly one fresh measured batch follows.'}
next={'status':'registered-not-implemented-or-measured','hypothesis':'Compose exact affine index and immediately consuming vector-at as one emitter, preserving handle/index check order, original frame/fuel/traps and prefix temps. Eliminate final index home/store/reload and redundant descriptor transitions; use original successful vector read destination directly.','structuralEvidence':{'source':'Pinned current-product complete native SIR census; original matmult FN5','sequences':[{'sir':3291,'highTemp':7,'prefix':800,'nextSir':3297,'nextRecord':[14,176,5,2]},{'sir':3300,'highTemp':8,'prefix':1200,'nextSir':3306,'nextRecord':[14,176,6,2]}],'meaning':'Exact adjacent structural matches only; not admission, dynamic cost or performance evidence.'},'admission':'No workload names. Exact integer six-record chain plus RT-VECTOR-AT n2 at t-2; resident local sources, known prefix, same-function loop, original check order and liveness proof for consumed t/t+1/index; preserve aliases/coalescing/folded destination. Unknown structures or live index refuse original emission. State14 remains scalar-tree flag.','requiredProof':'Native fixedpoint; unchanged original402/7989 expectations; actual original19 source/result/fuel/guest admission; independent wrap/alias/RET2/live-index refusal and vector invalid-handle/index tests; allocating imports, partial fuel/resource states; exact actual instruction audits. Start from qualified product, not rejected experimental source.','timing':'Only new distinct quiet machine, one fresh30-triple batch; same current-product/C and unchanged rule; no identical-machine retiming. Performance pass then permanent guards/product gates/integrated3gen/full corpus before promotion.','contentIdentity':'An exact typed implementation identity could key reusable specialization artifacts once native DefCID is connected. This local SIR proof is not connected DefCID/result caching.'}
(d/'next-hypothesis.json').write_text(json.dumps(next,indent=2)+'\n')
s={'status':'rejected-affine-chain-after-fresh-timing','decision':'Mean10.40% shorter, meanGap1883.72ns below summedSD2406.45ns. Reject; no identical-code retiming; qualified product unchanged.','hypothesis':load(w/'hypothesis.json'),'generations':load(w/'generations.json'),'codeChanges':load(w/'code-change.json'),'preflight':load(w/'preflight-audit.json'),'actualNativeSites':load(w/'instruction-audit.json'),'observer':load(w/'observer-byte-audit.json'),'timing':t,'authoringCorrections':corrections,'productChanged':False,'officialEmbenchScore':False,'COrBetter':False,'productGatesAndIntegration':'Not rerun for performance-rejected prototype; previously qualified product remains unchanged.'}
for n,key in [('permanent-regression-proof.json','permanentRegression'),('ports-state.json','original19State'),('chain-proof.json','independentAffineState'),('effect-proof.json','allocatingImportVectorResourceState')]:s[key]={k:v for k,v in load(w/n).items() if k not in ['observations','runs']}
(d/'summary.json').write_text(json.dumps(s,indent=2)+'\n');(d/'archive.py').write_bytes(Path(__file__).read_bytes());(d/'timing-summary.json').write_bytes((w/'timing-summary.json').read_bytes())
q=subprocess.run(['git','diff','--no-index',str(w/'baseline-41-a64gen.kotoba'),str(w/'41-a64gen-prototype.kotoba')],capture_output=True,text=True);assert q.returncode==1;(d/'prototype.diff').write_text(q.stdout)
with tarfile.open(d/'native-proof.tgz','w:gz') as a:
 for x in sorted(w.iterdir()):
  if x.name in ['__pycache__','collected','timing-package','permanent-regression-run']:continue
  a.add(x,arcname=x.name)
 for n in ['seed/MANIFEST','seed/SIR','seed/HEADS','seed/MEMORY-MAP','AGENTS.md','seed/41-a64gen.kotoba','seed/40-a64enc.kotoba','tools/kexe_loader.c','scripts/seed/a64gen-fixtures.py','seed/tests/unit/41-a64gen.expected']:a.add(r/n,arcname='baseline-source/'+n)
 for n in ['clobber-state-loader.c','clobber-state-loader']:a.add(Path('/private/tmp/amu-context-call-20261005')/n,arcname='diagnostic/'+n)
with tarfile.open(d/'timing.tgz','w:gz') as a:
 for n in ['remote-timing.py','timing-package','audit-workload.py','timing-artifact-audit.py','timing-summary.json','batch-status.json']:a.add(w/n,arcname=n)
 for x in w.glob('timing-*-matmult-int.json'):a.add(x,arcname=x.name)
(d/'checksums.sha256').write_text(''.join(sha(x)+'  '+x.name+'\n' for x in sorted(d.iterdir()) if x.is_file() and x.name!='checksums.sha256'))
b=z['summary'];report=f'''# Affine-chain composition: rejected after fresh native timing

Current identity is content addressing of checked implementations. It can support
reusable specialized artifacts, but the measured native route has no linked
DefCID/result cache. This experiment reduces fresh execution work using exact
local SIR proofs. It is not computation-result memoization.

Only original matmult changes, from10328B to10288B; all18 other guest machines
and all19 source/result/exact-fuel outcomes equal current qualified product.
Fresh30 accepted triples of31 attempts fail the unchanged promotion criterion.
Product remains unchanged; C-or-better across all19 remains unachieved.
These are aligned native body measurements, not official Embench scores.

[Summary](evidence/coscientist-affine-chain-20261006/summary.json),
[timing](evidence/coscientist-affine-chain-20261006/timing-summary.json),
[checksums](evidence/coscientist-affine-chain-20261006/checksums.sha256).
Native/timing archives retain actual source, all native generations, hand fixtures,
independent oracles, observations, actual guest machines, C/runner/spec and all
accepted/rejected rows. Experimental new Kotoba algorithm and independent hand
fixture authoring are one-off exceptions; no mechanical product rewrite occurred.

## Implementation and proof

A bounded exact proof admits six integer records: LGET high temp/localA,
CONST high+1/factor, MUL high, LGET high+1/localB, ADD high, ADD high-1.
The prefix high-1 must be a known constant in[-4095,4095], factor excludes0/1/-1,
locals must be valid register residents, consumed intermediates dead before
later reads, and an actual same-function backward loop must enclose the site.
Unknown structures refuse. Existing alias protection, original final placement,
coalescing and folded-LSET skip bookkeeping remain. Frame/local allocation stays
unchanged, no new callee registers, scalar-tree state14 untouched.

All4 native generations are byte-identical813968B,
SHA-256 `a1645031371657ae8b4351c03aaaccac8d35c393d4c904e5782444bfd9dadc2a`.
Diagnostic observation reproduces quiet guest bytes/entry offsets for all19.
Only2 actual sites: matmult SIR3291/3300. Independent word audit finds one exact
MOVZ/MADD/ADD-immediate sequence for each site, with factors20/prefixes800/1200.

All402 permanent fixtures/7989 fresh native runs pass unchanged expectations,
golden and real/test code/literal/function-offset parity.4950 independent affine
full-state comparisons cover6 high depths,6 factors,3 prefixes, aliases and
coalescing, i64 extremes, future intermediate reads/RET2 refusal, cold/no-loop,
large prefix and trivial-factor refusal, plus exact partial fuel. Independent
modular arithmetic and actual MADD admission/counts are checked for330 cases.
1260 additional vector/actual allocating open-import comparisons cover invalid
handles/indices, fuel before/after read/import, table/item capacity exhaustion,
allocation counts and partial vector writes.209 original19 full/partial-fuel
states pass. Total6419 full-state comparisons sealed before timing.

Initial large hand unit exceeded existing compiler region capacity; split into14
units instead of raising it. Preserve existing last-function guard state with the
original cold-control sentinel. Correct diagnostic path authoring and diagnostic
compile CPU budget. Remote preflight caught a stale directory name before timing;
fix the new experiment root. Original failures/repairs remain explicit in evidence.
No program fuel/resource limits, old expectations or product gates were relaxed.

## One fresh comparison and rejection

Apple M4 zebulun; original pinned source/spec/C/runner, rotating three-arm order,
load<=4, background idle>=90%, all relativeSD<=10%. Independent audits recompute
all row rejection/order/means/SDs and verify source/machine/compiler/offset/C/
runner/preflight receipt hashes.

|Original workload|Current product µs/body|Candidate µs/body|C µs/body|Mean time reduction|Adopted|
|---|---:|---:|---:|---:|---|
|matmult-int|{b['baseline']['meanNsPerBody']/1000:.3f}|{b['candidate']['meanNsPerBody']/1000:.3f}|{b['C']['meanNsPerBody']/1000:.3f}|{z['savedTimeFraction']*100:.2f}%|No|

Mean gap{z['meanGapNs']:.2f}ns < summedSD{z['summedSdNs']:.2f}ns.
Candidate/C time ratio{b['candidateOverC']:.2f}. Keep negative result, reject
prototype, do not retime identical machine. No newall19 aggregate or product
integration claim. Existing qualified product remains at affb9855665f6cb0cbe1d97a5803ac6efdb50b65.

## Next registered hypothesis

[Compose the affine index with its immediate checked vector read](evidence/coscientist-affine-chain-20261006/next-hypothesis.json).
Pinned original native SIR has vector-at records immediately after both chains,
at3297/3306. These are structural matches, not compiler admission or cost shares.
A new proof must preserve all checks, fuel, prefix aliases and refusal for a live
intermediate index. Start from qualified product; only a distinct machine with
full native preflight may get a new timing batch.
'''
(r/'docs/coscientist-affine-chain-20261006.md').write_text(report)
p=r/'docs/coscientist-content-address-20261005.md';v=p.read_text();head='''Latest experimental follow-up: [affine-chain composition](coscientist-affine-chain-20261006.md)
passes4 native generations,7989 permanent runs and6419 extra state comparisons.
Fresh30triples show10.40% shorter matmult mean but fail unchanged summed-variation
criterion; reject, product unchanged. C remains17.58x faster than candidate.
Next registered: exact affine index plus immediately consuming checked vector read.

''';v=v.replace('# Content identity, computation identity, and native performance\n\n','# Content identity, computation identity, and native performance\n\n'+head,1);p.write_text(v)
print('PASS rejection, raw native/timing evidence and next prospective hypothesis archived')
