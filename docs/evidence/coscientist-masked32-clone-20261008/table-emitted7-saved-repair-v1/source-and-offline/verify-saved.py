"""Read-only saved-evidence verification; writes one fresh offline report. No operational APIs."""
from pathlib import Path
import json,hashlib,struct,stat
D=Path(__file__).resolve().parent;H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def checked(p,v):
 p=Path(p);a=p.lstat();need(stat.S_ISREG(a.st_mode)and not p.is_symlink()and a.st_size==v['bytes']and a.st_size<=402653184,'regular exact input stat bound');b=p.read_bytes();z=p.lstat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns),'input immutable while read');need(H(b)==v['sha256'],'input full hash');return b
def main():
 pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=D/'offline-outputs'
 need(pr['maximumNativeCompilerGuestCalls']==0 and len(ip)<=4096 and sum(v['bytes']for v in ip.values())<=536870912,'finite saved-data gate')
 def guard():
  for name,v in sp.items():checked(D/name,v)
  for name,v in ip.items():checked(name,v)
 guard();need(not O.exists(),'fresh offline output/no mutation of previous failure')
 p=pr['savedOutputs'];attempts=load(p+'/attempts.json');terminal=load(p+'/terminal.json');failure=load(p+'/failure.json')
 need(len(attempts)==7 and all(r['reaped']is True and r['returncode']==0 and r['state']=='terminal'for r in attempts),'exact saved seven reaped0')
 need(terminal=={'attemptedCalls':7,'allChildrenClosed':True,'failure':True,'noRetry':True}and failure['attemptedCalls']==7 and failure['status']=='FAIL_FIRST_FAILURE_NO_RETRY','preserved original failure, not original8 completion')
 need(not Path(p+'/observed-on-input.bin').exists()and not Path(p+'/completion.json').exists(),'eighth extraction and original completion absent')
 raw=Path(p+'/observed-on-input-compile.stdout').read_bytes();need(0<len(raw)<=8388608,'bounded saved raw')
 blob=Path(p+'/observed-on-input.kseed').read_bytes();need(0<len(blob)<=4194560 and blob==Path(p+'/on-input.kseed').read_bytes(),'saved whole observer/unobserved container identity')
 end=blob.index(b'\n\n');header=blob[:end].splitlines();magic,n,en=header[0].split();need(magic==b'KSEED1','container header')
 payload=blob[end+2:];need(0<len(payload)<=4194304 and len(payload)==int(n) and len(header)-1==int(en),'whole saved container counts')
 exports=[]
 for row in header[1:]:
  z=row.split();need(len(z)==3,'export row');exports.append((z[0].decode(),int(z[1]),int(z[2])))
 need(payload==Path(p+'/on-input.bin').read_bytes(),'existing native child6 exactly equals both saved container payloads; no extraction substitute produced')
 ns={'__file__':str(D/'validate.py'),'__name__':'pinned_saved_emission_repair'};exec(compile((D/'validate.py').read_bytes(),str(D/'validate.py'),'exec'),ns)
 result=ns['verify'](raw,payload,exports,Path(pr['originalSource']).read_bytes(),load(pr['currentTypedBinding']))
 guard();O.mkdir();report={'status':'PASS_SAVED_RAW_TC_EMISSION_REPAIR_ONLY','sourcePinsSHA256':H((D/'source-pins.json').read_bytes()),'inputPinsSHA256':H((D/'input-pins.json').read_bytes()),'preregistrationSHA256':H((D/'preregistration.json').read_bytes()),'oldBuild8StillFailed':True,'savedCalls':7,'repeatedNativeCalls':0,'remainingExtractionExecuted':False,'selectedEmission':result['actualEmission'],'wholeCodeWords':result['wholeCodeWords'],'wholeObservedUnobservedContainerIdentity':True,'existingUnobservedNativeEqualsBothPayloads':True,'guestRuntimeQualified':False,'fixedPointQualified':False,'performanceQualified':False,'OSStackLimitProof':False}
 (O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
