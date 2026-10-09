from pathlib import Path
import json, hashlib, stat, sys, importlib.util, runpy, contextlib, io, ast
D=Path('/Users/junkawasaki/github/workspaces/codex/tc-hft-compose511-bound-hoist-g4-original19-compile38-source-v1-20261009')
A=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(D))
def receipt(p):
 p=Path(p);a=p.lstat();assert stat.S_ISREG(a.st_mode) and not p.is_symlink();b=p.read_bytes();z=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns);return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p):return json.loads(Path(p).read_bytes())
def registry():
 sp=load(D/'source-pins.json');ip=load(D/'input-pins.json')
 for n,r in sp.items():assert receipt(D/n)==r
 for p,r in ip.items():assert receipt(p)==r
 return dict(sourceFiles=len(sp),inputFiles=len(ip),inputLogicalBytes=sum(r['bytes']for r in ip.values()),sourcePinsSHA256=receipt(D/'source-pins.json')['sha256'],inputPinsSHA256=receipt(D/'input-pins.json')['sha256'])
before=registry();pr=load(D/'preregistration.json');freeze=load(D/'freeze.json');schema=load(D/'go-schema.json')
assert before['sourceFiles']==22 and before['inputFiles']==237 and before['inputLogicalBytes']==20237066
for k in ['sourcePinsSHA256','inputPinsSHA256']:assert before[k]==freeze[k]
assert pr['exactInputFiles']==237 and pr['exactInputLogicalBytes']==20237066 and pr['inputPinsSHA256']==before['inputPinsSHA256']
assert before['sourcePinsSHA256']=='48f8f48e264fe38c5f59dd3e069598270d97049a4f8728c6066cd61fd31bb193'
assert pr['maximumInputFiles']==256 and pr['maximumInputLogicalBytes']==33554432
import run
assert run.source_scope(pr,load(D/'input-pins.json'))
assert run.existing_g4_guard(pr)
expected=['status','maximumLoaderCalls','outputRoot','noRetry','timingAuthorized','runtimeGuestAuthorized','C2','outerHostLaunchRequiresEscalation','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','candidateSourcePinsSHA256']+run.PROOF_KEYS
assert schema['requiredExactKeys']==expected and len(expected)==len(set(expected))==16
proof=load(pr['fixedpointActualProof']['path']);assert proof['closedCompilerCalls']==6 and proof['generatedProducerReceiptGenerations']==[2,3,4]
assert proof['wholeArtifactsAndOwnExports'][2]['native']==pr['currentCompiler'] and proof['wholeArtifactsAndOwnExports'][2]['container']==pr['currentCompilerContainer']
assert proof['generatedProducerReceipts'][2]==pr['fixedpointBuildReceipt']
assert receipt(D/'fixedpoint_lineage.py')==receipt(pr['lineageDriverSource']['path'])
for name,r in load(D/'delta.json')['unchangedComponents'].items():assert receipt(D/name)==receipt(r['path'])=={k:r[k]for k in ['bytes','sha256']}
# Ordinary original matrix relationship is independently recomputed, separate from helper assertions.
m=load(pr['canonicalMatrix']['path']);assert len(m['entries'])==len(pr['entries'])==19
for i,(e,o) in enumerate(zip(pr['entries'],m['entries'])):
 assert (e['workload'],e['symbol'],e['iterations'],e['source']['sha256'])==(o['workload'],o['symbol'],o['iterations'],o['expectedSourceSha256'])
 assert e['source']['path']=='/Users/junkawasaki/github/wt/amu-seed17/'+o['source']
 assert [r['kind']for r in pr['cases'][2*i:2*i+2]]==['compile','extract']
 for c in pr['cases'][2*i:2*i+2]:assert c['producer']==pr['currentCompiler']['path'] and c['nativeArgv'][2:7]==['0','0','aarch64','35,37,38,39','--'] and c['arity']==1
assert sum(len(e['iterations'])for e in pr['entries'])==95
controls={}
for name,expectedfile in [('pure-controls.py','pure-controls.json'),('wrapper-controls.py','wrapper-controls.json')]:
 stream=io.StringIO()
 with contextlib.redirect_stdout(stream):runpy.run_path(str(D/name),run_name='__independent_pure_only__')
 out=json.loads(stream.getvalue());assert out==load(D/expectedfile);controls[name]=out
 assert out['operationalCalls']==0
