# Test observer only, not runtime tooling.
import json, os, pathlib, subprocess
base=pathlib.Path('/private/tmp/awai152-contract-check')
cases=[('normal','/usr/bin/printf:/usr/bin/false',0,''),('normal','/usr/bin/false',126,'spawn/program-not-granted'),('missing','/awai152-test-only-nonexistent',126,'spawn/exec-failed')]
for compiler in ('base','candidate'):
 for name,grants,code,reason in cases:
  env=dict(os.environ,KEXE_ALLOW='20,35,37,38',KEXE_CAP_RESOURCES_20=grants,KEXE_CAP_RESOURCES_35=str(base))
  p=subprocess.run([str(base/(compiler+'-'+name+'.elf'))],env=env,capture_output=True,timeout=15)
  result={'compiler':compiler,'case':name,'grant':grants,'exit':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')}
  print(json.dumps(result),flush=True)
  assert p.returncode==code and reason in result['stderr'] and not p.stdout, result
