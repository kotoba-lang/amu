from pathlib import Path
import json,hashlib,shutil,runpy
D=Path(__file__).parent
P=Path('/Users/junkawasaki/github/workspaces/codex/native-ctx-query-observer-source-v1-20261009-independent')
T=Path('/Users/junkawasaki/github/workspaces/codex/tc-homogeneous-tail-frame-native4-source-v2-20261009')
def load(p):return json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);b=p.read_bytes();assert p.is_file()and not p.is_symlink();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(n,q):(D/n).write_text(json.dumps(q,indent=2)+'\n')
for n in ['helpers.kotoba','prepare_source.py','pure_controls.py','decode_protocol.py','scratch-reference-census.txt']:
 shutil.copyfile(P/n,D/n)
h=(D/'helpers.kotoba').read_text();a=h.index('(defn- qo-safe-note ');z=h.index('(defn- qo-scan-note ',a)
h=h[:a]+'''(defn- qo-safe-note [M :vector-i64 f :i64 n :i64 depth :i64 work :i64] :i64
 (let [m (gn-gs M (+ qo-base 2) (inc (gn-g M (+ qo-base 2))))
       valid-f (and (> f 0) (< f (vector-at m MM-FN-N)))
       p (if valid-f (gn-fnf m f FF-SIR) -1)
       valid-p (and (> p 0) (< p (vector-at m MM-SIR-N)))
       w (if (<= (gn-g m qo-base) 16)
           (qo-row "QCALL" [(gn-g m qo-base) f n depth work p
                 (if valid-p (gn-op m p) -1)
                 (if valid-p (gn-sir m p IF-A) 0)
                 (if valid-p (gn-sir m p IF-B) 0)]) 0)] 0))
'''+h[z:]
h=h.replace('valid (and (< j (vector-at m MM-SIR-N)) (> work 0))','valid (and (> j 0) (< j (vector-at m MM-SIR-N)) (> work 0))');(D/'helpers.kotoba').write_text(h)
d=(D/'decode_protocol.py').read_text().replace('def decode(lines):','import re\ndef decode(lines):').replace("q=[int(x)for x in xs[1:]];", "assert all(re.fullmatch(r'(?:0|-?[1-9][0-9]*)',x)for x in xs[1:]);q=[int(x)for x in xs[1:]];")
d=d.replace("assert valid==int(j<init[4]and work>0)","assert valid==int(0<j<init[4]and work>0)")
d=d.replace("header=(p,op,a,b)","assert (0<f<init[3]) or (p,op,a,b)==(-1,-1,0,0)\n   assert (0<p<init[4]) or (op,a,b)==(-1,0,0)\n   header=(p,op,a,b)")
(D/'decode_protocol.py').write_text(d)
# Only inert source assembly and arithmetic models; never an operational driver.
runpy.run_path(str(D/'prepare_source.py'),run_name='__pure_source_assembly__')
runpy.run_path(str(D/'pure_controls.py'),run_name='__pure_models__')
for n in ['capture.py','integration.py','controller.py','typed-adapter.py','runtime.py','artifact_admission.py','native-call.py']:
 shutil.copyfile(T/n,D/n)
