from pathlib import Path
import json,hashlib,re,stat
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-leaf-straight-read-cache-functional30-plan-v2-controls';O=D/'run-outputs';A=Path(__file__).resolve().parent;G=W/'vector-leaf-straight-read-cache-functional30-go-v2-root/root-go.json'
H=lambda b:hashlib.sha256(b).hexdigest();J=lambda p:json.loads(Path(p).read_bytes());pins={}
def record(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();pins[str(p)]={'bytes':len(b),'sha256':H(b)};return b
def checked(p,v):
 b=record(p);assert pins[str(p)]=={k:v[k]for k in ['bytes','sha256']};return b
pr=J(D/'preregistration.json');sp=J(D/'source-pins.json');cl=J(D/'input-closure.json');g=J(G)
assert H(record(G))=='69bc70ba20b1b202c5cf8eea84edfbfa1e69e7b17114da3c7ede871a095fc0de'
for p,v in cl.items():checked(p,v)
for n,v in sp.items():checked(D/n,v)
assert g['sourcePinsSHA256']==H(record(D/'source-pins.json')) and g['driverSHA256']==H(record(D/'run.py')) and g['preregistrationSHA256']==H(record(D/'preregistration.json')) and g['inputClosureSHA256']==H(record(D/'input-closure.json'))
for q in g['sourceReviews']:
 x=json.loads(checked(q['path'],q));assert x['status']==pr['sourceReviewStatus'] and x['sourcePinsSHA256']==g['sourcePinsSHA256']
for role,q in pr['proofs'].items():
 x=json.loads(checked(q['report']['path'],q['report']));assert x['status']==q['status'] and x['inputPinsSHA256']==q['inputPins']['sha256']; ip=json.loads(checked(q['inputPins']['path'],q['inputPins']));assert all(cl[k]==v for k,v in ip.items())
raw=J(pr['CConsumerRawReport']['path']);cr=J(pr['proofs']['C19']['report']['path']);rr=J(pr['proofs']['CConsumer19']['report']['path'])
for c in pr['cases']:
 for arm in ['OFF','ON']:
  b=checked(c[arm+'Container']['path'],c[arm+'Container']);head,pay=b.split(b'\n\n',1);ls=head.decode().splitlines();assert ls[0]==f'KSEED1 {len(pay)} {len(ls)-1}'; ex=[dict(name=(v:=s.split())[0],offset=int(v[1]),arity=int(v[2]))for s in ls[1:]];assert ex==c[arm+'Exports'] and pay==checked(c[arm]['path'],c[arm]);assert dict(name=c['symbol'],offset=c[arm+'Offset'],arity=1)in ex
 cb=checked(c['C']['path'],c['C']);rb=checked(c['CRunner']['path'],c['CRunner']);row=next(x for x in rr['images']if x['workload']==c['workload']);assert rb.count(cb)==1 and rb.find(cb)==row['immutableImageByteAnchors']['C']
rows=J(O/'attempts.json');report=J(O/'report.json');terminal=J(O/'terminal.json');eff=J(O/'effective-environment.json');assert terminal=={'calls':30,'allCallsClosed':True,'failure':False,'noRetry':True};assert len(rows)==30
rx=re.compile(rb'\{:status :ok :result ([01]) :fuel \{:initial ([0-9]+) :remaining ([0-9]+)\} :heap \{:capacity ([0-9]+) :used ([0-9]+)\} :string-pool \{:capacity ([0-9]+) :used ([0-9]+)\} :vectors \{:capacity ([0-9]+) :used ([0-9]+)\} :vector-items \{:capacity ([0-9]+) :used ([0-9]+)\}\}\n');comparisons=[];idx=0
for c in pr['cases']:
 for n in [0,1,2,17,32]:
  pair={}
  for arm in ['OFF','ON','C']:
   r=rows[idx];idx+=1;label=c['workload']+'-'+arm+'-n'+str(n);assert r['index']==idx and r['label']==label and r['state']=='terminal' and r['returncode']==0 and r['failure']is None and r['cleanupException']is None
   expected=[c['CRunner']['path'],'dylib',c['C']['path'],c['CSymbol'],'aarch64',str(n),'1','0','16777216']if arm=='C'else[pr['loader']['path'],c[arm]['path'],str(c[arm+'Offset']),'1','aarch64','-',str(n)];assert r['argv']==expected and r['environment']==eff['C'if arm=='C'else'native']
   out=record(O/(label+'.stdout'));err=record(O/(label+'.stderr'));assert H(out)==r['stdoutSHA256'] and H(err)==r['stderrSHA256'] and err==b''
   if arm=='C':
    q=json.loads(out);assert q['result']==(n!=0) and q['calls']==1 and q['warmupCalls']==0 and q['contextFuelConsumed']==0 and q['contextFuelBefore']==q['contextFuelAfter']==q['fuelPerCall']==16777216 and q['nativeArenaStatus']=='unavailable-C'and q['nativeArenas']is None;pair[arm]={k:v for k,v in q.items()if k not in ['elapsedNanoseconds','maxRssBytes']}
   else:
    m=rx.fullmatch(out);assert m;v=list(map(int,m.groups()));assert v[0]==(n!=0) and v[1]==16777216 and 0<v[2]<=v[1];arena={}
    for j,(k,cap)in enumerate([('heap',2097152),('string-pool',65536),('vectors',4096),('vector-items',65536)]):
     a,u=v[3+2*j:5+2*j];assert a==cap and 0<=u<=a;arena[k]={'capacity':a,'used':u}
    pair[arm]={'status':'ok','result':v[0],'fuel':{'initial':v[1],'remaining':v[2]},'terminalArenas':arena}
  assert pair['OFF']==pair['ON'];comparisons.append({'workload':c['workload'],'n':n,'arms':pair})
assert comparisons==J(O/'comparisons.json')==report['comparisons'] and report['calls']==30 and report['completedTriples']==10 and report['status']=='PASS_FINITE_LC_MD5_SHA30_FUNCTIONAL_ONLY'
for folder in [O,G.parent]:
 for p in sorted(folder.rglob('*')):
  if p.is_file():record(p)
for p,v in list(pins.items()):assert H(Path(p).read_bytes())==v['sha256']
(A/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n');q={'status':'PASS_INDEPENDENT_ACTUAL_LC_MD5_SHA30_FUNCTIONAL_ONLY','sourcePinsSHA256':g['sourcePinsSHA256'],'inputPinsSHA256':H((A/'input-pins.json').read_bytes()),'counts':{'closedChildCalls':30,'nativeCalls':20,'historicalCCalls':10,'completeTriples':10,'inputFiles':len(pins),'inputLogicalBytes':sum(v['bytes']for v in pins.values())},'exactArgvEnvironmentRawSHA':True,'nativeResultFuelFourTerminalArenaPairsExact':True,'historicalCEmbeddedWholeBytePositionExact':True,'CZeroFuelUnavailableNullArenas':True,'comparisons':comparisons,'sourceReviewParticipation':'Reviewer earlier read LC emitter/build source; did not author functional30 or its source review. Saved raw audit invokes no native or driver.', 'nativeCallsByAuditor':0,'full19Qualified':False,'runtimeRegisterCanaryQualified':False,'timingQualified':False,'officialScore':False}
(A/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({'reportSHA256':H((A/'report.json').read_bytes()),'inputPinsSHA256':q['inputPinsSHA256'],'counts':q['counts']}))
