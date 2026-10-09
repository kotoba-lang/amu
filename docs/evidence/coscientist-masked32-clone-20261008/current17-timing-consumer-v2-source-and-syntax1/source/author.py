"""SOURCE construction only; never compiles or launches the consumer."""
from pathlib import Path
import hashlib,shutil,json
D=Path(__file__).resolve().parent
S=Path('/Users/junkawasaki/github/workspaces/codex/current-runtime-process-ownership-race-source-v6-20261009-independent')
b=(S/'kexe_loader_diagnostic.c').read_bytes()
assert hashlib.sha256(b).hexdigest()=='04428f47af807fcb19342d035ce730f980f97c001747c806e059bbc4380c52b2'
s=b.decode();s=s.replace('int main(int argc, char **argv) {','#include "timing-extension.h"\nstatic int timing_loader_main(int argc, char **argv) {',1)
a='''    result = fn(args[0], args[1], args[2], args[3], args[4], 0, 0,
                (int64_t)(uintptr_t)&shared->context);'''
assert s.count(a)==1
s=s.replace(a,'    result = timing_loop(timing_arm==2?timing_c_fn:fn, shared, args);')
a='''    if (munmap(shared, sizeof(*shared)) != 0) fail("supervisor shared munmap");'''
assert s.count(a)==1
s=s.replace(a,'    timing_parent_report(child_status);\n'+a)
s+='\n#include "timing-frontend.h"\n'
(D/'timing-loader.c').write_text(s)
for name in ('kexe_gpu_vulkan.c','ownership-hooks.c'):
 if (S/name).exists():shutil.copyfile(S/name,D/name)
# The ownership hook is embedded in diagnostic source, not a separate include.
(D/'construction.json').write_text(json.dumps({'base':str(S/'kexe_loader_diagnostic.c'),'baseSHA256':hashlib.sha256(b).hexdigest(),'substitutions':3,'helperBodies':'exact original copied bytes; only main naming/invocation/parent timing report hooks'},indent=2)+'\n')
