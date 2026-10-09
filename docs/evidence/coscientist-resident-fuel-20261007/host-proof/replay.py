#!/usr/bin/env python3
"""Local selected host admission proof replay, stdlib only. No native/solver/network/timing."""
from pathlib import Path
import argparse,json,hashlib,tarfile,shutil,re,sys
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args();here=Path(__file__).resolve().parent;m=load(here/'host-proof.manifest.json');arc=here/'host-proof.tgz'
 assert sha(arc)==m['archive']['sha256'],'archivehash';assert sha(Path(__file__))==m['reader']['sha256'],'readerhash'
 args.out.mkdir(exist_ok=False);root=args.out/'payload';root.mkdir();sys.dont_write_bytecode=True
 allowed=[args.out.resolve(),here.resolve(),Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve()]
 def audit(event,v):
  if event in ['subprocess.Popen','os.system','socket.connect']:raise PermissionError('offline')
  if event=='open'and isinstance(v[0],(str,bytes)):
   p=Path(v[0].decode()if isinstance(v[0],bytes)else v[0]).resolve();assert any(p==x or x in p.parents for x in allowed),'external input'
 sys.addaudithook(audit)
 with tarfile.open(arc)as t:
  seen=set()
  for e in t.getmembers():
   p=Path(e.name);assert e.isfile()and not p.is_absolute()and '..'not in p.parts and e.name not in seen;seen.add(e.name);d=root/p;d.parent.mkdir(parents=True,exist_ok=True)
   with t.extractfile(e)as f,d.open('wb')as g:shutil.copyfileobj(f,g)
 assert sha(root/'inventory.json')==m['inventorySHA256'];inv=load(root/'inventory.json');assert len(inv['entries'])==737
 for e in inv['entries']:assert sha(root/e['member'])==e['sha256']and(root/e['member']).stat().st_size==e['bytes']
 assert {str(p.relative_to(root))for p in root.rglob('*')if p.is_file()}=={e['member']for e in inv['entries']}|{'inventory.json'}
 for o in inv['owners']:
  x=load(root/o['manifest']);items=x if isinstance(x,list)else[{'path':k,'sha256':v['sha256']if isinstance(v,dict)else v}for k,v in x.items()];assert len(items)==o['count']
  for e in items:assert sha(root/o['base']/e['path'])==e['sha256']
 def original(s):return root/inv['relocations'][str(s)]
 W=root/'resident';S=W/'root-timing-host';T=S/'team-host-setup-tests';src=(S/'timing-host.c').read_text();assert sha(S/'timing-host.c')=='39cdbfa14ace3196029c5f1d50be8d2a1200d7aa9ab3c08d2435837e23b752eb'
 base=original('/Users/junkawasaki/github/wt/amu-seed17/bench/runtime-comparison/kexe-benchmark.c').read_text();loader=original('/private/tmp/amu-embedded-host-feature-gate-20261007/host-feature-loader.c').read_text()
 assert src[:src.index('static struct bench_shared shared;')]==base[:base.index('static struct bench_shared shared;')]
 assert src[src.index('  memset(&shared,'):].replace('  HG_STAGE("ENTRY");\n','')==base[base.index('  memset(&shared,'):]
 def clean(s):return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S))
 def fn(s,n):
  a=s.index('static int '+n+'(');return s[a:s.index('\n}',a)+2]
 for n in ['kexe_host_cpu_feature','kexe_embedded_host_gate']:assert clean(fn(src,n))==clean(fn(loader,n))
 assert src[src.index('int main('):].split('\n')[1]=='  if(!kexe_embedded_host_gate(KEXE_EMBEDDED_ISA))return 2;'
 assert src.index('if(strcmp(argv[4],KEXE_EMBEDDED_ISA)')<src.index('memory = mmap(')<src.index('if(!timing_known_image(memory,artifact_bytes,offset))')<src.index('mprotect(memory, mapped, PROT_READ | PROT_EXEC)')
 assert 'size==timing_known_sizes[i] && offset==timing_known_offsets[i]'in src and 'memcmp(bytes,timing_known_images[i],size)==0'in src
 assert all(x not in src for x in ['pthread_create(','fork(','sigaction(','signal(']);assert len(re.findall(r'context->fuel\s*=',src))==2
 c=src[src.index('static void *timing_known_c_library('):src.index('\nint main(')]
 assert c.index('strcmp(symbol,TIMING_KNOWN_C_SYMBOL)')<c.index('fopen(path,"rb")')<c.index('memcmp(buf,timing_known_c_bytes+pos,need)')<c.index('mkdtemp(dir)')<c.index('write(fd,timing_known_c_bytes+pos')<c.index('fchmod(fd,0400)')<c.index('dlopen(file,RTLD_NOW|RTLD_LOCAL)')<c.index('unlink(file);rmdir(dir);')
 assert 'fgetc(input)!=EOF'in c and 'ferror(input)'in c and 'O_WRONLY|O_CREAT|O_EXCL,0600'in c and 'dlopen(argv[2]'not in src
 raw=0
 for phase,p in [('v1',T),('v2',T/'v2')]:
  r=load(p/'report.json');rows=r['controls']if phase=='v1'else r['runs'];assert len(rows)==24 and len(r['builds'])==8
  for e in rows:
   rr=load(p/e.get('rawPath',e['variant']+'/'+e['case']+'.json'))
   for k in ['case','variant','exit','stdout','stderr','stages']:assert rr[k]==e[k]
   stages=[x for x in ['RX','ENTRY']if 'HG_STAGE '+x+'\n'in rr['stderr']];assert stages==rr['stages']
   if rr['exit']==0:
    j=json.loads(rr['stdout']);assert j['result']==0 and j['contextFuelBefore']==j['contextFuelAfter']==32 and j['contextFuelConsumed']==0
    if rr['variant']!='production6':assert stages==['RX','ENTRY']
   elif rr['case']=='absent-immutable-C-declaration':assert rr['exit']==1 and 'no immutable C library declared'in rr['stderr']and not stages and not rr['stdout']
   else:assert rr['exit']==2 and not stages and not rr['stdout']
   raw+=1
 V=T/'v3';r=load(V/'report.json');assert len(r['controls'])==8 and len(r['builds'])==3
 for e in r['controls']:
  assert load(V/(e['case']+'.json'))==e;assert e['temporaryDirectorySetUnchanged']and e['diagnosticElapsedNotPerformance']
  if e['exit']==0:
   j=json.loads(e['stdout']);assert j['calls']==1 and j['warmupCalls']==0 and j['result']==0 and j['contextFuelBefore']==j['contextFuelAfter']==32 and j['contextFuelConsumed']==0
   if e['case']=='raw-known-RET-unaffected':assert e['stderr']=='HG_STAGE RX\nHG_STAGE ENTRY\n'
   else:
    q=re.fullmatch(r'HOST_TINY_CTOR path=(/private/tmp/amu-timing-C-[^ /]+/known.dylib) fileMode=400 dirMode=700\n(?:HG_STAGE ENTRY\n)?',e['stderr']);assert q and q[1]==e['privateCopyPath'];assert e['loadedPrivateFileMode']==400 and e['privateDirectoryMode']==700
  else:assert e['exit']==1 and e['stdout']==''and 'HOST_TINY_CTOR'not in e['stderr']and 'HG_STAGE'not in e['stderr']
  raw+=1
 h=(V/'embedded.h').read_text();arr=re.search(r'static const unsigned char timing_known_c_bytes\[\] = \{([0-9,]+)\};',h);assert bytes(map(int,arr[1].split(',')))==(V/'tiny-c.dylib').read_bytes()
 assert (V/'timing-host-frozen.c').read_bytes()==(S/'timing-host.c').read_bytes()
 K=W/'team-timing/timing-package';build=load(W/'team-timing/build-report.json');assert len(build['entries'])==19 and build['guestCalls']==build['performanceRuns']==0
 for e in build['entries']:
  p=K/e['workload'];assert load(p/'input-manifest.json')==e
  for f,k in [('baseline.bin','baselineNativeSHA256'),('candidate.bin','candidateNativeSHA256'),('c.dylib','CbinarySHA256'),('source.kotoba','sourceSHA256'),('immutable-header.h','immutableHeaderSHA256'),('runner','runnerSHA256')]:assert sha(p/f)==e[k]
  h=(p/'immutable-header.h').read_text();arrays={n:bytes(map(int,v.split(',')))for n,v in re.findall(r'static const unsigned char (\w+)\[\] = \{([0-9,]+)\};',h)}
  for a,f in [('known_baseline','baseline.bin'),('known_candidate','candidate.bin'),('timing_known_c_bytes','c.dylib')]:assert arrays[a]==(p/f).read_bytes()
  assert '#define KEXE_EMBEDDED_REQUIRED_HOST_FEATURES 6ULL'in h and '#define KEXE_EMBEDDED_ISA "aarch64"'in h and f'#define TIMING_KNOWN_C_SYMBOL "{e["Csymbol"]}"'in h
  assert re.search(r'timing_known_offsets\[\] = \{(\d+),(\d+)\}',h).groups()==(str(e['baselineOffset']),str(e['candidateOffset']))
  assert e['n']==(2000 if e['workload']=='depthconv'else 32)and e['requiredMask']==6 and e['expectedResult']==1
  b=load(p/'build.status.json');assert b['exit']==0 and b['sourceSHA256']==build['sourceSHA256']and b['headerSHA256']==e['immutableHeaderSHA256']
 assert [e['workload']for e in build['entries']if e['changedNative']]==['nettle-aes']
 report={'status':'PASS offline selected host source/admission/raw/package proof','selectedFiles':737,'ownerManifests':len(inv['owners']),'rawSetupControls':raw,'workloads':19,'packagePins':412,'source':'39cdbfa14ace3196029c5f1d50be8d2a1200d7aa9ab3c08d2435837e23b752eb','timedLoopAndContextExact':True,'futureRemote57Executed':False,'newNative':0,'newSolver':0,'performance':0,'limits':['Diagnostic elapsed values retained uninterpreted, no official scores','v1 raw-only source gap and sourcecopy race retained; v2 harness classification exit1 retained','C compiler version/flags unknown; exact C bytes/export/dependencies trusted, no reconstructed C build proof','Current raw receipts show trusted tinyC only; full19 runtime preflight and performance unexecuted','Context exclusive writer scoped owned host only, not generic ABI/security guarantee','Static source/order and saved process receipts, no universal OS/hardware/compiler proof']}
 (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
