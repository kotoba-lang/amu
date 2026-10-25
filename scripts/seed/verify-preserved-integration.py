#!/usr/bin/env python3
"""Correctness-only integration of frozen source; no timing/search or host-language compiler.

Ported after the C loader was removed (scripts/seed/RETIRED.md): every compiler and guest
call goes through the C-free aarch64 runner from a selfhost-bootstrap.py output
(--bootstrap). Run on arm64 Linux.
"""
import argparse,hashlib,json,os,pathlib,platform,re,subprocess,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
def require_smoke_42(stdout,stderr):
 assert stdout==b'42\n' and stderr==b'', 'smoke result must be exactly 42, no diagnostics'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--main',action='store_true');ap.add_argument('--bootstrap',type=pathlib.Path,required=True);a=ap.parse_args()
 if platform.system()!='Linux' or platform.machine() not in ('aarch64','arm64'):raise SystemExit('requires arm64 Linux')
 out=a.output.resolve();out.mkdir(exist_ok=False,parents=True);host=out/'host';art=out/'artifacts';host.mkdir();art.mkdir()
 archive=ROOT/'docs/evidence/native-selfhost-paused-20261012/evidence.tgz'
 cp=json.loads((archive.parent/'checkpoint.json').read_text());assert sha(archive)==cp['evidence_archive']['sha256']
 paths=[p for p in (ROOT/('seed/MANIFEST' if a.main else 'seed/preserved-20261012/MANIFEST')).read_text().splitlines() if p and not p.startswith('#')];assert len(paths)==16
 unity=b''.join((ROOT/p).read_bytes()+b'\n' for p in paths);source=art/'seed-unity.kotoba';source.write_bytes(unity)
 loader=host/'R-aarch64.elf';loader.write_bytes((a.bootstrap.resolve()/'R-aarch64.elf').read_bytes());loader.chmod(0o755);loader_pin=sha(loader)
 env=dict(os.environ);env.update(KEXE_COMMAND='1',KEXE_STACK_BYTES='8388608',KEXE_CAP_RESOURCES_35=str(art),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(art))
 calls=[]
 def run(argv,name,expect=0):
  inputs=[source,loader]
  for arg in argv[1:]:
   path=pathlib.Path(str(arg))
   if path.is_file() and path not in inputs:inputs.append(path)
  pins={str(p):sha(p) for p in inputs}
  with (host/(name+'.stdout')).open('wb') as stdout,(host/(name+'.stderr')).open('wb') as stderr:
   call_env=dict(env)
   if name=='policy-free-run':call_env.pop('KEXE_COMMAND',None)
   r=subprocess.run([str(x) for x in argv],cwd=art,env=call_env,stdout=stdout,stderr=stderr,timeout=1800)
  assert all(sha(pathlib.Path(p))==v for p,v in pins.items()),'input mutation'
  calls.append({'label':name,'argv':[str(x) for x in argv],'exit':r.returncode});(host/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
  if r.returncode!=expect:
   stdout=(host/(name+'.stdout')).read_bytes()[-4000:]
   stderr=(host/(name+'.stderr')).read_bytes()[-4000:]
   raise AssertionError(f'{name}: exit {r.returncode}, expected {expect}; stdout={stdout!r}; stderr={stderr!r}')
  return (host/(name+'.stdout')).read_bytes()+(host/(name+'.stderr')).read_bytes()
 frozen='workspace/held-compiler-cli30-bounded-balanced-byte-tree-token-capacity-picojpeg-fixedpoint6-source-v4-20261012-next/run-outputs/G4.bin'
 original19='workspace/held-compiler-cli30-bounded-balanced-byte-tree-token-capacity-picojpeg-g4-original19-compile38-source-v4-20261012-next/run-outputs/'
 with tarfile.open(archive) as t:
  receipt=json.loads((ROOT/'seed/adoption-20261022.json').read_text()) if a.main else None
  bootstrap=host/'historical-producer.bin';bootstrap.write_bytes((ROOT/receipt['bootstrapPath']).read_bytes() if a.main else t.extractfile(frozen).read())
  if not a.main:assert sha(bootstrap)==cp['fixed_point']['native_sha256']
  original_report=json.loads(t.extractfile(original19+'report.json').read())
  symbols={c['label'].removesuffix('-extract'):c['case']['symbol'] for c in original_report['calls'] if c['case']['kind']=='extract'}
  source_members={pathlib.PurePosixPath(m.name).stem:m for m in t.getmembers() if m.name.startswith(original19) and m.name.endswith('.kotoba')};source_members.pop('seed-unity',None);assert len(source_members)==19,len(source_members)
  expected={}
  for name,m in source_members.items():
   (art/(name+'.kotoba')).write_bytes(t.extractfile(m).read());expected[name]=hashlib.sha256(t.extractfile(original19+name+'.bin').read()).hexdigest()
 if a.main:
  receipt=json.loads((ROOT/'seed/adoption-20261022.json').read_text())
  if 'policyNativeGoldenPath' in receipt:
   golden=(ROOT/receipt['policyNativeGoldenPath']).resolve();golden_archive=(ROOT/receipt['policyNativeGoldenArchivePath']).resolve()
   assert golden.is_relative_to(ROOT.resolve()) and golden_archive.is_relative_to(ROOT.resolve())
   assert sha(golden)==receipt['policyNativeGoldenSHA256'] and sha(golden_archive)==receipt['policyNativeGoldenArchiveSHA256']
   baseline=json.loads(golden.read_text())
   assert baseline['producerNativeSHA256']==receipt['historicalReferenceProducerSHA256']
   assert baseline['sourceUnitySHA256']==receipt['historicalReferenceSourceUnitySHA256']
  else:
   baseline=json.loads((ROOT/'seed/main-pre-policy-native19.json').read_text())
   assert baseline['producerNativeSHA256']==receipt['previousMainSafetySnapshot']['nativeImageSHA256']
   golden_archive=ROOT/'docs/evidence/native-selfhost-paused-20261012/main-pre-policy-native19.tgz'
  historical={row['workload']:row['nativeSHA256'] for row in baseline['images']}
  assert set(historical)==set(expected)
  with tarfile.open(golden_archive) as old:
   for name,digest in historical.items():assert hashlib.sha256(old.extractfile(name+'.bin').read()).hexdigest()==digest
  for row in baseline['images']:assert sha(art/(row['workload']+'.kotoba'))==row['sourceSHA256']
  evidence=receipt['currentAll19Evidence']
  pinned={}
  for name,row in evidence.items():
   if not isinstance(row,dict):continue
   path=(ROOT/row['path']).resolve();assert path.is_relative_to(ROOT.resolve()) and sha(path)==row['sha256']
   pinned[name]=json.loads(path.read_text())
  build=pinned['buildReport'];images_by_name=pinned['images'];exactness=pinned['exactness']
  # the all-19 evidence names the compiler that built it; a later round's compiler must reproduce its images (below)
  assert build['sourceCommit']==evidence['sourceCommit']==evidence.get('producerSourceCommit',receipt['sourceCommit'])
  assert build['chain']['G1']==evidence.get('producerNativeSHA256',receipt['nativeImageSHA256'])==build['chain']['Gstar']
  assert exactness['status']=='PASS' and exactness['workloads']==len(expected)==19
  current={name:row['native']['sha256'] for name,row in images_by_name.items()}
  exact={row['workload']:row['imageSHA256'] for row in exactness['rows'] if row['exact']}
  assert len(exact)==len(exactness['rows'])==19 and current==exact
  assert set(current)==set(expected)
  current_sources={}
  ports=ROOT/'bench/embench/reproduce-20261015/ports'
  for name,row in images_by_name.items():
   workload_source=(ports/('official-'+name+'.kotoba')).resolve()
   assert workload_source.is_relative_to(ROOT.resolve())
   assert sha(workload_source)==row['sourceSHA256']
   source_copy=art/(name+'-current.kotoba')
   source_copy.write_bytes(workload_source.read_bytes())
   assert sha(source_copy)==row['sourceSHA256']
   current_sources[name]=source_copy
  expected=current
 producer=bootstrap;gens=[]
 for n in range(1,4):
  container=art/f'G{n}.kseed';image=art/f'G{n}.bin';prefix=[loader,producer,'0','0','aarch64','35,37,38,39','--']
  run(prefix+['compile',source,'--target','aarch64-macos','--output',container],f'G{n}-compile')
  run(prefix+['extract-native',container,'--symbol','main','--output',image],f'G{n}-extract')
  gens.append({'generation':n,'bytes':image.stat().st_size,'sha256':sha(image),'containerSHA256':sha(container)});producer=image
 assert len({g['sha256'] for g in gens})==1 and len({g['containerSHA256'] for g in gens})==1,'fixed point mismatch'
 if a.main:assert gens[0]['sha256']==receipt['nativeImageSHA256'],'adopted image differs from the receipt'
 prefix=[loader,producer,'0','0','aarch64','35,37,38,39','--']
 smoke=art/'smoke.kotoba';smoke.write_text('(ns smoke (:export [main]))\n(defn main [] :i64 42)\n')
 policies=['{:allow #{}}','{:allow #{} :deny #{[:cap/call 37]}}','{:allow #{}} ; [:cap/call 37]','{:allow #{[:cap/call 37]}}','not-edn','{:deny #{[:cap/call 37]}}','{:allow #{[:cap/call 999]}}']
 for i,text in enumerate(policies):
  policy=art/f'policy-{i}.edn';policy.write_text(text)
  for command in ['compile','check']:
   for project in [False,True]:
    tag=f'policy-{i}-{command}-{project}';target=art/(tag+'.kseed');argv=prefix+[command,smoke,'--policy',policy,'--target','aarch64-macos']
    if project:argv+=['--source-path',art,'--unpinned']
    if command=='compile':argv+=['--output',target]
    logs=run(argv,tag,expect=1);assert b'E2170' in logs and not target.exists(),tag+' did not fail closed'
 for cmd in ['compile','check']:
  missing=art/'nonexistent-policy.edn';target=art/f'policy-missing-{cmd}.kseed';argv=prefix+[cmd,smoke,'--policy',missing,'--target','aarch64-macos']
  if cmd=='compile':argv+=['--output',target]
  logs=run(argv,'policy-missing-'+cmd,expect=1);assert b'E2170' in logs and not target.exists()
 for command in ['compile','check']:
  for project in [False,True]:
   tag='policy-missing-value-'+command+'-'+str(project);target=art/(tag+'.kseed');argv=prefix+[command,smoke,'--target','aarch64-macos']
   if project:argv+=['--source-path',art,'--unpinned']
   if command=='compile':argv+=['--output',target]
   logs=run(argv+['--policy'],tag,expect=1);assert b'E2170' in logs and not target.exists()
 run(prefix+['compile',smoke,'--target','aarch64-macos','--output',art/'smoke.kseed'],'policy-free-compile')
 run(prefix+['extract-native',art/'smoke.kseed','--symbol','main','--output',art/'smoke.bin'],'policy-free-extract')
 run([loader,art/'smoke.bin','0','0','aarch64','0'],'policy-free-run');require_smoke_42((host/'policy-free-run.stdout').read_bytes(),(host/'policy-free-run.stderr').read_bytes())
 images=[]
 for name,oldsha in expected.items():
  container=art/(name+'-new.kseed');image=art/(name+'-new.bin')
  source_input=current_sources[name] if a.main else art/(name+'.kotoba')
  run(prefix+['compile',source_input,'--target','aarch64-macos','--output',container],name+'-compile')
  run(prefix+['extract-native',container,'--symbol',symbols[name],'--output',image],name+'-extract');assert sha(image)==oldsha,name+' payload changed'
  images.append({'workload':name,'sha256':sha(image),'baselineImageExact':True})
 report={'status':'PASS_MAIN_AND_PRESERVED_POLICY_SAFETY' if a.main else 'PASS_PRESERVED_SOURCE_SAFETY_REINTEGRATION','sourceUnitySHA256':hashlib.sha256(unity).hexdigest(),'generations':gens,'explicitPolicyRefusals':len(policies)*4+6,'policyFreeResult':42,'inputCorpus':'current-official-all19' if a.main else 'preserved-original19','cFreeRunnerSHA256':loader_pin,'cCompilerOrLoader':False,'performanceMeasurement':False,'goalStatus':receipt.get('performanceGoalStatus','unspecified') if a.main else 'paused','mainDefaultCompilerChanged':a.main,'publicLoaderChanged':False}
 report['currentAll19Images' if a.main else 'original19Images']=images
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
