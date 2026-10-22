import pathlib,json,hashlib,tarfile,re
D=pathlib.Path(__file__).parent;h=lambda b:hashlib.sha256(b).hexdigest();m=json.loads((D/'entry-manifest.json').read_text())
assert m['singleVersion99Campaign'] is False and m['performanceGO'] is False and h((D/m['archive']).read_bytes())==m['archiveSHA256']
with tarfile.open(D/m['archive'],'r:gz') as t:
 assert len(t.getmembers())<=800 and all(x.isfile() and not x.name.startswith('/') and '..' not in pathlib.PurePosixPath(x.name).parts for x in t.getmembers());p={x.name:t.extractfile(x).read() for x in t.getmembers()}
assert set(p)==set(m['members'])
for n,r in m['members'].items():assert h(p[n])==r['sha256'] and len(p[n])==r['bytes']
j=lambda n:json.loads(p[n]);A='team-inverse-timing-prep/local-fullbody-runtime/';B='team-local-fullbody-remaining-v2/'
for name,r in j(B+'preregistration.json')['inputs'].items():
 n=str(pathlib.PurePosixPath(name).relative_to(m['originRoot']));assert h(p[n])==r['sha256'] and len(p[n])==r['bytes']
first=j(A+'results/pairs.json');later=j(B+'actual/pairs.json');assert len(first)==19 and len(later)==80
assert [x['spec'] for x in later]==j(B+'schedule.json')
allrows=first+later;assert sorted(x['spec']['originalIndex'] for x in allrows)==list(range(99))
old=j(A+'results/attempts.json');assert len(old['builds'])==38 and len(old['runs'])==38
for b in old['builds']:
 root=A+'results/'+b['workload']+'/'+b['arm']+'/'
 assert b['exit']==0 and h(p[root+'loader'])==b['binarySHA256'] and h(p[root+'image.bin'])==b['imageSHA256'] and h(p[root+'embedded.h'])==b['headerSHA256']
 hdr=p[root+'embedded.h'].decode();assert '#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES 6ULL' in hdr and f"#define KEXE_EMBEDDED_OFFSET {b['offset']}u" in hdr
 assert h(p[A+'diagnostic-loader.c'])==b['sourceSHA256']
 assert j(root+'build.status.json')['exit']==0
calls=j(B+'actual/attempts.json');assert len(calls)==160
for c in calls:
 n=B+'actual/'+str(c['index'])+'-'+c['arm']+'.json';assert h(p[n])==c['receiptSHA256'] and c['state']=='terminal'
infos={x['workload']:x for x in j('team-inverse-timing-prep/timing-package/manifest.json')['entries']}
ordinary=[];prefix=[]
for row in allrows:
 s=row['spec'];b=row['baseline'];c=row['candidate'];assert b==c and not b.get('timeout') and b['exit'] is not None and b['exit']>=0
 if row in first:
  for arm in ['baseline','candidate']:assert j(A+'results/'+s['workload']+'/'+arm+'/case'+str(s['originalIndex'])+'.json')==row[arm]
 else:
  for arm in ['baseline','candidate']:assert j(B+'actual/'+str(s['originalIndex'])+'-'+arm+'.json')==row[arm]
 out=b['stdout'];initial=int(re.search(r':initial (\d+)',out)[1]);remaining=int(re.search(r':remaining (\d+)',out)[1]);assert initial==s['fuel'] and 0<=remaining<=initial
 if s['phase']=='ordinary-original-fullbody':
  result=int(re.search(r':result (-?\d+)\b',out)[1]);want=0 if s['args']==[0] else 1
  assert s['expectedResult']==want and result==want and b['exit']==0 and ':status :ok' in out
  info=infos[s['workload']]
  if s['args']==[info['n']]:assert initial-remaining==info['expectedNativeFuelConsumed']
  ordinary.append((s['workload'],s['args'][0],result,initial-remaining))
 else:prefix.append(s)
assert len(ordinary)==57 and len(prefix)==42 and sum(x[1]==0 for x in ordinary)==19
assert next(x[3] for x in ordinary if x[0]=='nettle-aes' and x[1]==32)==427363
for x in j(B+'source-expectations.json'):
 source=p['team-inverse-timing-prep/timing-package/'+x['workload']+'/source.kotoba'];assert h(source)==x['sourceSHA256'] and x['evidence'] in source.decode() and x['expectedN0']==0
for i in range(1,5):assert h(p[f'root-inverse-selfbuild-v2/seed-{i}.bin'])=='7ea1b815396ef85dabe25a5c648efe74ff853d823507412c59178c1e26795f92' and p[f'root-inverse-selfbuild-v2/seed-{i}.offset'].strip()==b'0'
audit=j('team-inverse-compilerM-independent/local-fullbody-results-review/report.json');assert audit['actualCounts']['pairs']==99 and audit['actualCounts']['guests']==198 and audit['actualCounts']['singleVersion99Campaign'] is False
print(json.dumps({'status':'PASS offline original19 finitefunctional receipt replay','members':len(p),'pairs':99,'actualGuests':198,'hostBuilds':38,'procedures':2,'singleVersion99Campaign':False,'zeroBoundaryPairs':19,'positiveOrdinaryPairs':38,'AESFuelPrefixPairs':42,'AESn32ConsumedFuel':427363,'performanceGO':False,'newNativeBuildGuestSolverNetworkTiming':0}))
