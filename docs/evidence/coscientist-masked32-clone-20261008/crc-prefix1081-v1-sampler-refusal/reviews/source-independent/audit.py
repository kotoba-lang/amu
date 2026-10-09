from pathlib import Path
import hashlib,json,stat,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'crc-table-full256-prefix1081-source-v1-20261009';V=W/'crc-original-guest-native-controller-source-v4-20261009-dense';O=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def check(p,v):
 assert stat.S_ISREG(p.lstat().st_mode)and not p.is_symlink();b=p.read_bytes();assert len(b)==v['bytes']and sha(b)==v['sha256'],str(p)
f=json.loads((D/'freeze.json').read_text());sp=json.loads((D/'source-pins.json').read_text());ip=json.loads((D/'input-pins.json').read_text());pr=json.loads((D/'preregistration.json').read_text());cert=json.loads((D/'fuel-reach-certificate.json').read_text())
assert sha((D/'freeze.json').read_bytes())=='6b8f5aa6bbd873b60a352c1775600fd7af2d8415a53fd232b0df0a9a46b9b29c'
assert sha((D/'source-pins.json').read_bytes())=='8dc2886e507d7b677b26c7c6c4c4691e142f981bbac58461d775cb38fb7a7d1d'
for n,v in sp.items():check(D/n,v)
for n,v in ip.items():check(Path(n),v)
assert len(sp)==18 and len(ip)==2141 and sum(v['bytes']for v in ip.values())==405190069
unchanged=['capture.py','integration.py','controller.py','typed-adapter.py','adapter.py','runtime.py','validate-runtime.py','launch-wrapper.py']
for n in unchanged:assert (D/n).read_bytes()==(V/n).read_bytes()
for p in D.glob('*.py'):ast.parse(p.read_text())
assert len(pr['cases'])==2 and len(pr['environment'])==17 and pr['maximumPythonWrapperStarts']==2 and pr['maximumNativeGuestChildStarts']==2 and pr['maximumNativeCompilerChildStarts']==0
for c,arm,offset in zip(pr['cases'],['OFF','ON'],[1352,1392]):
 assert c['arm']==arm and c['symbol']=='prefix-crc'and c['argument']==1081 and c['expectedResult']==4018572661 and c['expectedRemainingFuel']==997836 and c['offset']==offset
 assert c['nativeArgv']==[pr['loader']['path'],pr['offArtifact'if arm=='OFF'else'onArtifact']['path'],str(offset),'1','aarch64','-','1081']
