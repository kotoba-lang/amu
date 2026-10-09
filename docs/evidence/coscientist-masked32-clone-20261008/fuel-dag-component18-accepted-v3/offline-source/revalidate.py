"""Inert import; exactly one retained raw validation, no subprocess/native."""
from pathlib import Path
import json,hashlib,stat,sys
D=Path(__file__).resolve().parent;H=lambda b:hashlib.sha256(b).hexdigest()
def need(x,m):
 if not x:raise AssertionError(m)
def load(p):return json.loads(Path(p).read_bytes())
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def pin(p,r):
 p=Path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_size==r['bytes']and 0<=s.st_size<=384*1024**2,'stat before bounded read');b=p.read_bytes();s2=p.lstat();need((s.st_ino,s.st_dev,s.st_size,s.st_mtime_ns)==(s2.st_ino,s2.st_dev,s2.st_size,s2.st_mtime_ns)and H(b)==r['sha256'],'immutable exact pin');return b
def main(gopath):
 gp=Path(gopath);gb=gp.read_bytes();g=json.loads(gb);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot']);old=Path(pr['oldDirectory'])
 need(g['status']==pr['rootGOStatus']and g['maximumOfflineValidations']==1 and g['maximumNativeCalls']==0 and g['noRetry']is True and g['outputRoot']==str(O),'exact finite offline GO')
 need(H((D/'source-pins.json').read_bytes())==g['sourcePinsSHA256']and H((D/'revalidate.py').read_bytes())==g['driverSHA256']and H((D/'preregistration.json').read_bytes())==g['preregistrationSHA256']and H((D/'input-pins.json').read_bytes())==g['inputPinsSHA256']==pr['inputPinsSHA256'],'GO source bindings')
 need(len(g['sourceReviews'])==2 and len({r['path']for r in g['sourceReviews']})==2,'two independent source reviews')
 def guard():
  need(gp.read_bytes()==gb and H((D/'source-pins.json').read_bytes())==g['sourcePinsSHA256'],'immutable GO/registry')
  for n,z in sp.items():pin(D/n,z)
  need(len(ip)<=pr['maximumInputFiles']and sum(z['bytes']for z in ip.values())<=pr['maximumInputLogicalBytes'],'complete closure cap')
  total=0
  for p,z in ip.items():
   q=Path(p);st=q.lstat();need(stat.S_ISREG(st.st_mode)and not q.is_symlink()and st.st_size==z['bytes'],'closure stat');total+=st.st_size;need(total<=pr['maximumInputLogicalBytes'],'closure aggregate before reads')
  for p,z in ip.items():pin(p,z)
  for z in g['sourceReviews']:
   r=json.loads(pin(z['path'],z));need(r['status']==pr['sourceReviewStatus']and r['sourcePinsSHA256']==g['sourcePinsSHA256']and r['driverSHA256']==g['driverSHA256']and r['validatorSHA256']==sp['validate.py']['sha256'],'specific complete source review')
  r=load(pr['failureAudit']);need(r['status']=='FAIL_PRESERVED_INDEPENDENT_SAVED_RAW_FUEL_DAG_COMPONENT18'and r['loaderCalls']==3 and r['componentCasesVerified']==0 and r['firstFailureIndex']==3 and r['allRecordedChildrenClosed']is True,'preserved independent failure3')
  t=load(old/'run-outputs/terminal.json');a=load(old/'run-outputs/attempts.json');need(t=={'loaderCalls':3,'allChildrenClosed':True,'failure':True}and len(a)==3 and all(z['state']=='terminal'and z['returncode']==0 and z['reaped']is True for z in a),'original closed failure3 remains failure')
  need((D/'validate.py').read_bytes().replace(b'al[4:]==[1,0]',b'al[4:]==[0,0]')==(old/'validate.py').read_bytes(),'exact one-hunk reverse')
 guard();need(not O.exists(),'fresh once-only offline root');O.mkdir();ok=False
 try:
  validator_namespace={'__file__':str(D/'validate.py'),'__name__':'fuel_dag_pinned_validator_v3'}
  exec(compile(pin(D/'validate.py',sp['validate.py']),str(D/'validate.py'),'exec'),validator_namespace)
  validate=type('PinnedValidator',(),{'verify':staticmethod(validator_namespace['verify'])})
  raw=pin(pr['savedRaw'],ip[pr['savedRaw']]);result=validate.verify(raw,0);guard()
  save(O/'report.json',{'status':'COMPLETE_OFFLINE_SAVED_FUEL_DAG_CASE0_VALIDATOR_V3_ONLY','offlineValidations':1,'nativeCalls':0,'case0':result,'savedRaw':dict(path=pr['savedRaw'],**ip[pr['savedRaw']]),'sourcePinsSHA256':g['sourcePinsSHA256'],'rootGOSHA256':H(gb),'oldFailure3Preserved':True,'remainingCasesExecuted':0,'actualGeneratedCodeTrapQualified':False});ok=True
 except BaseException as ex:save(O/'failure.json',{'error':type(ex).__name__+': '+str(ex),'nativeCalls':0,'noRetry':True});raise
 finally:save(O/'terminal.json',{'offlineValidations':1,'nativeCalls':0,'failure':not ok})
if __name__=='__main__':need(len(sys.argv)==2,'root GO required');main(sys.argv[1])
