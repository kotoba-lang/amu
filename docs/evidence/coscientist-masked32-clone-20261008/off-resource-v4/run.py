"""Finite OFF-only two compilation resource probes. Import inert."""
from pathlib import Path
import json,hashlib,sys,os,re,subprocess,signal
D=Path(__file__).resolve().parent;O=D/'run-outputs';H=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def pin(p,v):
 p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size==v['bytes'] and H(p.read_bytes())==v['sha256'];return p
def main():
 assert len(sys.argv)==2;gp=Path(sys.argv[1]);gb=gp.read_bytes();g=json.loads(gb);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json')
 assert g['status']=='ROOT_GO_MASKED32_OFF_RESOURCE_PROBES2_ONLY' and g['sourcePinsSHA256']==H((D/'source-pins.json').read_bytes()) and g['maximumChildCalls']==2 and g['ONInstallerAuthorized'] is False and g['benchmarkGuestAuthorized'] is False and g['noRetry'] is True
 assert len(g['sourceReviews'])==2 and len({e['path']for e in g['sourceReviews']})==2
 for e in g['sourceReviews']:
  q=load(pin(e['path'],e));assert q['status']=='PASS_SOURCE_ONLY_MASKED32_OFF_RESOURCE_PROBES2' and q['sourcePinsSHA256']==g['sourcePinsSHA256']
 accepted=g['actualBuild'];q=load(pin(accepted['report']['path'],accepted['report']));ip=load(pin(accepted['inputPins']['path'],accepted['inputPins']))
 assert accepted['report']['sha256']==pr['mandatoryActualCompilerReportSHA256']
 assert q['status']=='PASS_INDEPENDENT_ACTUAL_MASKED32_COMPILER_BUILD4_ONLY' and q['sourcePinsSHA256']==pr['sourcePinsSHA256'] and q['inputPinsSHA256']==accepted['inputPins']['sha256']
 counts=q['counts'];expectedCounts={'closedLoaderCalls':4,'compileCalls':2,'extractCalls':2,'generatedInstallerCalls':0,'benchmarkGuestCalls':0,'auditorNativeCalls':0}
 assert type(counts)is dict and set(counts)==set(expectedCounts) and all(type(counts[k])is int and counts[k]==v for k,v in expectedCounts.items())
 assert type(q['images'])is list and len(q['images'])==2 and {r['arm']for r in q['images']}=={'OFF','ON'} and all(r['generatedProgramExecuted'] is False and type(r['offset'])is int and r['offset']==0 and type(r['arity'])is int and r['arity']==0 for r in q['images'])
 off=[r for r in q['images']if r['arm']=='OFF'];assert len(off)==1;image=off[0]['native'];assert ip[image['path']]=={'bytes':image['bytes'],'sha256':image['sha256']}
 newAcceptance=g['newLoaderActualAcceptance'];nr=load(pin(newAcceptance['report']['path'],newAcceptance['report']));nip=load(pin(newAcceptance['inputPins']['path'],newAcceptance['inputPins']));rawRef=g['newLoaderBuildReport'];br=load(pin(rawRef['path'],rawRef))
 assert newAcceptance['report']['sha256']==pr['mandatoryActualLoaderReportSHA256']
 assert nr['status']=='PASS_INDEPENDENT_ACTUAL_SOURCE_BOUND_DIAGNOSTIC_LOADER16_BUILD_IDENTITY_ONLY' and nr['inputPinsSHA256']==newAcceptance['inputPins']['sha256'] and nr['sourcePinsSHA256']==pr['newLoaderPlanPinsSHA256'] and nr['actualReportSHA256']==rawRef['sha256']
 lc=nr['counts'];expectedLoaderCounts={'closedChildCalls':16,'identityQueries':14,'dependencyCalls':1,'CBuildCalls':1,'clangInvocationsIncludingVersionAndTarget':6,'guestCalls':0,'auditorNativeCompilerSSHCalls':0}
 assert type(lc)is dict and set(lc)==set(expectedLoaderCounts) and all(type(lc[k])is int and lc[k]==v for k,v in expectedLoaderCounts.items())
 assert nr['CSourceSHA256']==pr['inputs']['/Users/junkawasaki/github/wt/amu-seed17/tools/kexe_loader.c']['sha256'] and nr['loader']==br['loader']
 assert br['status']=='COMPLETE_SOURCE_BOUND_DIAGNOSTIC_LOADER16_BUILD_IDENTITY_ONLY' and br['childCalls']==16 and br['guestCalls']==0 and br['sourceSHA256']==pr['inputs']['/Users/junkawasaki/github/wt/amu-seed17/tools/kexe_loader.c']['sha256']
 loader=br['loader'];assert nip[loader['path']]=={'bytes':loader['bytes'],'sha256':loader['sha256']} and nip[rawRef['path']]=={'bytes':rawRef['bytes'],'sha256':rawRef['sha256']}
 allInputs=dict(ip)
 for p,v in nip.items():
  assert p not in allInputs or allInputs[p]==v
  allInputs[p]=v
 assert len(allInputs)<=8192 and sum(v['bytes']for v in allInputs.values())<=402653184

 def guard():
  assert gp.read_bytes()==gb and H((D/'source-pins.json').read_bytes())==g['sourcePinsSHA256']
  for n,v in sp.items():pin(D/n,v)
  for p,v in pr['inputs'].items():pin(p,v)
  for p,v in allInputs.items():pin(p,v)
  for e in [accepted['report'],accepted['inputPins'],newAcceptance['report'],newAcceptance['inputPins'],rawRef]:pin(e['path'],e)
  for e in g['sourceReviews']:pin(e['path'],e)
 guard();assert not O.exists();O.mkdir();rows=[];usage=[];ok=False
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(Path.home()),'TMPDIR':str(O),'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_COMMAND':'1','KEXE_CAP_RESOURCES_35':str(O),'KEXE_STRING_POOL':'268435456','KEXE_VECTORS':'4194304','KEXE_PAIRS':'16777216','KEXE_VECTOR_ITEMS':'134217728','KEXE_CPU_SECONDS':'1800','KEXE_WALL_SECONDS':'1800','KEXE_ARENA_USE':'1','KEXE_FUEL':'off'}
 fields=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
 pat=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)' for k in fields)+'}\n').encode())
 try:
  for c in pr['cases']:
   guard();src=O/(c['workload']+'.kotoba');src.write_bytes(Path(c['source']).read_bytes());src.chmod(0o444);dst=O/(c['workload']+'.kseed')
   argv=[loader['path'],image['path'],'0','0','aarch64','35,37,38,39','--','compile',str(src),'--target','aarch64-macos','--output',str(dst)];r={'index':len(rows)+1,'label':c['workload'],'argv':argv,'effectiveEnvironment':env,'state':'started','timeoutSeconds':1810};rows.append(r);save(O/'attempts.json',rows);p=None;raw=err=b'';failure=None;cleanup=None
   try:p=subprocess.Popen(argv,cwd=O,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);raw,err=p.communicate(timeout=1810)
   except BaseException as ex:
    failure=repr(ex)
    if p is not None:
     try:
      try:os.killpg(p.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      raw,err=p.communicate(timeout=30)
     except BaseException as ex2:
      cleanup=repr(ex2)
      try:p.wait(timeout=30)
      except BaseException as ex3:cleanup+=';reap='+repr(ex3)
   (O/(c['workload']+'.stdout')).write_bytes(raw);(O/(c['workload']+'.stderr')).write_bytes(err);closed=p is None or p.returncode is not None;r.update(state='terminal'if closed else 'unclosed',returncode=None if p is None else p.returncode,failure=failure,cleanupException=cleanup,stdoutSHA256=H(raw),stderrSHA256=H(err));save(O/'attempts.json',rows)
   assert closed and failure is None and cleanup is None and p.returncode==0 and b':ok true'in raw and b':ok false'not in raw
   m=pat.fullmatch(err);assert m is not None;u=dict(zip(fields,map(int,m.groups())));assert u['heap-bytes']==u['pairs']*16+u['string-pool-bytes']+u['vectors']*16+u['vector-items']*8
   assert u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
   assert src.read_bytes()==Path(c['source']).read_bytes() and dst.read_bytes()==Path(c['baselineWholeContainer']).read_bytes();guard();usage.append({'workload':c['workload'],'arenaHighwater':u,'wholeOriginalContainerIdentity':True,'ONAdmission':False});save(O/'usage.json',usage)
  save(O/'report.json',{'status':'COMPLETE_TWO_OFF_COMPILER_RESOURCE_OBSERVATIONS_ONLY','childCalls':2,'observations':usage,'ONAdmission':False,'physicalFuelHeadroomObserved':False,'performanceQualified':False});ok=True
 except BaseException as ex:save(O/'failure.json',{'exception':repr(ex),'childCalls':len(rows),'noRetry':True});raise
 finally:save(O/'terminal.json',{'childCalls':len(rows),'allChildrenClosed':all(r['state']=='terminal'for r in rows),'failure':not ok})
if __name__=='__main__':main()
