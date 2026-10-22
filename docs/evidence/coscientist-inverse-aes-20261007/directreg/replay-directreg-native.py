"""Stdlib-only selected byte/state reader; no native/solver/network/timing execution."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,re,struct
HERE=Path(__file__).resolve().parent;MANIFEST_SHA='6aa2c44e9e5b0749a0a574e4671c5bdbe285a0a6d1ca56c54eebb72d3ef8dbbe';sha=lambda b:hashlib.sha256(b).hexdigest();MASK=(1<<64)-1
def main():
 mp=HERE/'directreg-native-manifest.json';assert sha(mp.read_bytes())==MANIFEST_SHA,'manifest integrity';m=json.loads(mp.read_text());arc=HERE/m['archive'];assert sha(arc.read_bytes())==m['archiveSHA256']and arc.stat().st_size==m['archiveBytes'],'archive integrity'
 with tempfile.TemporaryDirectory(prefix='amu-offline-directreg-')as td:
  root=Path(td);objects={}
  with tarfile.open(arc,'r:gz')as t:
   for info in t:
    assert info.isfile()and info.name.startswith('objects/')and len(info.name)==72 and info.size<=100000000
    h=info.name[8:];assert h not in objects;b=t.extractfile(info).read();assert len(b)==info.size and sha(b)==h;objects[h]=b
  assert len(objects)==m['uniqueByteObjects']and len(m['members'])==m['logicalMembers']<=2200
  for n,row in m['members'].items():
   p=PurePosixPath(n);assert not p.is_absolute()and'..'not in p.parts;b=objects[row['sha256']];assert len(b)==row['bytes'];q=root/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
  def ld(p):return json.loads(p.read_text())
  I=root/'team-inverse-directreg-v1';B=I/'runtime-compiled';D=I/'runtime-plan';V1=I/'runtime-executor/results';V2=I/'runtime-executor-v2/results';V3=I/'runtime-coupling-v3/results'
  ind=root/m['finalIndependentReport'];assert sha(ind.read_bytes())==m['finalIndependentReportSHA256'];final=ld(ind);assert final['successfulNativeEntries']==566 and final['hostBuilds']==57 and final['loaderInvocations']==569
  assert final['preEntryRefusals']=={'signedArgsV1':2,'bakedFuelV2':1}
  for k in range(1,5):assert sha((I/('seed-'+str(k)+'.bin')).read_bytes())=='4f2c1e1a48257c5116d9cf0ca503834923339d2eb06d2c8ed73640955f55ebe8' and int((I/('seed-'+str(k)+'.offset')).read_text())==0
  on=(I/'41-directreg-on.kotoba').read_text();off=(I/'41-directreg-default.kotoba').read_text();assert on.replace('(def dr-feature 1)','(def dr-feature 0)')==off
  original=(root/'team-inverse-compiled-call-plan/source.kotoba').read_text().splitlines(True);fixture=(D/'source.kotoba').read_text().splitlines(True);assert fixture[1:len(original)]==original[1:]
  csource=(D/'source-oracle.c').read_text();oldc=(root/'team-inverse-compiled-call-plan/source-oracle.c').read_text();assert csource[:csource.index('struct testcase')]==oldc[:oldc.index('struct testcase')]
  tables={}
  for role in ['enc','dec']:
   s=csource.split('static const uint32_t '+role+'[4][256] = {',1)[1].split('};',1)[0];tables[role]=[int(x)for x in re.findall(r'(\d+)U',s)];assert len(tables[role])==1024
  cases=ld(D/'cases.json')
  for c in cases:
   T=tables['enc'if c['mode']==0 else'dec'];a,b,cc,d=c['state'];rv=(T[a&255]^T[256+((b>>8)&255)]^T[512+((cc>>16)&255)]^T[768+((d>>24)&255)]^c['key'])&MASK
   if c['symbol']=='direct-t1':expected=(((rv+((c['args'][0]&MASK)^(c['args'][4]&MASK)))&MASK)^17)
   elif c['symbol']=='call-live':expected=((rv^c['key'])+1)&MASK
   else:expected=rv^17
   assert rv==c['expectedRawRoundU64']and expected==c['expectedResultU64'],c['id']
  orig=ld(I/'original19-images/report.json');machine=ld(root/'team-inverse-directreg-machine-independent/report.json');known={r['workload']:r for r in ld(I/'original19-images/inverse-baseline19.json')}
  for profile,rows in orig['images'].items():
   assert len(rows)==19
   for row in rows:
    p=I/'original19-images'/('default/ports'if profile=='default'else profile)/row['workload'];assert sha((p/'native.bin').read_bytes())==row['nativeSha256']and int((p/'native.offset').read_text())==row['offset']
    if profile=='default' or row['workload']!='nettle-aes':assert row['nativeSha256']==known[row['workload']]['nativeSha256']
  sb=ld(I/'site-binding/report.json');native=(I/'original19-images/on/nettle-aes/native.bin').read_bytes();words=struct.unpack('<'+'I'*(len(native)//4),native)
  for s in sb['sites']:
   assert s['newWords']==66 and list(words[s['newWordStart']-1:s['newWordStart']-1+66])==s['newWordsRaw']
  images=ld(B/'images.json')
  for profile,rows in images.items():
   for symbol,row in rows.items():assert sha((B/profile/(symbol+'.bin')).read_bytes())==row['nativeSHA256']
  binding=ld(I/'runtime-executor-v2/actual-binding.json');assert binding['wrapperEntryFuel']==1 and binding['calleeFuel']==6
  for s in binding['sites']:
   if s['symbol']in['direct-t0','direct-t1']:assert s['direct']and[sx[3]for sx in s['args']]==list(range(9+s['t'],15+s['t']))and s['post'][6]==67+s['t']
   else:assert not s['direct']
  def value(c,f,x):
   assert not x.get('timeout');text=x['stdout'];assert int(re.search(r':initial (\d+)',text)[1])==f;rem=int(re.search(r':remaining (\d+)',text)[1])
   if f>=7:assert x['exit']==0 and ':status :ok'in text and (int(re.search(r':result (-?\d+)',text)[1])&MASK)==c['expectedResultU64']and rem==f-7 and not x['stderr']
   else:assert x['exit']==120 and ':status :trap'in text and rem==0 and ':budget/fuel'in x['stderr']
   for name in ['heap','string-pool','vectors','vector-items']:assert re.search(r':'+name+r' \{:capacity \d+ :used 0\}',text)
  first=ld(V1/'preflight4-raw.json');assert len(first)==2 and first[0]['case']==4 and first[1]['case']==6
  assert all(first[1][p]=={'exit':2,'stdout':'','stderr':''}for p in['baseline','candidate'])
  pairs=[first[0]]+ld(V2/'preflight3-raw.json')+ld(V2/'remaining164-raw.json');assert len(pairs)==len({(x['case'],x['fuel'])for x in pairs})==168
  wanted={(x['case'],x['fuel'])for x in ld(D/'schedule.json')['pairs']};assert wanted=={(x['case'],x['fuel'])for x in pairs}
  for x in pairs:assert x['baseline']==x['candidate'];value(cases[x['case']],x['fuel'],x['candidate'])
  body=ld(V2/'fullbody99-raw.json');schedule=ld(D/'fullbody-fresh99-schedule.json');assert len(body)==len(schedule)==99;ordinary=prefix=0
  for x,s in zip(body,schedule):
   assert x['spec']==s and x['baseline']==x['candidate'];out=x['candidate'];assert not out.get('timeout')and int(re.search(r':initial (\d+)',out['stdout'])[1])==s['fuel']
   if s['phase']=='ordinary-original-fullbody':ordinary+=1;assert out['exit']==0 and int(re.search(r':result (-?\d+)',out['stdout'])[1])==s['expectedResult']==(0 if s['args'][0]==0 else 1)
   else:prefix+=1
  assert ordinary==57 and prefix==42
  abirows=ld(V2/'abi28-raw.json');assert len(abirows)==28
  for x,s in zip(abirows,ld(D/'abi-schedule.json')):assert all(x[k]==v for k,v in s.items());value(cases[x['case']],x['fuel'],x['outcome'])
  failed=ld(V2/'coupling4-raw.json');assert len(failed)==1 and failed[0]['outcome']=={'exit':2,'stdout':'','stderr':'kexe-loader: KEXE_FUEL exceeds the maximum budget 9007199254740991 (2^53-1)\n'}
  ns={};exec(compile((I/'runtime-executor-v2/abi.py').read_text(),'frozen-data-only-abi','exec'),ns)
  allbuilds=[]
  for stage,total,hosts in[(V2,565,53),(V3,4,4)]:
   ledger=ld(stage/'attempts.json');assert len(ledger['guestInvocations'])==total and len(ledger['hostBuilds'])==hosts;allbuilds+=ledger['hostBuilds']
   for row in ledger['hostBuilds']:
    p=stage/row['label'];assert row['returncode']==0 and sha((p/'loader').read_bytes())==row['binarySHA256']and sha((p/'embedded.h').read_bytes())==row['headerSHA256'];hdr=(p/'embedded.h').read_text();match=re.search(r'kexe_embedded_code\[\] = \{([^}]+)\}',hdr);assert bytes(map(int,match[1].split(',')))==(p/'image.bin').read_bytes()
    assert '#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES 6ULL'in hdr
    if row['label'].startswith('abi/'):
     _,profile,symbol=row['label'].split('/');raw=(B/profile/(symbol+'.bin')).read_bytes();expect,offset=ns['append'](raw,images[profile][symbol]['offset']);assert expect==(p/'image.bin').read_bytes()and '#define KEXE_EMBEDDED_OFFSET '+str(offset)+'u'in hdr
    if stage==V3:
     profile,symbol=row['label'].split('/');c=cases[6 if symbol=='direct-t0'else 10];raw=(B/profile/(symbol+'.bin')).read_bytes();expect,offset=ns['coupling'](raw,images[profile][symbol]['offset'],c['args'],c['expectedResultU64']);assert expect==(p/'image.bin').read_bytes()and '#define KEXE_EMBEDDED_FUEL 7u'in hdr
   for n,row in enumerate(ledger['guestInvocations']):
    if stage==V2 and n<4:continue # first4 retained verbatim from v1, including2refusals
    receipt=stage/row['label']/(row['tag']+'.json');assert sha(receipt.read_bytes())==row['receiptSHA256']and row['state']=='terminal'
    assert row['wireArgs']==[((v+(1<<63))%(1<<64))-(1<<63)for v in row['args']]
  v1=ld(V1/'attempts.json');assert len(v1['hostBuilds'])==10 and len(v1['guestInvocations'])==4 and ld(V2/'attempts.json')['guestInvocations'][:4]==v1['guestInvocations']
  couplings=ld(V3/'raw.json');assert len(couplings)==4
  for x in couplings:
   o=x['outcome'];assert x['fuel']==7 and o['exit']==0 and ':status :ok'in o['stdout']and re.search(r':result 0\b',o['stdout'])and ':initial 7 'in o['stdout']and ':remaining 0'in o['stdout']and not o['stderr']
  assert len(allbuilds)==57
  print(json.dumps({'status':'PASS selected directreg3file offline replay','logicalMembers':len(m['members']),'uniqueByteObjects':len(objects),'fixedGenerations':4,'original19OnOffImages':38,'typedPositiveModes':['t0','t1'],'uniqueValuePairs':168,'originalBodyPairs':99,'completedABICalls':28,'normalBudgetCouplings':4,'hostBuilds':57,'loaderInvocations':569,'preEntryRefusals':3,'successfulNativeEntries':566,'mixedProcedures':True,'nativeSolverNetworkTimingRuns':0,'performanceQualified':False,'productAdopted':False},indent=2))
if __name__=='__main__':main()
