"""Consumer two-record decoder. C observables remain unavailable, no timing adoption."""
from qualification import parse
def qualify(rawOut,rawErr,case):
 q=parse(rawOut,rawErr,case,case['expected'],0)
 return {'timing':q['timing'],'observables':q['observables'],'arena17':q['observables'].get('arena17'),'result':q['observables']['result']}
