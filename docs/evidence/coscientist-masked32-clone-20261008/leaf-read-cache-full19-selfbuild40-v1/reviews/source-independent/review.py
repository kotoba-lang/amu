from pathlib import Path
import hashlib,json,stat,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-leaf-straight-read-cache-full19-selfbuild40-plan-v1-native-controls';A=Path(__file__).resolve().parent;H=lambda b:hashlib.sha256(b).hexdigest();J=lambda p:json.loads(Path(p).read_bytes());pins={}
def get(p,v=None):
 p=Path(p);st=p.lstat();assert stat.S_ISREG(st.st_mode)and not p.is_symlink();b=p.read_bytes();r={'bytes':len(b),'sha256':H(b)}
 if v:assert r=={k:v[k]for k in ['bytes','sha256']}
 pins[str(p)]=r;return b
sp=J(D/'source-pins.json');pr=J(D/'preregistration.json');ip=J(D/'input-pins.json');assert H(get(D/'source-pins.json'))=='535e27cbe60dfb3320d804ece7a23c7ed6b5b451083851c6a9dc5361c9e9f346'
for n,v in sp.items():get(D/n,v)
for p,v in ip.items():get(p,v)
for n in ['run.py','prepare.py','pure-controls.py']:ast.parse((D/n).read_bytes())
assert len(ip)==1843 and sum(v['bytes']for v in ip.values())==379860457 and pr['maximumLoaderCalls']==40 and pr['remainingWorkloadCalls']==34 and pr['selfbuildCalls']==6
s=(D/'run.py').read_bytes();ns={'__file__':str(D/'run.py'),'__name__':'independent_source_reader'};exec(compile(s,str(D/'run.py'),'exec'),ns)
mat=J(pr['canonicalMatrix']);assert len(pr['entries'])==len(mat['entries'])==19
for e,m in zip(pr['entries'],mat['entries']):
 assert e['workload']==m['workload']and e['symbol']==m['symbol']and e['iterations']==m['iterations']and e['source']['sha256']==m['expectedSourceSha256'];get(e['source']['path'],e['source'])
 if 'retained'in e:
  payload,exports=ns['parse_container'](get(e['retained']['container']['path'],e['retained']['container']));assert payload==get(e['retained']['native']['path'],e['retained']['native'])and any(x[0]==e['symbol']and x[2]==1 for x in exports)
assert [e['workload']for e in pr['entries']if 'retained'in e]==['md5sum','nettle-sha256']
# Exact inherited ledger: no native or main invocation.
old=get(pr['callLedgerOrigin']['path'],pr['callLedgerOrigin']).decode();actual=s.decode();a=old[old.index(' def call('):old.index('\n try:\n  decoderPath')];b=actual[actual.index(' def call('):actual.index('\n try:\n  def build')];assert b==a.replace('len(rows)<10','len(rows)<40').replace('finite18 no retry','finite40 no retry')
payload=bytes.fromhex('1f2003d5')*2;valid=b'KSEED1 8 1\nmain 0 0\n\n'+payload;assert ns['parse_container'](valid)==(payload,[('main',0,0)])
mutants=[valid[:-1],valid.replace(b'8 1',b'7 1'),valid.replace(b'main 0 0',b'main 8 0'),valid.replace(b'main 0 0',b'main 1 0'),valid.replace(b'8 1',b'8 2'),valid.replace(b'main 0 0',b'main 0 33'),b'KSEED1 8 2\nmain 0 0\nmain 4 0\n\n'+payload]
for m in mutants:
 try:ns['parse_container'](m)
 except AssertionError:pass
 else:raise AssertionError('bad container accepted')
for key in ['actualProducerProof','actualLoaderProof','actualOwnerProof']:assert J(pr[key])['status']==pr[key+'Status']
owner=J(pr['actualOwnerProof']);assert owner['counts']['closedLoaderCalls']==10 and owner['checks']['wholeOrdinaryObservedContainersNativeExportsOffsetsIdentical']
for p,v in list(pins.items()):assert H(Path(p).read_bytes())==v['sha256']
(A/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n');q={'status':'PASS_SOURCE_ONLY_LC_FULL19_SELFBUILD40','sourcePinsSHA256':H((D/'source-pins.json').read_bytes()),'driverSHA256':H(s),'preregistrationSHA256':H((D/'preregistration.json').read_bytes()),'inputPinsSHA256':H((A/'input-pins.json').read_bytes()),'counts':{'reviewedInputFiles':len(pins),'reviewedLogicalBytes':sum(v['bytes']for v in pins.values()),'maximumFutureLoaderCalls':40,'newRemaining17Calls':34,'retainedOrdinaryCalls':4,'joinedOriginal19Calls':38,'selfbuildCalls':6,'nativeCallsByReviewer':0},'checks':{'exactFrozenRegistryAndFullInputClosure':True,'canonical19SourceSymbolProfilesExact':True,'retainedTwoWholeContainerPayloadAndExports':True,'specificTwoSourceReviewsAndRootGORequired':True,'freshWire35ScopeReadOnlySourceCopies':True,'captureContainerBeforeExtractAndGuardBeforeAfterEveryChild':True,'originalReviewedLedgerOnlyCapMessageDelta':True,'rawFirstGroupKillBoundedReapFirstFailureNoRetry':True,'strict17CounterSchemaResources':True,'fullNativePayloadAndBoundedExportOffsets':True,'G0ToG1DifferenceAllowedRecorded':True,'G1G2G3WholeContainerNativeMain0EqualityRequired':True,'purePositiveAndSevenRejects':True},'participation':'Earlier read LC emitter/build source; independently audited actual functional30 saved raw. Did not author this driver or its source/owner artifacts. SOURCE review only; no main/native/compiler/SSH invoked.','limitations':['Original19 compile/export and selfbuild experiment only; no new17 workload execution or machine semantic parity claim.','SOURCE40 does not consume the newly frozen functional30 receipt; that independent result is available separately and is not needed for compile-only admission.','run.py opening docstring says Exactly10, inherited stale commentary; executable/prereg guards consistently enforce40.','No standalone register canary, arbitrary frame/trap/resource theorem, full selfhost goal, C timing, official score or adoption qualified.']}
(A/'report.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({'reportSHA256':H((A/'report.json').read_bytes()),'inputPinsSHA256':q['inputPinsSHA256'],'counts':q['counts']}))
