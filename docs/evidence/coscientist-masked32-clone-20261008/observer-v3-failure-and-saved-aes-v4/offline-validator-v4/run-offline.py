"""Single saved-AES replay; no compiler/guest/SSH/subprocess calls."""
from pathlib import Path
import json,hashlib,sys,stat
D=Path(__file__).resolve().parent;H=lambda b:hashlib.sha256(b).hexdigest()
def read(p,cap):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size<=cap;return p.read_bytes()
def main():
 assert len(sys.argv)==2;gp=Path(sys.argv[1]);gb=read(gp,1048576);g=json.loads(gb);pr=json.loads(read(D/'preregistration.json',1048576));spb=read(D/'source-pins.json',1048576);sp=json.loads(spb)
 assert g['status']=='ROOT_GO_OFFLINE_SAVED_AES_OBSERVER_VALIDATION_V4_ONLY' and g['sourcePinsSHA256']==H(spb) and g['maximumOfflineValidations']==1 and type(g['maximumOfflineValidations'])is int and g['nativeAuthorized']is False and g['noRetry']is True
 def guard():
  assert read(gp,1048576)==gb and H(read(D/'source-pins.json',1048576))==g['sourcePinsSHA256']
  for n,v in sp.items():
   b=read(D/n,v['bytes']);assert len(b)==v['bytes'] and H(b)==v['sha256']
  for p,v in pr['inputs'].items():
   b=read(p,v['bytes']);assert len(b)==v['bytes'] and H(b)==v['sha256']
 guard();O=D/'offline-outputs';assert not O.exists();O.mkdir();ok=False;result=None
 try:
  report=json.loads(read(pr['failedReport'],1048576));terminal=json.loads(read(pr['failedTerminal'],1048576));attempts=json.loads(read(pr['failedAttempts'],1048576))
  assert report['status']=='FAIL_READONLY_ON_CLONE_OBSERVER6' and report['childCalls']==3 and report['cumulativeChildCalls']==4 and report['priorFailureReclassified']is False
  assert terminal['childCalls']==3 and terminal['allChildrenClosed']is True and terminal['failure']is True and len(attempts)==3 and all(r['state']=='terminal' and r['returncode']==0 and r['failure']is None for r in attempts)
  assert [r['label']for r in attempts]==['observer-compile','observer-extract','nettle-aes-compile']
  raw=read(pr['raw'],67108864);assert H(raw)==attempts[2]['stdout']['sha256']
  ns={'__file__':str(D/'validate.py')};exec(compile(read(D/'validate.py',1048576),str(D/'validate.py'),'exec'),ns)
  guard();result=ns['validate'](raw,'nettle-aes',pr['observedContainer'],pr['ordinaryContainer']['path'],pr['ordinaryContainer']);guard()
  assert result['status']=='PASS_FIXED_ON_CLONE_CAPTURE_WHOLE_NONINSTRUMENTED_IDENTITY_ONLY';ok=True
 finally:
  (O/'report.json').write_text(json.dumps({'status':'PASS_OFFLINE_SAVED_AES_OBSERVER_VALIDATION_V4_ONLY'if ok else'FAIL_OFFLINE_SAVED_AES_OBSERVER_VALIDATION_V4','result':result,'nativeCalls':0,'originalFailedCampaignPreserved':True,'sourcePinsSHA256':H(spb),'rootGOSHA256':H(gb)},indent=2)+'\n')
if __name__=='__main__':main()
