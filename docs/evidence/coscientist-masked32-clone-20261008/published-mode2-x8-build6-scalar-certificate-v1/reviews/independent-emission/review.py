from pathlib import Path
import json,hashlib,stat,importlib.util,struct,copy
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-fixture-saved-emission-certificate-v1-20261009-dense';R=Path(__file__).parent
h=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=h(b))
def ck(p,v):assert stat.S_ISREG(p.lstat().st_mode)and not p.is_symlink();b=p.read_bytes();assert len(b)==v['bytes']and h(b)==v['sha256'];return b
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());fr=json.loads((D/'freeze.json').read_bytes());saved=json.loads((D/'report.json').read_bytes())
for k,v in sp.items():ck(D/k,v)
for k,v in ip.items():ck(Path(k),v)
for v in fr.values():
 if isinstance(v,dict)and {'path','bytes','sha256'}<=set(v):ck(Path(v['path']),v)
spec=importlib.util.spec_from_file_location('inert_finite_fixture_word_model',D/'audit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);codes={};graphs={}
for side in ['off','on']:
 a=saved['savedArtifacts'][side];raw=ck(Path(a['native']['path']),a['native']);packed=ck(Path(a['container']['path']),a['container']);assert packed==b'KSEED1 236 1\nbench 208 1\n\n'+raw and a['export']==['bench',208,1]
 code=m.decoded(raw);assert code=={int(k):v for k,v in saved['decoded'][side].items()};codes[side]=code;graphs[side]=m.cfg(code);assert graphs[side]['reachableWords']==56
 assert graphs[side]=={**saved['CFG'][side],'edges':{int(k):v for k,v in saved['CFG'][side]['edges'].items()}}
 # Independent immediate target decoding from actual u32words.
 for i,(word,)in enumerate(struct.iter_unpack('<I',raw)):
  pc=i*4;op=code[pc]['op']
  if op in ['b','bl']:
   v=word&0x3ffffff;d=(v-(1<<26)if v&(1<<25)else v)*4;assert code[pc]['target']==pc+d
  elif op in ['bne','bhs']:
   v=(word>>5)&0x7ffff;d=(v-(1<<19)if v&(1<<18)else v)*4;assert code[pc]['target']==pc+d and word&15==(1 if op=='bne' else 2)
assert [p for p in codes['off']if codes['off'][p]!=codes['on'][p]]==saved['changedOffsets']==[208,212,224]and all(codes['off'][p]==codes['on'][p]for p in range(208)if p%4==0)
traces=[]
for n in range(5):
 for fuel in list(range(11))+[2**64-1]:
  a=m.execute(codes['off'],n,fuel);b=m.execute(codes['on'],n,fuel);assert a==b and a['status']==('return'if fuel>=n+2 else'fuel-trap0')and a['fuel']==max(0,fuel-(n+2))
  if a['status']=='return':assert a['result']==17
  traces.append(dict(n=n,fuel=fuel,status=a['status'],pc=a.get('pc'),steps=a['steps']))
assert traces==saved['pureModeledCases']and len(traces)==60
negative=[]
for name,mutation in [('unknown-x8-writer',lambda c:c.update({64:m.decode(0xd2800008,64)})),('unknown-target',lambda c:c[228].update(target=240)),('wrong-context-restore',lambda c:c.update({68:m.decode(0xf94003e7,68)})),('skipped-published-fuel',lambda c:c[224].update(op='mov9,17')),('missing-x8-initialization',lambda c:c[208].update(op='mov9,17'))]:
 try:
  c=copy.deepcopy(codes['on']);mutation(c);m.cfg(c);assert m.execute(c,2,6)==m.execute(codes['off'],2,6)
 except AssertionError:negative.append(name)
 else:raise AssertionError('mutantaccepted')
assert negative==saved['refusedMutants']
for k in ['actualNativeGuestExecuted','actualMachineModelIsProductionProof','helperPublishedX8Observed','privateFFCodePlus1Exercised','full19CertificateQualified','generalCandidateAdoptionQualified']:assert saved[k]is False
r={'status':'PASS_INDEPENDENT_SAVED_FIXTURE_ONLY_CFG_FINITE_WORD_MODEL_STAGE_PATHS_HOLD','independent':True,'priorImplementationAuthorship':False,'sourcePins':rec(D/'source-pins.json'),'inputPins':rec(D/'input-pins.json'),'freeze':rec(D/'freeze.json'),'subjectReport':rec(D/'report.json'),'auditorSource':rec(D/'audit.py'),'sourceRegistry':{'files':len(sp),'logicalBytes':sum(v['bytes']for v in sp.values())},'inputRegistry':{'files':len(ip),'logicalBytes':sum(v['bytes']for v in ip.values())},'savedArtifacts':saved['savedArtifacts'],'wordsPerArtifact':59,'reachableCFGWords':56,'independentBranchImmediateChecks':True,'helpersBytes0Through207Unchanged':True,'changedOffsets':[208,212,224],'modeledCases':60,'negativeMutants':negative,'qualification':'Exact saved236Bfixture bench208 singlefuelcharge+terminalB; both framed returning helpers unchanged. Pure finite result/fuel/publication-write/PCtrace/context and modeledstackclosure parity under explicit validcontext/stack/noexternalfuelwrite premises.','limits':['Model comparison dictionary exposes result/fuel/writes/trace/context/steps, not entire register/flag/debug state; do not read exactstate label as general ABI equivalence. Initial registers are fixed model values.','CFG RET continuations are static overapprox76/180 plus distinguished originalouterX30; it is not an independent universalreturnownership proof.','Unknownwriter/contextrestore mutants can refuse at decoderwhitelist; they are refusalcontrols, not tested production CFG clobberdataflow.','Singledebitmode2bench only; multipledebitcache/privateFFCODE+1 entry and typedadmission path remain HOLD.','No nativeguest, actualfueltrap/17arena/runtimeobservations, generalcandidate/full19/fixedpoint/performance/adoption certification.','Framed helper code remains ordinarypublishedfuel and unchanged; this model does not authorize bareNOP epilogue/prologue alteration or narrowing x30/stacktrap/debug observables.'],'operations':{'nativeThreadFDPipeProcessGroupSetterNetworkCalls':0,'frozenSubjectWrites':0}}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
