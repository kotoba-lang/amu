#!/usr/bin/env python3
"""Correctness-only integration of frozen source; no timing/search or host-language compiler."""
import argparse,hashlib,json,os,pathlib,platform,re,subprocess,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
def require_smoke_42(stdout,stderr):
 assert stdout==b'42\n' and stderr==b'', 'smoke result must be exactly 42, no diagnostics'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--main',action='store_true');a=ap.parse_args()
 if (platform.system(),platform.machine())!=('Darwin','arm64'):raise SystemExit('requires macOS arm64')
 out=a.output.resolve();out.mkdir(exist_ok=False,parents=True);host=out/'host';art=out/'artifacts';host.mkdir();art.mkdir()
 archive=ROOT/'docs/evidence/native-selfhost-paused-20261012/evidence.tgz'
 cp=json.loads((archive.parent/'checkpoint.json').read_text());assert sha(archive)==cp['evidence_archive']['sha256']
 receipt=None
 if a.main:
  receipt=json.loads((ROOT/'seed/adoption-20261017.json').read_text())
  manifest_path=ROOT/receipt['manifestPath']
 else:
  manifest_path=ROOT/'seed/preserved-20261012/MANIFEST'
 paths=[p for p in manifest_path.read_text().splitlines() if p and not p.startswith('#')]
 if a.main:
  assert len(paths)==receipt['moduleCount']
  for row in receipt['sourceFiles']:
   path=ROOT/row['path'];assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],row['path']
 else:
  assert len(paths)==16
 unity=b''.join((ROOT/p).read_bytes()+b'\n' for p in paths);source=art/'seed-unity.kotoba';source.write_bytes(unity)
 if a.main:assert hashlib.sha256(unity).hexdigest()==receipt['sourceUnitySHA256']
 loader_source=ROOT/(receipt['loaderPath'] if a.main else 'seed/bootstrap/adopted-loader-20261012.c');loader_pin=sha(loader_source);loader=host/'loader'
 env=dict(os.environ);env.update(KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(art),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(art))
 calls=[]
 def run(argv,name,expect=0):
  inputs=[source,loader_source]+([loader] if loader.exists() else [])
  if len(argv)>1 and pathlib.Path(str(argv[1])).is_file():inputs.append(pathlib.Path(str(argv[1])))
  pins={str(p):sha(p) for p in inputs}
  with (host/(name+'.stdout')).open('wb') as stdout,(host/(name+'.stderr')).open('wb') as stderr:
   call_env=dict(env)
   if name=='policy-free-run':call_env.pop('KEXE_COMMAND',None)
   r=subprocess.run([str(x) for x in argv],cwd=art,env=call_env,stdout=stdout,stderr=stderr,timeout=1800)
  assert all(sha(pathlib.Path(p))==v for p,v in pins.items()),'input mutation'
  calls.append({'label':name,'argv':[str(x) for x in argv],'exit':r.returncode});(host/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
  assert r.returncode==expect,name
  return (host/(name+'.stdout')).read_bytes()+(host/(name+'.stderr')).read_bytes()
 run(['clang','-std=c11','-O2',loader_source,'-o',loader],'loader-build')
 frozen='workspace/held-compiler-cli30-bounded-balanced-byte-tree-token-capacity-picojpeg-fixedpoint6-source-v4-20261012-next/run-outputs/G4.bin'
 original19='workspace/held-compiler-cli30-bounded-balanced-byte-tree-token-capacity-picojpeg-g4-original19-compile38-source-v4-20261012-next/run-outputs/'
 with tarfile.open(archive) as t:
  bootstrap=host/'historical-producer.bin';bootstrap.write_bytes((ROOT/receipt['bootstrapPath']).read_bytes() if a.main else t.extractfile(frozen).read())
  if a.main:assert sha(bootstrap)==receipt['nativeImageSHA256']
  if not a.main:assert sha(bootstrap)==cp['fixed_point']['native_sha256']
  original_report=json.loads(t.extractfile(original19+'report.json').read())
  symbols={c['label'].removesuffix('-extract'):c['case']['symbol'] for c in original_report['calls'] if c['case']['kind']=='extract'}
  source_members={pathlib.PurePosixPath(m.name).stem:m for m in t.getmembers() if m.name.startswith(original19) and m.name.endswith('.kotoba')};source_members.pop('seed-unity',None);assert len(source_members)==19,len(source_members)
  expected={}
  for name,m in source_members.items():
   (art/(name+'.kotoba')).write_bytes(t.extractfile(m).read());expected[name]=hashlib.sha256(t.extractfile(original19+name+'.bin').read()).hexdigest()
 if a.main:
  if 'policyNativeGoldenPath' in receipt:
   golden=(ROOT/receipt['policyNativeGoldenPath']).resolve();golden_archive=(ROOT/receipt['policyNativeGoldenArchivePath']).resolve()
   assert golden.is_relative_to(ROOT.resolve()) and golden_archive.is_relative_to(ROOT.resolve())
   assert sha(golden)==receipt['policyNativeGoldenSHA256'] and sha(golden_archive)==receipt['policyNativeGoldenArchiveSHA256']
   baseline=json.loads(golden.read_text())
   assert baseline['producerNativeSHA256']==receipt['historicalReferenceProducerSHA256']
   assert baseline['sourceUnitySHA256']==receipt['historicalReferenceSourceUnitySHA256']
  assert {row['workload'] for row in baseline['images']}==set(expected)
  expected={row['workload']:row['nativeSHA256'] for row in baseline['images']}
  with tarfile.open(golden_archive) as old:
   for name,digest in expected.items():assert hashlib.sha256(old.extractfile(name+'.bin').read()).hexdigest()==digest
  for row in baseline['images']:assert sha(art/(row['workload']+'.kotoba'))==row['sourceSHA256']
 producer=bootstrap;gens=[]
 for n in range(1,4):
  container=art/f'G{n}.kseed';image=art/f'G{n}.bin';prefix=[loader,producer,'0','0','aarch64','35,37,38,39','--']
  run(prefix+['compile',source,'--target','aarch64-macos','--output',container],f'G{n}-compile')
  run(prefix+['extract-native',container,'--symbol','main','--output',image],f'G{n}-extract')
  gens.append({'generation':n,'bytes':image.stat().st_size,'sha256':sha(image),'containerSHA256':sha(container)});producer=image
 assert len({g['sha256'] for g in gens})==1 and len({g['containerSHA256'] for g in gens})==1,'fixed point mismatch'
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
  run(prefix+['compile',art/(name+'.kotoba'),'--target','aarch64-macos','--output',container],name+'-compile')
  run(prefix+['extract-native',container,'--symbol',symbols[name],'--output',image],name+'-extract');assert sha(image)==oldsha,name+' payload changed'
  images.append({'workload':name,'sha256':sha(image),'baselineImageExact':True})
 report={'status':'PASS_MAIN_AND_PRESERVED_POLICY_SAFETY' if a.main else 'PASS_PRESERVED_SOURCE_SAFETY_REINTEGRATION','sourceUnitySHA256':hashlib.sha256(unity).hexdigest(),'selfhostCompilerSHA256':receipt['nativeImageSHA256'] if a.main else None,'historicalReferenceCompilerSHA256':receipt['historicalReferenceProducerSHA256'] if a.main else None,'generations':gens,'explicitPolicyRefusals':len(policies)*4+6,'policyFreeResult':42,'original19Images':images,'trustedLoaderSHA256':loader_pin,'performanceMeasurement':False,'goalStatus':receipt.get('performanceGoalStatus','unspecified') if a.main else 'paused','currentSourceMainPath':a.main,'releaseOrDefaultLauncherChanged':False,'publicLoaderChanged':False}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
