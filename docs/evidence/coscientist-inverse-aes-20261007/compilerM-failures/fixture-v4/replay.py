import pathlib,json,tarfile,hashlib,re
D=pathlib.Path(__file__).parent;h=lambda b:hashlib.sha256(b).hexdigest();m=json.loads((D/'entry-manifest.json').read_text())
assert m['single32V4Campaign'] is False and m['posttakeEncoderRefusalQualified'] is False
assert h((D/m['archive']).read_bytes())==m['archiveSHA256']
with tarfile.open(D/m['archive'],'r:gz') as t:
 assert len(t.getmembers())<=140 and all(x.isfile() and not x.name.startswith('/') and '..' not in pathlib.PurePosixPath(x.name).parts for x in t.getmembers());p={x.name:t.extractfile(x).read() for x in t.getmembers()}
assert set(p)==set(m['members'])
for n,r in m['members'].items():assert h(p[n])==r['sha256'] and len(p[n])==r['bytes']
j=lambda n:json.loads(p[n]);v='team-inverse-compilerM-plan/fixture-v4/';r=v+'runtime-three/';a=r+'actual/'
c=j(v+'compiled/pins.json');assert len(c)==21
for n,x in c.items():assert h(p[v+'compiled/'+n])==x['sha256'] and len(p[v+'compiled/'+n])==x['bytes']
combined={}
for n in [r+'preregistration.json',r+'compiled-input-binding.json']:
 for name,x in j(n)['inputs'].items():
  q=str(pathlib.PurePosixPath(name).relative_to(m['originRoot']));assert h(p[q])==x['sha256'] and len(p[q])==x['bytes'];combined[name]=x
assert len(combined)==31
build=j(v+'compiled/attempts.json');assert len(build)==4 and all(x['returncode']==0 for x in build)
rows=j(a+'attempts.json');assert [(x['profile'],x['case']) for x in rows]==[('inverse-v2-core-probe',14),('RF-core-probe',15),('inverse-v2-core-probe',15)]
for i,x in enumerate(rows,1):
 name=f"{i}-{x['profile']}-{x['case']}";assert p[a+name+'.stdout']==b'0\n' and p[a+name+'.stderr']==b''
 assert x['returncode']==0 and x['value']==0 and x['PASS'] is True
 assert x['argv'][2]==p[v+'compiled/'+x['profile']+'/native.offset'].decode().strip()
rep=j(a+'report.json');assert rep['rows']==rows and rep['nativeCalls']==3 and rep['single32V4Campaign'] is False and rep['posttakeEncoderRefusalQualified'] is False
obs='team-inverse-compilerM-plan/case14-observation-v2/observation/'
items=[int(x) for x in re.search(r':result-items\s*\[([^]]*)\]',p[obs+'stdout'].decode())[1].split()]
assert items==[0,1,1,4001,0,0,0,73,1,0,2,73,1,1,1,40,2852127720,-1]
assert j(obs+'status.json')['returncode']==0 and p[obs+'stderr']==b'' and j(obs+'report.json')['nativeCalls']==1
old='team-inverse-compilerM-failure-publication/v3-finite-results/';prior=j(old+'offline-replay.json')
oldrows=json.loads(next(x['stdout'] for x in prior['runs'] if x['label']=='isolated'))['rows'];assert len(oldrows)==30 and sum(x['PASS'] for x in oldrows)==29
unique={(x['profile'],x['case']) for x in oldrows if x['PASS']};assert ('inverse-v2-core-probe',14) not in unique
unique.update((x['profile'],x['case']) for x in rows);assert len(unique)==32
ref=j('prior29-reference.json');assert ref['priorArchiveSHA256']==j(old+'entry-manifest.json')['archiveSHA256'] and ref['priorArchiveIncluded'] is False
print(json.dumps({'status':'PASS offline mixed-fixture finite32 reference replay','V3retainedPASS':29,'V3inverse14FAILRetained':True,'V4actualCalls':3,'V4PASS':3,'uniqueProfileCaseCombinations':32,'single32V4Campaign':False,'posttakeEncoderRefusalQualified':False,'case15Scope':'active canonical ranges only','prior29RawInSeparateFrozenArchive':True,'members':len(p),'compiledPins':21,'runtimeInputs':31,'newNativeBuildGuestSolverTimingNetwork':0}))
