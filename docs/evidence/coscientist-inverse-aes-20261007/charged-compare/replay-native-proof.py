"""Standalone selected-proof replay. Python stdlib only; no native/solver/network calls."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,tempfile,struct,collections,sys
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ld=lambda p:json.loads(p.read_text())
def replay():
 m=ld(D/'native-proof.manifest.json');a=D/m['archive'];assert sha(a)==m['archiveSHA256'] and a.stat().st_size==m['archiveBytes']
 with tarfile.open(a)as t:
  entries=t.getmembers();assert len(entries)==len(m['regularMembers']);assert len({e.name for e in entries})==len(entries)
  blob={}
  for e in entries:
   assert e.isfile() and not e.name.startswith('/') and '..'not in PurePosixPath(e.name).parts
   b=t.extractfile(e).read();r=m['regularMembers'][e.name];assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];blob[e.name]=b
 assert hashlib.sha256(blob['index.json']).hexdigest()==m['indexSHA256'];index=json.loads(blob['index.json']);assert len(index['files'])==m['selectedCount']
 with tempfile.TemporaryDirectory(prefix='charged-native-offline-')as td:
  W=Path(td)
  for n,r in index['files'].items():
   assert not n.startswith('/') and '..'not in PurePosixPath(n).parts
   b=blob[r['blob']];assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']==r['originSHA256'];p=W/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  I=W/'team-charged-compare-v1';on=(I/'41-charged-compare-on.kotoba').read_text();off=(I/'41-charged-compare-default.kotoba').read_text();base=(W/'team-inverse-directreg-v1/41-directreg-on.kotoba').read_text()
  assert sha(I/'41-charged-compare-on.kotoba')=='5e545aaff311b8852e1179659944d4242f980f53006c8a45976b8a7919bf7e10'
  assert on.replace('(def uc-feature 1)','(def uc-feature 0)')==off
  s=on.index(';; Experimental charged full64 unsigned comparison.');e=on.index('(defn- gn-op-call',s)
  assert (on[:s]+on[e:]).replace('(cond (uc-admit M i f t n) (uc-call M i t) inverse','(cond inverse')==base
  assert (I/'unity-charged-compare-on.kotoba').read_text().replace('(def uc-feature 1)','(def uc-feature 0)')==(I/'unity-charged-compare-default.kotoba').read_text()
  for g in range(1,5):assert sha(I/('seed-%d.bin'%g))=='3ad29932428206a84a8c571a8089a793d0dcf95d167c23cbcbb43effdba2a346' and int((I/('seed-%d.offset'%g)).read_text())==0
  # Exact archived raw machine parser, restricted to source, bytes, decoder and finite controls. No native instruction execution.
  audit=(W/'team-charged-compare-independent/audit.py').read_text();code=audit[audit.index('ident=[]'):audit.index("r={'status'")]
  ns={'Path':Path,'json':json,'struct':struct,'hashlib':hashlib,'W':W,'P':I,'I':I/'original19-images','B':W/'team-inverse-directreg-v1/original19-images/on','sha':sha,'ld':ld}
  exec(compile(code,'archived-machine-audit-offline','exec'),ns)
  assert ns['proof']==ld(W/'team-charged-compare-independent/report.json')['machine'];assert len(ns['faults'])==3 and all(f['detected']for f in ns['faults']);assert len(ns['ident'])==19
  # Same immutable original wrapper source, source-derived unsigned/wrapping oracle and every actual raw pair.
  R=W/'team-charged-compare-runtime-procedure';F=R/'results';rows=ld(F/'attempts.json');pairs=ld(F/'pairs.json');cases=ld(R/'cases.json')['cases'];assert len(cases)==len(pairs)==120 and len(rows['guestInvocations'])==240 and len(rows['hostBuilds'])==10
  M=(1<<64)-1;sign=lambda v:((v+(1<<63))%(1<<64))-(1<<63)
  def value(c):
   a,b,carry,_,_=c['args'];s=c['symbol'];lhs=(a^(1<<63))&M if s=='uc-computed'else a&M;v=int(lhs>=(b&M))
   if s=='uc-alias':v=1
   if s=='uc-live-reg':v=sign(carry+17+v)
   if s=='uc-live-local':v=sign(carry+v)
   return v
  for build in rows['hostBuilds']:
   q=F/build['profile']/build['symbol'];p=R/'prepared'/build['profile']/build['symbol'];assert build['exit']==0 and build['state']=='terminal' and build['arity']==5
   for n,k in [('loader','binarySHA256'),('embedded.h','headerSHA256'),('image.bin','nativeSHA256')]:assert sha(q/n)==build[k]
   for n in ['embedded.h','image.bin']:assert(q/n).read_bytes()==(p/n).read_bytes()
   assert not(q/'build.stdout').read_bytes() and not(q/'build.stderr').read_bytes()
  assert len({(b['profile'],b['symbol'])for b in rows['hostBuilds']})==10
  for i,pair in enumerate(pairs):
   c=cases[i];assert pair['caseIndex']==i and pair['spec']==c;fuel=c['fuel'];after=max(0,fuel-2);trap=fuel<2
   assert c['expectedFuelAfter']==after and c['expectedStatus']==('trap'if trap else'return') and c['expectedChargesOnSuccess']==2 and c['expectedReturn']==(None if trap else value(c))
   for profile in ['baseline','candidate']:
    path=F/profile/c['symbol']/('case%d.json'%i);r=ld(path);assert r==pair[profile]
    g=[g for g in rows['guestInvocations']if g['caseIndex']==i and g['profile']==profile];assert len(g)==1;g=g[0];assert sha(path)==g['receiptSHA256'] and g['state']=='terminal' and g['fuel']==fuel and g['args']==c['args'] and g['wireArgs']==[sign(a)for a in c['args']]
    suffix=' :fuel {:initial %d :remaining %d} :heap {:capacity 1048576 :used 0} :string-pool {:capacity 16777216 :used 0} :vectors {:capacity 131072 :used 0} :vector-items {:capacity 4194304 :used 0}}\n'%(fuel,after)
    prefix='{:status :trap :exit 120'if trap else'{:status :ok :result %d'%value(c)
    assert r['stdout']==prefix+suffix and r['exit']==(120 if trap else 0);assert r['stderr']==('KEXE_TRAP {:kind :signal :signal :SIGTRAP}\nKEXE_TRAP {:kind :budget :reason :budget/fuel}\n'if trap else'')
   assert pair['baseline']==pair['candidate']
  assert [(g['caseIndex'],g['profile'])for g in rows['guestInvocations']]==[(i,p)for i in range(120)for p in ['baseline','candidate']]
  # Observer output parity covers this fixture; no admission assertion for arbitrary future inputs.
  O=W/'team-charged-compare-fixture-observer';C=W/'team-charged-compare-runtime-plan/compiler-phase/candidate'
  k=(C/'image.kseed').read_bytes();assert k==(O/'fixture.kseed').read_bytes();native=k.split(b'\n\n',1)[1];assert native==(C/'native.bin').read_bytes()==(O/'fixture-native.bin').read_bytes()
  records=ld(O/'records.json');tags={r['tag']for r in records};actual=[]
  for line in(O/'fixture-traversal.stdout').read_text().splitlines():
   cols=line.split()
   if cols and cols[0]in tags:actual.append({'tag':cols[0],'fields':list(map(int,cols[1:]))})
  assert actual==records
  admit=[r['fields']for r in records if r['tag']=='UCADM'];rep=ld(O/'report.json');assert [r for r in admit if r[4]==1]==rep['admittedUC'] and [r for r in admit if r[4]==0]==rep['refusedUC'];assert len(rep['admittedUC'])==6 and len(rep['refusedUC'])==1
  ar=ld(W/'team-charged-compare-actual-admission-review/report.json');words=list(struct.unpack('<%dI'%(len(native)//4),native))
  for span in ar['spans']:
   lo=span['firstWordOneBased']-1;hi=span['endExclusiveOneBased']-1;assert ['%08x'%z for z in words[lo:hi]]==span['words'];assert span['fullSpanWords']<=14
  # Elementary full64 sign-bit order identity, finite vectors; deliberately no SMT invocation/certificate.
  for a in [0,1,2,(1<<32)-1,1<<32,(1<<63)-1,1<<63,(1<<63)+1,M]:
   for b in [0,1,2,(1<<32)-1,1<<32,(1<<63)-1,1<<63,(1<<63)+1,M]:assert (not(sign(a^(1<<63))<sign(b^(1<<63))))==(a>=b)
  decision=ld(W/'root/chargedcompare-native-stage-decision.json');assert decision['nativeFixtureInvocations']==240 and decision['uniqueValueFuelPairs']==120 and decision['performanceQualified']is False and decision['productAdopted']is False
  return {'status':'PASS selected offline source/machine/observer/raw120pairs240calls','selectedFiles':len(index['files']),'uniqueBlobs':index['uniqueBlobCount'],'runtimePairs':120,'runtimeCalls':240,'trapPairs':sum(c['fuel']<2 for c in cases),'returnPairs':sum(c['fuel']>=2 for c in cases),'fourGenerations':4,'original19DefaultExact':True,'onOther18Exact':True,'machineFaultsRejected':len(ns['faults']),'observerSixAdmissionsAliasRefusal':True,'elementaryBoundaryPairs':81,'originalExternalReads':0,'nativeExecutions':0,'solverExecutions':0,'networkCalls':0,'scope':'normal terminal finite evidence; no universalABI/fullM/async/timing/adoption'}
if __name__=='__main__':print(json.dumps(replay(),indent=2))
