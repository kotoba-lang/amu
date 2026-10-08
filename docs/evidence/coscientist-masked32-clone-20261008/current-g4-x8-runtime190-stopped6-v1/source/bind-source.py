"""SOURCE metadata binder only; never invokes native/guest/OS resource APIs."""
from pathlib import Path
import json,hashlib,sys,runpy,ast
D=Path(__file__).resolve().parent;W=D.parent;B=W/'published-mode2-x8-statemate-vector-runtime12-source-v1-20261009';C=W/'published-mode2-x8-g4-original19-compile38-source-v1-20261009';A=W/'published-mode2-x8-g4-original19-compile38-actual-review-independent-20261009-crc/report.json'
def load(p):return json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);assert p.is_file()and not p.is_symlink();b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
assert A.is_file(),'current G4 compile38 actual proof pending'
a=load(A);complete=load(C/'run-outputs/report.json');base=load(B/'preregistration.json');cp=load(C/'preregistration.json');pr={k:base[k]for k in ['loader','loaderArtifact','interpreter','environment','zeroCapabilityGrants','OFFActualProof','OFFActualProofStatus','C95Oracle','C95OracleProof','C95OracleStatus','C95OracleProofStatus','qualifiedIntegrationFixtureProof','guestFuelPerCall','guestArenaCaps','canonicalMatrix','operationalEnvironment','C2','timingAuthorized','generalCandidateAdoptionQualified','fullClobberCertificateQualified','actualTypedMode2AdmissionObserved','loaderSupervisorProtocolView']}
pr.update(format='current-g4-x8-original19-runtime190-source/v1',rootGOStatus='GO_CURRENT_G4_X8_ORIGINAL19_RUNTIME190_V1',sourceReviewStatus='PASS_SOURCE_ONLY_CURRENT_G4_X8_ORIGINAL19_RUNTIME190_V1',freshOutputRoot=str(D/'run-outputs'),maximumLoaderCalls=190,maximumRuntimeNativeStarts=190,maximumConservativeWrapperLoaderNativeStages=570,maximumAuxiliaryThreadStarts=380,maximumInputFiles=256,maximumInputLogicalBytes=33554432,controlledOutputReservationBytes=4294967296,hardFilesystemQuotaQualified=False,maximumCaptureStdoutBytes=8388608,maximumCaptureStderrBytes=1048576,maximumMemoryJournalBytesPerCall=8388608,maximumSamplesPerCall=2048,maximumSerializedSampleRowBytes=4096,maximumControllerEventsPerCall=4096,maximumReceiptBytes=16777216,maximumReceiptBytesPerCase=65536,resourceJournalMaximumBytes=65536,nativeCPUSeconds=30,kernelCPUHardSeconds=31,nativeWallSeconds=30,outerDeadlineSeconds=30,maximumReapSeconds=30,maximumSequentialCampaignSeconds=12000,maximumInitialParentFDs=32,maximumControlledExtraParentFDs=9,maximumControlledParentFDs=41,invocationSealVersion='current-g4-x8-runtime190-invocation/v1',noRetry=True)
pr['environment']=dict(pr['environment'],TMPDIR=pr['freshOutputRoot'])
pr.update(G4Original19ActualProof=rec(A),G4Original19ActualProofStatus=a['status'],G4Original19Completion=rec(C/'run-outputs/report.json'),FixedpointActualProof=cp['fixedpointActualProof'],FixedpointActualProofStatus=cp['fixedpointActualProofStatus'],G4Producer=dict(native=cp['currentCompiler'],container=cp['currentCompilerContainer']),entries=cp['entries'],imagesON=complete['original19Images'])
pr['imagesOFF']=load(pr['OFFActualProof']['path'])['joinedOriginal19Images'];oracle=load(pr['C95Oracle']['path']);pr['cases']=[]
for e in pr['entries']:
 for n in e['iterations']:
  answer=next(x['result']for x in oracle['rows']if x['workload']==e['workload']and x['n']==n)
  for arm in ['OFF','ON']:
   im=next(x for x in pr['images'+arm]if x['workload']==e['workload']);off=im['offset']if arm=='OFF'else im['selectedExport'][1];pr['cases'].append(dict(label=e['workload']+'-'+arm+'-n'+str(n),workload=e['workload'],arm=arm,profile=n,symbol=e['symbol'],offset=off,arity=1,native=im['native'],container=im['container'],source=e['source'],expectedResult=answer,nativeArgv=[pr['loader'],im['native']['path'],str(off),'1','aarch64','-',str(n)]))
# Targeted regular owners read by runtime guards, not full prior SDK archive.
pins={}
def add(p):
 r=rec(p);pins[r['path']]={k:r[k]for k in ['bytes','sha256']}
for k in ['loaderArtifact','interpreter','OFFActualProof','C95Oracle','C95OracleProof','qualifiedIntegrationFixtureProof','canonicalMatrix','loaderSupervisorProtocolView','G4Original19ActualProof','G4Original19Completion','FixedpointActualProof']:add(pr[k]['path'])
for r in load(pr['loaderSupervisorProtocolView']['path'])['pins']:add(r['path'])
for arm in ['OFF','ON']:
 for im in pr['images'+arm]:
  for k in ['source','native','container']:add(im[k]['path'])
for r in pr['G4Producer'].values():add(r['path'])
fp=load(pr['FixedpointActualProof']['path']);add(fp['completion']['path']);add(fp['sourceCandidate']['path'])
for r in fp['wholeArtifactsAndOwnExports']:
 for k in ['native','container']:add(r[k]['path'])
for r in fp['generatedProducerReceipts'].values():add(r['path'])
assert len(pins)<=256 and sum(r['bytes']for r in pins.values())<=33554432
(D/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n');pr.update(inputFiles=len(pins),inputLogicalBytes=sum(r['bytes']for r in pins.values()),inputPinsSHA256=rec(D/'input-pins.json')['sha256']);(D/'preregistration.json').write_text(json.dumps(pr,indent=2)+'\n')
sys.path.insert(0,str(D));m=runpy.run_path(str(D/'run.py'));assert m['source_scope'](pr)
for p in D.glob('*.py'):ast.parse(p.read_text())
print('bound targeted input owners',len(pins),pr['inputLogicalBytes'],'source still requires controls/reviews/freeze/GO')
