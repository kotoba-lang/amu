"""Pure source/read-only registration constraints; no wrapper/main/process APIs."""
from pathlib import Path
import json,ast
import loader_grammar as g
D=Path(__file__).parent;pr=json.loads((D/'preregistration.json').read_bytes());keys=json.loads((D/'go-schema.json').read_bytes())['exactKeys'];tree=ast.parse((D/'run.py').read_bytes());literals=[ast.literal_eval(n)for n in ast.walk(tree)if isinstance(n,ast.Set)and all(isinstance(e,ast.Constant)for e in n.elts)];assert set(keys)in literals and len(keys)==len(set(keys))
for c in pr['cases']:
 a=c['nativeArgv'];q=g.interpretation(a);assert q=={'typedI64':[2],'guestArgv':None,'effectiveArgc':7};bad=a[:6]+['--']+a[6:]
 try:g.interpretation(bad)
 except AssertionError:pass
 else:raise AssertionError('misplaced guest separator accepted')
assert len(pr['cases'])==pr['maximumLoaderCalls']==2 and len(pr['environment'])==17
assert "need(len(rows)<2 and pr['cases'][len(rows)]==case"in(D/'native-call.py').read_text()
assert pr['originalOuterWallSeconds']==30 and pr['diagnosticLoaderChildFailureCleanupSeconds']==5
assert pr['maximumParentFDs']==44 and pr['maximumAuxiliaryThreadsPerCall']==3
result={'status':'PASS_PURE_PAIRED2_V4_REGISTRATION_ONLY','typedPositives':2,'typedSeparatorRefusals':2,'thirdCallBeforeAPIRefused':True,'schemaExact':True,'actualOperations':0};(D/'registration-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
