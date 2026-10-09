#!/usr/bin/env python3
# BOOTSTRAP-TOOL: observe native Kotoba and unchanged C; no product dependency.
import pathlib,subprocess,json,re,ctypes,hashlib,statistics,time,sys,argparse
parser=argparse.ArgumentParser();parser.add_argument('directory',type=pathlib.Path)
parser.add_argument('--reference',type=pathlib.Path);args=parser.parse_args()
p=args.directory.resolve();reference=args.reference.resolve() if args.reference else None
runner=p.parent/'runner';up=p.parent/'upstream'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(up/'src/edn/libedn.c')=='2604a80fbe70e2b6bc4276649bfb5974d02e18f70b84fc804c7d52bf47f6a20e'
report_path=p/'results.json'
if report_path.exists():raise SystemExit('refusing to replace evidence')
subprocess.run(['clang','-O2','-std=gnu11','-dynamiclib','-I',str(up/'support'),str(p/'c-bridge.c'),'-o',str(p/'c.dylib')],check=True)
c=ctypes.CDLL(str(p/'c.dylib'));c.stage_cell.restype=ctypes.c_int64;c.stage_cell.argtypes=[ctypes.c_int64]*8
def offset(symbol,root):return int(re.search(r':offset (\d+)',(root/(symbol+'-extract.log')).read_text()).group(1))
def native(symbol,n,calls=1,warm=0,root=p):
 return json.loads(subprocess.check_output([str(runner),'raw',str(root/(symbol+'.bin')),str(offset(symbol,root)),'aarch64',str(n),str(calls),str(warm),'16777216'],text=True))
def crun(n,calls=1,warm=0):
 return json.loads(subprocess.check_output([str(runner),'dylib',str(p/'c.dylib'),'batch','aarch64',str(n),str(calls),str(warm),'16777216'],text=True))
def load():return float(subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).split()[1])
report={'format':'amu.coscientist.edn-full/v1','officialEmbenchScore':False,'formalPerfgateQualified':False,'compilerSha256':sha(p.parent/'images/r6m'),'runnerSha256':sha(runner),'upstreamSha256':sha(up/'src/edn/libedn.c'),'sourceSha256':sha(p/'edn.kotoba'),'nativeSha256':sha(p/'batch.bin'),'cSha256':sha(p/'c.dylib'),'bridgeSha256':sha(p/'c-bridge.c'),'nativeCheck':(p/'check.log').read_text(),'clang':subprocess.check_output(['clang','--version'],text=True),'host':subprocess.check_output(['uname','-a'],text=True),'cells':[],'batches':[],'rows':[]}
if (p/'prototype.json').exists():
 report['prototype']=json.loads((p/'prototype.json').read_text())
 assert report['nativeSha256']==report['prototype']['patchedSha256']
for stage in range(9):
 for i in range(603):
  encoded=stage*1024+i;expected=c.stage_cell(encoded,0,0,0,0,0,0,0);sample=native('stage-cell',encoded)
  assert sample['result']==expected,(stage,i,sample,expected)
  report['cells'].append({'stage':stage,'cell':i,'Kotoba':sample['result'],'C':expected})
 report_path.write_text(json.dumps(report,indent=2)+'\n');print('all 603 state cells match after stage',stage,flush=True)
for n in (0,1,2,17,32):
 a=native('batch',n);b=crun(n);assert a['result']==b['result']==(0 if n==0 else 1),(n,a,b)
 report['batches'].append({'iterations':n,'Kotoba':a,'C':b})
 if reference:
  r=native('batch',n,root=reference);assert r['result']==a['result'];report['batches'][-1]['reference']=r
iterations=32;arms=[('Kotoba',lambda count,warm:native('batch',iterations,count,warm)),('C',lambda count,warm:crun(iterations,count,warm))]
if reference:
 arms.append(('reference',lambda count,warm:native('batch',iterations,count,warm,root=reference)))
 report.update(referenceSourceSha256=sha(reference/'edn.kotoba'),referenceNativeSha256=sha(reference/'batch.bin'))
counts={}
for name,run in arms:
 s=run(3,1);counts[name]=max(1,round(300000000/(s['elapsedNanoseconds']/3)))
report.update(iterationsPerCall=iterations,warmupCalls=1,samplesPerArm=30,countByArm=counts)
for i in range(30):
 for name,run in arms[i%len(arms):]+arms[:i%len(arms)]:
  before=load();assert before<=4,before
  s=run(counts[name],1);after=load();assert after<=4,after
  assert s['result']==1 and s['calls']==counts[name] and s['warmupCalls']==1 and s['elapsedNanoseconds']>=50000000,s
  s.update(arm=name,pair=i,loadBefore=before,loadAfter=after,recordedAt=time.time());report['rows'].append(s)
 report_path.write_text(json.dumps(report,indent=2)+'\n')
 if i%5==4:print('paired timing samples',i+1,flush=True)
report['summary']={}
for name,_ in arms:
 xs=[s['elapsedNanoseconds']/(s['calls']*iterations) for s in report['rows'] if s['arm']==name];mu=statistics.mean(xs);sd=statistics.stdev(xs)
 report['summary'][name]={'meanNsPerBody':mu,'sdNs':sd,'relativeSd':sd/mu}
report['summary']['KotobaTimeOverC']=report['summary']['Kotoba']['meanNsPerBody']/report['summary']['C']['meanNsPerBody']
if reference:
 b=report['summary']['reference'];c=report['summary']['Kotoba'];gain=1-c['meanNsPerBody']/b['meanNsPerBody'];gap=b['meanNsPerBody']-c['meanNsPerBody'];spread=b['sdNs']+c['sdNs']
 report['summary']['candidateVsReference']={'speedup':b['meanNsPerBody']/c['meanNsPerBody'],'timeReduction':gain,'gapNs':gap,'combinedSdNs':spread,'diagnosticGatePass':gain>=.05 and gap>spread and b['relativeSd']<=.10 and c['relativeSd']<=.10,'formalPerfgateQualified':False}
report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2),flush=True)
