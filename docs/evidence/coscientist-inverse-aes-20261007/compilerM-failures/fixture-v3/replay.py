import pathlib,json,hashlib,tarfile
D=pathlib.Path(__file__).parent;h=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((D/'entry-manifest.json').read_text());assert m['qualificationPASS'] is False
assert h((D/m['archive']).read_bytes())==m['archiveSHA256']
with tarfile.open(D/m['archive'],'r:gz') as t:
 assert len(t.getmembers())<=200 and all(x.isfile() and not x.name.startswith('/') and '..' not in pathlib.PurePosixPath(x.name).parts for x in t.getmembers())
 p={x.name:t.extractfile(x).read() for x in t.getmembers()}
assert set(p)==set(m['members'])
for n,r in m['members'].items():assert h(p[n])==r['sha256'] and len(p[n])==r['bytes']
j=lambda n:json.loads(p[n]);v='team-inverse-compilerM-plan/fixture-v3/';r=v+'runtime-procedure-v3/'
c=j(v+'compiled/pins.json');assert len(c)==21
for n,x in c.items():assert h(p[v+'compiled/'+n])==x['sha256'] and len(p[v+'compiled/'+n])==x['bytes']
inputs={}
for n in [r+'preregistration.json',r+'compiled-input-binding.json']:
 for path,x in j(n)['inputs'].items():
  q=str(pathlib.PurePosixPath(path).relative_to(m['originRoot']));assert h(p[q])==x['sha256'] and len(p[q])==x['bytes'];inputs[path]=x
assert len(inputs)==31
build=j(v+'compiled/attempts.json');assert len(build)==4 and all(x['returncode']==0 for x in build)
rows=[]
for phase,cases in [('preflight',[0]),('remaining',list(range(1,15)))]:
 prefix=r+phase+'/';attempts=j(prefix+'attempts.json');assert len(attempts)==len(cases)*2
 assert 'KEXE_COMMAND' not in j(prefix+'effective-owned-environment.json')
 for i,row in enumerate(attempts):
  case=cases[i//2];profile=['RF-core-probe','inverse-v2-core-probe'][i%2]
  name=f'{case:02d}-{profile}';assert row==j(prefix+name+'.status.json')
  raw=p[prefix+name+'.stdout'];err=p[prefix+name+'.stderr'];want=9008 if case==14 and profile=='inverse-v2-core-probe' else 0
  assert raw==f'{want}\n'.encode() and err==b'' and row['actualReturn']==want and row['returncode']==0
  assert row['case']==case and row['profile']==profile and row['expectedReturn']==0 and row['PASS']==(want==0)
  assert row['argv'][2]==p[v+'compiled/'+profile+'/native.offset'].decode().strip()
  assert row['argv'][1].endswith('/compiled/'+profile+'/native.bin') and row['argv'][-1]==str(case)
  rows.append({'case':case,'profile':profile,'value':want,'PASS':want==0})
assert len(rows)==30 and sum(x['PASS'] for x in rows)==29
assert not any(n.startswith(r+'remaining/15-') for n in p)
assert j(r+'preflight/report.json')['guestCalls']==2 and j(r+'preflight/report.json')['status']=='PASS'
f=j(r+'remaining/report.json');assert f['guestCalls']==28 and f['failedCase']==14 and f['failedProfile']=='inverse-v2-core-probe' and f['value']==9008
reg=j(r+'preregistration.json');assert reg['retries']==0 and reg['expectedReturn']==0
for name in ['RF-core-probe.kotoba','inverse-v2-core-probe.kotoba']:
 text=p[v+name].decode();original,end=json.JSONDecoder().raw_decode(text.split('(def cm-source ',1)[1]);assert original.encode()==p['team-inverse-native-images/continuation/sources/nettle-aes.kotoba']
 assert '(ck-r6b-lib ' in text and '(ck-run-h ' in text and '(drv-reread ' in text
print(json.dumps({'status':'PASS offline finite-receipt replay; qualification FAIL','members':len(p),'compiledPins':21,'runtimeInputs':31,'compilerProcesses':4,'actualGuestCalls':30,'PASS':29,'FAIL':1,'failedCase':14,'failedProfile':'inverse-v2-core-probe','failedValue':9008,'case15Executed':False,'cases3and5':'admission-only','case14':'intentionally invalid diagnostic state','qualificationPASS':False,'newNativeBuildSolverNetworkTiming':0,'rows':rows}))
