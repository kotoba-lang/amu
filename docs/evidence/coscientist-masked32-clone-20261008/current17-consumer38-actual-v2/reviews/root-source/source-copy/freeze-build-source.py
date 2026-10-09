"""Local SOURCE freeze only; no compiler/native/process/FD authority."""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent
FILES=['build.py','build-limit-exec.py','build-preregistration.json','build-go-schema.json','BUILD-CONTRACT.md','build-pure-controls.py','build-pure-controls.json','prepare.py','header.py','qualification.py','packet.json','consumer-source-pins.json','recipes.json','freeze-build-source.py','sdk-library-selection.json']
def receipt(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
sp={n:receipt(D/n)for n in FILES}
(D/'source-pins.json').write_text(json.dumps(sp,indent=2)+'\n')
f={'status':'FROZEN_SOURCE_ONLY_CURRENT17_CONSUMER_BUILD38_V2','sourcePins':receipt(D/'source-pins.json'),'inputPins':receipt(D/'input-pins.json'),'driver':receipt(D/'build.py'),'preregistration':receipt(D/'build-preregistration.json'),'sourceFiles':len(sp),'inputFiles':108,'inputLogicalBytes':sum(r['bytes']for r in json.loads((D/'input-pins.json').read_text()).values()),'actualCalls':0,'qualifier342Registration':'UNFROZEN separate follow-on; no execution authority'}
(D/'build-freeze.json').write_text(json.dumps(f,indent=2)+'\n')
print(json.dumps(f))
