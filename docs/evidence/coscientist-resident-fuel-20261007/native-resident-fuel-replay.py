#!/usr/bin/env python3
"""Resident fuel selected evidence offline replay. Python standard library only.
No solver/native/compiler/process/network/timing execution. Three files suffice.
"""
from pathlib import Path
import argparse,json,hashlib,tarfile,tempfile,shutil,sys,struct,copy,re
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def need(v,message):
 if not v:raise AssertionError(message)
def main():
 sys.dont_write_bytecode=True;ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--archive',type=Path);ap.add_argument('--manifest',type=Path);ap.add_argument('--out',type=Path);args=ap.parse_args();here=Path(__file__).resolve().parent;arc=args.archive or here/'native-resident-fuel.tgz';mp=args.manifest or here/'native-resident-fuel.manifest.json';m=load(mp)
 need(sha(arc)==m['archive']['sha256'],'archivehash');need(sha(Path(__file__))==m['replay']['sha256'],'replayhash');out=args.out or Path(tempfile.mkdtemp(prefix='amu-resident-fuel-offline-'));out.mkdir(parents=True,exist_ok=True);root=out/'unpacked';root.mkdir(exist_ok=True);allowed=[out.resolve(),here.resolve(),Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve(),arc.resolve(),mp.resolve()];blocked=[]
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
 W=P/'resident';I=W/'implementation';F=W/'root-formal';Q=W/'team-independent';R=W/'team-regressions';V=W/'team-value-contract-review';B=P/'baseline';candidate='a236b3e86d3f3b4ab9b886f60cb5be8abb292e241e8fcf0611b359d4b0076af3';source='e94ab4dfcf80a5688646b1011481cc69d8efccec86e3e63079c2976a8594f0ec'
 def original(sp):return P/inv['sourceRelocations'][str(sp)]
 for owner in inv['owners']:
  x=load(P/owner['manifest']);entries=x if isinstance(x,list)else [{'path':k,'sha256':v['sha256']if isinstance(v,dict)else v}for k,v in x.items()];need(len(entries)==owner['declaredPins'],'owner count')
  for e in entries:need(sha(P/owner['base']/e['path'])==e['sha256'],'ownerpin '+e['path'])
 need(sha(I/'41-a64gen-prototype.kotoba')==source,'source')
 for e in load(I/'fixed-point.json')['generations']:need(e['sha256']==sha(I/f"seed-{e['generation']}.bin")==candidate and e['bytes']==871760 and e['offset']==0,'fixedpoint')
 for sp,h in load(I/'source-pins.json').items():need(sha(original(sp))==h,'source pins')
 need(sha(B/'seed-4.bin')=='8e35a8e1d768592de19b6135bd0c063cd0d33d4377205cceb06b4461df832ac5','AESv2 baseline')
 # Whole-machine projection and actual altered-opcode controls, in memory only.
 decoder=(Q/'machine-decoder.py').read_text();old=(Q/'baseline-machine-audit.py').read_text();ns={'Path':Path,'json':json,'struct':struct,'copy':copy,'hashlib':hashlib};exec(decoder,ns)
 exec('def aesload(p):'+old.split('def aesload(p):',1)[1].split('def verify_sites',1)[0],ns)
 exec('def normalized'+old.split('def normalized',1)[1].split('rows=[]',1)[0],ns)
 text=(Q/'machine-audit.py').read_text();exec(text[text.index('charge=['):text.index('exec(\'def normalized')],ns)
 exec('def verify_sites'+text.split('\ndef verify_sites',1)[1].split('rows=[];data={}',1)[0],ns)
 expected=load(Q/'machine-report.json');data={};sites=0
 for p in sorted((I/'observer/ports').iterdir()):
  a=ns['aesload'](B/'observer/ports'/p.name);b=ns['aesload'](p);r=ns['audit'](a,b);need(b['raw']==(I/'ports'/p.name/'native.bin').read_bytes(),'actual image');need(r=={k:v for k,v in next(e for e in expected['rows']if e['workload']==p.name).items()if k!='workload'},'projection rawrecompute');data[p.name]=(a,b);sites+=len(r['sites'])
 need(len(data)==19 and sites==4,'all19 four sites');a,b=data['nettle-aes'];faults=0
 for e in expected['controls']:
  x=copy.deepcopy(b);x['words'][e['word']-1]=e['alteredWord']
  try:ns['audit'](a,x)
  except(AssertionError,KeyError,IndexError):faults+=1
  else:raise AssertionError('actual fault accepted')
 need(faults==8,'eight faults')
 disabled=load(I/'disabled/parity.json');need(len(disabled['entries'])==19,'defaultoff19')
 for e in disabled['entries']:
  n=e['workload'];need((I/'disabled/ports'/n/'native.bin').read_bytes()==(B/'ports'/n/'native.bin').read_bytes(),'defaultoff native exact')
 # 99+112 paired fullstate outputs, each raw status/streams compared.
 C=W/'native-controls';ordinary=load(C/'report.json');typed=load(C/'typed-abi/report.json')
 for e in ordinary['entries']:
  for label in ['baseline','candidate']:need(load(C/e['workload']/label/(e['rawTag']+'.json'))==e['outcome'],'ordinary raw pair')
 for e in typed['rows']:
  for label in ['baseline','candidate']:need(load(C/'typed-abi'/label/e['symbol']/(e['tag']+'.json'))==e['outcome'],'typed raw pair')
 need(ordinary['pairs']==99 and typed['pairs']==112,'211 fullstatepairs')
 # Immutable embedded headers/native arrays and compiled-binary source/hash bindings.
 headerBindings=0
 for rr,base in [(ordinary,C),(typed,C)]:
  for e in rr['builds']:
   p=base/e['name'];need(sha(p/'embedded.h')==e['header']and sha(p/'loader')==e['binary'],'header/nativehost pin')
   h=(p/'embedded.h').read_text();need('#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES 6ULL'in h,'mask6')
   z=re.search(r'kexe_embedded_code\[\]\s*=\s*\{([^}]*)\}',h);raw=bytes(int(v)for v in z[1].split(',')if v.strip());need(raw==(p/'image.bin').read_bytes()and sha(p/'image.bin')==e['native'],'header guest byte binding');headerBindings+=1
 g1=load(C/'g1-adapted/report.json');need(len(g1['rows'])==19 and g1['processes']==76,'adaptedG1')
 for row in g1['rows']:
  need(sha(original(row['source']))==row['sourceSHA256']and row['expectedResult']==1,'originalG1 source/expect')
  for route in ['frozen','reporter']:
   vals=[]
   for e in row['entries']:
    o=next(z for z in e['observations']if z['route']==route);p=C/'g1-adapted'/row['workload']/e['compiler']/route
    need(sha(p/'embedded.h')==o['headerSHA256']and sha(p/'loader')==o['binarySHA256'],'G1headerbinary');raw=load(p/'run.json');need(all(raw[k]==o[k]for k in ['exit','stdout','stderr']),'G1 raw observation');vals.append({k:o[k]for k in ['exit','stdout','stderr']})
    need(o['exit']==(1 if route=='frozen'else 0),'frozencommand1 vs reporter0');need(':result 1' in o['stdout']if route=='reporter'else ':status :trap' in o['stdout'],'return1 diagnostic classification')
   need(vals[0]==vals[1],'G1 baseline candidate exact')
 owner=load(W/'owner-report.json');need(owner['G1']['unmodifiedScriptPASS']is False,'strict script boundary');need('Strict original Cbuild cap was not met'in owner['G1']['proceduralDeviation'],'strictcap deviation retained')
 # Recompute actual instrumented byte/origin/branch/logging maps, without executing them.
 def relbranch(z):
  if z&0xff000010==0x54000000:q=(z>>5)&0x7ffff;return q-(1<<19)if q&(1<<18)else q
  if z&0xfc000000==0x14000000:q=z&0x3ffffff;return q-(1<<26)if q&(1<<25)else q
  return None
 maps=0
 for mp in list((Q/'native-prefix-controls').glob('*-map.json'))+list((Q/'native-prefix-control-extension').glob('*-map.json')):
  mm=load(mp);bp=mp.with_name(mp.name.removesuffix('-map.json')+'.bin');ww=list(struct.unpack('<'+'I'*(bp.stat().st_size//4),bp.read_bytes()))
  need(ww[:len(mm['prologueWords'])]==mm['prologueWords']and ww[-len(mm['tailWords']):]==mm['tailWords'],'instrumented prologue/tail')
  labels={int(k):v for k,v in mm['branchLabelMap'].items()}
  for e in mm['entries']:
   at=e['word'];need(ww[at]==e['instruction'],'instrument actual word')
   if e['kind']=='original':
    z=mm['alteredWords'][e['originalWord']];q=relbranch(z)
    if q is not None:need(at+relbranch(ww[at])==labels[e['originalWord']+q]and (ww[at]&(0xff00001f if z&0xff000010==0x54000000 else 0xfc000000))==(z&(0xff00001f if z&0xff000010==0x54000000 else 0xfc000000)),'instrument exact branch projection')
    else:need(ww[at]==z,'instrument exact nonbranch')
  for h in mm['hooks']:
   if h['kind']=='publication logging':
    k=h['logicalCharge'];wantHook=[0xf9000ff1,0xf90013e9,0xf9400bf1,0xf94004e9,0xf9000000|(k<<10)|(17<<5)|9,0xf94013e9,0xd503201f if mm['unsafeLoggerControl']and k==0 else 0xf9400ff1]
    need(h['words']==wantHook and ww[h['first']:h['first']+len(wantHook)]==wantHook,'fresh actual CTX-FUEL read and borrowed x9/x17 restore')
   else:need(h['words'][:3]==[0xf9000ff1,0xf90013e9,0xf9400bf1]and h['words'][-2:]==[0xf94013e9,0xf9400ff1],'dispatch logging borrowed restore')
  maps+=1
 need(maps==11,'eleven actual prefix maps')
 rejected=load(Q/'instrumentation-initial-register-only-log/baseline-map.json');need(any(h['words'][3]!=0xf94004e9 for h in rejected['hooks']if h['kind']=='publication logging'),'initial register-only logger remains rejected')
 # Exact native instrumented publication witnesses, independently recompute original unsigned trace.
 trace=load(Q/'native-trace-report.json');mask=(1<<64)-1
 def want(f):
  n=min(f,6);z=(f-6)&mask if f>=6 else mask;prior=(f-5)&mask if f>=6 else 0
  flags=((z>>63)<<31)|(int(z==0)<<30)|(int(prior>=1)<<29)|(int((prior>>63)==1 and(z>>63)==0)<<28)
  return {'values':[f-i for i in range(1,n+1)],'fuel':max(f-6,0),'nzcv':flags,'trapped':f<6}
 for e in trace['positiveRows']+trace['faultRows']+[trace['nonproductiveControl']]:
  files=list(Q.rglob(e['name']+'-F'+str(e['F'])+'-raw.json'));need(len(files)==1,'unique retained raw prefix');raw=load(files[0]);need(raw['exit']==0 and json.loads(raw['stdout'])==e['actual'],'raw prefix actual');o=e['actual'];w=want(e['F']);need(w==e['expected'],'independent unsigned expected')
  same=o['values']==w['values']and o['fuel']==w['fuel']and o['nzcv']==w['nzcv']and bool(o['signal'])==w['trapped'];need(same==e['sameSemanticPublicationTrapNZCV'],'semantic prefix flag')
  if e in trace['positiveRows']:need(same and o['x17']==0x317 and o['x19']==0x319 and o['path']==(2 if e['name']=='baseline'or e['F']<6 else 1),'positive prefix/control/sentinel')
 need(len(trace['positiveRows'])==50 and len(trace['faultRows'])==15 and trace['nonproductiveControl']['passed'],'66 controls including nonproductive')
 independent=load(Q/'report.json');need(independent['memoryLayout']['ctxWordRange']==[0,15]and independent['memoryLayout']['publicationLogWordRange']==[16,31]and independent['memoryLayout']['signalAndReturnMetadataWordRange']==[32,38],'onepage disjoint ranges')
 need('One owned MAP_SHARED page'in independent['memoryLayout']['allocation'],'onepage')
 # Formal raw unchanged golden and six scripted gates, G1 adapted separately above.
 unit=F/'unit-build/unit/41-a64gen/stdout';gold=F/'source/seed/tests/unit/41-a64gen.expected';need(unit.read_bytes()==gold.read_bytes()and len(unit.read_text().splitlines())==5227,'unit golden');formal=load(F/'report.json');need(set(z[0]for z in formal['requiredGates'])=={'BUILD','ERR','G2','G3','G4','G5'}and all(z[1]=='PASS'for z in formal['requiredGates']),'six scriptedgates')
 words=[];lits=[];fns={};end=None
 for line in unit.read_text().splitlines():
  x=line.split()
  if not x:continue
  if x[0]=='w':words.extend(int(v,16)for v in x[1:])
  elif x[0]=='lit':lits.append((int(x[1]),bytes.fromhex(x[2])if len(x)>2 else b''))
  elif x[0]=='fn':fns[int(x[1])]=int(x[2])
  elif x[0]=='end':end=int(x[1])
 blob=bytearray(b''.join(z.to_bytes(4,'little')for z in words));need(end>=len(blob),'unitend');blob+=b'\0'*(end-len(blob))
 for at,bs in lits:blob[at:at+len(bs)]=bs
 need(bytes(blob)==(F/'unit-generated-blob.bin').read_bytes()and fns=={int(k):v for k,v in load(F/'unit-generated-offsets.json').items()},'unitcodepool offsets recomputed')
 pr=load(R/'adoption-permanent-proof.json');need(pr['fixtures']==593 and pr['runs']==25658,'permanent count')
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
 # Recompute scalar source meanings/effect traces using saved independent bounded interpreter, never native.
 script=F/'source/scripts/seed/a64gen_scalar_dag_fixtures.py';sns={'__file__':str(script),'__name__':'offline_source_math'};exec(script.read_text().split('# BOOTSTRAP-TOOL: standalone native scalar DAG regressions.',1)[0],sns)
 scalar=load(R/'scalar/report.json');readonly=load(R/'readonly/report.json');need(scalar['nativeExecutions']==318 and readonly['nativeObservations']==117,'435 native regressions')
 for e in scalar['observations']:
  generic=e['case'].endswith('-generic-entry');name=e['case'].removesuffix('-generic-entry');prog=sns['Program'](F/'source/seed/tests/scalar-dag'/(name+'.kotoba'))
  try:value=prog.call(('mix' if name=='five-args'else 'scalar')if generic else 'run',e['args'])
  except sns['Trap']:value=None
  consumed=0 if generic else 3 if name=='site-budget'else 2 if name in ['effect-refuse','indirect','five-args']else 1+(e['args'][0]&3)if name=='fuel-refuse'else 1
  effect=''.join(prog.trace);insufficient=e['fuel']==1 and consumed>1
  need(e['expected']==(None if insufficient else value),'original scalar source/fuel oracle')
  need(e['expectedEffectTrace']==(''if insufficient or generic else effect),'original scalar effect/fuel oracle')
  need(e['stdout'].startswith(e['expectedEffectTrace']),'scalar actual effect prefix')
 for e in readonly['controls']+scalar['observations']:
  if e['expected']is None:need(e['exit']!=0 and 'KEXE_TRAP'in e['stderr'],'435 trap oracle')
  else:
   v=re.search(r':result (-?\d+)',e['stdout']);need(e['exit']==0 and v and int(v[1])==e['expected'],'435 value oracle')
  if e['expectedConsumed']is not None:
   left=re.search(r':remaining (-?\d+)',e['stdout']);need(left and e['fuel']-int(left[1])==e['expectedConsumed'],'435 fuel oracle')
 pattern=struct.pack('<9I',*ns['hardware']);ledger=[json.loads(l)for l in(R/'pre-entry-guard.jsonl').read_text().splitlines()];need(len(ledger)==26179,'preentry invocation count');unique={}
 for e in ledger:
  p=original(e['image'])if e['image'].startswith('/')else R/e['image'];need(sha(p)==e['sha256']and pattern not in p.read_bytes(),'actual preentry pin/noAES group');unique[e['image']]=e
 ordinaryImages=0
 for name,e in unique.items():
  if e['class'].startswith('ordinary'):
   old=original('/private/tmp/amu-hardware-aes-20261006/root-regressions-v2/'+name);need((R/name).read_bytes()==old.read_bytes(),'baseline guest bytes');ordinaryImages+=1
 need(ordinaryImages==37,'37 ordinary images baselineexact')
 # Archived SMT query/results and concrete SAT witness renderings; no solver execution.
 law=load(V/'value-report.json');need(law['unsat']==3 and law['satControls']==7,'resident SMT3/7')
 for e in law['queries']:
  need((V/(e['query']+'.stdout')).read_text().splitlines()[0]==e['expected']==e['result'],'raw resident SMT log')
  if e['result']=='sat'and e['semanticDifferenceClaim']:
   x=e['actualComparedPrefixFuelValues'];need(any(a!=b for a,b in zip(x['original'],x['control']))and x['differences'],'SAT witness actual changedprefix')
  if e['query'].startswith('signed-'):need(e['semanticDifferenceClaim']is False and e['actualDispatch']['unsignedFast']!=e['actualDispatch']['signedFast'],'signed dispatch-only')
 contract=load(V/'source-contract-report.json');need(contract['sourceSHA256']==source and contract['sourceDeltaExact']and contract['newNativeRuns']==0,'frozen source/model binding')
 aeslaw=load(B/'value-laws/report.json');need(len(aeslaw['queries'])==13,'retained AESlaws')
 for e in aeslaw['queries']:need((B/'value-laws'/(e['query']+'.stdout')).read_text().splitlines()[0]==e['expected']==e['actual'],'old AES raw law')
 need(owner['gateTrust']['ownedReporterDelta']['notProductBudgetAdmission']and not owner['adopted']if 'adopted'in owner else owner['gateTrust']['ownedReporterDelta']['notProductBudgetAdmission'],'diagnostic domain')
 result={'status':'PASS portable selected resident fuel evidence offline replay','selectedFiles':len(inv['entries']),'candidate':candidate,'source':source,'wholeMachineWorkloads':19,'changedWorkloads':['nettle-aes'],'admittedSites':4,'machineFaultsDetected':faults,'ownerFullstatePairs':211,'embeddedHeaderBindings':headerBindings,'nativePublicationPositiveTraces':50,'nativeProductiveFaultTraces':15,'nativeNonproductiveFaultTraces':1,'formalUnitLines':5227,'scriptedGates':6,'G1AdaptedProcesses':76,'strictG1CbuildCapMet':False,'permanentFixtures':593,'permanentObservations':25658,'readonlyObservations':117,'scalarObservations':318,'preEntryOrdinaryUniqueImages':37,'residentArchivedSMTUNSAT':3,'residentArchivedSMTSAT':7,'processes':0,'network':0,'newNative':0,'newSolver':0,'timings':0,'blockedCalls':blocked,'limits':['No solver/native execution or universal hardware/compiler/OS proof','G1 strict initial build cap failed; adapted functional evidence does not erase procedural deviation','Nonproductive first slowload mutant preserved; exact machine audit detects it but semantics unchanged under ownership','One-page disjoint instrumentation trace only; no arbitrary rawhost ownership claim','Diagnostic rawu64 fuel beyond product budget admission; command return1 frozen status trap label differs reporter completion','Four concrete sites, not universal group100%admission; automatic producer/generic ABI integration and product adoption unimplemented','Per-step filewrite original harness receipts trusted; retained final files independently checked only','Performance remains unmeasured in this native proof publication']};(out/'replay-report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
