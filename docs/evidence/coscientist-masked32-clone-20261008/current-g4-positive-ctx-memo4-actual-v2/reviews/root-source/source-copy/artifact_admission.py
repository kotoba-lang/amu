"""Compiler semantic/artifact admission v3; physical-memory qualification remains separate."""
from integration import classify_memory,MEMORY_POLICY
def accept_artifact_observation(o):
 assert o['semanticQualification'] is True and o['sampleReceiptPersistenceQualified'] is True
 record=o['memoryAdmissionRecord'];assert record['policy']==MEMORY_POLICY
 assert record['acceptedSamples']>=1 and record['acceptedLeaderBirthBound'] is True and record['otherRefusals']==[]
 assert record['completePipeEOF'] is True and record['stoppedClosedCapture'] is True and record['rawTruncated'] is False and record['captureErrors']==[]
 assert record['exactDirectChildWait']=='closed0' and record['waitUncertain'] is False and record['withinOriginalDeadline'] is True
 assert record['groupAuthorityRetired'] is True and record['groupOperationsAfterUncertainty']==0 and record['groupOperationsAfterWait']==0 and record['loaderWaitProtocolPinned'] is True
 assert o['memoryObservation']==classify_memory(record)
 if o['status']=='COMPLETE_SEMANTIC_SAMPLED_MEMORY':
  assert o['strictOldMemoryPolicyPassed'] is True and record['failure'] is None and o['capture']['firstFailure'] is None and o['memoryObservation']['status']=='sampled-observations-only'
  return True
 assert o['status']=='SEMANTIC_DIAGNOSTIC_TERMINATION_GAP' and o['strictOldMemoryPolicyPassed'] is False
 assert o['capture']['firstFailure']=='sampling-uncertainty'
 mem=o['memoryObservation'];assert mem['status']=='termination-gap-unavailable' and mem['missingFootprint'] is None and mem['zeroSynthesized'] is False and mem['hardPeakQualified'] is False
 return True
