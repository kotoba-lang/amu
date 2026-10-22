from pathlib import Path
import json,hashlib,copy,tarfile,io,ast
D=Path(__file__).resolve().parent
ns={};exec(compile((D/'result-contract.py').read_bytes(),'result-contract.py','exec'),ns)
def dump(j):return json.dumps(j).encode()
def fixture(b,q,failure):
 c={};term={'allBuildsClosed':True,'allQueriesClosed':True,'builds':b,'identityQueries':q,'failure':failure};c['runner-build/terminal.json']=dump(term)
 for folder,count,labels in [('compiles',b,ns['WORKLOADS']),('queries',q,ns['QLABELS'])]:
  rows=[]
  for i,label in enumerate(labels[:count]):
   r={'index':i+1,'label':label,'state':'terminal','returncode':0,'timeout':False,'stdoutSHA256':hashlib.sha256(b'').hexdigest(),'stderrSHA256':hashlib.sha256(b'').hexdigest()};rows.append(r)
   for ext in ['.stdout','.stderr']:c['runner-build/'+folder+'/'+label+ext]=b''
  c['runner-build/'+folder+'/attempts.json']=dump(rows)
 if failure:c['runner-build/failure.json']=dump({'builds':b,'identityQueries':q,'policy':'STOP_FIRST_FAILURE_NO_RERUN'})
 else:
  for n in ['report.json','images.json','identity-before.json','identity-after.json','effective-environment.json']:c['runner-build/'+n]=b'{}'
  for n in ns['WORKLOADS']:c['runner-build/'+n+'/runner']=b'MACHO_TEST_ONLY'
 return c
v=fixture(19,14,False);ns['validate_result'](v)
c=fixture(0,0,True);del c['runner-build/queries/attempts.json'];del c['runner-build/compiles/attempts.json'];ns['validate_result'](c)
for b in range(20):ns['validate_result'](fixture(b,7,True))
for q in range(15):ns['validate_result'](fixture(0,q,True))
reject=0
def bad(c):
 global reject
 try:ns['validate_result'](c)
 except (AssertionError,KeyError):reject+=1
 else:raise AssertionError('adverse accepted')
for k,val in [('identityQueries',True),('builds',20),('allQueriesClosed',False)]:
 c=copy.deepcopy(v);t=json.loads(c['runner-build/terminal.json']);t[k]=val;c['runner-build/terminal.json']=dump(t);bad(c)
c=copy.deepcopy(v);t=json.loads(c['runner-build/terminal.json']);t['queries']=t.pop('identityQueries');c['runner-build/terminal.json']=dump(t);bad(c)
c=copy.deepcopy(v);c['runner-build/credential.txt']=b'X';bad(c)
c=copy.deepcopy(v);rows=json.loads(c['runner-build/queries/attempts.json']);rows[-1]['state']='started';c['runner-build/queries/attempts.json']=dump(rows);bad(c)
c=copy.deepcopy(v);del c['runner-build/compiles/aha-mont64.stdout'];bad(c)
c=fixture(0,0,True);c['runner-build/aha-mont64/runner']=b'X';bad(c)
# Actual parser receives raw regular USTAR only; rejects hidden extension records.
def tar(fmt,pax=None):
 o=io.BytesIO()
 with tarfile.open(fileobj=o,mode='w',format=fmt) as t:
  z=tarfile.TarInfo('inventory.json');z.size=2
  if pax:z.pax_headers=pax
  t.addfile(z,io.BytesIO(b'{}'))
 return o.getvalue()
assert ns['parse_ustar'](tar(tarfile.USTAR_FORMAT))=={'inventory.json':b'{}'}
for raw in [tar(tarfile.PAX_FORMAT,{'comment':'hidden'}),tar(tarfile.GNU_FORMAT),tar(tarfile.USTAR_FORMAT)[:500]]:
 try:ns['parse_ustar'](raw)
 except AssertionError:reject+=1
 else:raise AssertionError('extension/truncated tar accepted')
for p in D.glob('*.py'):ast.parse(p.read_text())
(D/'offline-checks.json').write_text(json.dumps({'status':'PASS_PURE_METADATA_AND_RAW_ARCHIVE_CONTROLS_ONLY','positiveTerminal':1,'failureBuildCounts':20,'failureIdentityCounts':15,'rejectControls':reject,'sshCompilerNative':0},indent=2)+'\n')
if __name__=='__main__':print('PURE_CONTROLS_PASS')
