import sys
from pathlib import Path
D=Path(__file__).resolve().parent
exec(compile((D/'local-common.py').read_bytes(),str(D/'local-common.py'),'exec'),globals())
def main():
 assert len(sys.argv)==2;gp=Path(sys.argv[1]);gh=H(gp.read_bytes());g=guard(gp,'remote-build');assert g['maximumTransportProcesses']==1 and g['maximumRemoteChildren']==33
 go=g['remoteBuildGO'];expected=read(D/'remote-build-go-proposal.json');assert go==expected
 invpath=next(Path(p) for p in read(D/'input-pins.json') if p.endswith('/inventory.json'))
 inv=read(invpath);assert len(inv['members'])==285
 l=Ledger(D/'launch-outputs',1)
 try:
  o,e=l.call(remote('remote-build.py'),4500,(json.dumps({'go':go,'inventory':inv})+'\n').encode())
  assert H(gp.read_bytes())==gh;guard(gp,'remote-build')
  save(l.O/'report.json',{'status':'REMOTE_BUILD_DRIVER_RETURNED_ZERO_PENDING_COLLECTED_RAW_AUDIT','transportCalls':1,'remoteChildrenMaximum':33,'guests':0,'timing':False})
 except BaseException as e:save(l.O/'failure.json',{'error':repr(e),'noRetry':True,'remoteClosureRequiresCollectedTerminal':True});raise
 finally:l.terminal()
if __name__=='__main__':main()
