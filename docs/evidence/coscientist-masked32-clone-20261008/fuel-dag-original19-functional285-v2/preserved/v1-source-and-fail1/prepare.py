"""SOURCE ONLY authoring: file reads/writes and hashes; never imports/calls operational driver."""
from pathlib import Path
import json,hashlib,stat,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=Path(__file__).resolve().parent
L=W/'vector-leaf-straight-read-cache-functional255-plan-v1-width';L30=W/'vector-leaf-straight-read-cache-functional30-plan-v2-controls'
S=W/'vector-fuel-scalar-dag-original19-selfbuild44-plan-v1-native-controls';A=W/'vector-fuel-scalar-dag-original19-selfbuild44-actual-review-v1-fuel44-review';R=W/'vector-fuel-scalar-dag-original19-selfbuild44-go-v1-root'
H=lambda b:hashlib.sha256(b).hexdigest();J=lambda p:json.loads(Path(p).read_bytes())
def pin(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink();h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'path':str(p),'bytes':s.st_size,'sha256':h.hexdigest()}
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
assert not (D/'preregistration.json').exists() and not (D/'run.py').exists(),'fresh SOURCE registration only'
old=J(L/'preregistration.json');old30=J(L30/'preregistration.json');cl=J(L/'input-closure.json')
def add(v):
 x={k:v[k]for k in ['bytes','sha256']};assert v['path']not in cl or cl[v['path']]==x;cl[v['path']]=x
for folder in [L,L30,A]:
 for p in folder.iterdir():
  if p.is_file():add(pin(p))
for path,v in J(A/'input-pins.json').items():add({'path':path,**v})
for folder in [L,L30]:
 for path,v in J(folder/'input-closure.json').items():add({'path':path,**v})
accept=pin(R/'selfbuild44-acceptance.json');assert accept['sha256']=='13ba542130f9f1d795ac4a419ca771dde3ae06e82d5ec6a5a18fc2d8bdcd3896';add(accept)
add(pin(R/'original19-static-baseline-comparison.json'))
proofs=dict(old['proofs']);proofs['scalar44']={'report':pin(A/'report.json'),'inputPins':pin(A/'input-pins.json'),'status':'PASS_INDEPENDENT_SAVED_RAW_FUEL_DAG_ORIGINAL19_SELFBUILD44_FIXEDPOINT_ONLY'}
assert proofs['scalar44']['report']['sha256']=='4fb1eb14c7a9a8a77749d0f3977139651718817334de44da73e6be8b80887a96'
images=pin(S/'run-outputs/images.json');add(images);rows=J(images['path']);assert len(rows)==19
matrix=J(old['canonicalMatrix']['path'])['entries'];prior={c['workload']:c for c in old['cases']+old30['cases']};profiles=J(old['resourceProfiles']['path']);cases=[]
def exports(v):
 b=Path(v['path']).read_bytes();head,payload=b.split(b'\n\n',1);ls=head.decode('ascii').splitlines();assert ls[0]==f'KSEED1 {len(payload)} {len(ls)-1}'
 return [{'name':s,'offset':int(o),'arity':int(a)}for s,o,a in (l.split()for l in ls[1:])]
for e,z in zip(matrix,rows):
 n=e['workload'];assert z['workload']==n and z['source']['sha256']==e['expectedSourceSha256'] and z['iterations']==e['iterations'];c=dict(prior[n]);c.update(ON=z['native'],ONContainer=z['container'],ONOffset=z['offset'],source=z['source'],iterations=e['iterations']);c['OFFExports']=exports(c['OFFContainer']);c['ONExports']=[{'name':s,'offset':o,'arity':a}for s,o,a in z['exports']];c['resourceReferenceProfiles']=[v for v in profiles if v['workload']==n]
 for k in ['source','OFF','OFFContainer','ON','ONContainer','C','CRunner']:add(c[k])
 cases.append(c)
