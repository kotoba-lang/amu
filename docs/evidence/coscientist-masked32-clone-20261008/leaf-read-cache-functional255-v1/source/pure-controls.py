from pathlib import Path
import hashlib,json,ast
D=Path(__file__).resolve().parent;s=(D/'run.py').read_bytes();ast.parse(s);ns={'__file__':str(D/'run.py'),'__name__':'source_only_parser_controls'};exec(compile(s,str(D/'run.py'),'exec'),ns)
pr=json.loads((D/'preregistration.json').read_bytes());assert len(pr['cases'])==17 and sum(len(c['iterations'])for c in pr['cases'])==85 and pr['maximumFutureChildCalls']==255 and pr['maximumInputLogicalBytes']==448*1024**2 and pr['maximumInputFiles']==3072
for c in pr['cases']:
 for arm in ['OFF','ON']:
  ex,p=ns['container'](c[arm+'Container']);assert p==Path(c[arm]['path']).read_bytes()and {'name':c['symbol'],'offset':c[arm+'Offset'],'arity':1}in ex
 # Prior finite records are independently decoded as parser controls, not new LC guest results.
 for r in c['resourceReferenceProfiles']:
  a=r['nativeArenas'];b=('{' +f':status :ok :result {r["result"]} :fuel '+'{'+f':initial 16777216 :remaining {16777216-r["nativeFuelConsumed"]}'+'} '+ ' '.join(':'+x+' {'+f':capacity {a[y]["capacity"]} :used {a[y]["used"]}'+'}'for x,y in [('heap','pairs'),('string-pool','stringPoolBytes'),('vectors','vectors'),('vector-items','vectorItems')])+'}\n').encode();ns['native'](b,b'',r['n'])
  for mutant in [b[:-1],b.replace(b':remaining ',b':unknown '),b.replace(b':initial 16777216',b':initial 0')]:
   try:ns['native'](mutant,b'',r['n'])
   except AssertionError:pass
   else:raise AssertionError('mutant accepted')
print('PASS17 artifact and85 resource parser controls/255 mutants; no child/native')
