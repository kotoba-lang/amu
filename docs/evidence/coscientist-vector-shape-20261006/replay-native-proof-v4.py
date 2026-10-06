#!/usr/bin/env python3
"""Portable offline replay of selected V4 native evidence. Standard library only.
No guest/native/compiler/solver execution, SSH, timing or product changes.
"""
from pathlib import Path
import argparse,json,hashlib,tarfile,tempfile,shutil,sys,types,contextlib,io,re,struct
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(v,msg):
 if not v:raise AssertionError(msg)
def load(p):return json.loads(p.read_text())
def paired(rows,a,b):
 require(all(r[a]==r[b]for r in rows),'paired native raw states differ')
def main():
 sys.dont_write_bytecode=True;ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--archive',type=Path);ap.add_argument('--manifest',type=Path);ap.add_argument('--out',type=Path);args=ap.parse_args();here=Path(__file__).resolve().parent
 arc=args.archive or here/'native-proof-v4.tgz';mp=args.manifest or here/'native-proof-v4.manifest.json';m=load(mp);require(sha(arc)==m['archive']['sha256'],'archive SHA mismatch');require(sha(Path(__file__))==m['replay']['sha256'],'replay SHA mismatch')
 out=args.out or Path(tempfile.mkdtemp(prefix='amu-vector-v4-offline-replay-'));out.mkdir(parents=True,exist_ok=True);root=out/'unpacked';root.mkdir(exist_ok=True)
 allowed=[out.resolve(),here.resolve(),Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve(),arc.resolve(),mp.resolve()];blocked=[]
 def offline_audit(event,argv):
  if event in ['subprocess.Popen','os.system','socket.connect']:
   blocked.append(event);raise PermissionError('offline replay forbids process/network execution')
  if event=='open'and isinstance(argv[0],(str,bytes)):
   target=Path(argv[0].decode()if isinstance(argv[0],bytes)else argv[0]).resolve()
   if not any(target==r or r in target.parents for r in allowed):
    blocked.append(str(target));raise PermissionError('offline replay attempted unselected external path')
 sys.addaudithook(offline_audit)
 with tarfile.open(arc,'r:gz')as t:
  for x in t.getmembers():
   p=Path(x.name);require(not p.is_absolute()and '..'not in p.parts and x.isfile(),'unsafe archive member')
   dest=root/p;dest.parent.mkdir(parents=True,exist_ok=True)
   with t.extractfile(x)as f,dest.open('wb')as g:shutil.copyfileobj(f,g)
 P=root/'payload';inv=load(P/'selected-inventory.json');require(sha(P/'selected-inventory.json')==m['inventory']['sha256'],'selected inventory SHA mismatch')
 require(len(inv['entries'])==m['inventory']['selectedFiles'],'selected count mismatch')
 for e in inv['entries']:
  p=P/e['member'];require(p.is_file()and p.stat().st_size==e['bytes']and sha(p)==e['sha256'],'member hash mismatch: '+e['member'])
 require({str(p.relative_to(P))for p in P.rglob('*')if p.is_file()}=={e['member']for e in inv['entries']}|{'selected-inventory.json'},'undeclared archive member')
 V=P/'vector';I=V/'implementation-v4';B=P/'baseline';T=V/'typed-v4';reports={};candidate='924b03c26998aed4d2a6b15a720cea14866fa3c70d803f56e52de6efdd0a35eb';require(sha(I/'seed-4.bin')==candidate,'candidate wrong');require(sha(B/'implementation/seed-4.bin')=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93','baseline wrong')
 for name,h in load(I/'source-pins.json').items():require(sha(I/name)==h,'frozen source changed')
 generations=load(I/'fixed-point.json')['generations'];require(len(generations)==4 and all(r['sha256']==candidate and r['bytes']==910456 and r['offset']==0 for r in generations),'fixedpoint receipts wrong')
 require(all(sha(I/f'seed-{g}.bin')==candidate for g in [1,2,3,4]),'fixedpoint raw binaries wrong')
 ports=load(I/'ports-build.json')['entries'];bas=load(B/'implementation/ports-build.json')['entries'];obs=load(I/'observer/report.json')['entries'];require(len(ports)==len(bas)==len(obs)==19,'19 corpus missing');changes=[]
 for e in ports:
  name=e['workload'];b=next(x for x in bas if x['workload']==name);o=next(x for x in obs if x['workload']==name);require(sha(I/'ports'/name/'native.bin')==e['nativeSha256']==sha(I/'observer/ports'/name/'native.bin')==o['sha256']and e['offset']==o['offset'],'19 source/native/observer mismatch')
  if e['nativeSha256']!=b['nativeSha256']or e['offset']!=b['offset']:changes.append(name)
 require(set(changes)=={'matmult-int','nsichneu','statemate','ud'},'unexpected changed code set')
 for e in load(P/'reference19/comparison-matrix.json')['entries']:require(sha(P/'reference19'/e['source'])==e['expectedSourceSha256'],'original19 source wrong')
 resource=V/'team-resource-v4';sizes={'ordinary-states.json':57,'fuel-states.json':209,'resource-states.json':161};zeroReturns=0
 for fn,n in sizes.items():
  r=load(resource/fn);require(len(r['rows'])==n,'resource count wrong');paired(r['rows'],'product','candidate');zeroReturns+=sum(x['candidate']['exit']==0 and ':remaining 0}'in x['candidate']['stdout']for x in r['rows'])
 require(load(resource/'resource-states.json')['trappedPairs']==46,'resource traps wrong');reports['nativeStatePairs']=427
 mainStates=load(T/'raw-paired-states.json');require(len(mainStates)==266,'typed rows wrong');paired(mainStates,'baseline','candidate');ext=load(T/'export-index-report.json');require(ext['pairs']==16 and len(ext['rows'])==16,'external index rows wrong');paired(ext['rows'],'baseline','candidate');sent=load(T/'sentinel-report.json');require(sent['pairs']==15 and len(sent['rows'])==15 and all(r['outcome']['exit']==0 for r in sent['rows']),'ABI sentinel evidence wrong')
 reports['typedFullStatePairs']=282;reports['sentinelPairs']=15;zeroReturns+=sum(x['candidate']['exit']==0 and ':remaining 0}'in x['candidate']['stdout']for x in mainStates)
 # Eight actually compiled cap controls: expectation uses measured emission counts, never raised limits.
 limits={'matmult-int':89,'nsichneu':142,'statemate':16144,'ud':755};caps=load(V/'team-controls-v4/fallback-report.json')['controls'];require(len(caps)==8,'cap controls missing')
 for c in caps:
  kind=c['control'];cap=0 if kind=='disabled'else int(kind.removeprefix('clone-word-cap'));require(len(c['ports'])==19,'cap19 missing')
  for e in c['ports']:
   n=e['workload'];expected=next(x for x in(bas if n not in limits or cap<limits[n]else ports)if x['workload']==n);f=V/'team-controls-v4'/kind/n/'native.bin';require(sha(f)==e['sha256']==expected['nativeSha256']and e['offset']==expected['offset'],'cap fallback/code boundary mismatch')
 reports['capNativeOutputs']=152
 # Exact committed golden/source invariants, unit-generated code/pool reconstructed from raw output.
 G=V/'team-adoption-gates-v4';S=G/'source';u=G/'unit-build/unit/41-a64gen/stdout';golden=S/'seed/tests/unit/41-a64gen.expected';require(u.read_bytes()==golden.read_bytes()and len(u.read_text().splitlines())==5227,'unit golden changed')
 with tarfile.open(G/'source-44bf.tar')as t:
  for x in t.getmembers():
   if not x.isfile():continue
   data=t.extractfile(x).read();actual=S/x.name;require(actual.is_file(),'source archive member missing')
   if x.name=='seed/41-a64gen.kotoba':require(actual.read_bytes()==(I/'41-a64gen-prototype.kotoba').read_bytes(),'sole overlay mismatch')
   else:require(actual.read_bytes()==data,'unexpected committed source/golden change: '+x.name)
 words=[];lit=[];fns={};end=0
 for l in u.read_text().splitlines():
  q=l.split()
  if not q:continue
  if q[0]=='w':words.extend(int(z,16)for z in q[1:])
  elif q[0]=='lit':lit.append((int(q[1]),bytes.fromhex(q[2])if len(q)>2 else b''))
  elif q[0]=='fn':fns[int(q[1])]=int(q[2])
  elif q[0]=='end':end=int(q[1])
 blob=bytearray(b''.join(z.to_bytes(4,'little')for z in words));blob.extend(b'\0'*(end-len(blob)))
 for off,data in lit:blob[off:off+len(data)]=data
 require(bytes(blob)==(G/'unit-generated-blob.bin').read_bytes(),'unit code/pool wrong');require({str(k):v for k,v in fns.items()}==load(G/'unit-generated-offsets.json'),'unit public offsets wrong')
 gates=[x.split('\t')for x in(G/'gate-build/gates/r6m/summary.tsv').read_text().splitlines()];require({x[0]for x in gates}=={'BUILD','ERR','G1','G2','G3','G4','G5'}and all(x[1]=='PASS'for x in gates),'formal gates wrong');reports['unitLines']=5227;reports['formalGates']=7
 # Fresh native standalone rows and original registered permanent oracles, not regenerated native execution.
 F=V/'team-regressions-v4';ro=load(F/'readonly/report.json');sc=load(F/'scalar/report.json');require(ro['nativeObservations']==117 and len(ro['controls'])==117 and sc['nativeExecutions']==318 and len(sc['observations'])==318,'standalone rows wrong');require(ro['seedSha256']==sc['seedSha256']==candidate,'standalone stale seed')
 fixture=types.ModuleType('portable_fixture_oracle');fixture.__file__=str(F/'permanent-a64gen-fixtures.py');oldsys=list(sys.path);sys.path.insert(0,str(F));source=(F/'permanent-a64gen-fixtures.py').read_text().replace('/private/tmp/amu-vector-shape-specialize-20261006/team-adoption-gates-v4/source',str(S))
 exec(compile(source,fixture.__file__,'exec'),fixture.__dict__);sys.path[:]=oldsys;pe=load(F/'adoption-permanent-proof.json');require(len(fixture.FIX)==593 and len(fixture.RUNS)==len(pe['observations'])==25658,'permanent count/oracle mismatch')
 for r,(name,args,expected,opts)in zip(pe['observations'],fixture.RUNS):
  require(r['fixture']==name and r['args']==list(args)and r['expect']==expected,'permanent oracle row changed');stdout=r['stdout'];stderr=r['stderr'];status=r['exit']
  if 'fuel_remaining'in opts:
   remaining=re.search(r':remaining (-?\d+)',stdout);result=re.search(r':result (-?\d+)',stdout);good=(status!=0 and 'KEXE_TRAP'in stderr)if expected=='trap'else(status==0 and result is not None and int(result[1])==expected);good=good and remaining is not None and int(remaining[1])==opts['fuel_remaining']
  elif expected=='trap':good=status!=0 and 'KEXE_TRAP'in stderr
  elif 'cmd'in opts:good=status==(expected&255)
  else:good=status==0 and bool(stdout.splitlines())and stdout.splitlines()[-1]==str(expected)
  if 'stdout'in opts:good=good and stdout.startswith(opts['stdout'])
  require(good,'permanent actual native observation violates original oracle')
 reports['standaloneObservations']=435;reports['permanentFixtures']=593;reports['permanentObservations']=25658
 # SameM closed/open/closed actual source mutants and malformed undo error receipts.
 reuse=load(V/'team-reuse-v4/report.json');rr=reuse['rows'];require(rr[0]['accepted']and all(r['detected']for r in rr[1:]),'sameM mutants undetected');o=rr[0]['observations'];require(o['CLOSED-FN']==o['AGAIN-FN']==4 and o['OPEN-FN']==3 and o['OPEN-SIR']==13,'sameM counts wrong');require(all(o[k]==1 for k in ['CODE-EQUAL','OPEN-ORIGINAL-SIR','OPEN-FRESH-META','OPEN-FRESH-CODE','OPEN-FRESH-FIX','AGAIN-CLOSED-META','AGAIN-CLOSED-SIR','AGAIN-CLOSED-FIX','HEAP-OWNED']),'sameM state not equal');require(all(o[k]==4102 for k in ['BAD-ORIGIN','BAD-COUNT','BAD-FNCOUNT','BAD-SITE','BAD-TARGET','BAD-NONCALL']),'malformed undo not refused')
 A=V/'team-independent-v4';require((A/'exhaustion/run.stdout').read_text().strip()=='0'and(A/'exhaustion-mutant/run.stdout').read_text().strip()=='4004','fullM error/mutant evidence wrong');errsrc=(A/'exhaustion/source.kotoba').read_text();require('ex-compare a1 b1 0 0'in errsrc and 'ex-compare c1 d1 0 0'in errsrc and '(= i MM-WORDS)'in errsrc,'fullM source comparison unbound');require('(def MM-WORDS 8388608)'in errsrc,'fullM wrong size')
 # Run frozen machine/IR/literal audit code against selected raw packets with path-only adaptation.
 auditout=out/'derived-audits';auditout.mkdir(exist_ok=True);namespace={'__name__':'machine','__file__':str(A/'machine.py'),'OUT':auditout};module=types.ModuleType('machine');module.__dict__.update(namespace);sys.modules['machine']=module
 repl={'/private/tmp/amu-vector-shape-specialize-20261006/implementation-v4':str(I),'/private/tmp/amu-scalar-dag-inline-20261006/implementation/observer/ports':str(B/'observer/ports')}
 for name in ['machine.py','controls.py','generic.py','ir-binding.py','literals.py']:
  code=(A/name).read_text()
  for a,b in repl.items():code=code.replace(a,b)
  for f in ['machine-report.json','machine-controls.json','generic-report.json','ir-binding-report.json','literal-report.json']:code=code.replace("(D/'"+f+"')","(OUT/'"+f+"')")
  ns=module.__dict__ if name=='machine.py'else{'__name__':'portable_audit_'+name.replace('.','_'),'__file__':str(A/name),'OUT':auditout}
  with contextlib.redirect_stdout(io.StringIO()):exec(compile(code,str(A/name),'exec'),ns)
 mr=load(auditout/'machine-report.json');require(mr['totals']['handleChecksDeleted']==631 and mr['totals']['boundsDeleted']==732,'machine deletion total wrong');require(len(load(auditout/'machine-controls.json')['controls'])==8 and all(x['status']=='DETECTED'for x in load(auditout/'machine-controls.json')['controls']),'machine mutations not refused');require(len(load(auditout/'ir-binding-report.json')['controls'])==3,'IR mutations missing');reports['machineProjection']=mr['totals'];reports['offlineMachineMutations']=8;reports['offlineIrMutations']=3
 # Retained falsified hypotheses are part of evidence, not overwritten successes.
 h=P/'history';patch=load(h/'first-statemate/cached-target-control.json');require(len(patch['events'])==383,'first failure branches missing');bad=(h/'first-statemate/ports/native.bin').read_bytes();fixed=bytearray(bad)
 for e in patch['events']:
  at=e['branchWord']-1;require(int.from_bytes(bad[4*at:4*at+4],'little')==int(e['oldWord'],16),'first branch binding wrong');fixed[4*at:4*at+4]=int(e['newWord'],16).to_bytes(4,'little')
 require(bytes(fixed)==(h/'first-statemate/statemate-cached-target-repaired.bin').read_bytes(),'first causal native repair mismatch')
 dirt=(h/'v2-dirty-cap/matmult-int/native.bin').read_bytes();base=(B/'observer/ports/matmult-int/native.bin').read_bytes();require(len(dirt)==len(base)and sum(dirt[j:j+4]!=base[j:j+4]for j in range(0,len(base)//4*4,4))==28,'V2 dirty fallback evidence wrong')
 require((h/'v3-exhaustion/exhaustion/run.stdout').read_text().strip()!='0','V3 exposure missing')
 reports['zeroFuelSuccessfulReturns']=zeroReturns;reports['selectedMembers']=len(inv['entries']);reports['freshNativeRuns']=0;reports['freshSolverRuns']=0;reports['performanceMeasurements']=0;reports['unselectedExternalReads']=len(blocked);reports['status']='PASS selected copied offline native evidence replay'
 reports['trustBoundary']=['Hashes establish selected artifact identity, not historical execution authenticity by themselves. Native stdout/status receipts are captured prior executions; this replay does not execute native or solvers.','Pairwise equality includes fuel/partialwrites/traps. Successful product return with remaining fuel0 is legal; diagnostic trap is determined by exit/status, not remaining0 alone.','Per-observation permanent file checks were executed by original harness; offline rows preserve result/stdout/fuel oracles and binding, not fresh per-row filesystem effects.','Finite machine/IR projection and tested resource/sameM states do not prove all dynamic paths or universal OS stack boundary parity.','Owner inventory references outside selection are provenance, not required replay paths. No timing or adoption claim.','Some inherited raw auditor report text mentions older candidate labels; actual archived paths/source/native924 are authoritative bindings.']
 (out/'replay-result.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2));return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:print('FAIL offline replay:',type(e).__name__,str(e),file=sys.stderr);sys.exit(1)
