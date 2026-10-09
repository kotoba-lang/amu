"""One-off diagnostic SOURCE authoring only. No native, network or product edits."""
from pathlib import Path
import json,hashlib,ast
D=Path(__file__).resolve().parent;W=D.parent
A=W/'crc-table-decision-collapse-original-crc-guest8-source-draft-v1-20261008'
X=W/'crc-table-decision-collapse-tc-remaining-extract1-source-v2-20261009'
def load(p):return json.loads(Path(p).read_bytes())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def pin(p):
 p=Path(p);assert p.is_file() and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
pr=load(A/'preregistration-draft.json')
ep=pin(W/'crc-table-decision-collapse-tc-saved-emission-actual-review-independent-20261008/report.json')
xp=pin(W/'crc-table-decision-collapse-tc-remaining-extract1-v2-actual-review-independent-20261009/report.json')
x=load(xp['path']);ec=x['completion']
pr.update(status='SOURCE_FROZEN_CURRENT_ORIGINAL_TC_GUEST8_READY',actualEmissionProof=ep,acceptedEmissionProofStatus='PASS_INDEPENDENT_SAVED_RAW_TC_EMISSION_REPAIR_ONLY',actualExtractionProof=xp,acceptedExtractionProofStatus=x['status'],actualExtractionCompletion=ec,onArtifact=x['extractedNative'],onContainer=x['savedContainer'],oldBuild8FailureProof=pin(W/'crc-table-decision-collapse-tc-emitted-build8-saved-failure-review-independent-20261008/report.json'),freshOutputRoot=str(D/'run-outputs'),currentEmitterQualified=True)
for k in ['actualEmissionCompletion','prospectiveOnArtifactPath','prospectiveOnContainerPath','prospectiveEmissionCompletionPath','compilerFuel']:pr.pop(k,None)
pr['environment']['TMPDIR']=pr['freshOutputRoot']
pr['maxProcessStartsAccounting']='8 Python wrappers exec8 loader images, each loader forks at most1 native guest child:16 distinct starts across8 groups, max2 members/group. Zero compiler calls.'
pr['ownershipUncertaintyLimitations']=pr['ownershipUncertaintyLimitations'].replace('Native compiler child','Native guest child')
pr['gateScope']='eight ordered adjacent OFF/ON guest calls, four pairs; no compiler/extraction calls'
pr['zeroCapabilityGrants']=True;pr['C2Enabled']=False
# Read complete container metadata independently for both arms; bind own offsets.
import re
def container(p):
 b=Path(p).read_bytes();m=re.match(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)\n',b);assert m
 e=b.index(b'\n\n',m.end());rows=[r.split(b' ') for r in b[m.end():e].splitlines()];assert len(rows)==int(m[2]);payload=b[e+2:];assert len(payload)==int(m[1]);return payload,[(r[0].decode(),int(r[1]),int(r[2]))for r in rows]
exports={}
for arm in ['OFF','ON']:
 prefix=arm.lower();payload,rows=container(pr[prefix+'Container']['path']);assert payload==Path(pr[prefix+'Artifact']['path']).read_bytes();exports[arm]=rows
for c in pr['cases']:
 hits=[(o,a)for s,o,a in exports[c['arm']]if s==c['symbol']];assert len(hits)==1 and hits[0][1]==1
 c['offset']=hits[0][0];c['nativeArgv']=[pr['loader']['path'],pr[c['arm'].lower()+'Artifact']['path'],str(c['offset']),'1','aarch64','-',str(c['argument'])];c.pop('nativeArgvTemplate',None)