proof=pr['priorActualGuest8IndependentProof'];check(Path(proof['path']),proof);assert proof['sha256']=='6c8e86547cb5311ce48a8ce7ef5a8eada9daac1568b59d4b4f841d643dc6105c'
# Reuse our independently authored SOURCE interpreter, stopping before mutations/report writes.
ind=W/'crc-original-table-reach-source-trace-review-independent-20261009/audit.py';code=ind.read_text().split('# Concrete table mutation')[0];ns={'__file__':str(ind)};exec(compile(code,'independent-source-interpreter-readonly','exec'),ns)
assert ns['fullVisits']==cert['orderedIndices'] and cert['expectedCRC']==4018572661 and cert['firstVisitIterationByIndex']=={str(i):v for i,v in enumerate(ns['first'])}and set(cert['orderedIndices'])==set(range(256))and cert['lastFirstVisitIteration']==1081
# Independently derive exact fuel sites from pinned typed table rather than author certificate arithmetic.
raw=Path(cert['typedCurrentRaw']['path']);check(raw,cert['typedCurrentRaw']);lines=[line.split()for line in raw.read_text().splitlines()]
sir={int(x[2]):list(map(int,x[3:]))for x in lines if x[0]=='FSIR'and x[1]=='0'};ff={(int(x[2]),int(x[3])):int(x[4])for x in lines if x[0]=='FF'and x[1]=='0'}
assert [ff[(i,12)]for i in [1,2,3,6]]==[1,175,186,291]and [ff[(i,14)]for i in [1,2,3,6]]==[1,0,1,1]
for start,end,sites in [(1,175,[2]),(175,186,[]),(186,239,[187,234]),(291,298,[292])]:assert [j for j in range(start,end)if sir[j][0]==18]==sites
assert sir[220]==[13,1,0,1]and sir[207]==[13,2,0,1]and sir[295]==[13,3,0,1]
assert cert['consumedFuel']==1+1+2*len(ns['fullVisits'])==2164 and cert['expectedRemainingFuel']==1000000-2164
assert not(D/'run-outputs').exists()and not(D/'GO.json').exists()
r={'status':'PASS_SOURCE_ONLY_TC_FULL256_PREFIX1081_PAIRED2','independent':True,'priorAuthorship':False,'sourcePinsSHA256':sha((D/'source-pins.json').read_bytes()),'driverSHA256':sha((D/'run.py').read_bytes()),'subject':str(D),'freeze':pin(D/'freeze.json'),'inputPins':pin(D/'input-pins.json'),'verifiedClosure':{'sourceFiles':18,'inputFiles':2141,'inputBytes':405190069,'allDeclaredFilesExactRegularNonSymlink':True},'priorActualGuest8Proof':proof,'fuelReachCertificate':pin(D/'fuel-reach-certificate.json'),'verifiedScope':{'calls':2,'arms':['OFF','ON'],'argument':1081,'expectedCRC':4018572661,'initialFuel':1000000,'consumedFuel':2164,'remainingFuel':997836,'environmentFields':17,'compilerCalls':0,'wrapperStarts':2,'nativeGuestStarts':2,'sourceUniqueIndices':256,'lastNewIndex':154,'firstCompleteSourcePrefix':1081},'unchangedRuntimeComponents':{n:sha((D/n).read_bytes())for n in unchanged},
'observations':['Independent unchanged source parser/interpreter reproduces all1081 ordered indices/256 first visits and CRC, without executing author derive-source or native driver. Full table literal identity with accepted ON/OFF was already checked in independent interpreter and rechecked by its bounded read-only prefix.', 'Pinned typed FN/SIR records independently bind reader/next-seed/checksum/prefix owners and fuel sites2,187,234,292; calls220/207/295. Next-seed FF-FUEL0/no fuel site. Charge prefix1+checksum1+1081 reader entry+1081 recur=2164, remaining997836; ON logical debit retained by prior repaired13-word proof.', 'native-call exact V4 delta is two ordered calls and independent per-arm remainingFuel check; lifecycle/capture/resource/typed sampler code otherwise unchanged. run delta fixes fresh status/GO/review schema/call count, binds prior actual8 and certificate, requires own arm export offsets and exact CRC/fuel, whole OFF/ON reports/raw hashes/all17 counters/normal exits.', 'Exact two reviews/GO/fresh output/no retry/source-input guards remain; zero grants/no compile/no timing. Current producer7618/repair984169/extractf746511/old failure inputs unchanged. Completed namespace remains absent before this SOURCE review.', 'Future completion retains full256CandidateReachQualified=false and records only sourceBoundFull256PrefixParityQualified=true with exact priorActualGuest8/fuel certificate; no dynamic per-index trace claim.'],
'limitations':['SOURCE acceptance only; paired1081 runtime remains pending separately specific root GO and two exact reviews. No reviewer native/thread/FD/process/API operation.', 'All256 is source-derived conditional reach, not independent guest per-index tracing/general proof. Existing original8/full19 bodies and old strict failure are not changed or enlarged.', 'V4 inherited cooperative IO/FD/descendant-closure and sampled soft-memory limitations remain. Eligible termination gap never becomes zero footprint/hardpeak or old strict failure relabeling.', 'No malformed-domain/fueltrap/sentinel/fallback/FADDR/caps/fixedpoint/full19/timing/performance/ComputeCID/ResultCID qualification.'],
'operationalCalls':0,'actualThreadsFDsProcessesNativeNetworkAPICalls':0,'subjectEdits':0,'reviewerSource':pin(Path(__file__))}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(O/'report.json')))
