"""Offline source assembly after an independently frozen actual40 receipt is supplied.
No native/compiler/SSH. Not a GO; SOURCE freeze and two reviews still required.
"""
from pathlib import Path
import json,hashlib,stat,sys,ast
D=Path(__file__).resolve().parent;W=D.parent;P=W/'vector-leaf-straight-read-cache-full19-selfbuild40-plan-v1-native-controls';A=P/'run-outputs'
def load(p):return json.loads(Path(p).read_bytes())
def r(p):
 p=Path(p);z=p.lstat();assert stat.S_ISREG(z.st_mode)and not p.is_symlink()and z.st_size<=402653184;return dict(bytes=z.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
assert len(sys.argv)==2,'exact frozen independent actual40 report path required';q=Path(sys.argv[1]);review=load(q);qip=q.parent/'input-pins.json';assert review['inputPinsSHA256']==r(qip)['sha256'];assert review['status']=='PASS_INDEPENDENT_ACTUAL_LC_FULL19_SELFBUILD40_IDENTITY_ONLY'and r(q)['sha256']=='5242a003dccdf9c19d1bba6f5b5047eddf1b985fbd251906419988b03c33a4c1'and r(qip)['sha256']=='80045053fbf68ef7a35e3c39504931a3fada311740e369e18d7653564b93e1a0','exact actual40 receipt';raw=load(A/'report.json');assert raw['status']=='COMPLETE_LC_ORIGINAL19_COMPILATION_G1_G2_G3_FIXEDPOINT_ONLY'and raw['closedLoaderCalls']==40 and len(raw['images'])==19 and len(raw['generations'])==3;assert load(A/'terminal.json')==dict(loaderCalls=40,allChildrenClosed=True,failure=False)
assert review['sourcePinsSHA256']=='535e27cbe60dfb3320d804ece7a23c7ed6b5b451083851c6a9dc5361c9e9f346'and review['counts']['closedLoaderCalls']==40 and review['counts']['originalWorkloads']==19 and review['G1G2G3WholeContainerAndNativeByteFixedpoint']is True and review['images']==raw['images']and review['generations']==raw['generations']
assert len({g['native']['sha256']for g in raw['generations']})==1 and len({g['container']['sha256']for g in raw['generations']})==1;g3=raw['generations'][2];assert g3['generation']==3 and g3['native']['bytes']==966824 and g3['native']['sha256']=='5f4f591a1eb3bb46d3042a3463805a5cfb0897b766ee2de4909088be3369e1af'
ip=load(P/'input-pins.json')
for p,z in load(qip).items():
 assert p not in ip or ip[p]=={k:z[k]for k in ['bytes','sha256']};ip[p]={k:z[k]for k in ['bytes','sha256']}
for p in [q,qip,*[P/n for n in ['source-pins.json','run.py','preregistration.json','input-pins.json','source-report.json']],*[p for p in A.iterdir()if p.is_file()]]:ip[str(p)]=r(p)
for image in raw['images']:
 for k in ['container','native']:
  z=image[k];assert r(z['path'])=={k:z[k]for k in ['bytes','sha256']};ip[z['path']]={k:z[k]for k in ['bytes','sha256']}
assert len(ip)<=2048 and sum(v['bytes']for v in ip.values())<=402653184,'HOLD rather than prune closure or increase cap';save(D/'input-pins.json',dict(sorted(ip.items())))
pr=load(P/'preregistration.json');pr.update(status='PROSPECTIVE_SOURCE_ONLY_G3_ORIGINAL19_COMPILE38_REGISTERED_BEFORE_DRIVER_ASSEMBLY',schema='LC_G3_ORIGINAL19_COMPILE38/v1',producer=g3['native']['path'],producerSHA256=g3['native']['sha256'],actual40Proof=str(q),actual40ProofStatus=review['status'],actual40AcceptedReport=review,actual40InputPins=str(qip),actual40RawReport=str(A/'report.json'),actual40RawTerminal=str(A/'terminal.json'),maximumLoaderCalls=38,remainingWorkloadCalls=38,retainedOrdinaryWorkloadCalls=0,joinedOriginal19CompileExtractCalls=38,selfbuildCalls=0,generationNames=['auditedG3'],equalityRequired=['eachG3wholeContainer=eachG0wholeContainer before extract','eachG3wholeNative=eachG0wholeNative; exports+offset+arity exact'],stageOrder=['canonical original19 compile/extract38'],freshOutputRoot=str(D/'run-outputs'),rootGOStatus='ROOT_AUTHORIZED_LC_G3_ORIGINAL19_COMPILE38_ONLY',sourceReviewStatus='PASS_SOURCE_ONLY_LC_G3_ORIGINAL19_COMPILE38',inputPinsSHA256=r(D/'input-pins.json')['sha256'],exactInputFiles=len(ip),exactInputLogicalBytes=sum(v['bytes']for v in ip.values()),maximumChildWallAndReapSeconds=38*1840,maximumOutputDiskBytes=2147483648,callLedgerOrigin=dict(path=str(P/'run.py'),**r(P/'run.py')),qualification='Latest fixedpoint compiler correspondence with already accepted G0 original19 images; no workload guests/traps/fuel/ABI/performance/official score/selfhost100% qualification')
for k in ['G0ToG1','actualProducerProof','actualProducerProofStatus']:pr.pop(k,None)
for e in pr['entries']:
 e.pop('retained',None);e['baseline']=next(z for z in raw['images']if z['workload']==e['workload'])
save(D/'preregistration.json',pr) # Written before concrete driver authoring.
s=(P/'run.py').read_text();s=s.replace('Exactly10 compile/extract children','Exactly38 compile/extract children').replace("g['maximumLoaderCalls']==40","g['maximumLoaderCalls']==38").replace("'exact40 GO'","'exact38 GO'").replace("len(rows)<40","len(rows)<38").replace("'finite40 no retry'","'finite38 no retry'")
s=s.replace("pr['producerSHA256']=='258670d2371f3c03167fb02f574c6597479a1ce3e0af9a42cac8e41499d56931'", "pr['producerSHA256']=='5f4f591a1eb3bb46d3042a3463805a5cfb0897b766ee2de4909088be3369e1af'")
s=s.replace("['actualProducerProof','actualLoaderProof','actualOwnerProof']","['actual40Proof','actualLoaderProof','actualOwnerProof']")
old="  ar=load(pr['actualProducerProof']);need(ar['counts']['closedLoaderCalls']==4 and next(z for z in ar['images']if z['arm']=='ON')['native']==dict(path=pr['producer'],**ip[pr['producer']]),'producer actual correspondence')"
new="""  ar=load(pr['actual40Proof']);need(ar==pr['actual40AcceptedReport']and ar['inputPinsSHA256']==receipt(pr['actual40InputPins'])['sha256'],'entire exact independent actual40 receipt')
  rr=load(pr['actual40RawReport']);need(rr['status']=='COMPLETE_LC_ORIGINAL19_COMPILATION_G1_G2_G3_FIXEDPOINT_ONLY'and rr['closedLoaderCalls']==40 and rr['sourcePinsSHA256']=='535e27cbe60dfb3320d804ece7a23c7ed6b5b451083851c6a9dc5361c9e9f346'and len(rr['images'])==19 and len(rr['generations'])==3 and load(pr['actual40RawTerminal'])==dict(loaderCalls=40,allChildrenClosed=True,failure=False),'actual40 raw join')
  need(rr['generations'][2]['generation']==3 and rr['generations'][2]['native']==dict(path=pr['producer'],**ip[pr['producer']])and rr['generations'][2]['native']['bytes']==966824,'exact G3 producer')
  need(len({q['native']['sha256']for q in rr['generations']})==1 and len({q['container']['sha256']for q in rr['generations']})==1,'three generation identity')
  need(all(q['exports']==[['main',0,0]]and q['offset']==0 for q in rr['generations']),'audited sole main0 producers')"""
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace("  need([e['workload']for e in pr['entries']if 'retained'in e]==['md5sum','nettle-sha256'],'exact retained complement')", "  need(all('retained'not in e for e in pr['entries'])and [e['baseline']['workload']for e in pr['entries']]==[q['workload']for q in rr['images']],'all19 fresh exact accepted G0 mapping')\n  for e,z in zip(pr['entries'],rr['images']):need(e['baseline']==z,'entire baseline receipt from accepted40')")
start=s.index('\n try:\n  def build');s=s[:start]+'''
 try:
  for e in pr['entries']:
   label=e['workload'];old=e['baseline'];src=O/(label+'.kotoba');src.write_bytes(Path(e['source']['path']).read_bytes());src.chmod(0o444);need(receipt(src)=={k:e['source'][k]for k in ['bytes','sha256']},'unchanged original source');capture(src,4194304)
   k=O/(label+'.kseed');b=O/(label+'.bin');raw=call(label+'-compile',['compile',str(src),'--target','aarch64-macos','--output',str(k)]);need(b':ok true'in raw and b':ok false'not in raw,'compile success');kr=capture(k,pr['containerBytesMaximum']);payload,exports=parse_container(k.read_bytes());need(k.read_bytes()==Path(old['container']['path']).read_bytes(),'STOP_G3_G0_WHOLE_CONTAINER_MISMATCH_BEFORE_EXTRACT');entry=[z for z in exports if z[0]==e['symbol']];need(len(entry)==1 and entry[0][2]==1 and entry[0][1]==old['offset']and [list(z)for z in exports]==old['exports'],'exact old export names/arity/offset')
   raw2=call(label+'-extract',['extract-native',str(k),'--symbol',e['symbol'],'--output',str(b)]);br=capture(b,pr['nativeBytesMaximum']);need(b':ok true'in raw2 and b':ok false'not in raw2 and re.findall(rb':offset ([0-9]+)\\b',raw2)==[str(old['offset']).encode()],'extract offset');need(b.read_bytes()==payload==Path(old['native']['path']).read_bytes(),'whole native payload G0 equality');images.append(dict(workload=label,container=kr,native=br,exports=exports,offset=old['offset'],wholeG0ContainerNativeEqual=True,baseline=old));save(O/'images.json',images)
  guard();need(len(rows)==38 and len(images)==19,'exact38/19');save(O/'report.json',dict(status='COMPLETE_LC_G3_ORIGINAL19_COMPILE_EXTRACT38_WHOLE_G0_IDENTITY_ONLY',closedLoaderCalls=38,compileCalls=19,extractCalls=19,producer=dict(path=pr['producer'],**ip[pr['producer']]),images=images,sourcePinsSHA256=g['sourcePinsSHA256'],rootGOSHA256=gh['sha256'],wholeOriginal19G3G0ContainerNativeExportOffsetEqual=True,workloadGuestExecution=False,timingQualified=False,officialScore=False,fullSelfhostGoalAchieved=False));ok=True
 except BaseException as ex:save(O/'failure.json',dict(error=type(ex).__name__+': '+str(ex),loaderCalls=len(rows),completedImages=len(images),firstFailureStop=True,noRetry=True));raise
 finally:save(O/'terminal.json',dict(loaderCalls=len(rows),allChildrenClosed=all(r['state']=='terminal'for r in rows),failure=not ok))
if __name__=='__main__':need(len(sys.argv)==2,'root GO only');main(sys.argv[1])
'''
ast.parse(s);(D/'run.py').write_text(s);print(json.dumps(dict(inputFiles=len(ip),logicalBytes=sum(z['bytes']for z in ip.values()),driver=r(D/'run.py'),prereg=r(D/'preregistration.json'))))
