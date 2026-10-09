"""SOURCE-only freeze, no build/guest/FD/thread authority."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
FILES=['artifact_admission.py','callback_contract.py','capture.py','consumer-source-pins.json','controller.py','expected-observables.json','header.py','held-component-identity.json','integration.py','launch-wrapper.py','native-call.py','ownership.py','packet.json','prepare.py','preregistration.json','pure-controls.py','pure-controls.json','qualification.py','run.py','runtime.py','typed-adapter.py','verify_saved.py','go-schema.json','CONTRACT.md','freeze-source.py','saved-zero-diagnostic.json']
def receipt(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
sp={n:receipt(D/n)for n in FILES};(D/'source-pins.json').write_text(json.dumps(sp,indent=2)+'\n')
f={'status':'FROZEN_SOURCE_ONLY_CURRENT17_CONSUMER_QUALIFY342_V2','sourcePins':receipt(D/'source-pins.json'),'inputPins':receipt(D/'input-pins.json'),'driver':receipt(D/'run.py'),'preregistration':receipt(D/'preregistration.json'),'sourceFiles':len(sp),'inputFiles':108,'inputLogicalBytes':2931240,'actualCalls':0,'consumer19ActualProofsRequiredAtGO':True,'runtimeQualification':False,'performanceQualification':False}
(D/'freeze.json').write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(f))
