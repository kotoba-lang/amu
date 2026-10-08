"""Exactly freshC19+freshconsumer19+identity14. No guest/timing execution."""
from common import *
from header import header
import struct,sys,platform
def main():
 def alarm(signum,frame):raise TimeoutError('remote cohort absolute deadline')
 signal.signal(signal.SIGALRM,alarm)
 need(len(sys.argv)==2,'exact build GO');gp=Path(sys.argv[1]);g=authorize('build',gp);gh=sha(gp)
 need(D==ROOT/'package' and Path.home()==Path('/Users/zebulun') and platform.machine()=='arm64','actual selected native arm64 task')
 need(g.get('maximumChildren')==52 and g.get('CBuilds')==19 and g.get('consumerBuilds')==19 and g.get('identityQueries')==14,'exact finite52 GO')
 need(g.get('transferAcceptance',{}).get('sha256'),'independent actual transfer acceptance')
 ta=load(pin(g['transferAcceptance'],1048576));need(str(ta.get('status','')).startswith('PASS') and ta.get('archiveSHA256')==g.get('archiveSHA256'),'transfer acceptance same archive')
 spec=load(D/'preregistration.json');originmap=load(D/'origin-map.json');manifest=load(D/'manifest.json');mh=sha(D/'manifest.json')
 need(mh==g.get('manifestSHA256') and manifest['sourcePinsSHA256']==g['sourcePinsSHA256'],'installed manifest exact GO')
 output=ROOT/'build52';need(not output.exists() and not (ROOT/'tmp').exists(),'fresh private build namespace');output.mkdir();(ROOT/'tmp').mkdir()
 env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin',LANG='C',LC_ALL='C',TZ='UTC',HOME='/Users/zebulun',TMPDIR=str(ROOT/'tmp'))
 led=Ledger(output/'children',52,env);images=[];headers=[]
 def guard():
  need(time.monotonic()-led.started<7800,'whole build52 phase deadline')
  need(sha(gp)==gh and sha(D/'manifest.json')==mh,'GO/manifest immutable');authorize('build',gp)
  expected={m['path'] for m in manifest['members']}|{'package/manifest.json'}
  actual={'package/'+str(p.relative_to(D)) for p in D.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
  need(actual==expected,'complete immutable installed member set')
  for m in manifest['members']:pin(dict(m,path=str(ROOT/m['path'])),67108864)
  for q in images:pin(q['C']);
  for q in headers:pin(q['header']);pin(q['runner'])
 def identity(phase):
  def query(label,argv):
   guard();o,e,_=led.call(phase+'-'+label,argv,30);guard();need(not e,'identity stderr');return o.decode().strip()
  compiler=Path(query('resolved-clang',['/usr/bin/xcrun','--find','clang'])).resolve(strict=True)
  sdk=Path(query('sdk-path',['/usr/bin/xcrun','--sdk','macosx','--show-sdk-path'])).resolve(strict=True)
  sdkver=query('sdk-version',['/usr/bin/xcrun','--sdk','macosx','--show-sdk-version'])
  version=query('clang-version',[str(compiler),'--version']);target=query('clang-target',[str(compiler),'-dumpmachine'])
  osv=query('OS-version',['/usr/bin/sw_vers','-productVersion']);osb=query('OS-build',['/usr/bin/sw_vers','-buildVersion'])
  e=spec['expectedHost'];need(version.splitlines()[0]==e['version'] and target==e['target'] and sdkver==e['SDK'] and osv==e['OS'] and osb==e['OSBuild'],'exact selected compilerSDKOS identity')
  settings={str(p):sha(p) for p in sorted(sdk.glob('SDKSettings.*')) if p.is_file() and not p.is_symlink()};need(settings,'SDKsettings present')
  return dict(compiler=str(compiler),compilerSHA256=sha(compiler),usrBinClangSHA256=sha('/usr/bin/clang'),SDK=str(sdk),SDKVersion=sdkver,SDKSettings=settings,version=version,target=target,OS=osv,OSBuild=osb)
 def current(base):
  need(str(Path(base['compiler']).resolve(strict=True))==base['compiler'] and sha(base['compiler'])==base['compilerSHA256'] and sha('/usr/bin/clang')==base['usrBinClangSHA256'],'stable compiler binary identities')
  need(str(Path(base['SDK']).resolve(strict=True))==base['SDK'],'stable canonical SDKroot')
  need({str(p):sha(p) for p in sorted(Path(base['SDK']).glob('SDKSettings.*')) if p.is_file() and not p.is_symlink()}==base['SDKSettings'],'stable SDKsettings identity');return base.copy()
 def resolve(pinrow):
  target=originmap[pinrow['path']];need(isinstance(target,str),'runtime operand must be ordinary exact file, no chunk compiler input');p=ROOT/target;pin(dict(pinrow,path=str(p)));return p
 def macho(p,kind):
  b=p.read_bytes();need(len(b)>=32 and b[:4]==b'\xcf\xfa\xed\xfe' and struct.unpack_from('<I',b,4)[0]==0x100000c and struct.unpack_from('<I',b,12)[0]==kind,'thinARM64 output kind')
 try:
  guard();before=identity('before');save(output/'identity-before.json',before);env['SDKROOT']=before['SDK'];save(output/'effective-environment.json',dict(environment=env,allOtherInheritedVariablesRemoved=True,removedNames=sorted(set(os.environ)-set(env))))
  # All19 C builds complete before any derived header/consumer.
  for row in spec['entries']:
   guard();current(before);name=row['workload'];folder=output/name;folder.mkdir();c=folder/'c.dylib'
   argv=[s.replace('$RESOLVED_CLANG',before['compiler']).replace('$TASK_ROOT',str(D/'c-inputs')).replace('$FRESH_BUILD',str(output)) for s in row['CBuild']]
   need(all('$' not in s for s in argv) and argv[:4]==[before['compiler'],'-O2','-std=gnu11','-dynamiclib'] and argv[-2:]==['-o',str(c)],'exact materialized C argv')
   led.call('C-'+name,argv,180);guard();current(before);macho(c,6)
   images.append(dict(workload=name,C=ref(c),symbol=row['CSymbol'],argv=argv,compilerIdentityBefore=before,compilerIdentityAfter=current(before)));save(output/'C-images.json',images)
  for row,crow in zip(spec['entries'],images):
   guard();current(before);need(row['workload']==crow['workload'],'exact cohortorder');folder=output/row['workload'];hp=folder/'header.h'
   c=pin(crow['C']).read_bytes();b0=resolve(row['OFF']).read_bytes();b1=resolve(row['LC']).read_bytes();hb=header(row,b0,b1,c)
   need(len(hb)<=67108864 and not hp.exists(),'bounded fresh header');hp.write_bytes(hb);hp.chmod(0o444);hpin=ref(hp)
   runner=folder/'runner';argv=[before['compiler'],'-O2','-std=c11','-include',str(hp),str(D/'sources/timing-host-telemetry.c'),'-o',str(runner)]
   need(sha(D/'sources/timing-host-telemetry.c')==spec['consumerSource']['sha256'],'typed Csource role/hash')
   save(folder/'header-receipt.json',dict(header=hpin,OFF=row['OFF'],LC=row['LC'],C=crow['C'],CSymbol=row['CSymbol'],featureRequirements=row['nativeFeatureRequirements'],entryOffsets=[row['OFF']['offset'],row['LC']['offset']],privateContext='unchanged cb3f private reset zeroed sync context;16M fuel/four pools',bodyUnchanged=True))
   led.call('consumer-'+row['workload'],argv,180);guard();current(before);pin(hpin);macho(runner,2)
   headers.append(dict(workload=row['workload'],header=hpin,runner=ref(runner),C=crow['C'],argv=argv,compilerIdentityBefore=before,compilerIdentityAfter=current(before),nativeCalls=0));save(output/'consumer-images.json',headers)
  guard();after=identity('after');save(output/'identity-after.json',after);need(before==after,'wholecohortidentity stable')
  need(len(images)==19 and len(headers)==19 and len(led.rows)==52 and led.terminal()['allClosed'],'exact52 closed')
  save(output/'report.json',dict(status='PASS_FRESH_C19_CONSUMER19_BUILD52_IDENTITY_ONLY',CBuilds=19,consumerBuilds=19,identityQueries=14,children=52,nativeCalls=0,timingCalls=0,sourcePinsSHA256=g['sourcePinsSHA256'],preregistrationSHA256=g['preregistrationSHA256'],archiveSHA256=g['archiveSHA256'],manifestSHA256=mh,rootFunctional285AcceptanceSHA256=g['rootFunctional285AcceptanceSHA256'],functionalQualified=False,quietQualified=False,SDKWholeTreeHashQualified=False,images=headers))
 except BaseException as ex:save(output/'failure.json',dict(exception=repr(ex),children=len(led.rows),noRetry=True));raise
 finally:save(output/'terminal.json',dict(**led.terminal(),failure=(output/'failure.json').exists(),nativeCalls=0,timingCalls=0))
if __name__=='__main__':main()
