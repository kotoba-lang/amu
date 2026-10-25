#!/usr/bin/env python3
"""Bootstrap the statemate zero-branch compiler candidate from a pinned selfhost G3."""
import hashlib, json, os, platform, subprocess, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('worktrees/codex/amu-crossdomain-coscientist-20261016')
PREV=ROOT/"workspaces/codex/amu-statemate-singleuse-inline-20261017/attempt-3/build"
PREV_REPORT=PREV/"build-report.json"
PREV_COMPILER=PREV/"artifacts/G3.bin"
CANDIDATE=HERE/"seed-41-candidate.kotoba"
LOADER_SOURCE=ROOT/"seed/bootstrap/adopted-loader-20261012.c"
MAX_GENERATIONS=6

def sha(x):
    return hashlib.sha256(x.read_bytes() if isinstance(x,Path) else x).hexdigest()
def main():
    if platform.system()!="Darwin" or platform.machine()!="arm64": raise SystemExit("requires macOS arm64")
    if (HERE/"build").exists(): raise SystemExit("preserving existing build directory")
    prev=json.loads(PREV_REPORT.read_text())
    if prev.get("status")!="PASS_G1_TO_GN_BYTE_IDENTICAL_FIXED_POINT" or sha(PREV_COMPILER)!=prev["fixedPointSHA256"]: raise SystemExit("pinned predecessor is not verified")
    if not CANDIDATE.is_file(): raise SystemExit("candidate source missing")
    files=prev["sourceFiles"]
    parts=[]
    for name in files:
        src=CANDIDATE if name=="seed/41-a64gen.kotoba" else ROOT/name
        parts.append(src.read_bytes()+b"\n")
    unity=b"".join(parts)
    out=HERE/"build"; host=out/"host"; artifacts=out/"artifacts"
    host.mkdir(parents=True); artifacts.mkdir()
    unity_path=artifacts/"seed-unity.kotoba"; unity_path.write_bytes(unity)
    loader=host/"kexe-loader"
    report={"status":"RUNNING","sourceFiles":files,"sourceUnityBytes":len(unity),"sourceUnitySHA256":sha(unity),
      "candidateSourceSHA256":sha(CANDIDATE),"previousCompilerSHA256":sha(PREV_COMPILER),"previousFixedPointReport":str(PREV_REPORT.relative_to(ROOT)),
      "trustedLoaderSourceSHA256":sha(LOADER_SOURCE),"host":{"system":platform.system(),"machine":platform.machine(),"version":platform.mac_ver()[0]},
      "JVMNodeOrGraalFallback":False,"startedUnix":time.time(),"generations":[],"calls":[]}
    rp=out/"build-report.json"; rp.write_text(json.dumps(report,indent=2)+"\n")
    env=dict(os.environ); env.update({"KEXE_COMMAND":"1","KEXE_CAP_RESOURCES_35":str(artifacts),"KEXE_FUEL":"off","KEXE_VECTORS":"4194304","KEXE_VECTOR_ITEMS":"134217728","KEXE_STRING_POOL":"268435456","KEXE_PAIRS":"16777216","KEXE_CPU_SECONDS":"1800","KEXE_WALL_SECONDS":"1800","TMPDIR":str(artifacts)})
    def run(name,argv):
        with (host/f"{name}.stdout").open("wb") as so,(host/f"{name}.stderr").open("wb") as se:
            x=subprocess.run([str(a) for a in argv],cwd=artifacts,env=env,stdout=so,stderr=se,timeout=1800)
        report["calls"].append({"name":name,"argv":[str(a) for a in argv],"exit":x.returncode}); rp.write_text(json.dumps(report,indent=2)+"\n")
        if x.returncode: raise SystemExit(f"{name} failed; outputs preserved")
    run("loader-build",["clang","-std=c11","-O2",LOADER_SOURCE,"-o",loader]); report["loaderBinarySHA256"]=sha(loader)
    producer=PREV_COMPILER; last=None
    for generation in range(1,MAX_GENERATIONS+1):
        stem=f"G{generation}"; ks=artifacts/f"{stem}.kseed"; native=artifacts/f"{stem}.bin"
        prefix=[loader,producer,"0","0","aarch64","35,37,38,39","--"]
        run(stem+"-compile",prefix+["compile",unity_path,"--target","aarch64-macos","--output",ks])
        run(stem+"-extract",prefix+["extract-native",ks,"--symbol","main","--output",native])
        h=sha(native); report["generations"].append({"generation":generation,"bytes":native.stat().st_size,"sha256":h,"containerSHA256":sha(ks),"compilerInputSHA256":sha(producer)}); rp.write_text(json.dumps(report,indent=2)+"\n")
        print(f"{stem} {native.stat().st_size} {h}",flush=True)
        if generation>=3 and h==last:
            report["status"]="PASS_G1_TO_GN_BYTE_IDENTICAL_FIXED_POINT"; report["fixedPointSHA256"]=h; report["endedUnix"]=time.time(); rp.write_text(json.dumps(report,indent=2)+"\n"); return
        last=h; producer=native
    report["status"]="FAIL_NO_FIXED_POINT_WITHIN_GENERATION_LIMIT"; report["endedUnix"]=time.time(); rp.write_text(json.dumps(report,indent=2)+"\n"); raise SystemExit(report["status"])
if __name__=="__main__": main()
