#!/usr/bin/env python3
"""Bootstrap loader qualification only; frozen coverage floors, no performance work."""
import argparse,hashlib,json,os,pathlib,platform,re,shutil,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--trusted-bootstrap',action='store_true');a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 baseline=(ROOT/'fuzz/baselines/native-parser.edn').read_text();expected=re.search(r':loader-source-sha256 "([0-9a-f]{64})"',baseline)[1]
 loader=ROOT/('seed/bootstrap/adopted-loader-20261012.c' if a.trusted_bootstrap else 'tools/kexe_loader.c')
 if a.trusted_bootstrap:expected=json.loads((ROOT/'seed/adoption-20261012.json').read_text())['loaderSourceSHA256']
 assert digest(loader)==expected,'loader source differs from coverage pin'
 profiles={arch:tuple(map(int,v)) for arch,*v in re.findall(r':(x64|arm64)\s+\{:min-cov (\d+) :min-features (\d+) :min-corpus (\d+)\}',baseline)};assert set(profiles)=={'x64','arm64'}
 corpus=out/'corpus';shutil.copytree(ROOT/'fuzz/corpus/parser',corpus);binary=out/'parser-fuzz';linux=platform.system()=='Linux';target=ROOT/('seed/bootstrap/adopted-parser-fuzz-20261012.c' if a.trusted_bootstrap else 'tools/kexe_parser_fuzz.c');pins={str(p):digest(p) for p in [loader,target,ROOT/'fuzz/baselines/native-parser.edn']}
 if a.trusted_bootstrap:assert digest(target)==json.loads((ROOT/'seed/adoption-20261012.json').read_text())['loaderFuzzTargetSHA256']
 build_target=target
 if a.trusted_bootstrap:
  staging=out/'source';staging.mkdir();(staging/'kexe_loader.c').write_bytes(loader.read_bytes());build_target=staging/'kexe_parser_fuzz.c';build_target.write_bytes(target.read_bytes());pins[str(build_target)]=digest(target);pins[str(staging/'kexe_loader.c')]=expected
 flags=['-fsanitize=fuzzer,address,undefined'] if linux else ['-DKEXE_STANDALONE_FUZZ','-fsanitize=address,undefined']
 build=['clang','-std=c11','-O1','-g','-Wall','-Wextra','-fno-omit-frame-pointer']+flags+['-I'+str(ROOT/'tools'),str(build_target),'-o',str(binary)]
 with (out/'build.stdout').open('wb') as stdout,(out/'build.stderr').open('wb') as stderr:subprocess.run(build,stdout=stdout,stderr=stderr,check=True,timeout=300)
 argv=[str(binary),str(corpus),'-runs=20000','-max_len=1024','-timeout=2','-seed=104','-print_final_stats=1','-verbosity=1','-artifact_prefix='+str(out/'crash-')] if linux else [str(binary),'20000']+[str(p) for p in sorted(corpus.iterdir())]
 env=dict(os.environ);env.update(ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with (out/'fuzz.stdout').open('wb') as stdout,(out/'fuzz.stderr').open('wb') as stderr:r=subprocess.run(argv,stdout=stdout,stderr=stderr,env=env,timeout=300)
 assert r.returncode==0,'fuzz failed; raw logs preserved';assert all(digest(pathlib.Path(p))==v for p,v in pins.items())
 log=(out/'fuzz.stdout').read_text(errors='replace')+(out/'fuzz.stderr').read_text(errors='replace');marker='{:format :kotoba.fuzz-reach/v1';tail=log[log.rfind(marker):];reach=tail.split('}')[0]+'}'
 keys=['inputs','ops-completed','ops-trapped','string-bytes-read','dataspace-calls','string-result','record-result','tagged-result','variant-result','string-handle'];counts={k:int(re.search(':'+k+r' (\d+)',reach)[1]) for k in keys};assert all(n>0 for n in counts.values()),'unexercised family'
 arch='arm64' if platform.machine() in ('arm64','aarch64') else 'x64';coverage=None
 if linux:
  lines=[s for s in log.splitlines() if 'cov:' in s];line=lines[-1];coverage={k:int(re.search(p,line)[1]) for k,p in [('cov',r'cov: (\d+)'),('features',r'ft: (\d+)'),('corpus',r'corp: (\d+)/')]}
  assert all(coverage[k]>=n for k,n in zip(['cov','features','corpus'],profiles[arch])),'coverage floor failed'
 report={'status':'PASS_LOADER_SOURCE_BOUND_FUZZ','loaderScope':'trusted-bootstrap' if a.trusted_bootstrap else 'public-production','loaderSHA256':expected,'platform':platform.system(),'arch':arch,'engine':'libfuzzer' if linux else 'deterministic-sanitized','runs':20000,'reach':counts,'coverage':coverage,'floors':profiles[arch],'floorsLowered':False,'performanceMeasurement':False,'goalStatus':'paused','clang':subprocess.check_output(['clang','--version'],text=True).splitlines()[0]};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
