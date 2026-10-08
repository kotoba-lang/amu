"""Offline saved raw only, one exact verified validator-buffer execution after root GO."""
from pathlib import Path
import hashlib,json,stat,sys
D=Path(__file__).resolve().parent;H=lambda b:hashlib.sha256(b).hexdigest()
def read(p,z=None):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and 0<=s.st_size<=402653184;b=p.read_bytes();assert len(b)==s.st_size
 if z:assert len(b)==z['bytes']and H(b)==z['sha256']
 return b
def load(p):return json.loads(read(p))
def main():
 assert len(sys.argv)==2;gp=Path(sys.argv[1]);gb=read(gp);g=json.loads(gb);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');O=Path(pr['freshOutputRoot'])
 assert g['status']==pr['rootGOStatus']and type(g['maximumOfflineValidations'])is int and g['maximumOfflineValidations']==1 and g['nativeAuthorized']is False and g['noRetry']is True and g['outputRoot']==str(O)
 for n,k in [('source-pins.json','sourcePinsSHA256'),('run.py','driverSHA256'),('validate.py','validatorSHA256'),('preregistration.json','preregistrationSHA256'),('input-pins.json','inputPinsSHA256')]:assert H(read(D/n))==g[k]
 assert len(g['sourceReviews'])==2 and len({x['path']for x in g['sourceReviews']})==2
 def guard():
  assert read(gp)==gb and H(read(D/'source-pins.json'))==g['sourcePinsSHA256'];assert len(ip)<=2048 and sum(z['bytes']for z in ip.values())<=402653184
  for p,z in ip.items():read(p,z)
  for n,z in sp.items():read(D/n,z)
  for x in g['sourceReviews']:
   q=json.loads(read(x['path'],x));assert q['status']==pr['sourceReviewStatus']and q['sourcePinsSHA256']==g['sourcePinsSHA256']and q['driverSHA256']==g['driverSHA256']and q['validatorSHA256']==g['validatorSHA256']
 guard();pf=load(pr['priorOfflineFailureReport']['path']);assert pf['status']==pr['priorOfflineFailureStatus']and pf['counts']=={'offlineValidations':1,'newNativeCalls':0,'oldClosedNativeCalls':3,'oldFourthExtractUnexecuted':1,'inputFiles':1844,'logicalBytes':376389897}and pf['originalOfflineFailure']is True and pf['nativeCompilerFailure']is False and pf['validatorRerun']is False and pf['inputPinsSHA256']==pr['priorOfflineFailureInputPins']['sha256'];pt=load(pr['priorOfflineFailureNamespace']+'/terminal.json');assert pt=={'offlineValidations':1,'nativeCalls':0,'failure':True};f=load(pr['failureAuditReport']['path']);assert f['status']==pr['failureAuditStatus']and f['counts']['closedCalls']==3 and f['counts']['nativeRC0']==3 and f['counts']['compile']==2 and f['counts']['extract']==1 and f['counts']['unexecutedExtract']==1 and f['originalTerminalFailure']is True and f['nativeCompilerFailure']is False and f['inputPinsSHA256']==pr['failureAuditInputPins']['sha256']
 t=load(pr['oldFailedNamespace']+'/terminal.json');assert t=={'loaderCalls':3,'allChildrenClosed':True,'failure':True}
 old=Path(pr['oldFailedNamespace']);k=read(old/'positive.kseed');base=read(pr['baselineContainer']);assert k==base and len(k)==298;head,native=k.split(b'\n\n',1);assert len(native)==272 and native==read(pr['baselineNative'])and H(native)==pr['baselineNativeSHA256'];src=read(old/'positive.kotoba');assert src==read(pr['fixture']);raw=read(old/'positive-compile.stdout')
 assert all(x in raw.splitlines()for x in [b'FSIR 0 23 13 1 0 1',b'FSIR 0 24 19 0 0 0',b'FSIR 0 25 2 3 0 0',b'FSIR 1 23 13 1 0 1',b'FSIR 1 24 19 0 0 0',b'FSIR 1 25 2 3 0 0']);vb=read(D/'validate.py',sp['validate.py']);ns={'__file__':str(D/'validate.py'),'__name__':'pinned_offline_typed_owner_validator_v3'};exec(compile(vb,str(D/'validate.py'),'exec'),ns)
 assert not O.exists();O.mkdir();ok=False
 try:
  result=ns['verify'](raw,src,native,140);guard();(O/'report.json').write_text(json.dumps({'status':'COMPLETE_OFFLINE_FUEL_DAG_TYPED_OWNER_SAVED_RAW_VALIDATOR_V3_ONLY','offlineValidations':1,'nativeCalls':0,'sourcePinsSHA256':g['sourcePinsSHA256'],'validatorSHA256':H(vb),'rootGOSHA256':H(gb),'savedRawSHA256':H(raw),'failureAuditReportSHA256':pr['failureAuditReport']['sha256'],'observed':result,'oldFailedNativeCallsPreserved':3,'newNativeExtracts':0,'generatedCodeExecution':False,'actualCPUTrapQualified':False,'performanceQualified':False},indent=2)+'\n');ok=True
 except BaseException as ex:(O/'failure.json').write_text(json.dumps({'error':repr(ex),'offlineValidations':1,'nativeCalls':0,'noRetry':True},indent=2)+'\n');raise
 finally:(O/'terminal.json').write_text(json.dumps({'offlineValidations':1,'nativeCalls':0,'failure':not ok},indent=2)+'\n')
if __name__=='__main__':main()
