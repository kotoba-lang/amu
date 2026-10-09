"""New diagnostic ownership policy only; no old policy success alias."""
from integration import classify_memory,MEMORY_POLICY
def accept_artifact_observation(o):
 assert o['semanticQualification']is True and o['sampleReceiptPersistenceQualified']is True
 r=o['memoryAdmissionRecord'];assert r['policy']==MEMORY_POLICY and r['heldOwnershipQualified']is True and r['exactHeldChildWait0']is True and r['initialHeldSamples']==2 and r['otherRefusals']==[]
 assert o['memoryObservation']==classify_memory(r)
 if o['status']=='COMPLETE_HELD_LAUNCH_SEMANTIC_SAMPLED_MEMORY':
  assert r['failure']is None and o['strictHeldSamplingPolicyPassed']is True and o['memoryObservation']['status']=='held-launch-sampled-observations-only';return True
 assert o['status']=='HELD_LAUNCH_SEMANTIC_TERMINATION_GAP'and o['strictHeldSamplingPolicyPassed']is False and r['freshKnownFailureVerified']is True and o['memoryObservation']['status']=='held-launch-owned-termination-gap';return True
