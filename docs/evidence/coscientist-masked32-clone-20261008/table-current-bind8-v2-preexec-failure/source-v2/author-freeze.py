"""Pure filesystem/source authoring only. No subprocess or native execution."""
from pathlib import Path
import json,hashlib,stat
D=Path(__file__).resolve().parent;W=D.parent;R=Path('/Users/junkawasaki/github/wt/amu-seed17')
def receipt(p):
 p=Path(p);st=p.lstat();assert stat.S_ISREG(st.st_mode)and not p.is_symlink()and st.st_size<=384*1024**2
 h=hashlib.sha256()
 with p.open('rb')as f:
  while b:=f.read(1024**2):h.update(b)
 assert (st.st_size,st.st_mtime_ns)==(p.stat().st_size,p.stat().st_mtime_ns)
 return {'bytes':st.st_size,'sha256':h.hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
ip={};origins=[]
proofs=[W/'vector-fuel-scalar-dag-compiler-build4-actual-review-v2-census-review',W/'vector-masked32-source-bound-loader-actual-review-v2-width']
for d in proofs:
 pins=json.loads((d/'input-pins.json').read_text());origins.append({'registry':str(d/'input-pins.json'),**receipt(d/'input-pins.json'),'files':len(pins)})
 for p,v in pins.items():
  v={k:v[k]for k in ['bytes','sha256']};assert p not in ip or ip[p]==v;ip[p]=v
 for n in ['input-pins.json','report.json']:ip[str(d/n)]=receipt(d/n)
assembly=json.loads((D/'source-assembly.json').read_text())
extras=[R/p for p in assembly['modules']]+[R/'seed'/p for p in ['MANIFEST','SIR','MEMORY-MAP']]
extras += [R/'bench/embench/batch-ports/crc32.kotoba',W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width/helpers.kotoba',W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width/run.py',W/'vector-fuel-scalar-dag-emitted-observer4-source-v1-width/assemble.py',W/'vector-fuel-scalar-dag-source-v1-width/author.py',W/'vector-fuel-scalar-dag-source-v1-width/41-df-on.kotoba']
extras += list((W/'crc-table-decision-collapse-v2-20261008').iterdir())
extras += [W/'crc-table-decision-collapse-v2-review-root-20261008/report.json',W/'crc-table-decision-collapse-v2-review-independent-20261008/report.json']
extras += [Path(p)for p in json.loads((D/'source-controls.json').read_text())['historicalInputs']]
for p in extras:
 v=receipt(p);assert str(p)not in ip or ip[str(p)]==v;ip[str(p)]=v
# Verify complete declared historical pin closure now as pure filesystem inspection.
for p,v in ip.items():assert receipt(p)==v,('source/input drift',p)
ip=dict(sorted(ip.items()));save(D/'input-pins.json',ip)
pp=json.loads((proofs[0]/'report.json').read_text());lp=json.loads((proofs[1]/'report.json').read_text())
producer=next(r['native']for r in pp['images']if r['arm']=='ON');loader=lp['loader'];O=D/'run-outputs'
steps=[]
for role,src,prod,symbol in [('current-baseline','unity-baseline.kotoba',producer['path'],'main'),('readonly-observer','unity-observer.kotoba',producer['path'],'main'),('ordinary-input','original-input.kotoba',str(O/'current-baseline.bin'),'bench'),('observed-input','original-input.kotoba',str(O/'readonly-observer.bin'),'bench')]:
 for action in ['compile','extract']:
  args=['compile',str(O/src),'--target','aarch64-macos','--output',str(O/(role+'.kseed'))]if action=='compile'else['extract-native',str(O/(role+'.kseed')),'--symbol',symbol,'--output',str(O/(role+'.bin'))]
  steps.append({'index':len(steps)+1,'label':role+'-'+action,'argv':[loader['path'],prod,'0','0','aarch64','35,37,38,39','--',*args]})
pr={'status':'SOURCE_HOLD_READONLY_TC_CURRENT_BIND8_NO_GO','producer':producer,'loader':loader,'actualProducerProof':str(proofs[0]/'report.json'),'actualProducerProofStatus':pp['status'],'actualLoaderProof':str(proofs[1]/'report.json'),'actualLoaderProofStatus':lp['status'],'baseline41SHA256':assembly['baseline41Sha256'],'baselineUnitySHA256':assembly['baselineSha256'],'observerUnitySHA256':assembly['observerSha256'],'tcCandidateSHA256':assembly['tcCandidateSourceUnchanged'],'lineage':'fixed DAG d3 stage0 -> freshly built current repository MANIFEST baseline/readonly observer; measured LC variant not used','maximumInputFiles':4096,'maximumInputLogicalBytes':512*1024**2,'maximumIndividualInputBytes':384*1024**2,'inputCount':len(ip),'inputLogicalBytes':sum(v['bytes']for v in ip.values()),'inputRegistrySHA256':receipt(D/'input-pins.json')['sha256'],'proofRegistryOrigins':origins,'maximumLoaderCalls':8,'orderedChildren':steps,'maximumCPUSecondsPerChild':1800,'loaderWallSecondsPerChild':1800,'outerWallSecondsPerChild':1810,'maximumReapSeconds':30,'maximumProcessAddressBytes':4294967296,'hardPerFileBytes':67108864,'softPolledStdoutBytes':8388608,'softPolledStderrBytes':1048576,'pollSeconds':.02,'rawPolicy':'soft polled refusal thresholds may overshoot; retain/hash raw; no overcap decode; independent hard RLIMIT_FSIZE64MiB','compilerFuel':'off','arenaCaps':{'pairs':16777216,'stringPoolBytes':268435456,'vectors':4194304,'vectorItems':134217728},'noRetry':True,'freshOutputRoot':str(O),'artifactIdentityOnly':True,'compilerArenaEquivalenceClaimed':False,'TCEmitterExecutionAuthorized':False,'generatedWorkloadExecutionAuthorized':False,'timingAuthorized':False,'execution':{'compiler':0,'native':0,'ssh':0,'solver':0,'CPUProbe':0}}
assert len(ip)<=pr['maximumInputFiles']and pr['inputLogicalBytes']<=pr['maximumInputLogicalBytes'];save(D/'preregistration.json',pr)
sp={p.name:receipt(p)for p in sorted(D.iterdir())if p.is_file()and p.name not in ['source-pins.json','freeze.json']};save(D/'source-pins.json',sp)
freeze={'status':'SOURCE_HOLD_PENDING_ROOT_AND_INDEPENDENT_EXACT_REVIEW','files':{p.name:receipt(p)for p in sorted(D.iterdir())if p.is_file()and p.name!='freeze.json'},'sourcePinsSHA256':receipt(D/'source-pins.json')['sha256'],'inputCount':len(ip),'inputLogicalBytes':pr['inputLogicalBytes'],'localSourceCount':len(sp),'localSourceLogicalBytes':sum(v['bytes']for v in sp.values()),'execution':pr['execution']};save(D/'freeze.json',freeze)
print(json.dumps({'freeze':receipt(D/'freeze.json'),'sourcePins':receipt(D/'source-pins.json'),'inputPins':receipt(D/'input-pins.json'),'preregistration':receipt(D/'preregistration.json'),'driver':receipt(D/'run.py'),'inputCount':len(ip),'inputLogicalBytes':pr['inputLogicalBytes'],'sourceCount':len(sp),'sourceLogicalBytes':freeze['localSourceLogicalBytes']},indent=2))
