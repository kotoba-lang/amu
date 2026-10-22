# BOOTSTRAP-TOOL: measurements and statistics; never used by the product.
import pathlib,subprocess,json,statistics,hashlib,time,sys
if len(sys.argv) != 2:
 raise SystemExit('usage: measure-identity-division.py <evidence-directory>; runner must be in its parent')
p=pathlib.Path(sys.argv[1]).resolve()
subprocess.run(['clang','-O2','-std=c11','-dynamiclib',str(p/'div-one.c'),'-o',str(p/'div-one-c.dylib')],check=True)
value=17
for _ in range(10000):value=(value*6364136223846793005+1)&((1<<64)-1)
if value>>63:value-=1<<64
arms=[('r6m','raw',p/'div-one.bin','0'),('candidate','raw',p/'div-one-candidate.bin','0'),('clang-c11','dylib',p/'div-one-c.dylib','run')]
report={'format':'amu.coscientist.reflect/v1','scope':'synthetic signed-i64 quotient-by-one recurrence; NOT Embench','expected':value,'calls':30000,'samplesPerArm':30,'warmupCalls':1,'minimumTimedNs':50000000,'maximumLoad1':4,'artifacts':{x[0]:hashlib.sha256(x[2].read_bytes()).hexdigest() for x in arms},'runnerSha256':hashlib.sha256((p.parent/'runner').read_bytes()).hexdigest(),'compiler':subprocess.check_output(['clang','--version'],text=True),'host':subprocess.check_output(['uname','-a'],text=True),'rows':[]}
for i in range(30):
 for name,kind,f,entry in arms[i%3:]+arms[:i%3]:
  before=float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1]);assert before<=4,before
  s=json.loads(subprocess.check_output([str(p.parent/'runner'),kind,str(f),entry,'aarch64','0',str(report['calls']),'1','16777216'],text=True));after=float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1]);assert after<=4,after
  assert s['result']==value and s['calls']==report['calls'] and s['warmupCalls']==1 and s['elapsedNanoseconds']>=report['minimumTimedNs'],s
  s.update(arm=name,pair=i,loadBefore=before,loadAfter=after,recordedAt=time.time());report['rows'].append(s)
 (p/'candidate-results.json').write_text(json.dumps(report,indent=2)+'\n')
report['summary']={}
for name,*_ in arms:
 xs=[r['elapsedNanoseconds']/r['calls'] for r in report['rows'] if r['arm']==name];report['summary'][name]={'meanNs':statistics.mean(xs),'medianNs':statistics.median(xs),'sdNs':statistics.stdev(xs),'minNs':min(xs),'maxNs':max(xs),'relativeSd':statistics.stdev(xs)/statistics.mean(xs)}
for baseline in ('r6m','clang-c11'):
 b=report['summary'][baseline];c=report['summary']['candidate'];gain=1-c['meanNs']/b['meanNs'];gap=b['meanNs']-c['meanNs'];spread=b['sdNs']+c['sdNs']
 report['summary']['candidate-vs-'+baseline]={'speedup':b['meanNs']/c['meanNs'],'timeReduction':gain,'gapNs':gap,'combinedSdNs':spread,'diagnosticGatePass':gain>=.05 and gap>spread and b['relativeSd']<=.10 and c['relativeSd']<=.10,'formalPerfgateQualified':False}
(p/'candidate-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2),flush=True)