pr=dict(old);pr.update(status='PROSPECTIVE_SOURCE_ONLY_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_REGISTERED_BEFORE_DRIVER_AUTHORING',maximumFutureChildCalls=285,nativeCalls=190,CCalls=95,retainedAcceptedCalls=0,joinedOriginal19Calls=285,sourceReviewStatus='PASS_SOURCE_ONLY_FUEL_DAG_ORIGINAL19_FUNCTIONAL285',rootGOStatus='ROOT_AUTHORIZED_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_ONLY',root44AcceptanceRequired='ROOT_ACCEPTED_FUEL_DAG_ORIGINAL19_SELFBUILD44_FIXEDPOINT_ONLY',scalar44RootAcceptance=accept,scalar44Images=images,proofs=proofs,cases=cases,maximumInputFiles=4096,maximumInputLogicalBytes=448*1024**2,outputRoot=str(D/'run-outputs'),parentProducerScope='G0 scalar DAG original19 images, independently accepted scalar44 compile/extract and G0=G1=G2=G3 native identity; no runtime or performance inference.',futureRootGORequired=True,twoIndependentSourceReviewsRequired=True,compilerExtractCalls=0,guestCallsByAuthor=0,operationalDriverCallsByAuthor=0,arms=['OFF','ON','C'],historicalLC30Scope='Lineage and parser controls only. Zero retained candidate acceptance: all19 profiles freshly executed in this prospective285.',root44SourcePinsSHA256=J(accept['path'])['sourcePinsSHA256'])
pr.pop('root40AcceptanceRequired');pr.pop('LC30Acceptance');save('input-closure.json',dict(sorted(cl.items())));save('preregistration.json',pr)
s=(L/'run.py').read_text()
s=s.replace("<255,'finite255'","<285,'finite285'").replace("==255 and g['functionalAuthorized']","==285 and type(g['maximumChildCalls'])is int and g['functionalAuthorized']").replace('specific finite255 root GO','specific finite285 root GO').replace("g['LC40RootAcceptance']","g['scalar44RootAcceptance']")
a=s.index(" a40=load(");b=s.index(" old285=load(",a)
s=s[:a]+''' a44=load(g['scalar44RootAcceptance']['path']);need(g['scalar44RootAcceptance']==pr['scalar44RootAcceptance']and a44['status']==pr['root44AcceptanceRequired']and a44['independentActualReceipt']==pr['proofs']['scalar44']['report']and a44['sourcePinsSHA256']==pr['root44SourcePinsSHA256']and a44['closedLoaderCalls']==44 and a44['original19CompileExtractCalls']==38 and a44['selfbuildCalls']==6 and a44['G0G1G2G3NativeSHA256']=='d3a0e2ffe5887a1b77ace0e0a366dd8bda180f3e9ef2f7067a1e3436f9c3d15a'and a44['nativeBytes']==969864 and a44['original19RuntimeQualified']is False and a44['timingQualified']is False and a44['C2Enabled']is False,'root44 exact SOURCE-bound fixedpoint acceptance')
 scalar44=load(pr['proofs']['scalar44']['report']['path']);need(scalar44['sourcePinsSHA256']==a44['sourcePinsSHA256']and scalar44['loaderCalls']==44 and scalar44['allChildrenClosed']is True and scalar44['failure']is False and scalar44['wholeOriginal19BodiesSymbolsProfilesExportsPayloads']is True and scalar44['wholeUnitySourceAndProducerSequence']is True and scalar44['G1G2G3WholeContainerNativeSoleMain0']is True,'scalar44 independent actual fixedpoint schema')
 onimages=load(pr['scalar44Images']['path']);need(len(onimages)==19,'exact scalar44 all19 image registry')
 lr=load(pr['proofs']['loader16']['report']['path']);need(lr['loader']==pr['loader']and pr['loader']['sha256']=='e14c2919ac5afd0960d9e6a4ac30ed90da26047c99842ef4d66428322764a77f','exact diagnostic loader source binding')
 raw=load(pr['CConsumerRawReport']['path']);need(raw['sourceSHA256']==pr['CConsumerSource']['sha256']and raw['builds']==19,'C consumer historical source binding')
''' +s[b:]
s=s.replace("expected=[e for e in matrix['entries']if e['workload']not in ['md5sum','nettle-sha256']];need(len(expected)==len(pr['cases'])==17,'exact17 complement')","expected=matrix['entries'];need(len(expected)==len(pr['cases'])==19 and sum(len(c['iterations'])for c in pr['cases'])==95,'exact original19 and95 profiles')")
s=s.replace("'nettle-aes'else'SR40'","'nettle-aes','nettle-sha256']else'SR40'") if False else s
s=s.replace("c['workload']=='nettle-aes'","c['workload']in ['nettle-aes','nettle-sha256']")
s=s.replace("next(v for v in lc40['images']if v['workload']==c['workload'])","next(v for v in onimages if v['workload']==c['workload'])").replace('G0 LC actual full artifact identity','G0 scalar actual full artifact identity')
s=s.replace("exports,payload=container(c[arm+'Container']);need(payload==pin(c[arm]).read_bytes()and dict(name=c['symbol'],offset=c[arm+'Offset'],arity=1)in exports,'full native/container/export binding')","exports,payload=container(c[arm+'Container']);need(exports==c[arm+'Exports']and payload==pin(c[arm]).read_bytes()and dict(name=c['symbol'],offset=c[arm+'Offset'],arity=1)in exports,'full native/container/ALL exports exact binding')\n  need([(v['name'],v['arity'])for v in c['OFFExports']]==[(v['name'],v['arity'])for v in c['ONExports']],'whole OFF ON exported ABI parity')")
s=s.replace("len(led.rows)==255 and len(completed)==85,'255 calls85triples'","len(led.rows)==285 and len(completed)==95,'285 calls95triples'").replace('PASS_FINITE_LC_REMAINING17_FUNCTIONAL255_ONLY','PASS_FINITE_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_ONLY').replace('FAIL_FINITE_LC_REMAINING17_FUNCTIONAL255_FIRST_FAILURE','FAIL_FINITE_FUEL_DAG_ORIGINAL19_FUNCTIONAL285_FIRST_FAILURE').replace("'retainedAcceptedCalls':30","'retainedAcceptedCalls':0")
s=s.replace("all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256'])","all(q[k]==g[k]for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256','inputClosureSHA256'])and q['independent']is True and q['priorAuthorship']is False")
s=s.replace("led=Ledger();completed=[];ok=False","led=Ledger();completed=[];ok=False")
ast.parse(s);(D/'run.py').write_text(s)
print('SOURCE preregistered then driver authored:',len(cl),'files',sum(v['bytes']for v in cl.values()),'bytes; child calls=0')
