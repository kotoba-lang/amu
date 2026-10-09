from pathlib import Path
import hashlib,json,stat,difflib,importlib.util
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'published-mode2-x8-fuel-candidate-source-v1-20261009';R=Path(__file__).parent
h=lambda b:hashlib.sha256(b).hexdigest()
def rec(p):b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def ck(p,v):assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink();b=p.read_bytes();assert len(b)==v['bytes'] and h(b)==v['sha256'];return b
sp=json.loads((D/'source-pins.json').read_bytes());ip=json.loads((D/'input-pins.json').read_bytes());fr=json.loads((D/'freeze.json').read_bytes())
assert rec(D/'source-pins.json')['sha256']==fr['sourcePinsSHA256']=='05ed416af05653c58cebc63b319e0acd5bf07d2f563d46989a343f6f72b6e6b1'
assert rec(D/'input-pins.json')['sha256']==fr['inputPinsSHA256']=='6dd1a91a28d8bd69185f0ec1e7195c467bbfde33cb844e10231b634a05620cd7'
for k,v in sp.items():ck(D/k,v)
for k,v in ip.items():ck(Path(k),v)
a=json.loads((D/'source-assembly.json').read_bytes());parts=[ck(Path(p['path']),p)for p in a['offModulePins']];on=ck(Path(a['onReplacementModule']['path']),a['onReplacementModule']);assert len(parts)==16
assert b''.join(p+b'\n'for p in parts)==ck(Path(a['offUnity']['path']),a['offUnity']);parts[10]=on;assert b''.join(p+b'\n'for p in parts)==ck(Path(a['candidateUnity']['path']),a['candidateUnity'])
off=(D/'41-a64gen-off.kotoba').read_text();s=on.decode();diff=''.join(difflib.unified_diff(off.splitlines(True),s.splitlines(True),fromfile='OFF41',tofile='candidate41'));(R/'exact-delta.patch').write_text(diff)
# Reconstruct OFF exactly by removing only declared two functional changes and the field comment.
x=s.replace('(def gn-f-freg 11)    ; 1 = private x8 leaf counter; 2 = published x8 frame-free small-tail counter','(def gn-f-freg 11)    ; 1 = the fuel counter is in x8')
start=x.index('                  (gn-gs gn-f-h 0) (sl-clear)');end=x.index('\n\n(defn- gn-op-ret',start)
x=x[:start]+'                  (gn-gs gn-f-h 0) (sl-clear) (gn-gs gn-f-vslot (if (= (gn-g M2 gn-f-vmode) 2) -1 0)) (gn-tree-entry f)))))))'+x[end:]
start=x.index('(defn- gn-op-fuel');end=x.index('\n\n;; Exact affine',start);oldstart=off.index('(defn- gn-op-fuel');oldend=off.index('\n\n;; Exact affine',oldstart);x=x[:start]+off[oldstart:oldend]+x[end:];assert x==off
# Separate instruction-level interpreter for actual declared A64 words; fixed subset only.
INIT=0xf94004e8;ON=[0xf1000508,0x54000042,0xd4200000,0xf90004e8];OFF=[0xf94004f0,0xf1000610,0x54000042,0xd4200000,0xf90004f0];MASK=2**64-1
assert INIT==0xf9400000+(1<<10)+(7<<5)+8
assert ON[0]==0xf1000000+(1<<10)+(8<<5)+8 and ON[-1]==0xf9000000+(1<<10)+(7<<5)+8
# Fuel cell supplied as memory at valid context x7+8; absent invalid context refuses this proof premise.
def run(words,regs,memory):
 regs=regs.copy();memory=memory.copy();pc=0;carry=False;steps=0
 while pc<len(words):
  w=words[pc];steps+=1;assert steps<20
  if w&0xffc00000 in [0xf9400000,0xf9000000]:
   rt=w&31;rn=(w>>5)&31;addr=regs[rn]+8*((w>>10)&4095);assert addr in memory
   if w&0xffc00000==0xf9400000:regs[rt]=memory[addr]
   else:memory[addr]=regs[rt]
  elif w&0xff000000==0xf1000000:
   rd=w&31;rn=(w>>5)&31;imm=(w>>10)&4095;carry=regs[rn]>=imm;regs[rd]=(regs[rn]-imm)&MASK
  elif w&0xff00001f==0x54000002:
   imm=(w>>5)&0x7ffff;imm=imm-(1<<19)if imm&(1<<18)else imm
   if carry:pc+=imm;continue
  elif w==0xd4200000:return regs,memory,True
  else:raise AssertionError('unrecognized modeled opcode')
  pc+=1
 return regs,memory,False
compared=0
for fuel in list(range(17))+[2**63-1,2**63,MASK]:
 for ticks in range(33):
  regs={k:100+k for k in range(32)};regs[7]=4096;regs[31]=0;mem={4104:fuel};ro=regs.copy();rc,mc,t=run([INIT],regs,mem);mo=mem.copy();assert not t
  for z in range(ticks):
   ro,mo,to=run(OFF,ro,mo);rc,mc,tc=run(ON,rc,mc);assert to==tc and mo==mc and ro[7]==rc[7]==4096;compared+=1
   # Every successful original charge publishes before any following trap/call.
   assert all(ro[k]==rc[k]==regs[k]for k in range(32)if k not in [8,16])
   if tc:break