p0=load(P/'preregistration.json');old=load(T/'preregistration.json');O=D/'run-outputs'
pr={k:old[k]for k in ['loader','loaderArtifact','interpreter','qualifiedIntegrationFixtureProof','capabilities','outerWallSeconds','nativeCPUSeconds','nativeWallSeconds','compileFuel','C2','timingAuthorized','runtimeGuestAuthorized','generatedArtifactMaximum','captureStdoutMaximum','captureStderrMaximum','perCallMemoryJournalMaximum','maximumControlledFDs','maximumAuxiliaryThreadsPerCall','maximumTotalOutputBytes','maximumInputFiles','maximumInputLogicalBytes','artifactAdmissionVersion','maximumInvocationSealBytes']}
pr.update(format='amu.current-g4-ctx-observer4/source-v2',freshOutputRoot=str(O),maximumLoaderCalls=4,rootGOStatus='GO_CURRENT_G4_CTX_QUERY_OBSERVER4_V2',sourceReviewStatus='PASS_SOURCE_ONLY_CURRENT_G4_CTX_QUERY_OBSERVER4_V2',invocationSealVersion='ctx-observer4-fixed-invocation/v2',producer=p0['ordinaryG4Compiler']['path'],candidateContainer=p0['ordinaryG4CompilerContainer']['path'],producerSHA256=p0['ordinaryG4Compiler']['sha256'],sourceSHA256=rec(D/'unity-observer.kotoba')['sha256'],sourceAssembly=str(D/'source-assembly.json'),currentProducerProof=p0['currentFixedpointActualProof'],currentG4BuildReceipt=p0['currentG4BuildReceipt'],baseCandidate=p0['baseCandidate'],baseUnity=p0['baseUnity'],entries=p0['expectedWholeOutputs'],scratch=p0['scratch'],hostAuthorizedOuterEscalationRequired=True,loaderOwnedSandboxUnchanged=True,noRetry=True,firstFailureStop=True,maximumDistinctProcessStarts=8,maximumConservativeProcessStages=12,maximumAuxiliaryThreadStarts=8,maximumGuestWorkloadExecutions=0,maximumProtocolRecords=16931,maximumProtocolLineBytes=256,maximumTopSummaries=256,maximumFullyTracedTopQueries=16,nativeAnswerReuse=False,performanceQualified=False,sharedCIDCacheImplemented=False,observerActualParsingPending=True,previousPrototype=dict(path=str(P/'source-pins.json'),**{k:rec(P/'source-pins.json')[k]for k in ['bytes','sha256']}))
pr['environment']=dict(old['environment']);pr['environment']['TMPDIR']=str(O);pr['environment']['KEXE_CAP_RESOURCES_35']=str(O)
pr['cases']=[]
for label,kind,producer,inp,out,arity,observer,work in [('observer-build','compile',pr['producer'],O/'unity-observer.kotoba',O/'observer.kseed',0,False,None),('observer-extract','extract',pr['producer'],O/'observer.kseed',O/'observer.bin',0,False,None),('statemate-compile','compile',str(O/'observer.bin'),O/'statemate.kotoba',O/'statemate.kseed',1,True,'statemate'),('nsichneu-compile','compile',str(O/'observer.bin'),O/'nsichneu.kotoba',O/'nsichneu.kseed',1,True,'nsichneu')]:
 argv=[pr['loader'],producer,'0','0','aarch64','35,37,38,39','--',('compile'if kind=='compile'else'extract-native'),str(inp)]
 argv+=['--target','aarch64-macos','--output',str(out)]if kind=='compile'else['--symbol','main','--output',str(out)]
 pr['cases'].append(dict(label=label,kind=kind,outputPath=str(out),arity=arity,symbol='main'if not observer else'batch',observer=observer,workload=work,nativeArgv=argv))
for e in pr['entries']:shutil.copyfile(e['source']['path'],D/(e['workload']+'.kotoba'))
save('preregistration.json',pr)
# Original strict compiler output grammar plus bounded observer prefix decoder.
parser=(T/'compiler_output.py').read_text();parser=parser.replace('def parse_output(', 'def ordinary_output(')
parser+='''\nfrom decode_protocol import decode

def parse_output(out,case):
 if not case['observer']:return ordinary_output(out,case)
 assert len(out)<=8388608 and out.endswith(b'\\n')
 lines=out.splitlines(keepends=True);assert 4<=len(lines)<=16932
 prefix=lines[:-1];assert all(len(x)<=256 for x in prefix)
 summary=decode([x.decode('ascii')for x in prefix])
 ordinary=ordinary_output(lines[-1],case)
 return dict(ordinary,observerSummary=summary)
'''
(D/'compiler_output.py').write_text(parser)
# Admission keeps original resource/env mechanics; generated compiler use additionally requires two closed calls receipt.
w=(T/'launch-wrapper.py').read_text();w=w.replace("assert producer in [str(Path(pr['freshOutputRoot'])/'G1.bin'),str(Path(pr['freshOutputRoot'])/'G2.bin')]", "assert producer==str(Path(pr['freshOutputRoot'])/'observer.bin')\n  from producer_guard import validate_producer\n  validate_producer(pr,seal['rootGO'],seal['sourcePinsSHA256'],seal['preregistrationSHA256'])")
(D/'launch-wrapper.py').write_text(w)
