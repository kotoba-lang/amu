import sys
from pathlib import Path
D=Path(__file__).resolve().parent
exec(compile((D/'local-common.py').read_bytes(),str(D/'local-common.py'),'exec'),globals())
def functional_proofs(g):
 go=g['remoteFunctionalGO'];fixed=read(D/'remote-functional-go-fixed-fields.json')
 assert set(go)==set(fixed)|{'buildIndependentReview','buildReviewAcceptance'} and all(go[k]==v for k,v in fixed.items())
 def pin(role):
  e=g[role];p=Path(e['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==e['bytes'] and H(p.read_bytes())==e['sha256'];return p
 rv=pin('actualBuildIndependentReview');ip=pin('actualBuildIndependentInputPins');ac=pin('rootBuildReviewAcceptance')
 review=read(rv);raw=read(ip);assert review['status'].startswith('PASS_') and review['inputPinsSHA256']==H(ip.read_bytes())
 # Specific current cohort binding, never an unrelated PASS boolean.
 inputs=read(D/'input-pins.json')
 for suffix in ['/runner-build/report.json','/runner-build/terminal.json','/runner-build/identity-before.json','/runner-build/identity-after.json']:
  path=next(k for k in inputs if k.endswith(suffix));assert raw[path]==inputs[path]
 a=read(ac);assert a=={'status':'ROOT_ACCEPTED_INDEPENDENT_EXTR_FRESH19_BUILD_ONLY','reviewSHA256':H(rv.read_bytes()),'buildReportSHA256':fixed['runnerBuild']['report']['sha256'],'buildTerminalSHA256':fixed['runnerBuild']['terminal']['sha256'],'builds':19,'identityQueries':14,'clangInvocations':23}
 for field,p,name in [('buildIndependentReview',rv,'actual-build-independent-review.json'),('buildReviewAcceptance',ac,'root-build-review-acceptance.json')]:assert go[field]=={'path':R+'/'+name,'sha256':H(p.read_bytes()),'bytes':p.stat().st_size}
 return rv.read_text(),ac.read_text()
def main():
 assert len(sys.argv)==2;gp=Path(sys.argv[1]);gh=H(gp.read_bytes());g=guard(gp,'remote-functional');assert g['maximumTransportProcesses']==1 and g['maximumGuestCalls']==171
 review,acceptance=functional_proofs(g);invpath=next(Path(p) for p in read(D/'input-pins.json') if p.endswith('/inventory.json'))
 l=Ledger(D/'launch-outputs',1);save(l.O/'remote-functional-go-used.json',g['remoteFunctionalGO'])
 try:
  o,e=l.call(remote('remote-functional.py'),5400,(json.dumps({'go':g['remoteFunctionalGO'],'review':review,'acceptance':acceptance,'inventory':read(invpath)})+'\n').encode())
  assert H(gp.read_bytes())==gh;guard(gp,'remote-functional');functional_proofs(g)
  save(l.O/'report.json',{'status':'REMOTE_FUNCTIONAL_DRIVER_RETURNED_ZERO_PENDING_COLLECTED_RAW_AUDIT','transportCalls':1,'guestMaximum':171,'timingQualified':False})
 except BaseException as e:save(l.O/'failure.json',{'error':repr(e),'noRetry':True,'remoteClosureRequiresCollectedTerminal':True});raise
 finally:l.terminal()
if __name__=='__main__':main()
