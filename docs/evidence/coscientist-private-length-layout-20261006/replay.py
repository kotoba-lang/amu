from pathlib import Path
import hashlib,importlib.util,json,re,subprocess,sys,tarfile,tempfile
E=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(E/'native-proof.tgz')==load(E/'archive-manifest.json')['sha256']
with tempfile.TemporaryDirectory(prefix='amu-layout-proof-replay-') as tmp:
 W=Path(tmp);T=W/'team-proof'
 with tarfile.open(E/'native-proof.tgz') as t:t.extractall(W,filter='data')
 for n,v in load(T/'all-proof-pins.json')['files'].items():assert sha(W/n)==v['sha256'],n
 fixed=load(W/'fixed-point.json');assert {x['sha256'] for x in fixed['generations'][1:]}=={'b13e68066dd54ba604f9bb989106d9412c75db7012d46469eb388b74c0eb837d'}
 old=load(T/'layout-audit.json');q=subprocess.run([sys.executable,str(T/'layout-audit.py')],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
 assert load(T/'layout-audit.json')==old
 a=load(W/'team-constructor/semantic.json');assert len(a['rows'])==300 and all(x['baseline']==x['candidate'] for x in a['rows'])
 for z in a['publicExportRows']:
  if z['label']=='baseline':
   v=next(v for v in a['publicExportRows'] if v['label']=='candidate' and v['handle']==z['handle'])
   assert {k:v for k,v in z.items() if k!='label'}=={k:v for k,v in v.items() if k!='label'}
 assert load(W/'team-constructor/mutant.json')['detected']
 rs=load(W/'team-resource/resource-states.json');assert len(rs['rows'])==161 and all(x['product']==x['candidate'] for x in rs['rows'])
 state=load(T/'ports-state.json');assert len(state['rows'])==209 and all(x['product']==x['candidate'] for x in state['rows'])
 source=(T/'permanent-a64gen-fixtures.py').read_text().replace("R = '/Users/junkawasaki/github/wt/amu-seed17'",'R = '+repr(str(T/'contracts')))
 (T/'fixtures.py').write_text(source);sys.path.insert(0,str(T));sp=importlib.util.spec_from_file_location('fx',T/'fixtures.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
 p=load(T/'adoption-permanent-proof.json');assert len(m.FIX)==p['fixtures']==593 and len(m.RUNS)==p['runs']==25658
 for i,((name,args,expect,opts),z) in enumerate(zip(m.RUNS,p['observations'])):
  assert z['index']==i and z['fixture']==name and z['args']==list(args) and z['expect']==expect
  so=z['stdout'];se=z['stderr'];exit=z['exit']
  if expect=='trap':good=exit!=0 and 'KEXE_TRAP' in se
  elif 'cmd' in opts:good=exit==(expect&255)
  else:good=exit==0 and bool(so.splitlines()) and so.splitlines()[-1]==str(expect)
  if 'fuel_remaining' in opts:
   r=re.search(r':remaining (-?\d+)',so);v=re.search(r':result (-?\d+)',so)
   good=(exit!=0 and 'KEXE_TRAP' in se) if expect=='trap' else (exit==0 and v is not None and int(v[1])==expect)
   good=good and r is not None and int(r[1])==opts['fuel_remaining']
  if 'stdout' in opts:good=good and so.startswith(opts['stdout'])
  assert good,(i,name)
 test=m.blob_from((T/'adoption-permanent-test.stdout').read_text());real=m.blob_from((T/'adoption-permanent-real.stdout').read_text())
 assert test[1]==real[1] and test[0][:len(real[0])]==real[0] and not any(test[0][len(real[0]):])
 assert (T/'adoption-permanent-fixture.bin').read_bytes()==real[0]
 result={'status':'PASS extracted independent layout native proof replay','allPinsVerified':True,'nativeGenerations2To4ByteExact':True,'all19MachineAuditRecomputed':True,'instructionsAdded':0,'instructionsRemoved':0,'currentFixtures':593,'currentNativeObservationsRecomputed':25658,'constructorPairs':304,'resourcePairs':161,'original19FullStatePairs':209,'freshNativeExecutions':0,'performanceClaim':False,'productPromoted':False,'COrBetterAchieved':False}
 (E/'replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