# Read every registered Python body and reject syntax errors; no entrypoint launch.
for p in D.glob('*.py'):ast.parse(p.read_text())
caller=ast.parse((D/'native-call.py').read_text());f=next(n for n in caller.body if isinstance(n,ast.FunctionDef)and n.name=='call');assert isinstance(f.body[0],ast.Expr) and ast.unparse(f.body[0].value)=="need(len(rows) < 42 and pr['cases'][len(rows)] == case, 'fixed ordered remaining42 no retry')"
# Inherited 42 descriptive ceiling is bounded by actual38 list indexing before the API import/setup.
assert not Path(pr['freshOutputRoot']).exists()
assert pr['maximumLoaderCalls']==38 and len(pr['cases'])==38 and pr['maximumConservativeWrapperLoaderNativeStages']==114 and pr['maximumAuxiliaryThreadStarts']==76
assert pr['maximumSequentialCampaignSeconds']==71000 and pr['controlledOutputReservationBytes']==2147483648
assert pr['nativeCPUSeconds']==1800 and pr['kernelCPUHardSeconds']==1801 and pr['nativeWallSeconds']==1800 and pr['outerWallSeconds']==1810 and pr['cleanupSeconds']==30
s=(D/'run.py').read_text();assert s.index("save(O/'terminal.json'")<s.index("save(O/'report.json'") and 'time.monotonic()+1840<=deadline' in s
assert 'len(rows)==len(results)==38 and len(artifacts)==19' in s and "payload==Path(c['outputPath']).read_bytes()" in s
# Pinned primary loader grammar: first -- separates compiler guest argv after arity0, prior to arity check.
source=Path('/Users/junkawasaki/github/wt/amu-seed17/tools/kexe_loader.c').read_text();main=source[source.index('int main('):]
assert 'strcmp(argv[i], "--")' in main or 'strcmp(argv[i],"--")' in main
assert main.index('argc = i;') < main.index('argc != (int)(6 + arity)') < main.index('FILE *file = fopen(argv[1], "rb")')
for c in pr['cases']:
 a=c['nativeArgv'];assert a.index('--')==6 and int(a[3])==0 and len(a[:6])==6+int(a[3])
assert pr['environment']['KEXE_COMMAND']=='1' and 'const int command_mode = getenv("KEXE_COMMAND") != NULL;' in main
assert registry()==before
report=dict(status=pr['sourceReviewStatus'],**before,driverSHA256=receipt(D/'run.py')['sha256'],preregistrationSHA256=receipt(D/'preregistration.json')['sha256'],subject=str(D),reviewerScope='Independent Dense compile38 adaptation/harness review. Reviewer authored prior copied fixedpoint_lineage.py and hoist algorithm; neither is presented as independently requalified architecture here.',operationalCalls=0,nativeCalls=0,sourceUnchanged=True,checks=dict(currentG4Proof=pr['fixedpointActualProof'],orderedGenerations=[2,3,4],currentG4Native=pr['currentCompiler'],currentG4Container=pr['currentCompilerContainer'],current16Source=pr['sourceCandidate'],fullOriginalWorkloads=19,unchangedProfiles=95,exactCompilerCases=38,unchangedOperationalComponents=8,registryRealGuardExact=True,goKeys=16,goDuplicateKeys=0,sourceBoundCompilerArity0Grammar=True,wholePayloadOwnExportChecks=True,terminalBeforeValidLast=True,thirtyNinthRefusedBeforeAPI=True),pureControls=controls,limitations=['SOURCE only: fresh38 compiler calls remain unauthorized until exact root GO and two reviews.','Inherited exact native-call42 list-index guard safely refuses39 before APIs; descriptive old42 text is not a38-call increase.','Strict old memory policy or only separately typed termination-gap artifact admission is unchanged; unknown/unbound PID remains refusal.','Sequential sampled memory has no hard peak/finite overshoot guarantee; per-file/output reservations do not prove filesystem quotas.','No benchmark runtime, full19 semantic qualification, performance, general ABI/clobber certificate or product adoption.','Prior lineage helper authored by reviewer is rehashed byteexact; newly adapted38 ownership/schedule/GO/registry are the independent scope.'])
(A/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(report=receipt(A/'report.json'),source=before,controls={k:(len(v['refusedMutants']),v.get('positiveCompilerCases',v.get('compilerCases')))for k,v in controls.items()})))
