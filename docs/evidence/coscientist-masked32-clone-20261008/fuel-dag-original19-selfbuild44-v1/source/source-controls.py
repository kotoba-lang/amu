"""Finite AST/byte SOURCE controls only; never imports or executes run.py."""
from pathlib import Path
import ast,json,hashlib
D=Path(__file__).resolve().parent
def load(p):return json.loads(Path(p).read_bytes())
def rec(p):
 p=Path(p);assert p.is_file() and not p.is_symlink();b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
p=load(D/'preregistration.json');ip=load(D/'input-pins.json');s=(D/'run.py').read_text();tree=ast.parse(s)
origin=Path(p['callLedgerOrigin']['path']);osrc=origin.read_text();otree=ast.parse(osrc)
def ledger(src,t):
 n=next(n for n in ast.walk(t)if isinstance(n,ast.FunctionDef)and n.name=='call');return ast.get_source_segment(src,n)
assert ledger(s,tree)==ledger(osrc,otree).replace('len(rows)<40','len(rows)<44').replace('finite40','finite44')
for name,z in ip.items():assert rec(name)==z,name
assert len(ip)==p['exactInputFiles']<=3072 and sum(z['bytes']for z in ip.values())==p['exactInputLogicalBytes']<=448*1024**2
assert len(p['entries'])==19 and len({e['workload']for e in p['entries']})==19
assert all('retained'not in e and len(e['iterations'])==5 for e in p['entries'])
assert p['maximumLoaderCalls']==44 and p['remainingWorkloadCalls']==38 and p['selfbuildCalls']==6 and p['retainedOrdinaryWorkloadCalls']==0
assert "len(rows)==38" in s and "len(rows)==44" in s and "for generation in [1,2,3]" in s
assert "if 'retained'in e"not in s and 'actualOwnerProof'not in s and "G1 G2 G3 fixed point whole artifact"in s
assert "exports==[('main',0,0)]"in s and "b.read_bytes()==payload"in s
assert "guestRootAcceptanceSchema"in s and "guest['scope']==pr['guestReceiptScope']"in s
assert p['compileResources']==dict(stringPool=268435456,vectors=4194304,pairs=16777216,vectorItems=134217728,CPUSeconds=1800,WallSeconds=1800,compilerFuel='off',arenaDiagnostics=True)
assert p['workloadGuestAuthorized']is False and p['timingAuthorized']is False and not (D/'run-outputs').exists()
result=dict(status='PASS_FINITE_SOURCE_CONTROLS_ONLY',driverAST=True,ledgerExactExcept44CapAndLabel=True,exactInputFiles=len(ip),exactInputLogicalBytes=sum(z['bytes']for z in ip.values()),matrix19ExactSourcesAnd5Profiles=True,all19FreshCompileExtract38=True,selfbuild6WholeFixedpointRequired=True,compilerResourcesUnchanged=True,nativeCompilerSSHDriverCalls=0)
(D/'source-controls.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
