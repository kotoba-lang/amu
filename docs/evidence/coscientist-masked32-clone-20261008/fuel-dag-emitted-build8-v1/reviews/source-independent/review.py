from pathlib import Path
import sys,json,hashlib,ast
sys.dont_write_bytecode=True
W=Path('/Users/junkawasaki/github/workspaces/codex');D=W/'vector-fuel-scalar-dag-emitted18-source-v1-width';O=Path(__file__).resolve().parent;ip={}
def j(p):return json.loads(p.read_text())
def pin(p,v=None):
 p=Path(p);assert p.is_file()and not p.is_symlink()and p.stat().st_size<=402653184;h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 z={'bytes':p.stat().st_size,'sha256':h.hexdigest()}
 if v is not None:assert z=={k:v[k]for k in ['bytes','sha256']},str(p)
 ip[str(p)]=z;return z
sp=pin(D/'source-pins.json');assert sp['sha256']=='4b289f6f678dbef35112a8a9d9ed98ef975a10c4e7150fccdc6deb9c8ada66b9'
for n,v in j(D/'source-pins.json').items():pin(D/n,v)
orig=j(D/'input-pins.json');assert len(orig)==1738 and sum(v['bytes']for v in orig.values())==369725436
for p,v in orig.items():pin(p,v)
bp=j(D/'build-preregistration.json');gp=j(D/'guest-preregistration.json');pr=j(D/'preregistration.json');build=(D/'build8.py').read_text();guest=(D/'guest10.py').read_text()
assert bp['maximumLoaderCalls']==8 and gp['maximumLoaderCalls']==10 and pr['maximumLoaderCalls']==18
assert bp['workloadGuestAuthorized']is False and gp['workloadGuestAuthorized']is True and bp['rootGOStatus']!=gp['rootGOStatus']
for k in ['actualProducerProof','actualLoaderProof']:assert j(Path(bp[k]))['status']==bp[k+'Status']
assert pr['positiveGuestBudgets']==[1,2,3]and pr['negativeGuestBudgets']==[2,3]
assert "[('positive',[1,2,3],7),('negative',[2,3],-1)]"in guest and "callenv.pop('KEXE_COMMAND')"in guest and "'aarch64','-'"in guest
assert "q['actualLoaderCalls']==18"in guest and "q['savedCase0V3Accepted']is True"in guest and "q['remainingCases']==list(range(1,16))"in guest
assert "q['actualBuildCalls']==8"in guest and "q['positiveQualifiedSiteCount']==1"in guest and "q['negativeWholeIdentity']is True"in guest
assert "fp=={'benchEntryUnits':1,'outerUnits':1,'additionalDynamicCharges':0,'privateContextX7Preserved':True,'fuelInteriorIngress':False,'directBenchABI':True}"in guest
assert 'exec(compile(parser_bytes' in guest and "H(parser_bytes)==sp['guest-check.py']['sha256']"in guest and 'import validate'not in guest and 'import guest'not in guest
for p in ['build8.py','guest10.py','guest-check.py','source-controls.py']:ast.parse((D/p).read_text())
s=(D/'source-controls.py').read_text();cut=s.index("(D/'pure-controls.json').write_text");ns={'__file__':str(D/'source-controls.py'),'__name__':'offline_pure_review'};exec(compile(s[:cut],str(D/'source-controls.py'),'exec'),ns)
# Exact selected body and mathematical unsigned-mask oracle; no inserted helper or fixture bypass.
pos=(D/'positive.kotoba').read_text();neg=(D/'negative.kotoba').read_text();assert '(defn bench [n :i64] :i64 (+ (mix n 7) n))'in pos and '(defn bench [n :i64] :i64 (mix n 7))'in neg
assert (((7<<1)^7)&0xffffffff)+7==16 and (((-1<<1)^7)&0xffffffff)==4294967289
# Source pin and proof binding checks stop before any guest; future root receipts remain unknown/pending.
r={'status':'PASS_SOURCE_ONLY_FUEL_DAG_EMITTED18_PARTITION','driverSourcePinsSHA256':sp['sha256'],'driverSHA256':pin(D/'build8.py')['sha256'],'buildDriverSHA256':pin(D/'build8.py')['sha256'],'guestDriverSHA256':pin(D/'guest10.py')['sha256'],'preregistrationSHA256':pin(D/'build-preregistration.json')['sha256'],'guestPreregistrationSHA256':pin(D/'guest-preregistration.json')['sha256'],'maximumBuildCalls':8,'maximumGuestCalls':10,'maximumCombinedCalls':18,'fullInputFiles':1738,'fullInputLogicalBytes':369725436,'separateGOStages':True,'pinnedSourceBufferGuestParser':True,'positiveInitialFuel':[1,2,3],'negativeInitialFuel':[2,3],'initialZeroNeverRequested':True,'strictResultFuelTrapFourArenaOracle':True,'negativeWholeKSEEDNativeIdentityRequired':True,'actualComponent18AndActualMachine8MandatoryBeforeGuest':True,'actualMachineFuelRequirements':{'benchEntryUnits':1,'outerUnits':1,'additionalDynamicCharges':0,'privateContextX7Preserved':True,'fuelInteriorIngress':False,'directBenchABI':True},'pureSyntheticAccepted':5,'pureReceiptRejects':8,'pureContainerRejects':3,'scope':'SOURCE acceptance of build8 only and conditional guest10 gate. This is not actual machine proof or guest GO. Machine receipt must independently establish exact owned compiled path, context/entry/outer charges and no interior ingress/additional dynamic charge before root authorizes guests.','actualCompiledFuelOrderingQualified':False,'actualComponent18Accepted':False,'actualMachine8Accepted':False,'actualGuestExecutionQualified':False,'actualNonresumingTrapQualified':False,'performanceQualified':False,'full19Qualified':False,'nativeCompilerSSHCallsByReviewer':0,'participation':'Reviewed parent fuel component and earlier LC source/diagnostics; width authored this emitted fixture/driver/parser. Saved SOURCE inspection and pure controls only.','limitations':['Only signed n7/-1 finite cases; no universal integer or resource equivalence theorem.','Negative tail whole identity is prospective experiment guard until artifacts exist.','Runtime input closure/actual machine acceptance unavailable now; guest admission must remain false.','Root must parse specific actual acceptance receipts; no caller booleans can substitute instruction evidence.']}
for n,z in [('report.json',r),('input-pins.json',ip)]:(O/n).write_text(json.dumps(z,indent=2)+'\n')
(O/'source-pins.json').write_text(json.dumps({p.name:pin(p)for p in sorted(O.iterdir())if p.is_file()and p.name!='source-pins.json'},indent=2)+'\n');print(json.dumps({'report':pin(O/'report.json'),'inputPins':pin(O/'input-pins.json')}))
