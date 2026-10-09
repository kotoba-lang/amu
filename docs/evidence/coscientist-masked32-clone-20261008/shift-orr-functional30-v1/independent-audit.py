"""Saved-raw only; execute only after explicit root terminal notification. No subprocess calls."""
from pathlib import Path
import importlib.util,json,hashlib,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-masked32-shift-orr-functional30-plan-v1-native-controls';O=D/'run-outputs';A=Path(__file__).resolve().parent
G=W/'vector-masked32-shift-orr-functional30-go-v1-root/root-go.json';GH='b5e8ea80ae46f57a59f98e20c3eabfec2a8f3b7cc63bc322423a345cb766962f';SP='548f448a0d7e8aefa93658b8056fa4b8a2c501bb3fe0e0e396e013964467d310'
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();return {'bytes':s.st_size,'sha256':H(p)}
def main():
 spec=importlib.util.spec_from_file_location('saved_functional30',D/'run.py');V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
 assert H(G)==GH and H(D/'source-pins.json')==SP
 g=load(G);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');pins=load(D/'input-closure.json')
 assert len(pins)==1243 and sum(v['bytes']for v in pins.values())<=384*1024**2
 for p,v in pins.items():assert rec(p)==v
 for n,v in sp.items():assert rec(D/n)==v;pins[str(D/n)]=v
 assert g['status']==pr['rootGOStatus']and g['outputRoot']==str(O)and g['sourcePinsSHA256']==SP and g['driverSHA256']==H(D/'run.py')and g['preregistrationSHA256']==H(D/'preregistration.json')and g['inputClosureSHA256']==H(D/'input-closure.json')and g['maximumChildCalls']==30 and g['noRetry']is True and not g['timingAuthorized']and not g['compilerSSHAuthorized']
 assert len(g['sourceReviews'])==2 and len({v['path']for v in g['sourceReviews']})==2
 for v in g['sourceReviews']:
  assert rec(v['path'])=={k:v[k]for k in ['bytes','sha256']};q=load(v['path']);assert q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==SP;pins[v['path']]=rec(v['path'])
  ip=Path(v['path']).parent/'input-pins.json'
  if ip.exists():
   pins[str(ip)]=rec(ip)
   for p,e in load(ip).items():assert p not in pins or pins[p]==e;pins[p]=e
 for role,q in pr['proofs'].items():
  r=load(q['report']['path']);assert r['status']==q['status']and r['inputPinsSHA256']==q['inputPins']['sha256'];assert all(p in pins and pins[p]==v for p,v in load(q['inputPins']['path']).items())
 cmp=load(pr['proofs']['component36']['report']['path']);assert {k:cmp[k]for k in pr['componentFacts']}==pr['componentFacts']and cmp['sourcePinsSHA256']==pr['componentSourcePinsSHA256']
 rows=load(O/'attempts.json');t=load(O/'terminal.json');r=load(O/'report.json');assert t=={'calls':30,'allCallsClosed':True,'failure':False,'noRetry':True}and len(rows)==30
 assert r['status']=='PASS_FINITE_SR_AES_SHA30_FUNCTIONAL_ONLY'and r['calls']==30 and r['completedTriples']==10 and r['nativePairTerminalArenaFuelExact']is True and r['CNativeArenas']=='unavailable-C/null'and r['current19Qualified']is False and r['timingQualified']is False and r['officialScore']is False
 base={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(O/'tmp'),'LANG':'C','LC_ALL':'C','TZ':'UTC'}
 env={**base,'KEXE_ARG_TYPES':'i64','KEXE_RESULT_TYPE':'i64','KEXE_STRUCTURED_REPORT':'1','KEXE_FUEL':'16777216','KEXE_PAIRS':'2097152','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_VECTOR_ITEMS':'65536','KEXE_CPU_SECONDS':'30','KEXE_WALL_SECONDS':'30'}
 assert load(O/'effective-environment.json')=={'native':env,'C':base,'allInheritedRemoved':True}
 comparisons=[];i=0
 for c in pr['cases']:
  for arm in ['maskedON','SR']:
   ex,payload=V.container(c[arm+'Container']);assert ex==c['exports']and payload==V.pin(c[arm]).read_bytes()
  assert Path(c['CRunner']['path']).read_bytes().count(Path(c['C']['path']).read_bytes())==1
  for n in [0,1,2,17,32]:
   pair={}
   for arm in ['maskedON','SR','C']:
    z=rows[i];i+=1;label=c['workload']+'-'+arm+'-n'+str(n);e=base if arm=='C'else env
    argv=[c['CRunner']['path'],'dylib',c['C']['path'],c['CSymbol'],'aarch64',str(n),'1','0','16777216']if arm=='C'else[pr['loader']['path'],c[arm]['path'],str(c['offset']),'1','aarch64','-',str(n)]
    assert z['index']==i and z['label']==label and z['argv']==argv and z['environment']==e and z['timeoutSeconds']==40 and z['state']=='terminal'and z['returncode']==0 and z['failure']is None and z['cleanupException']is None
    out=(O/(label+'.stdout')).read_bytes();err=(O/(label+'.stderr')).read_bytes();assert len(out)<=1048576 and len(err)<=1048576 and hashlib.sha256(out).hexdigest()==z['stdoutSHA256']and hashlib.sha256(err).hexdigest()==z['stderrSHA256']
    pair[arm]=V.csample(out,err,n)if arm=='C'else V.native(out,err,n)
    if arm=='SR':assert pair['maskedON']==pair['SR']
   comparisons.append({'workload':c['workload'],'n':n,'arms':pair})
 assert comparisons==load(O/'comparisons.json')==r['comparisons']
 for p in [G,D/'source-pins.json',Path(__file__).resolve(),*O.rglob('*')]:
  assert not p.is_symlink()
  if p.is_file():pins[str(p)]=rec(p)
 for p,v in pins.items():assert rec(p)==v
 (A/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n');(A/'independent-comparisons.json').write_text(json.dumps(comparisons,indent=2)+'\n')
 report={'status':'PASS_INDEPENDENT_ACTUAL_SR_AES_SHA30_FUNCTIONAL_ONLY','sourcePinsSHA256':SP,'rootGOSHA256':GH,'inputPinsSHA256':H(A/'input-pins.json'),'independentComparisonsSHA256':H(A/'independent-comparisons.json'),'counts':{'closedChildCalls':30,'nativeCalls':20,'CCalls':10,'triples':10,'workloads':2,'profilesPerWorkload':5,'auditorNativeCompilerSSHCalls':0},'allRawArgvEnvironmentTypedSemanticRejoined':True,'nativePairResultFuelFourTerminalArenasExact':True,'CZeroFuelAndUnavailableNullArena':True,'wholeSRAndMaskedONContainerPayloadExportIdentityBound':True,'priorComponentFailuresPreserved':6,'participation':'Prior SOURCE reviewer and saved SR compilation/component auditor; not functional driver author or native executor.','limits':['Finite two-workload functionality on general e14 loader, distinct from previous self-contained285 context.','Historical immutable C consumer/source bytes qualified here for functionality only; fresh local SDK/toolchain/timing not certified.','Emitted output equivalence on five profiles is not universal X10/NZCV/CFG safety or resource proof.'],'current19Qualified':False,'timingQualified':False,'officialScore':False,'CIDRuntimeEffectQualified':False,'productAdopted':False}
 (A/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'reportSHA256':H(A/'report.json'),'inputPinsSHA256':report['inputPinsSHA256']}))
if __name__=='__main__':main()
