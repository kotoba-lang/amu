import pathlib,json,hashlib,tarfile
D=pathlib.Path(__file__).parent
def h(b):return hashlib.sha256(b).hexdigest()
m=json.loads((D/'entry-manifest.json').read_text());b=(D/m['archive']).read_bytes()
assert h(b)==m['archiveSHA256'];assert m['qualificationPASS'] is False and m['branchDirectlyObserved'] is False
with tarfile.open(D/m['archive'],'r:gz') as t:
 assert len(t.getmembers())<=120
 assert all(x.isfile() and not x.name.startswith('/') and '..' not in pathlib.PurePosixPath(x.name).parts for x in t.getmembers())
 p={x.name:t.extractfile(x).read() for x in t.getmembers()}
assert set(p)==set(m['members'])
for n,r in m['members'].items():assert len(p[n])==r['bytes'] and h(p[n])==r['sha256']
def j(n):return json.loads(p[n])
v='team-inverse-compilerM-plan/fixture-v2/';r=v+'runtime-procedure-v2/';f=r+'preflight/'
cp=j(v+'compiled/pins.json');assert len(cp)==21
for n,x in cp.items():assert h(p[v+'compiled/'+n])==x['sha256'] and len(p[v+'compiled/'+n])==x['bytes']
combined={}
for n in [r+'preregistration.json',r+'compiled-input-binding.json']:
 for path,x in j(n)['inputs'].items():
  member=str(pathlib.PurePosixPath(path).relative_to(m['originRoot']));assert h(p[member])==x['sha256'] and len(p[member])==x['bytes'];combined[path]=x
assert len(combined)==31
attempts=j(v+'compiled/attempts.json');assert len(attempts)==4
assert all(x['returncode']==0 for x in attempts)
s=j(f+'00-RF-core-probe.status.json');raw=p[f+'00-RF-core-probe.stdout']
assert raw==b'12101\n' and p[f+'00-RF-core-probe.stderr']==b''
assert s['actualReturn']==int(raw)==12101 and s['returncode']==0 and s['expectedReturn']==0 and s['PASS'] is False
assert s['case']==0 and s['profile']=='RF-core-probe'
assert s['argv'][1].endswith('/compiled/RF-core-probe/native.bin') and s['argv'][2]==p[v+'compiled/RF-core-probe/native.offset'].decode().strip()
a=j(f+'attempts.json');assert len(a)==1 and a[0]==s
q=j(f+'report.json');assert q['guestCalls']==1 and q['hostBuilds']==0 and q['failedProfile']=='RF-core-probe' and q['value']==12101
assert 'KEXE_COMMAND' not in j(f+'effective-owned-environment.json')
assert j(r+'preregistration.json')['expectedReturn']==0 and j(r+'preregistration.json')['retries']==0
for source in ['RF-core-probe.kotoba','inverse-v2-core-probe.kotoba']:
 text=p[v+source].decode();assert '(ck-run-h ' in text and '(ck-hint-again? ' in text and '(drv-reread ' in text
 value,end=json.JSONDecoder().raw_decode(text.split('(def cm-source ',1)[1]);assert value.encode()==p['team-inverse-native-images/continuation/sources/nettle-aes.kotoba']
cor=j('root/inverse-compilerM-failure-classification-scope-correction.json');assert cor['inferredCandidateOrigin']['branchDirectlyObserved'] is False
print(json.dumps({'status':'PASS offline receipt replay; qualification remains FAIL','members':len(p),'compiledPins':21,'runtimeInputs':31,'compilerProcesses':4,'RFGuestCalls':1,'fullValue':12101,'OSexit':0,'qualificationPASS':False,'inverseGuestCalls':0,'remainingGuestCalls':0,'MMERRBranchDirectlyObserved':False,'newNativeSolverTimingNetwork':0}))
