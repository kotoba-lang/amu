import pathlib,json,hashlib,tarfile,io,re
D=pathlib.Path(__file__).parent;h=lambda b:hashlib.sha256(b).hexdigest();m=json.loads((D/'entry-manifest.json').read_text())
assert m['performanceAuthorized'] is False and m['officialEmbenchScore'] is False
assert h((D/m['archive']).read_bytes())==m['archiveSHA256']
def readtar(b,cap):
 with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as t:
  assert len(t.getmembers())<=cap and all(x.isfile() and not x.name.startswith('/') and '..' not in pathlib.PurePosixPath(x.name).parts for x in t.getmembers());return {x.name:t.extractfile(x).read() for x in t.getmembers()}
p=readtar((D/m['archive']).read_bytes(),300);assert set(p)==set(m['members'])
for n,r in m['members'].items():assert h(p[n])==r['sha256'] and len(p[n])==r['bytes']
j=lambda n:json.loads(p[n]);E='team-remote57-inverse-prep/sealed-envelope/';blob=p[E+'remote57-package.tgz'];assert h(blob)=='d456ff754d42fd191d9a0584162d05e090b5041eccd815ad8731eb2b967aabe9'
z=readtar(blob,160);assert len(z)==145
for n,v in json.loads(z['package/package-input-pins.json']).items():assert h(z['package/'+n])==v
entries=json.loads(z['package/manifest.json'])['entries'];assert len(entries)==19
B='root/remote57-built/';S='root/remote57-semantic/'
for root in [B,S]:
 for n,v in j(root+'pins.json').items():assert h(p[root+n])==v
build=j(B+'attempts.json');calls=j(S+'attempts.json');assert len(build)==19 and len(calls)==57
for i,e in enumerate(entries):
 name=e['workload'];base='package/'+name+'/'
 for arm in ['baseline','candidate']:assert h(z[base+arm+'.bin'])==e[arm+'NativeSHA256']
 assert h(z[base+'c.dylib'])==e['CbinarySHA256'] and h(z[base+'source.kotoba'])==e['sourceSHA256']
 hdr=z[base+'immutable-header.h'].decode();assert h(z[base+'immutable-header.h'])==e['immutableHeaderSHA256']
 for sym,filename in [('known_baseline','baseline.bin'),('known_candidate','candidate.bin'),('timing_known_c_bytes','c.dylib')]:
  raw=re.search(r'\b'+sym+r'\[\]\s*=\s*\{([^}]*)\}',hdr)[1];arr=bytes(int(x) for x in raw.split(',') if x.strip());assert arr==z[base+filename]
 assert '#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES 6ULL' in hdr
 b=build[i];assert b['workload']==name and b['returncode']==0 and b['state']=='terminal' and b['headerSHA256']==e['immutableHeaderSHA256']
 assert h(p[B+name+'/runner'])==b['runnerSHA256'] and h(z['package/timing-host.c'])==b['hostSourceSHA256']==e['hostSourceSHA256']
 for k,arm in enumerate(['baseline','candidate','C']):
  c=calls[i*3+k];assert c['workload']==name and c['arm']==arm and c['state']=='terminal' and c['n']==e['n']
  n=S+name+'-'+arm+'.json';assert h(p[n])==c['receiptSHA256'];r=j(n);assert r['exit']==0 and r['stderr']=='' and r['diagnosticElapsedNotStatistics'] is True
  v=json.loads(r['stdout']);assert v['calls']==1 and v['warmupCalls']==0 and v['result']==1 and v['fuelPerCall']==16777216
  assert v['contextFuelBefore']==16777216 and v['contextFuelConsumed']==(0 if arm=='C' else e['expectedNativeFuelConsumed'])
  assert v['contextFuelAfter']==16777216-v['contextFuelConsumed']
  argv=r['argv'];assert argv[5]==str(e['n'])
f=j(S+'feature.json');assert f['arch']['stdout'].strip()=='arm64' and f['AES']['stdout'].strip()=='1' and f['CRC32']['stdout'].strip()=='1'
assert all(x['exit']==0 for x in f.values())
for root,labels in [('root/remote57-transfer-build-results/',['uniqueMkdir','archiveTransfer','verifyAndExtract','buildGOTransfer','build19']),('root/remote57-semantic-run-results/',['semanticGOTransfer','semantic57'])]:
 a=j(root+'attempts.json');assert [x['label'] for x in a]==labels and all(x['returncode']==0 and x['state']=='terminal' for x in a)
assert j('root/remote57-semantic-GO.json')['maximumCalls']==57 and j('root/remote57-semantic-GO.json')['performanceAuthorized'] is False
assert next(e for e in entries if e['workload']=='nettle-aes')['expectedNativeFuelConsumed']==427363
assert h(p['team-inverse-compilerM-independent/remote57-semantic-results-review/report.json'])=='d98594824ef44be7ca2b26161ddb7649988d61b3f223f2c7711cb755328eaf98'
print(json.dumps({'status':'PASS offline remote19build+57functional receipt replay','members':len(p),'sealedPayloadMembers':145,'builds':19,'functionalCalls':57,'results':57,'actualARM64AESCRC32':True,'AESFuelConsumed':427363,'performanceAuthorized':False,'officialEmbenchScore':False,'elapsedStatisticsComputed':False,'newNativeBuildGuestSolverNetworkTiming':0}))
