from pathlib import Path
import json,hashlib,ast,sys,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'current17-consumer-build38-qualify342-source-v1-20261009-dense';A=W/'current17-consumer-build38-source-review-independent-20261009';P=W/'tc-hft-current19-packet-install-source-v3-20261009-crc'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rec(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=h(p))
def load(p):return json.loads(p.read_bytes())
def check(p,r):assert p.is_file() and not p.is_symlink() and p.stat().st_size==r['bytes'] and h(p)==r['sha256'],p
sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');assert len(sp)==14 and len(ip)==108 and sum(x['bytes'] for x in ip.values())==2931240
for n,v in sp.items():check(D/n,v)
freeze=load(D/'build-freeze.json')
for n,k in [('source-pins.json','sourcePins'),('input-pins.json','inputPins'),('build.py','driver'),('build-preregistration.json','preregistration')]:check(D/n,freeze[k])
members={v['relativePath']:v for v in load(P/'manifest.json')['files']}
for n,v in ip.items():
 m=members[n];assert (m['bytes'],m['sha256'])==(v['bytes'],v['sha256']);check(Path(m['source']),v)
cs=load(D/'consumer-source-pins.json');assert len(cs)==13
for n,v in cs.items():assert ip['source/consumer/'+n]==v
packet=load(D/'packet.json')['entries'];assert len(packet)==19 and len({r['workload'] for r in packet})==19
for row in packet:
 w=row['workload'];check(Path(row['source']['path']),row['source']);assert ip['sources/kotoba/'+w+'.kotoba']=={k:row['source'][k]for k in ('bytes','sha256')}
 for arm in ['OFF','ON']:
  for typ,suffix in [('native','.bin'),('container','.kseed')]:
   r=row[arm][typ];check(Path(r['path']),r);assert ip[f'inputs/{w}/{arm}'+suffix]=={k:r[k]for k in ('bytes','sha256')}
 assert row['profiles']==([0,1,2,17,2000] if w=='depthconv' else [0,1,2,17,32]) and row['symbol'] in ('bench','batch')
# Pure imports only; build main and limit-exec are never executed.
sys.path.insert(0,str(D));sys.dont_write_bytecode=True
import build,header
pr=load(D/'build-preregistration.json');rs=load(D/'recipes.json')['commands'];assert build.scope(pr,ip,rs)
proofs={q['workload']:q for q in load(W/'current19-C-build38-v3-actual-review-independent-20261009/verified-proofs.json')}
headerSizes={}
for row,r in zip(packet,rs):
 assert row['workload']==r['workload'] and row['symbol']==r['cSymbol'];w=row['workload'];q=proofs[w];off=Path(row['OFF']['native']['path']).read_bytes();on=Path(row['ON']['native']['path']).read_bytes();c=Path(q['savedCopy']['path']).read_bytes();b=header.header(row,off,on,c,q);headerSizes[w]=len(b);assert len(b)<=16777216
 assert build.argv(r,Path('/fixed'),Path('/fixed/out'),{'compiler':{'path':'/fixed/clang'}},True)==build.argv(r,Path('/fixed'),Path('/fixed/out'),{'compiler':{'path':'/fixed/clang'}})[:4]+['-M']+build.argv(r,Path('/fixed'),Path('/fixed/out'),{'compiler':{'path':'/fixed/clang'}})[4:-3]
for n in ['build.py','build-limit-exec.py','prepare.py','header.py','qualification.py']:ast.parse((D/n).read_text(),feature_version=(3,9))
# Source-bound valid-last and no operational top-level in driver/helper modules.
s=(D/'build.py').read_text();assert s.index("save(O/'terminal.json'")<s.index("save(O/'report.json'");assert "guard()\n  save(O/'report.json'" in s;assert "if not closed:r['state']='closure-uncertain-no-output-hashes-no-further-operations'" in s
assert "prepared(root,g)" in (D/'build-limit-exec.py').read_text() and "os.execve(a[0],a,env)" in (D/'build-limit-exec.py').read_text()
(A/'checks.json').write_text(json.dumps(dict(sourceFiles=14,inputFiles=108,inputBytes=2931240,consumerSourceFiles=13,originalWorkloads=19,headerReconstructionFromActualCProofs=19,headerSizes=headerSizes,pureControls=load(D/'build-pure-controls.json'),operations=0),indent=2)+'\n')
print('PASS pins/recipes/header19/compiler38 static only')
