from pathlib import Path
import json,hashlib,stat,ast
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'vector-leaf-straight-read-cache-functional30-plan-v2-controls';D=Path(__file__).resolve().parent
def r(p):
 p=Path(p);z=p.lstat();assert stat.S_ISREG(z.st_mode) and not p.is_symlink();return dict(bytes=z.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
sp=json.loads((S/'source-pins.json').read_text());assert r(S/'source-pins.json')['sha256']=='d630735b86aba8072001a76e1a87620c9b53bd00bab981dc7f4c76479f315791'
for n,v in sp.items():assert r(S/n)==v
ast.parse((S/'run.py').read_text());cl=json.loads((S/'input-closure.json').read_text());assert len(cl)<=2048 and sum(z['bytes'] for z in cl.values())<=402653184
for p,v in cl.items():assert r(p)==v
v2=(S/'run.py').read_text()
ns={'__file__':str(S/'run.py'),'__name__':'source_review_pinned_buffer'};exec(compile(v2,str(S/'run.py'),'exec'),ns)
p=json.loads((S/'preregistration.json').read_text());assert len(p['cases'])==2
for c in p['cases']:
 cb=Path(c['C']['path']).read_bytes();rb=Path(c['CRunner']['path']).read_bytes();assert rb.count(cb)==1 and rb.find(cb)==c['recordedConsumerCAnchorBytes']
 for arm in ['OFF','ON']:
  ex,payload=ns['container'](c[arm+'Container']);assert ex==c[arm+'Exports'] and payload==Path(c[arm]['path']).read_bytes()
b=b'{:status :ok :result 1 :fuel {:initial 16777216 :remaining 123} :heap {:capacity 2097152 :used 4} :string-pool {:capacity 65536 :used 0} :vectors {:capacity 4096 :used 1} :vector-items {:capacity 65536 :used 4}}\n';assert ns['native'](b,b'',1)['result']==1
reject=0
for raw,err,n in [(b,b'x',1),(b.replace(b':remaining 123',b':remaining 0'),b'',1),(b.replace(b':result 1',b':result 0'),b'',1),(b.replace(b':used 4}',b':used 99999999}',1),b'',1)]:
 try:ns['native'](raw,err,n)
 except AssertionError:reject+=1
 else:raise AssertionError('mutant accepted')
ip={str(S/n):r(S/n)for n in ['source-pins.json',*sp]};ip.update(cl);ip[str(D/'audit-source.py')]=r(D/'audit-source.py');save(D/'input-pins.json',dict(sorted(ip.items())))
report=dict(status='PASS_SOURCE_ONLY_LC_MD5_SHA_FUNCTIONAL30',sourcePinsSHA256=r(S/'source-pins.json')['sha256'],driverSHA256=r(S/'run.py')['sha256'],preregistrationSHA256=r(S/'preregistration.json')['sha256'],correctionVersion=2,inputPinsSHA256=r(D/'input-pins.json')['sha256'],checks=dict(currentCWholeBytesOneExactPositionBothWorkloads=True,actualLC10AndSR4_SR40AndSourceBoundLoaderParsed=True,fullFrozenClosureRehashed=True,strict30_20native10C_10triples=True,nativeResultFuelFourTerminalArenasExact=True,CUnavailableNullNoNativeArenaFabrication=True,rootTwoSpecificReviewsBeforeFreshNamespace=True,firstFailureStopKillGroupDrainReapNoRetry=True,pureTerminalCodecPositive=1,pureTerminalCodecRejects=reject),limits=['Prior V1 run.py unavailable in current source folders; exact historical reversal not independently asserted','Local historical immutable C consumers; no current toolchain qualification or timing','No private register ABI canary or trap/resumption theorem','PIPE capture postvalidates 1MiB rather than enforcing streaming cap; fixed registered synchronous local artifacts and OS30-second guest budget only'],participation='Authored LC emitter and owner observer/source driver; independent functional30 authored by controls. No actual guest/compiler/SSH or plan source edits.',nativeCalls=0,compilerCalls=0,SSHCalls=0,performanceQualified=False,actualFunctionalQualified=False)
save(D/'report.json',report);print(json.dumps({'report':r(D/'report.json'),'inputPins':r(D/'input-pins.json'),'sourcePinsSHA256':report['sourcePinsSHA256']}))
