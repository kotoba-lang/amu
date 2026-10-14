from pathlib import Path
import json, hashlib, shutil, tarfile, subprocess

W = Path(__file__).parent
R = Path('/Users/junkawasaki/github/wt/codex/seed-copy-chain48-20261014')
E = R / 'docs/evidence/copy-chain48-20261014'

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p): return dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p))
def save(p, v): p.write_text(json.dumps(v, indent=2) + '\n')

source = read(W / 'candidate-source-receipt.json')
identity = read(W / 'all39-identity-v1.json')
generic = read(W / 'generic-identity-v1/report.json')
unit = read(W / 'headroom-unit-v1/report.json')
selfhost = read(W / 'selfbuild-v1/report.json')
first = read(W / 'compiler-only-v1/report.json')
assert len(identity['rows']) == 39 and generic['priorGuests'] == 7344
assert unit['guestCalls'] == 12
assert all(x['nativeSHA256'] == first['nativeSHA256'] and
           x['containerSHA256'] == first['containerSHA256'] for x in selfhost['stages'])
assert source['sourceCommit'] == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R).decode().strip()

modules = [x for x in (R / 'seed/MANIFEST').read_text().splitlines() if x and not x.startswith('#')]
assert len(modules) == 16
unity = b''.join((R / x).read_bytes() + b'\n' for x in modules)
assert unity == (W / 'candidate.kotoba').read_bytes()
review = dict(status='PASS_BOUNDED_PREFIX48_LOCAL_HEADROOM512_ORIGINAL16_FALLBACK',
    sourceCommit=source['sourceCommit'], unitySHA256=sha(W / 'candidate.kotoba'),
    modules=[dict(path=x, bytes=(R/x).stat().st_size, sha256=sha(R/x)) for x in modules],
    maximumFusedPrefixStages=48, longerChainsRetainOriginalTail=True,
    wholeChainLengthAbove48Refused=False, extendedHotPrefixWorstCaseWords=307,
    localHeadroomMinimumWords=512, limitedHeadroomUsesOriginal16=True,
    globalProgramSizeGuaranteeClaim=False,
    proof='Only the prefix-work selection changes: remaining code capacity >=512 selects at most48 stages; otherwise it selects the original16. Each stage emits at most four immediate moves, one narrowing instruction and one store. Guards plus tail require at most19 words, hence48*6+19=307. All source-stage, type, helper, fuel, descriptor and range admission stays. The emitted guests are whole identities to the measured and previously qualified48-stage snapshot.',
    all39WholeGuestIdentities=True, generic54WholeGuestIdentity=True,
    headroomBoundaryCases=12, adopted=False)
save(W / 'source-review.json', review)
save(E / 'source-review.json', review)
source.update(proofPending=False, localStandardChecksPending=True)
save(E / 'candidate-source-receipt.json', source)
for a, b in [('all39-identity-v1.json', 'review-fix-all39-identities.json'),
             ('generic-identity-v1/report.json', 'review-fix-generic-identity.json'),
             ('headroom-unit-v1/report.json', 'headroom-boundaries.json'),
             ('selfbuild-v1/report.json', 'selfhost.json')]:
    shutil.copy2(W/a, E/b)

for ext in ['bin', 'kseed']:
    shutil.copy2(W/'selfbuild-v1/artifacts'/('G4.'+ext), R/'seed/bootstrap'/('adopted-20261012.'+ext))

