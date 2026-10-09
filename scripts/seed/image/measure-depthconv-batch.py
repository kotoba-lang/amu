# BOOTSTRAP-TOOL: orchestrates native artifacts; no product dependency.
import pathlib,subprocess,json,statistics,hashlib,re,time,sys,argparse
parser=argparse.ArgumentParser(description='Compare selfhost depthconv batches with unchanged upstream C; research diagnostics only.')
parser.add_argument('directory',type=pathlib.Path)
parser.add_argument('--candidate',default='inline',choices=['table','unroll','inline'])
parser.add_argument('--baseline',default='base64',choices=['base64','table','unroll'])
parser.add_argument('--output',default='results.json')
args=parser.parse_args()
p=args.directory.resolve();runner=p.parent/'runner'
if (p/args.output).exists():raise SystemExit('refusing to replace an existing measurement')
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def call(arm,n,calls=1,warm=1):
 name,kind,file,entry=arm
 return json.loads(subprocess.check_output([str(runner),kind,str(p/file),str(entry),'aarch64',str(n),str(calls),str(warm),'16777216'],text=True))
def load():return float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
def offset(name,suffix=''):return int(re.search(r':offset (\d+)',(p/(name+suffix+'-extract.log')).read_text()).group(1))
up=p.parent/'upstream/src/depthconv/depthconv.c'
assert sha(up)=='a6aadf6e0741922d4b32b8a7821cbea64f9eae00ca8cb8603b1586ec49c94bad'
subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib',str(p/'c-bridge.c'),'-o',str(p/'c.dylib')],check=True)
expected=[-55,-22,-23,-52,18,-14,-5,54,-70,4,27,-51,-42,41,-6,59,-30,83,39,-74,-39,9,25,61,20,30,-8,-35,43,-59,26,19]
names=[args.baseline,args.candidate]
channels=[(name,'raw',name+'.bin',offset(name,'-output')) for name in names]+[('C','dylib','c.dylib','channel')]
correctness=[]
for arm in channels:
 for i,x in enumerate(expected):
  s=call(arm,i,1,0);assert s['result']==x,(arm,i,s)
  correctness.append(dict(arm=arm[0],channel=i,expected=x,sample=s))
arms=[(name,'raw',name+'.bin',offset(name)) for name in names]+[('C','dylib','c.dylib','batch')]
for arm in arms:
 for n in (1,2,17,2000):assert call(arm,n)['result']==1
counts={};iterations=2000
for arm in arms:
 s=call(arm,iterations,3);counts[arm[0]]=max(1,round(300000000/(s['elapsedNanoseconds']/3)))
report={'format':'amu.coscientist.depthconv-batch/v1','officialEmbenchScore':False,'iterationsPerCall':iterations,'warmupCalls':1,'samplesPerArm':30,'countByArm':counts,'correctness':correctness,'upstreamSha256':sha(up),'runnerSha256':sha(runner),'compilerSha256':sha(p.parent/'images/r6m'),'artifacts':{a[0]:sha(p/a[2]) for a in arms},'sources':{f:sha(p/f) for f in [name+'.kotoba' for name in names]+['c-bridge.c']},'clang':subprocess.check_output(['clang','--version'],text=True),'host':subprocess.check_output(['uname','-a'],text=True),'rows':[]}
for i in range(30):
 for arm in arms[i%3:]+arms[:i%3]:
  before=load();assert before<=4,before
  s=call(arm,iterations,counts[arm[0]],1);after=load();assert after<=4,after
  assert s['result']==1 and s['calls']==counts[arm[0]] and s['warmupCalls']==1 and s['elapsedNanoseconds']>=50000000,s
  s.update(arm=arm[0],pair=i,loadBefore=before,loadAfter=after,recordedAt=time.time());report['rows'].append(s)
 (p/args.output).write_text(json.dumps(report,indent=2)+'\n')
 if i%5==4:print('paired samples',i+1,flush=True)
report['summary']={}
for arm in arms:
 xs=[s['elapsedNanoseconds']/(s['calls']*iterations) for s in report['rows'] if s['arm']==arm[0]];mu=statistics.mean(xs);sd=statistics.stdev(xs)
 report['summary'][arm[0]]={'meanNsPerKernel':mu,'medianNsPerKernel':statistics.median(xs),'sdNs':sd,'relativeSd':sd/mu}
for baseline in [args.baseline,'C']:
 b=report['summary'][baseline];c=report['summary'][args.candidate];gain=1-c['meanNsPerKernel']/b['meanNsPerKernel'];gap=b['meanNsPerKernel']-c['meanNsPerKernel'];spread=b['sdNs']+c['sdNs']
 report['summary'][args.candidate+'-vs-'+baseline]={'speedup':b['meanNsPerKernel']/c['meanNsPerKernel'],'timeReduction':gain,'gapNs':gap,'combinedSdNs':spread,'diagnosticGatePass':gain>=.05 and gap>spread and b['relativeSd']<=.10 and c['relativeSd']<=.10,'formalPerfgateQualified':False}
(p/args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2),flush=True)