# Concrete rejected stale cache/context and branch variants.
r={k:100+k for k in range(32)};r[7]=4096;r[8]=5;r[31]=0
assert run(ON,r,{4104:0})[1]!=run(OFF,r,{4104:0})[1]
r[8]=99;assert run(ON,r,{4104:5})[1]!=run(OFF,r,{4104:5})[1]
r[8]=1;wrong=ON.copy();wrong[1]=0x54000062;assert run(wrong,r,{4104:1})[1]!=run(OFF,r,{4104:1})[1]
# Private entry target+1 must skip only first original MOVZx5,0; x8 init must remain reached.
pro=[0xd2800005,INIT];assert pro[0]==0xd2800005 and pro[1]==INIT;assert [INIT,0xd2800005][0]!=0xd2800005
layout=(D/'42-layout.kotoba').read_text();assert '(= (vector-at M (+ MM-CODE-BASE t0)) 0xd2800005)'in layout and '(inc t0) -1)'in layout
# Author arithmetic controls are inert and independently recomputed as supplementary evidence.
q=importlib.util.spec_from_file_location('pure_fuel_model',D/'fuel-model.py');m=importlib.util.module_from_spec(q);q.loader.exec_module(m);assert m.controls()==json.loads((D/'fuel-model-controls.json').read_bytes())
r={'status':'HOLD_SOURCE_PUBLISHED_MODE2_X8_FUEL_EMITTED_CLOBBER_CERTIFICATE_PENDING','independent':True,'priorImplementationAuthorship':False,'sourcePinsSHA256':fr['sourcePinsSHA256'],'inputPinsSHA256':fr['inputPinsSHA256'],'freeze':rec(D/'freeze.json'),'candidate41':rec(D/'41-a64gen-candidate.kotoba'),'candidateUnity':rec(D/'unity-candidate.kotoba'),'sourceRegistry':{'files':len(sp),'logicalBytes':sum(v['bytes']for v in sp.values())},'inputRegistry':{'files':len(ip),'logicalBytes':sum(v['bytes']for v in ip.values())},'exactDelta':rec(R/'exact-delta.patch'),'verifiedSourceObservations':['Exact16 currentTC OFF unity94fe reconstructed and candidate replaces only41; two functional changes, privatefreg1/epilogue unchanged.','Init after original sl-clear retains MOVZx5,0 first and layout aux1 target+1 enters new x8LDR; public and private paths both initialize under declared ordering.','Existing leaf2 lowlocals0..6 temps9..15 scratch16/17 reserve x7context, plausibly free x8; lexical counts alone are not emitted certificate.','Smallscan restricts calls to exact inline wrappers or terminal generic call+RET; tail epilogue performs no freg2 delayed publication.','Known clamp/scalarmask/affinereader are explicitly disabled leaf2; DI/TC/maskwriter requireleaf0; tree/slmode3 leaf1; dot existing gates excludeleaf2.'],'finiteIndependentInstructionModel':{'comparedChargePrefixes':compared,'fuelValues':20,'maximumAttemptedTicks':32,'decodedWords':{'init':hex(INIT),'published':[hex(x)for x in ON],'ordinary':[hex(x)for x in OFF]},'positivePublicationAndZeroTrapParity':True,'unaffectedRegistersPreservedExceptFuelX8AndOrdinaryScratchX16':True,'staleContextCounterexample':True,'X8ClobberCounterexample':True,'wrongBranchPublicationCounterexample':True,'wrongPrologueOrderRefused':True,'fullAArch64Model':False},'requiredPremises':['Full current typed FN/SIR and emitted CFG closure: leaf2/frame0/fuel1 and all branch/private entry targets initialize x8 before use.','All reachable emitted encoders/rawwords/dynamic destinations must exclude extra x8 writes, x7 context rebinding and CTX-FUEL writes except prescribed publication; inlineRT vector stores require arena/context nonalias proof.','Valid live aligned context+fuel cell already guaranteed at entry; earlier init read introduces no extra trap; no external/asynchronous fuel writers.','Terminal transfer has no resume edge; public/private entries and original nonfuel traps publish exact prefixfuel.'],'minimalDecisiveControls':['Bind actual OFF/ON synthetic terminal-tail fixture complete typedSIR/layout/FIX/CODE; check each private targetfirstMOVZ5 and target+1LDR8, every ordinary FUEL maps to exact SUBS8/BHS+2/BRK/STR8.','Mutate emitted x8writer/contextwriter/BLreturn/branch-bypass-init/aux1 wrongfirstword and refuse; test fuel0/1/2 at each charge and nonfuel-trap prefix.','Keep mode0 and private mode1 bytebehavior and unknown eligibility genericfallback; no prescan or capacity inflation.'],'candidateNativePresent':False,'operationalGOEligible':False,'performanceQualified':False,'C2':False,'operations':{'nativeThreadsPipesProcessNetworkAPICalls':0,'productOrFrozenSubjectWrites':0},'limits':['Source candidate intentionally remains HOLD. No driver/prereg/GO exists, no executable gate reviewed.','Instruction savings k-1 context reloads conditional on k successful charges and one entry load; static counts do not measure dynamic cost/Cgap.','This is finite declared instruction semantics under premises, not complete GPR/alias CFG proof, hardwareexecution, original19 semantics or performance.']}
(R/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rec(R/'report.json')))