rows = []
archive = E / 'review-fixes-results.tgz'
assert not archive.exists()
with tarfile.open(archive, 'w:gz') as t:
    for directory in ['compiler-only-v1', 'all39-g1-screen-v1', 'selfbuild-v1',
                      'headroom-unit-v1', 'generic-identity-v1', 'physical-audit-v1']:
        for p in sorted((W/directory).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                rel = str(p.relative_to(W)); rows.append(dict(path=rel, bytes=p.stat().st_size, sha256=sha(p)))
                t.add(p, arcname=rel, recursive=False)
    for name in ['candidate.kotoba', 'candidate-source-receipt.json', 'source-review.json',
                 'all39-identity-v1.json', 'run-headroom-unit-v1.py', 'check-generic-identity-v1.py']:
        p=W/name; rows.append(dict(path=name, bytes=p.stat().st_size, sha256=sha(p)))
        t.add(p, arcname=name, recursive=False)
save(E/'review-fixes-raw-custody.json', dict(status='PASS_NEW_NATIVE_FIXEDPOINT_ALL39_GENERIC_IDENTITIES_AND_HEADROOM_BOUNDARIES_RAW',
    files=rows, archiveSHA256=sha(archive), archiveBytes=archive.stat().st_size,
    previousQualificationArchiveUnchanged=True, previousPerformanceRetime=False))
save(E/'review-clarifications.json', dict(status='CORRECT_PREVIOUS_UPPER_REFUSAL_DESCRIPTION_AND_ADD_LOCAL_HEADROOM',
    previousMeasuredSourceCommit='878ebaef1af4130ec3b27a02217a3bff50ebe58d',
    currentSourceCommit=source['sourceCommit'],
    historicalMetadataCorrection='The earlier explicitUpperRefusal flag described an unreachable >48 condition. The actual behavior has always been an at-most48-stage prefix with the original tail retained for longer chains, including49 and96. Historical raw artifacts are retained; this correction supersedes that descriptive flag.',
    localHeadroom='New compilation retains the original16-stage choice below512 remaining words. This is a local emission guard, not a claim that every future whole program fits a fixed code capacity.',
    performanceReuse='All39 guest sources, complete native/container bytes and exports match the measured48 snapshot. Its statemate timing applies to these identical guests; compiler throughput was not measured.'))

gp=R/'seed/main-copy-chain48-native19.json'; g=read(gp)
g.update(producerCommit=source['sourceCommit'], producerNativeSHA256=first['nativeSHA256'],
         sourceUnitySHA256=source['candidateUnitySHA256'])
save(gp,g)
a=R/'seed/adoption-20261012.json'; d=read(a)
d.update(sourceCommit=source['sourceCommit'], sourceUnitySHA256=source['candidateUnitySHA256'],
    sourceUnityBytes=len(unity), nativeImageSHA256=first['nativeSHA256'],
    nativeImageBytes=(W/'compiler-only-v1/artifacts/candidate.bin').stat().st_size,
    bootstrapContainerSHA256=first['containerSHA256'], policyNativeGoldenSHA256=sha(gp))
for x in d['sourceFiles']:
    p=R/x['path']; x.update(bytes=p.stat().st_size,sha256=sha(p))
d['measurement'].update(sourceCommitUsedForTiming='878ebaef1af4130ec3b27a02217a3bff50ebe58d',
    currentSourceGuestImagesWholeIdentical=True, compilerThroughputMeasured=False, identicalRetime=False)
d['copyChain48Qualification'].update(standardPolicyAndSource19Pending=True,
    standardControlsActualPass=False, sourceReviewFixes=True, maximumFusedPrefixStages=48,
    longerChainsKeepOriginalTail=True, localHeadroomWords=512, lowHeadroomStages=16,
    original483PreservedByWholeGuestIdentity=True, generic7344PreservedByWholeGuestIdentity=True)
q=read(E/'qualification.json')
q.update(status='PASS_ROOT_CW48_REVIEW_FIX_WHOLE_GUEST_IDENTITIES_AND_HEADROOM_NOT_MAIN_ADOPTION',
    source=pin(W/'candidate.kotoba'),sourceReview=pin(E/'source-review.json'),
    selfhost=pin(W/'selfbuild-v1/report.json'),all39WholeIdentity=pin(W/'all39-identity-v1.json'),
    genericWholeIdentity=pin(W/'generic-identity-v1/report.json'),headroomBoundaries=pin(W/'headroom-unit-v1/report.json'),
    previousQualificationAndTimingRawRetained=True,performanceRetime=False)
save(E/'qualification.json',q)

readme=E/'README.md'
readme.write_text(readme.read_text()+f'\nReview revision: current source `{source["sourceCommit"]}`, compiler `{first["nativeSHA256"]}`. The earlier source/native hashes above identify the measured snapshot. The current snapshot emits exactly the same39 guest images and generic54 fixture, so the original483 and7344 observations and paired timing remain applicable without repetition. At most48 stages form a prefix; chains longer than48 retain the original tail, rather than being refused. A new local512-word reserve selects the original16-stage path when headroom is limited. Twelve actual-source boundary probes pass. Historical raw metadata is corrected by `review-clarifications.json`. Standard checks must be repeated for this compiler revision. Portable replay now disables Python bytecode writes.\n')

prefix='docs/evidence/copy-chain48-20261014/'
d['evidenceDigests']=[x for x in d['evidenceDigests'] if not x['label'].startswith(prefix)]
for p in sorted(E.iterdir()):
    if p.is_file()and p.name!='.gitignore':
        d['evidenceDigests'].append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p),label=str(p.relative_to(R))))
save(a,d)
print('PREPARED_REVIEW_FIX_SOURCE20_NATIVE_GOLDEN19_AND_RAW_STANDARD_PENDING')
