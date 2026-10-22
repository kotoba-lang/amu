from pathlib import Path
import hashlib,json,shutil
W=Path(__file__).resolve().parent
R=Path('/Users/junkawasaki/github/wt/amu-seed17')
B=Path('/private/tmp/amu-static-vector-chain-20261006')
OLD=Path('/private/tmp/amu-closed-chain-fuel-20261006')
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def passed(p):
 x=load(p);assert x['status'].startswith('PASS'),(p,x.get('status'));return x
# Do not make a timing package until every independent audit is terminal PASS.
machine=passed(W/'team-machine/audit.json')
constructor=passed(W/'team-constructor/report.json')
resource=passed(W/'team-resource/report.json')
assert machine['totals']['provedSirDeletedBounds']==machine['totals']['deletedBounds']==732
assert machine['totals']['emittedSirEvents']==66525 and len(machine['controls'])==8
assert all(x['status']=='REFUSED' for x in machine['controls'])
fixed=passed(W/'fixed-point.json');assert len(fixed['generations'])==3
assert {x['sha256'] for x in fixed['generations']}=={'20f9a9554a459725bcba06d6110f8b53ffd75c2e14f7ea1d6f08fa48f6040683'}
for e in fixed['generations']:assert sha(W/f"seed-{e['generation']}.bin")==e['sha256']
per=load(W/'adoption-permanent-proof.json');assert per['fixtures']==593 and per['runs']==25658
assert per['realTestCodeAndLiteralBytesEqual'] and per['realTestFnOffsetsEqual'] and not per['committedGoldenChanged']
state=passed(W/'ports-state.json');assert state['groups']==209
passed(W/'ir-audit.json')
p=W/'timing-package';assert not p.exists(),'preserve prior package';p.mkdir()
matrix=load(R/'bench/embench/comparison-matrix.json')
base=load(B/'ports-correctness.json');ca=passed(W/'ports-semantic.json')
changed=[]
for e in ca['entries']:
 old=next(x for x in base['entries'] if x['workload']==e['workload'])
 m=next(x for x in matrix['entries'] if x['workload']==e['workload'])
 assert sha(R/m['source'])==old['sourceSha256']==m['expectedSourceSha256']
 e['sourceSha256']=old['sourceSha256'];assert e['runs']==old['runs'] and e['fuelTrapReturncode']==old['fuelTrapReturncode']
 assert sha(W/'ports'/e['workload']/'native.bin')==e['nativeSha256']
 assert sha(B/'ports-2'/e['workload']/'native.bin')==old['nativeSha256']
 if e['nativeSha256']!=old['nativeSha256']:changed.append(e['workload'])
assert changed==['matmult-int','nsichneu','picojpeg','statemate','ud']
(p/'candidate-proof.json').write_text(json.dumps(ca,indent=2)+'\n')
shutil.copy2(B/'ports-correctness.json',p/'product-proof.json')
for n in ['comparison-matrix.json','paired-timing-spec.json']:shutil.copy2(R/'bench/embench'/n,p/n)
shutil.copy2(OLD/'timing-package/measure-native-candidate-v2.py',p/'measure-native-candidate-v2.py')
for name,path in {'machine-proof.json':W/'team-machine/audit.json','constructor-proof.json':W/'team-constructor/report.json','resource-proof.json':W/'team-resource/report.json','fixed-point.json':W/'fixed-point.json','permanent-proof.json':W/'adoption-permanent-proof.json','ports-state.json':W/'ports-state.json','ir-audit.json':W/'ir-audit.json','41-a64gen-prototype.kotoba':W/'41-a64gen-prototype.kotoba','42-layout-prototype.kotoba':W/'42-layout-prototype.kotoba','hypothesis.json':W/'hypothesis.json'}.items():shutil.copy2(path,p/name)
spec=load(p/'paired-timing-spec.json')
for name in changed:
 e=next(x for x in ca['entries'] if x['workload']==name);b=next(x for x in base['entries'] if x['workload']==name)
 d=p/name;(d/'candidate').mkdir(parents=True)
 shutil.copy2(B/'ports-2'/name/'native.bin',d/'baseline-native.bin');shutil.copy2(W/'ports'/name/'native.bin',d/'candidate/native.bin')
 n=next(x['iterationsPerCall'] for x in spec['entries'] if x['workload']==name)
 manifest={'workload':name,'offset':e['offset'],'baselineOffset':b['offset'],'sourceSha256':e['sourceSha256'],'baselineSourceSha256':b['sourceSha256'],'nativeSha256':e['nativeSha256'],'baselineNativeSha256':b['nativeSha256'],'compilerGenerationSha256':{str(x['generation']):x['sha256'] for x in fixed['generations']},'expectedFuelPerCall':next(x['fuelConsumed'] for x in e['runs'] if x['n']==n),'hypothesis':'constructor-established-private-length-clones-v3','prototypeSha256':sha(W/'41-a64gen-prototype.kotoba'),'layoutSha256':sha(W/'42-layout-prototype.kotoba'),'officialEmbenchScore':False}
 (d/'candidate/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
pre={'status':'complete-native-semantic-proof-before-timing','originalWorkloads':19,'fullSupervisorComparisons':209,'constructorProof':constructor['status'],'resourceProof':resource['status'],'machineProof':machine['status'],'permanentFixtures':593,'permanentNativeRuns':25658,'changedGuests':changed,'unchangedGuests':[x['workload'] for x in ca['entries'] if x['workload'] not in changed],'nativeSeedSha256':sha(W/'seed-4.bin'),'proofPins':{f.name:sha(f) for f in p.iterdir() if f.is_file()},'productPromoted':False,'timingDecision':'One fresh rotating product/candidate/C campaign. No identical retry; original rules unchanged.'}
(p/'preflight.json').write_text(json.dumps(pre,indent=2)+'\n');shutil.copy2(p/'preflight.json',W/'preflight.json')
print('PASS gated timing package',changed)
