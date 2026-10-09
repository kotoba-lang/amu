from pathlib import Path
import json,hashlib,runpy,io,contextlib
D=Path(__file__).resolve().parent
def p(path):
 b=path.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
# Main is inert; these controls only import static/source parsing functions.
b=io.StringIO()
with contextlib.redirect_stdout(b):runpy.run_path(str(D/'pure-controls.py'),run_name='__main__')
(D/'pure-controls.json').write_text(b.getvalue())
from run import GO_KEYS,HOST_KEYS
schema={'exactKeys':sorted(GO_KEYS),'hostBindingExactKeys':sorted(HOST_KEYS),'status':'GO_CURRENT19_ZEBULUN_C_BUILD38_ONCE_V2','maximumChildCalls':38,'guestAuthorized':False,'consumerAuthorized':False,'timingAuthorized':False,'noRetry':True,'C2':False,'taskRoot':'fresh canonical packet root; must contain source/C-build subject and pinned relative inputs','hostBinding':'fresh actual remote canonical CLT/interpreter/linker receipts and SDK/resource aliases/library pins; no synthetic values admitted','sourceReviews':'two distinct actual exact SOURCE reviews bound to SP/driver/prereg; creation/execution by root only'}
(D/'go-schema.json').write_text(json.dumps(schema,indent=2)+'\n')
names=['author.py','run.py','limit-exec.py','pure-controls.py','pure-controls.json','recipes.json','preregistration.json','CONTRACT.md','go-schema.json','freeze-source.py']
sp={n:p(D/n)for n in names};(D/'source-pins.json').write_text(json.dumps(sp,indent=2)+'\n');ip=json.loads((D/'input-pins.json').read_text())
(D/'freeze.json').write_text(json.dumps({'status':'FROZEN_SOURCE_ONLY_C19_BUILD38_OPERATIONAL_HOLD','sourcePins':{'path':str(D/'source-pins.json'),**p(D/'source-pins.json')},'inputPins':{'path':str(D/'input-pins.json'),**p(D/'input-pins.json')},'driver':{'path':str(D/'run.py'),**p(D/'run.py')},'preregistration':{'path':str(D/'preregistration.json'),**p(D/'preregistration.json')},'sourceFiles':len(sp),'inputFiles':len(ip),'inputBytes':sum(x['bytes']for x in ip.values()),'guestCalls':0,'compilerCalls':0,'networkCalls':0,'remaining':'two SOURCE reviews, fresh host-binding/preinstall identities and root GO before any operation; independent actual C19 audit before header'},indent=2)+'\n')
print((D/'freeze.json').read_text())
