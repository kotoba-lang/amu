from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
from decode import parse
D=Path(__file__).resolve().parent
def raw(edges=1,drop=False):
 support=0 if drop else 1
 lines=['CQ-ACTIVATE 0 3 50','CQ-ENTRY 1 6 0 0 3 '+str(edges)+' 0 4 0 0 0 4 0 0 0 1 1 0 0 0 0',f'CQ-EXIT 1 6 100 0 0 {support} 0 1',f'CR-RESULT 1 0 {support} 0 1 1 0 1 0 4 0']
 for k in range(16):lines += [f'CR-WVF 1 {k} {support if k==15 else 0}',f'CR-FNF 1 {k} 0']
 for e in range(edges):lines += [f'CQ-EDGE 1 {e} 20 2 0 0 -1 -1 -1',f'CR-EDGE 1 {e} 20 2 0 1 13 2 0 1 0 -1 -1 -1']
 lines+=[f'CR-END 1 1 0 1 {edges}','CQ-DEACTIVATE 0'];return ('\n'.join(lines)+'\n').encode()
a=raw();assert parse(a)['supportedSuccessful']==1;assert parse(raw(0))['supportedSuccessful']==1;assert parse(raw(2))['queries'][0]['projection']['orderedEdges'][1][1]==1;assert parse(raw(drop=True))['supportedSuccessful']==0
changed=a.replace(b'CR-RESULT 1 0 1 0 1 1 0 1 0 4 0',b'CR-RESULT 1 0 1 0 1 2 0 1 0 4 0')
assert parse(a)['queries'][0]['canonicalProjectionBytes']!=parse(changed)['queries'][0]['canonicalProjectionBytes']
arity=a.replace(b'CR-EDGE 1 0 20 2 0 1 13 2 0 1',b'CR-EDGE 1 0 20 2 0 2 13 2 0 2')
assert parse(a)['queries'][0]['canonicalProjectionBytes']!=parse(arity)['queries'][0]['canonicalProjectionBytes']
bad=[a.replace(b'CR-END 1 1 0 1 1\n',b''),a.replace(b'CR-FNF 1 15 0\n',b''),a.replace(b'CR-EDGE 1 0 20 2 0 1 13 2 0 1',b'CR-EDGE 1 0 20 2 0 2 13 2 0 1'),a.replace(b'CR-EDGE 1 0 20 2 0 1 13 2 0 1',b'CR-EDGE 1 0 20 2 0 1 14 2 0 1'),a.replace(b'CR-WVF 1 0 0',b'CR-WVF 1 1 0'),a.replace(b'CR-RESULT 1 0 1 0 1',b'CR-RESULT 1 0 0 0 1'),a.replace(b'CR-END 1 1 0 1 1',b'CR-END 1 1 0 1 2')]
for z in bad:
 try:parse(z)
 except AssertionError:pass
 else:raise AssertionError('malformed accepted')
save={'status':'PASS_PURE_DECLARED_OUTPUT_ROLE_SCHEMA_CONTROLS_ONLY','positive':6,'rejected':len(bad),'nativeCalls':0,'SSHCalls':0,'subprocessCalls':0,'fullResultCIDQualified':False}
(D/'pure-controls.json').write_text(json.dumps(save,indent=2)+'\n');(D/'positive-fixture.stdout').write_bytes(a);print('PURE controls pass')
