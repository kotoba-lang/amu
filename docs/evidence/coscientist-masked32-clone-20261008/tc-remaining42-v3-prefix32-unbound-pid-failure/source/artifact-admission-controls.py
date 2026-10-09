"""Saved observation + injected field mutants only; no process/thread/FD/sampler operations."""
from pathlib import Path
import json,copy
from artifact_admission import accept_artifact_observation
D=Path(__file__).resolve().parent
pr=json.loads((D/'preregistration.json').read_bytes());rows=json.loads((Path(pr['previousFailedCampaign'])/'run-outputs/attempts.json').read_bytes());base=rows[1]['controllerObservation'];assert accept_artifact_observation(base) is True
assert base['strictOldMemoryPolicyPassed'] is False and base['memoryObservation']['missingFootprint'] is None
assert accept_artifact_observation(rows[0]['controllerObservation']) is True
mutants=[]
for name,fn in [('unknown-errno',lambda o:o['memoryAdmissionRecord']['failure'].update(errno=None)),('non-ESRCH',lambda o:o['memoryAdmissionRecord']['failure'].update(errno=1)),('unknown-stage',lambda o:o['memoryAdmissionRecord']['failure'].update(stage='other')),('policy-refusal',lambda o:o['memoryAdmissionRecord']['failure'].update(failureClass='policy-refusal')),('unknown-origin',lambda o:o['memoryAdmissionRecord']['failure'].update(typedOrigin='untyped')),('zero-query',lambda o:o['memoryAdmissionRecord']['failure'].update(queryOrdinal=0)),('zero-samples',lambda o:o['memoryAdmissionRecord'].update(acceptedSamples=0)),('missing-birth',lambda o:o['memoryAdmissionRecord'].update(acceptedLeaderBirthBound=False)),('other-refusal',lambda o:o['memoryAdmissionRecord'].update(otherRefusals=['threshold'])),('partial-EOF',lambda o:o['memoryAdmissionRecord'].update(completePipeEOF=False)),('uncertain-wait',lambda o:o['memoryAdmissionRecord'].update(waitUncertain=True)),('false-semantic',lambda o:o.update(semanticQualification=False)),('zero-footprint-synthesis',lambda o:o['memoryObservation'].update(missingFootprint=0)),('strict-gap-inference',lambda o:o.update(strictOldMemoryPolicyPassed=True)),('nonsampling-first-refusal',lambda o:o['capture'].update(firstFailure='pipe-transfer-failure'))]:
 o=copy.deepcopy(base);fn(o)
 try:accept_artifact_observation(o)
 except AssertionError:mutants.append(name)
 else:raise AssertionError('mutant accepted:'+name)
print(json.dumps({'status':'PASS_PURE_ARTIFACT_ADMISSION_WITH_RETAINED_STRICT_FAILURE_ONLY','positives':2,'rejectedMutants':mutants,'oldCampaignReclassified':False,'operations':0},indent=2))
