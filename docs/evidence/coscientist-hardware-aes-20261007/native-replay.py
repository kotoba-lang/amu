#!/usr/bin/env python3
"""AESv2 selected evidence offline replay. Python standard library only.
No solver/native/compiler/process/network/timing execution. Three files suffice.
"""
from pathlib import Path
import argparse,json,hashlib,tarfile,tempfile,shutil,sys,struct,copy,re
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def need(v,message):
 if not v:raise AssertionError(message)
def main():
 sys.dont_write_bytecode=True;ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--archive',type=Path);ap.add_argument('--manifest',type=Path);ap.add_argument('--out',type=Path);args=ap.parse_args();here=Path(__file__).resolve().parent;arc=args.archive or here/'native-aes-v2.tgz';mp=args.manifest or here/'native-aes-v2.manifest.json';m=load(mp)
 need(sha(arc)==m['archive']['sha256'],'archivehash');need(sha(Path(__file__))==m['replay']['sha256'],'replayhash');out=args.out or Path(tempfile.mkdtemp(prefix='amu-aes-v2-offline-'));out.mkdir(parents=True,exist_ok=True);root=out/'unpacked';root.mkdir(exist_ok=True);allowed=[out.resolve(),here.resolve(),Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve(),arc.resolve(),mp.resolve()];blocked=[]
 def offline(event,argv):
  if event in ['subprocess.Popen','os.system','socket.connect']:blocked.append(event);raise PermissionError('offline forbids process/network')
  if event=='open'and isinstance(argv[0],(str,bytes)):
   p=Path(argv[0].decode()if isinstance(argv[0],bytes)else argv[0]).resolve()
   if not any(p==x or x in p.parents for x in allowed):blocked.append(str(p));raise PermissionError('offline forbids externalinput')
 sys.addaudithook(offline)
 with tarfile.open(arc,'r:gz')as tar:
  seen=set()
  for member in tar.getmembers():
   p=Path(member.name);need(member.isfile()and not p.is_absolute()and '..'not in p.parts and member.name not in seen,'unsafe/repeatedmember');seen.add(member.name);dest=root/p;dest.parent.mkdir(parents=True,exist_ok=True)
   with tar.extractfile(member)as a,dest.open('wb')as b:shutil.copyfileobj(a,b)
 P=root/'payload';inv=load(P/'selected-inventory.json');need(sha(P/'selected-inventory.json')==m['inventory']['sha256'],'inventoryhash');need(len(inv['entries'])==m['inventory']['files'],'inventorycount')
 for e in inv['entries']:
  p=P/e['member'];need(p.is_file()and p.stat().st_size==e['bytes']and sha(p)==e['sha256'],'filepin '+e['member'])
 need({str(p.relative_to(P))for p in P.rglob('*')if p.is_file()}=={e['member']for e in inv['entries']}|{'selected-inventory.json'},'undeclaredmember')
 W=P/'aes';I=W/'implementation-v2';F=W/'team-adoption-gates-v2';Q=W/'team-independent';R=W/'root-regressions-v2';candidate='8e35a8e1d768592de19b6135bd0c063cd0d33d4377205cceb06b4461df832ac5';source='6101b18f2e5618c3974ba21aafce96e001db348dc11ddae0b50f4624b161a993'
 need(sha(I/'seed-0.bin')==sha(P/'baseline/seed-4.bin')=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93','baseline');need(sha(I/'41-a64gen-prototype.kotoba')==source,'source')
 for n,h in load(I/'source-pins.json').items():need(sha(I/n)==h,'sourcepin')
 for e in load(I/'fixed-point.json')['generations']:need(e['sha256']==candidate and e['offset']==0 and e['bytes']==870760 and sha(I/('seed-'+str(e['generation'])+'.bin'))==candidate,'fixedpoint')
 ports=load(I/'ports-build.json')['entries'];base=load(P/'baseline/ports-build.json')['entries'];observer=load(I/'observer/report.json')['entries'];changes=[]
 need(len(ports)==len(base)==len(observer)==19,'original19 count')
 for e in ports:
  n=e['workload'];o=next(x for x in observer if x['workload']==n);b=next(x for x in base if x['workload']==n)
  need(sha(I/'ports'/n/'native.bin')==e['nativeSha256']==sha(I/'observer/ports'/n/'native.bin')==o['nativeSha256']and e['offset']==o['offset'],'portobserver')
  if e['nativeSha256']!=b['nativeSha256']or e['offset']!=b['offset']:changes.append(n)
 need(changes==['nettle-aes'],'only AES changed')
 for e in load(P/'original19/comparison-matrix.json')['entries']:need(sha(P/'original19'/e['source'])==e['expectedSourceSha256'],'originalsource')
 # Replay exact wholemachine projection and mutations in memory, with saved scripts/records only.
 ns={'__file__':str(I/'machine-audit.py')};text=(I/'machine-audit.py').read_text();exec(compile(text[:text.index('rows=[];data={}')],str(I/'machine-audit.py'),'exec'),ns);expected=load(I/'machine-audit.json');data={}
 for e in expected['rows']:
  n=e['workload'];a=ns['aesload'](I/'qualified-baseline-observer'/n);b=ns['aesload'](I/'observer/ports'/n);actual=ns['audit'](a,b);need(actual=={k:v for k,v in e.items()if k!='workload'},'fullmachine '+n);data[n]=(a,b)
 a,b=data['nettle-aes'];site=next(e for e in expected['rows']if e['workload']=='nettle-aes')['sites'][0];faults=0
 for word,mask in [(site['guard'],1),(site['guard']+2,1),(site['guard']+30,1),(site['guard']+36,0x20),(site['guard']+33,0x10000),(site['guard']+39,0x10000),(site['newFix'],1),(b['fn'][site['callee']][-1],1),(site['newHi']+3,1)]:
  mutant=copy.deepcopy(b);mutant['words'][word-1]^=mask
  try:ns['audit'](a,mutant)
  except (AssertionError,KeyError,IndexError):faults+=1
 need(faults==9 and sum(len(e['sites'])for e in expected['rows'])==4,'machine faultcontrols/sites')
 dis=load(I/'disabled/parity.json');need(len(dis['entries'])==19,'disabled19')
 for e in dis['entries']:
  b=next(x for x in base if x['workload']==e['workload']);need(sha(I/'disabled/ports'/e['workload']/'native.bin')==e['sha256']==b['nativeSha256']and e['offset']==b['offset'],'disabledexact')
 typed=load(I/'typed-controls/report.json');need(typed['pairs']==1044 and len(typed['entries'])==4,'typed counts')
 for e in typed['entries']:
  need(len(e['admissions'])==(3 if e['case']=='positive'else 0),'typed admission')
  for symbol in ['forward','reverse','modes','run']:
   need(sha(I/'typed-controls'/e['case']/('candidate-'+symbol+'.bin'))==sha(I/'typed-controls'/e['case']/('observer-'+symbol+'.bin')),'typedobserver')
   if not e['admissions']:need(sha(I/'typed-controls'/e['case']/('candidate-'+symbol+'.bin'))==sha(I/'typed-controls'/e['case']/('baseline-'+symbol+'.bin')),'refusalexact')
  ordinals={};nextIndex={}
  for pair in e['pairs']:
   symbol=pair['symbol'];key=(symbol,tuple(pair['args']))
   if key not in ordinals:ordinals[key]=nextIndex.get(symbol,0);nextIndex[symbol]=ordinals[key]+1
   index=ordinals[key];fuel=pair['fuel'];old=load(I/'typed-controls'/e['case']/f'baseline-{symbol}-{index}-f{fuel}.json');new=load(I/'typed-controls'/e['case']/f'candidate-{symbol}-{index}-f{fuel}.json')
   need(old==new==pair['outcome'],'typed complete raw status/message/resource pair')
 sc=load(I/'source-controls/report.json')['entries'];need(len(sc)==6 and all(x['baseline']!=x['mutant']for x in sc[:4])and all(x['baseline']==x['mutant']for x in sc[4:]),'actualsourcecontrols')
 need(len(load(I/'type-controls/report.json')['cases'])==13,'nativeNFcontrols')
 for e in load(I/'type-controls/report.json')['cases']:
  text=(I/'type-controls'/('case-'+str(e['case'])+'.stdout')).read_text();result=re.search(r':result (-?\d+)',text);need(result is not None and int(result[1])==e['expected']==e['actual'],'NF rawexpectation')
 isa=load(I/'isa-controls-reused/report.json');need(isa['count']==len(isa['cases'])==132,'ISA finitecount')
 for e in isa['cases']:
  result=re.search(r':result (-?\d+)',e['stdout']);need(e['status']==0 and result is not None and int(result[1])==e['result'],'ISA rawvalue')

 # All selected independent records bind the full finite v1 execution observations to identicalv2 guestbytes, notv1compiler state.
 states=load(Q/'full-state-pairs.json');need(len(states)==1242 and all(x['baseline']==x['candidate']for x in states),'full sharedstates')
 native=load(Q/'native-report.json');need(native['totalFullStatePairs']==1242 and native['trappedPairs']==689 and native['successfulZeroRemaining']==108,'nativecounts');need(len(native['abiSentinels'])==14 if 'abiSentinels'in native else len(native.get('sentinels',[]))==14,'sentinel count')
 need(all(x['direct']==x['sentinels'] for x in native['sentinels']),'ABI fullstate')
 v2=load(Q/'v2/report.json');need(v2['candidateSeedSha256']==candidate and v2['typedBridgeExports']==8 and v2['original19Bridge']==19 and v2['compilerFullMAllocationCases']==2,'v2bridge/fullM');need(len(v2['contexts'])==4 and all(e['candidateBaselineContextByteExact']for e in v2['contexts']),'open contexts');need(v2['sameMReuse']['closedSites']==v2['sameMReuse']['againSites']==3 and v2['sameMReuse']['openSites']==0,'sameM undo');need(v2['actualCompilerStateFaultControls']==1,'compilerstatefault')
 # Unchanged mandatory unit rawgolden, all7gates, actualcode/pool/offset reconstruct.
 unit=F/'unit-build/unit/41-a64gen/stdout';gold=F/'source/seed/tests/unit/41-a64gen.expected';need(unit.read_bytes()==gold.read_bytes()and len(unit.read_text().splitlines())==5227,'formalunit');fr=load(F/'report.json');need(fr['formalUnit']['allGeneratedCodePoolAndOffsetsExactPrevious']and fr['goldenChanges']==0 and set(x[0]for x in fr['requiredGates'])=={'BUILD','ERR','G1','G2','G3','G4','G5'}and all(x[1]=='PASS'for x in fr['requiredGates']),'all7 gates')
 need(sha(F/'unit-generated-blob.bin')==fr['formalUnit']['generatedCodeBlobSha256']and len(load(F/'unit-generated-offsets.json'))==593,'unitgeneratedblob')
 words=[];lits=[];fns={};end=None
 for line in unit.read_text().splitlines():
  x=line.split()
  if not x:continue
  if x[0]=='w':words += [int(v,16)for v in x[1:]]
  elif x[0]=='lit':lits.append((int(x[1]),bytes.fromhex(x[2])if len(x)>2 else b''))
  elif x[0]=='fn':fns[int(x[1])]=int(x[2])
  elif x[0]=='end':end=int(x[1])
 need(end is not None,'unitrawend');blob=bytearray(b''.join(v.to_bytes(4,'little')for v in words));need(end>=len(blob),'unitblobend');blob+=b'\0'*(end-len(blob))
 for offset,bs in lits:blob[offset:offset+len(bs)]=bs
 need(bytes(blob)==(F/'unit-generated-blob.bin').read_bytes()and fns=={int(k):v for k,v in load(F/'unit-generated-offsets.json').items()},'unitcodepooloffset replay')
 finalpins=load(W/'team-final-pin-review/formal-terminal-pins.json')
 for sp,e in finalpins.items():
  suffix=sp.split('/team-adoption-gates-v2/',1)[1];p=F/suffix;need(sha(p)==e['sha256']and p.stat().st_size==e['bytes'],'finalformalpin')
 oldpins=load(F/'artifact-pins.json');drift=[p for p,e in oldpins.items()if sha(F/p)!=e['sha256']];need(drift==['finish.log'],'retainedhistoriclograce')
 rr=load(R/'report.json');pr=load(R/'adoption-permanent-proof.json');need(rr['candidateNativeSha256']==candidate and rr['readonly']['observations']==117 and rr['scalar']['observations']==318,'readonlyscalar');need(pr['fixtures']==593 and pr['runs']==25658 and pr['realTestCodeAndLiteralBytesEqual']and pr['realTestFnOffsetsEqual']and not pr['committedGoldenChanged'],'permanent')
 sys.path.insert(0,str(R))
 fxns={'__name__':'portable_fixture','__file__':str(R/'permanent-a64gen-fixtures.py')}
 rawfx=(R/'permanent-a64gen-fixtures.py').read_text();oldroot="R = '/private/tmp/amu-vector-shape-specialize-20261006/team-adoption-gates-v4/source'";need(rawfx.count(oldroot)==1,'fixture contract relocation')
 exec(compile(rawfx.replace(oldroot,'R = '+repr(str(F/'source')),1),str(R/'permanent-a64gen-fixtures.py'),'exec'),fxns)
 need(len(fxns['FIX'])==593 and len(fxns['RUNS'])==25658,'originalfixturemetadata');finalFiles={}
 for e,(name,args,expect,opts) in zip(pr['observations'],fxns['RUNS']):
  need((e['fixture'],e['args'],e['expect'])==(name,args,expect),'originaloracleidentity');so=e['stdout'];se=e['stderr']
  if expect=='trap':good=e['exit']!=0 and 'KEXE_TRAP'in se
  elif 'cmd'in opts:good=e['exit']==(expect&255)
  else:good=e['exit']==0 and bool(so.splitlines())and so.splitlines()[-1]==str(expect)
  if 'fuel_remaining'in opts:
   left=re.search(r':remaining (-?\d+)',so);value=re.search(r':result (-?\d+)',so)
   good=(e['exit']!=0 and 'KEXE_TRAP'in se)if expect=='trap'else(e['exit']==0 and value is not None and int(value[1])==expect)
   good=good and left is not None and int(left[1])==opts['fuel_remaining']
  if 'stdout'in opts:good=good and so.startswith(opts['stdout'])
  need(good,'permanentoriginalobservationaloracle '+str(e['index']))
  if 'mkfile'in opts:finalFiles[opts['mkfile'][0]]=opts['mkfile'][1]
  if 'file'in opts:finalFiles[opts['file'][0]]=opts['file'][1]
 for name,wanted in finalFiles.items():need((R/'adoption-permanent-run'/name).read_bytes()==wanted,'retainedfinalfile')
 law=load(W/'team-value-laws/report.json');need(len(law['queries'])==13 and sum(x['actual']=='unsat'for x in law['queries'])==8 and sum(x['actual']=='sat'for x in law['queries'])==5,'lawcounts')
 for e in law['queries']:need((W/'team-value-laws'/(e['query']+'.stdout')).read_text().splitlines()[0]==e['expected']==e['actual'],'lawrawlog')
 need('unknown'in(W/'team-value-laws/rejected-array-timeout/table-role-0.stdout').read_text(),'initialSMTunknownretained')
 need('E2101'in((W/'rejected-v1/formal/unit-first.stderr').read_text()+(W/'rejected-v1/formal/unit-first.stdout').read_text()),'v1dependencyfailretained');need(load(W/'v1-unit-dependency-failure.json')['status'].startswith('FAIL'),'v1holisticfailure')
 need(load(I/'feature-recipe.json')['status'].startswith('EXPLICIT'),'featureboundary')
 # Restore no output inside archivedinput; allnew artifacts inout only.
 result={'status':'PASS portable selected AESv2 evidence offline replay','selectedFiles':len(inv['entries']),'candidateNativeSha256':candidate,'sourceSha256':source,'original19':19,'changedBodies':1,'certifiedAESCallSites':4,'fullmachineFaultsDetected':faults,'typedProductPairs':1044,'independentFullStatePairs':1242,'legalZeroRemainingReturns':108,'ABIRegisterSentinels':14,'nativeNFControls':13,'compilerFullMErrors':2,'openContexts':4,'sameM':'3/0/3','formalUnitLines':5227,'all7gates':True,'permanentFixtures':593,'permanentObservations':25658,'readonlyObservations':117,'scalarObservations':318,'SMTArchivedUNSAT':8,'SMTArchivedSAT':5,'oldFormalStaleLogPin':'retained; terminal2703 authoritative','v1DependencyFAIL':'retained','processes':0,'network':0,'newNative':0,'newSolver':0,'timings':0,'blockedCalls':blocked,'limits':'Per-stepfilewrites checkedby archived original nativeharness receipt; onlyretainedfinalfiles independently comparedoffline. Raw pinned evidence plus offline machineprojection; no execution/solver replay or universalproof/productadoption/performanceclaim.'};(out/'replay-report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