pr['orderedChildren']=pr['cases'];pr['resolvedOwnExports']=exports
for name in ['adapter.py','launch-wrapper.py','validate-runtime.py']:(D/name).write_bytes((A/name).read_bytes())
run=(A/'run-draft.py').read_text().replace('DRAFT8 current original CRC guest children; unresolved emission proof cannot run after specific root GO only.','Frozen8 original CRC guest plan; inert until exact reviewed root GO.')
start=run.index("  ep=load(pin(pr['actualEmissionProof']")
end=run.index("  for field in ['offArtifact'",start)
run=run[:start]+"  ep=load(pin(pr['actualEmissionProof']['path'],pr['actualEmissionProof']))\n  xp=load(pin(pr['actualExtractionProof']['path'],pr['actualExtractionProof']))\n  ec=load(pin(pr['actualExtractionCompletion']['path'],pr['actualExtractionCompletion']))\n  emission_guard(ep,xp,ec,pr)\n  old=load(pin(pr['oldBuild8FailureProof']['path'],pr['oldBuild8FailureProof']));need(old['status']=='PASS_INDEPENDENT_SAVED_FAILURE_TC_CURRENT_EMITTED_CALLS7_ONLY' and len(old['savedCalls'])==7,'preserved seven-call failure')\n"+run[end:]
helper='''def emission_guard(ep,xp,ec,pr):
 need(ep['status']==pr['acceptedEmissionProofStatus'] and ep['independent'] is True,'exact repaired emission proof')
 need(ep['wholeObservedUnobservedKSEEDSHA256']==pr['onContainer']['sha256'] and ep['oldBuild8StillFailed'] is True and ep['savedCalls']==7 and ep['completionAbsent'] is True,'saved repair does not complete old build8')
 need(ep['recomputedSelectedEmission']['selectedSite']==220 and ep['recomputedSelectedEmission']['TCEmitterExecuted'] is True and ep['guestRuntimeQualified'] is False if 'guestRuntimeQualified' in ep else ep['recomputedSelectedEmission']['guestRuntimeQualified'] is False,'selected saved emission only')
 need(xp['status']==pr['acceptedExtractionProofStatus'] and xp['independent'] is True and xp['completion']==pr['actualExtractionCompletion'],'exact separate extraction proof')
 need(xp['acceptedEmissionProof']==pr['actualEmissionProof'] and xp['extractedNative']==pr['onArtifact'] and xp['savedContainer']==pr['onContainer'],'extraction exact repaired lineage and whole artifacts')
 need(xp['oldBuild8StillFailed'] is True and xp['oldCallsRepeated']==0 and xp['freshExtractionCalls']==1 and xp['guestRuntimeQualified'] is False,'fresh one-call identity only; no old repeat')
 need(ec['status']=='COMPLETE_TC_SAVED_OBSERVER_EXTRACT1_IDENTITY_ONLY' and ec['sourcePinsSHA256']==xp['sourcePinsSHA256'] and ec['rootGOSHA256']==xp['rootGOSHA256'],'exact extraction completion source binding')
 need(ec['acceptedEmissionProof']==pr['actualEmissionProof'] and ec['native']==pr['onArtifact'] and ec['savedContainer']==pr['onContainer'] and ec['exports']==xp['exports'],'complete native/container own exports')
 need(ec['oldBuild8StillFailed'] is True and ec['oldCallsRepeated']==0 and ec['freshExtractionCalls']==1 and ec['TCEmitterExecuted'] is False and ec['generatedWorkloadExecuted'] is False,'separate extraction only')
'''
# Avoid conditional precedence: nested saved certificate owns this field.
helper=helper.replace("ep['guestRuntimeQualified'] is False if 'guestRuntimeQualified' in ep else ep['recomputedSelectedEmission']['guestRuntimeQualified'] is False","ep['recomputedSelectedEmission']['guestRuntimeQualified'] is False")
run=run.replace('def main(gopath):',helper+'\ndef main(gopath):')
run=run.replace("'exact emitted build8 GO'","'exact guest8 GO'")
run=run.replace("  case=next(c for c in pr['cases']if c['label']==label);", "  need(pr['cases'][len(rows)]['label']==label,'exact ordered adjacent sequence')\n  case=next(c for c in pr['cases']if c['label']==label);")
run=run.replace("'actualEmissionProof':pr['actualEmissionProof'],'sourcePinsSHA256'","'actualEmissionProof':pr['actualEmissionProof'],'actualExtractionProof':pr['actualExtractionProof'],'actualExtractionCompletion':pr['actualExtractionCompletion'],'oldBuild8FailureProof':pr['oldBuild8FailureProof'],'sourcePinsSHA256'")
(D/'run.py').write_text(run)
save(D/'preregistration.json',pr)
# Full inherited exact input closure plus new audit/extraction provenance and every draft input.
ip=load(X/'input-pins.json')
for base in [A,X]:
 for p in sorted(base.iterdir()):
  if p.is_file() and not p.is_symlink():r=pin(p);ip[r.pop('path')]=r
for r in [ep,xp,ec,pr['onArtifact'],pr['onContainer'],pr['offArtifact'],pr['offContainer'],pr['oldBuild8FailureProof']]:ip[r['path']]={k:r[k]for k in ['bytes','sha256']}
for path,v in ip.items():
 r=pin(path);assert {k:r[k]for k in ['bytes','sha256']}==v,(path,'input drift')
pr['inputCount']=len(ip);pr['inputLogicalBytes']=sum(v['bytes']for v in ip.values())
assert pr['inputCount']<=4096 and pr['inputLogicalBytes']<=536870912
save(D/'input-pins.json',dict(sorted(ip.items())));pr['inputRegistrySHA256']=pin(D/'input-pins.json')['sha256'];save(D/'preregistration.json',pr)
for p in D.glob('*.py'):ast.parse(p.read_text())
save(D/'author-report.json',{'status':'SOURCE_AUTHORING_ONLY_NO_GO','exports':exports,'inputCount':len(ip),'inputLogicalBytes':pr['inputLogicalBytes'],'nativeCalls':0,'networkCalls':0,'productEdits':0,'C2Enabled':False})
