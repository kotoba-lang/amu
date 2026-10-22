import pathlib,tarfile,json,hashlib,re
D=pathlib.Path(__file__).parent;h=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((D/'entry-manifest.json').read_text());assert m['qualificationPASS'] is False
assert h((D/m['archive']).read_bytes())==m['archiveSHA256']
with tarfile.open(D/m['archive'],'r:gz') as t:
 assert len(t.getmembers())<=60 and all(x.isfile() for x in t.getmembers());p={x.name:t.extractfile(x).read() for x in t.getmembers()}
assert set(p)==set(m['members'])
for n,r in m['members'].items():assert h(p[n])==r['sha256'] and len(p[n])==r['bytes']
j=lambda n:json.loads(p[n]);s='team-inverse-compilerM-plan/stage-localization-minimal-v1/';o=s+'observation/'
raw=p[o+'stdout'].decode();items=[int(x) for x in re.search(r':result-items\s*\[([^]]*)\]',raw)[1].split()]
assert items==[5,2101,32579,32579,32582,0,0] and ':status :ok' in raw and ':result-type :vector-i64' in raw
assert j(o+'status.json')['returncode']==0 and p[o+'stderr']==b''
assert j(o+'report.json')['nativeCalls']==1 and j(o+'report.json')['qualificationPASS'] is False
assert j(o+'started.json')['argv'][2]==p[s+'compiled/native.offset'].decode().strip()
a=j(s+'compiled/attempts.json');assert len(a)==2 and all(x['returncode']==0 for x in a)
for n,r in j(o+'authorization.json')['inputs'].items():
 member=n.split('/amu-aes-resident-fuel-20261007/',1)[1]
 if member in p:assert h(p[member])==r['sha256']
source=p[s+'RF-localize.kotoba'].decode();value,end=json.JSONDecoder().raw_decode(source.split('(def loc-source ',1)[1]);original=p['team-inverse-native-images/continuation/sources/nettle-aes.kotoba']
assert value.encode()==original and original[32579:32582]==b'rem' and original[:32579].count(b'\n')+1==80
assert 'MM-ERR-POS' in source and '(vector-assoc! V 1 (vector-at M MM-ERR))' in source and 'S loc-source H' in source
f=j('source-fragments.json');text=''.join(x['text'] for x in f['fragments'])
assert '(string-concat S0 (ck-r6b-lib S0))' in text and '(ck-r6b-pick m ck-r6b-g-rem (ck-r6b-t-rem))' in text and 'ck-r6b-t-rem' in text
assert all(x['text'] in source for x in f['fragments'])
r=j('team-inverse-compilerM-independent/minimal-observation-review/report.json');assert r['items']==items and r['position']['token']=='rem' and r['qualificationPASS'] is False
runner=p['root/minimal-localization-observe.py'].decode();assert 'timeout=3660' in runner and 'except subprocess.TimeoutExpired' not in runner
print(json.dumps({'status':'PASS offline localization receipt replay only','members':len(p),'compilerProcesses':2,'observedNativeCalls':1,'requestedStage':5,'directMMERR':2101,'positionToken':'rem','line':80,'qualificationPASS':False,'old12101BranchesRemainAmbiguous':True,'timeoutOccurred':False,'newNativeNetworkSolverTiming':0}))
