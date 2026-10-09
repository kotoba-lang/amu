from pathlib import Path
import ast,json
W=Path('/Users/junkawasaki/github/workspaces/codex');B=W/'published-mode2-x8-statemate-vector-runtime12-source-v1-20261009';D=Path(__file__).resolve().parent
names=['capture.py','controller.py','integration.py','runtime.py','typed-adapter.py','artifact_admission.py','callback_contract.py','loader_grammar.py','native-call.py']
for n in names:(D/n).write_bytes((B/n).read_bytes())
s=(B/'launch-wrapper.py').read_text();assert s.count("go['maximumLoaderCalls']==12")==1;(D/'launch-wrapper.py').write_text(s.replace("go['maximumLoaderCalls']==12","go['maximumLoaderCalls']==190"))
s=(B/'run.py').read_text();start=s.index('def source_scope(pr):');end=s.index('\ndef go_header',start)
new='''def source_scope(pr):
 loader_protocol(pr)
 off=load(pin(pr['OFFActualProof']['path'],pr['OFFActualProof']));actual=load(pin(pr['G4Original19ActualProof']['path'],pr['G4Original19ActualProof']));fp=load(pin(pr['FixedpointActualProof']['path'],pr['FixedpointActualProof']));oracle=load(pin(pr['C95Oracle']['path'],pr['C95Oracle']))
 need(off['status']==pr['OFFActualProofStatus']and off['currentBaselineNative']['sha256']=='761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93'and off['current16BaselineSource']['sha256']=='953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418','current OFF lineage')
 need(actual['status']==pr['G4Original19ActualProofStatus'],'independent saved current G4 original19 artifact proof')
 completion=load(pin(pr['G4Original19Completion']['path'],pr['G4Original19Completion']));need(actual['completion']==pr['G4Original19Completion'],'exact independently checked compile38 completion')
 need(fp['status']==pr['FixedpointActualProofStatus']and fp['G2G3G4WholeNativeEqual']is True and fp['G2G3G4WholeContainerEqual']is True,'exact ownfixedpoint')
 g4=pr['G4Producer'];need(g4['native']['sha256']=='6b410b003a428a40098bdd330539ccf3fef5fdd6d8e9bad23758f941b347462d'and g4['container']['sha256']=='3ebef5afb6b2b7cd826499722dbbbc250c8e71ed54afc893f5124ee8d6f952da','G4 fixedpoint hashes')
 payload,exports=container(pin(g4['container']['path'],g4['container']).read_bytes());need(payload==pin(g4['native']['path'],g4['native']).read_bytes()and exports==[('main',0,0)],'whole G4 producer main0')
 need(completion['producer']==g4['native']and completion['producerContainer']==g4['container']and completion['closedCompilerCalls']==38 and completion['images']==pr['imagesON'],'all19 assembled with exact current G4')
 matrix=load(pin(pr['canonicalMatrix']['path'],pr['canonicalMatrix']));need(matrix['upstreamCommit']=='09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'and len(matrix['entries'])==len(pr['entries'])==len(pr['imagesON'])==19,'original19 matrix')
 need(pr['imagesOFF']==off['joinedOriginal19Images'],'actual current OFF full19 identity');need(oracle['status']==pr['C95OracleStatus']and len(oracle['rows'])==95,'saved result-only C oracle')
 expected=[]
 from loader_grammar import interpretation
 for entry,mat in zip(pr['entries'],matrix['entries']):
  need(entry['workload']==mat['workload']and entry['source']['sha256']==mat['expectedSourceSha256']and entry['source']['path'].endswith('/'+mat['source'])and entry['symbol']==mat['symbol']and entry['iterations']==mat['iterations'],'unchanged original source/symbol/profiles')
  work=entry['workload'];ims={arm:next(x for x in pr['images'+arm]if x['workload']==work)for arm in ['OFF','ON']}
  for arm,im in ims.items():
   need(im['source']==entry['source']and im['iterations']==entry['iterations'],'image owner current source/profiles');payload,exports=container(pin(im['container']['path'],im['container']).read_bytes());need(payload==pin(im['native']['path'],im['native']).read_bytes()and (entry['symbol'],im['offset'],1)in exports,'own full image/export')
  for n in entry['iterations']:
   answers=[r for r in oracle['rows']if r['workload']==work and r['n']==n];need(len(answers)==1 and answers[0]['sourceSHA256']==entry['source']['sha256']and answers[0]['symbol']==entry['symbol'],'source-bound saved C result only');answer=answers[0]['result']
   for arm in ['OFF','ON']:
    c=pr['cases'][len(expected)];im=ims[arm];need(c==dict(label=work+'-'+arm+'-n'+str(n),workload=work,arm=arm,profile=n,symbol=entry['symbol'],offset=im['offset'],arity=1,native=im['native'],container=im['container'],source=entry['source'],expectedResult=answer,nativeArgv=[pr['loader'],im['native']['path'],str(im['offset']),'1','aarch64','-',str(n)]),'exact190 original case order')
    need(interpretation(c['nativeArgv'])==dict(typedI64=[n],guestArgv=None,effectiveArgc=7),'typed runtime no separator');expected.append(c)
 need(len(expected)==len(pr['cases'])==pr['maximumLoaderCalls']==190 and pr['guestFuelPerCall']==16777216,'190 original runtime calls/fuel')
 need(pr['guestArenaCaps']=={'pairs':2097152,'string-pool-bytes':65536,'vectors':4096,'vector-items':65536}and pr['environment']=={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':pr['freshOutputRoot'],'LANG':'C','LC_ALL':'C','TZ':'UTC','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_PAIRS':'2097152','KEXE_VECTOR_ITEMS':'65536','KEXE_CPU_SECONDS':'30','KEXE_WALL_SECONDS':'30','KEXE_FUEL':'16777216','KEXE_ARENA_USE':'1','PYTHONNOUSERSITE':'1','KEXE_STRUCTURED_REPORT':'1','KEXE_RESULT_TYPE':'i64'},'unchanged all17 env/caps')
 need(pr['operationalEnvironment']=={'version':'host-authorized-loader-owned-sandbox-v1','requiresOuterHostEscalation':True,'loaderOwnedSandboxRequired':True,'loaderSandboxWeakeningAuthorized':False,'hostEscalationDeclarationIsNotKernelMeasurement':True}and pr['C2']is False and pr['timingAuthorized']is False and pr['generalCandidateAdoptionQualified']is False and pr['fullClobberCertificateQualified']is False and pr['actualTypedMode2AdmissionObserved']is False,'diagnostic only/general HOLD')
 return True
'''
s=s[:start]+new+s[end:];s=s.replace("'CandidateCompilerActualProof'","'G4Original19ActualProof'").replace("'EmittedAssociationProof'","'FixedpointActualProof'")
s=s.replace("g['maximumLoaderCalls']==12","g['maximumLoaderCalls']==190").replace('time.monotonic()+820','time.monotonic()+12000').replace('len(rows)==len(results)==12','len(rows)==len(results)==190')
a=s.index("save(O/'report.json',");b=s.index("\nif __name__",a)
s=s[:a]+'''save(O/'report.json',{'status':'COMPLETE_CURRENT_G4_X8_ORIGINAL19_RUNTIME190_DIAGNOSTIC_ONLY','runtimeCalls':190,'originalWorkloads':19,'pairedProfiles':95,'results':results,'rootGO':dict(path=str(gp),**gr),'sourcePinsSHA256':g['sourcePinsSHA256'],'evidence':evidence,'G4Original19ActualProof':g['G4Original19ActualProof'],'FixedpointActualProof':g['FixedpointActualProof'],'C95Oracle':g['C95Oracle'],'C95FuelArenaAvailable':False,'C95FuelArena':None,'full19FunctionalAdmissionPassed':True,'generalCandidateAdoptionQualified':False,'fullClobberCertificateQualified':False,'actualTypedMode2AdmissionObserved':False,'performanceQualified':False,'hardPeakQualified':False,'strictPhysicalMemoryQualified':False,'all190StrictSampledPolicyPassed':all(r['strictOldMemoryPolicyPassed']for r in results),'C2':False})'''+s[b:]
s=s.replace('Published x8 statemate/vector runtime12','Current G4 x8 original19 runtime190').replace("'12 new closed runtime children'","'190 new closed runtime children'").replace("'exact runtime12 only under declared host profile'","'exact runtime190 only under declared host profile'")
(D/'run.py').write_text(s)
for f in D.glob('*.py'):ast.parse(f.read_text())
(D/'prospective.json').write_text(json.dumps(dict(status='UNFROZEN_PROSPECTIVE_RUNTIME190_AWAIT_CURRENT38_ACTUAL_ARTIFACT_PROOF',maximumCalls=190,sourcePinsFrozen=False,GOProvided=False,nativeCalls=0,copiedComponents=names,wrapperOnlyCounterChanged=True,resourcePerChildUnchanged=True,C2=False),indent=2)+'\n')
print('prepared unsealed driver; proof schema must be adapted to exact actual report before freeze')
