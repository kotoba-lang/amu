from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent
P=json.loads((D/'preregistration.json').read_text())
for row in P['inputPins']:
 b=Path(row['path']).read_bytes()
 assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
B=Path(P['inputPins'][0]['path']).parent
H=(D/'helpers.kotoba').read_text()
old='(sl-assign (gn-vmode (gn-assign MM) i) i f np)'
new='(lc-assign (gn-vmode (gn-assign MM) i) i f np)'
anchor=';; every instruction from i (an instruction may consume the next ones: gn-f-skip)'
rows=[]
for prefix in ('41','unity'):
 baseline=(B/(prefix+'-sr-on.kotoba')).read_text()
 assert baseline.count(old)==baseline.count(anchor)==1
 for flag in (0,1):
  helper=H.replace('(def lc-feature 0)',f'(def lc-feature {flag})')
  result=baseline.replace(anchor,helper+'\n'+anchor).replace(old,new)
  assert result.replace(new,old).replace(helper+'\n','')==baseline
  name=prefix+'-lc-'+('on' if flag else 'off')+'.kotoba'
  (D/name).write_text(result)
  rows.append({'path':name,'feature':flag,'bytes':len(result.encode()),'sha256':hashlib.sha256(result.encode()).hexdigest(),'exactReverse':True,'baseline':str(B/(prefix+'-sr-on.kotoba'))})
(D/'reversal.json').write_text(json.dumps({'variants':rows,'changedDefinition':'gn-op-fn2 only callsite','nativeCalls':0},indent=2)+'\n')
