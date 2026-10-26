#!/usr/bin/env python3
"""Diagnostic marker compiler; native verdict authority is always false.

Python stages existing source, invokes the admitted producer, and timestamps
stderr. It neither emits a native format nor supplies a qualification verdict.
"""
import argparse, hashlib, json, os, platform, re, struct, subprocess, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def pin(p):
 b=Path(p).read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main(out,seconds,revision=None,from_sir=0,ccf_only=False):
 assert platform.system()=="Linux" and platform.machine() in ("x86_64","aarch64")
 out.mkdir(parents=True,exist_ok=False)
 target="x86_64-linux" if platform.machine()=="x86_64" else "aarch64-linux"
 producer=ROOT/"bin/amu" if platform.machine()=="x86_64" else ROOT/"seed/bootstrap/aarch64-linux-static-root.elf"
 expected_machine=62 if platform.machine()=="x86_64" else 183
 assert struct.unpack_from("<H",Path("/proc/self/exe").read_bytes(),18)[0]==expected_machine
 assert struct.unpack_from("<H",producer.read_bytes(),18)[0]==expected_machine
 def read(path):
  if not revision: return (ROOT/path).read_bytes()
  return subprocess.run(['git','show',revision+':'+path],cwd=ROOT,check=True,capture_output=True).stdout
 paths=[p for p in read("seed/CORE-STATIC-MANIFEST").decode().splitlines() if p and not p.startswith("#")]
 source=b"".join(read(p)+b"\n" for p in paths)
 text=source.decode()
 functions=["gn-small-label","gn-op-fn","gn-op-call","qi-admit","pi-admit","ti-admit","rp-admit","rc-admit","gn-call-wrapper","gn-clamp","gn-scalar-mask","gn-affine-reader","mr-reader","di-admit","tc-admit","tb-admit","aw-admit","gn-mask-writer","gn-chain-mode","gn-chain-target","gp-shape","gn-ins","gn-small-tail","gn-small-end","jt-return","jdag-owner","gn-op-label","gn-op-fuel","gn-chain-step","srloop-entry","btg-entry","ts-entry","jssa-entry","sls-entry","brc-entry","snf-entry"]
 if ccf_only:
  functions=["gn-op-cmp","ccf-admit","ccf-code","ccf-fixes","ccf-labels","ccf-functions","ccf-label-source","ccf-owner","ccf-end","bd-edges"]
 if from_sir:
  assert not revision, 'late probe currently uses the candidate snapshot'
  quiet=text[text.index('(defn- gn-ins-quiet '):text.index(';; every instruction from i')]
  functions += sorted(set(re.findall(r"\(([\w-]+-entry) ", quiet))-set(functions))
  functions += ['dve-ins','dve-original-ins','gn-ins-quiet','ocb-post','vi-step','gn-op-rt','gn-op-bin']
  text=text.replace('(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 91))','(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 93))')
  text=text.replace('(let [M1 (gn-ins M i (gn-op M i))','(let [current (gn-gs M (+ gn-g-open 92) i) M1 (gn-ins current i (gn-op M i))')
 bindings={p:dict(bytes=len(read(p)),sha256=hashlib.sha256(read(p)).hexdigest()) for p in paths}
 for name in functions:
  match=re.search(r"\(defn- "+re.escape(name)+r" \[([^]]*)\] :(i64|bool|vector-i64)",text)
  assert match,name
  start=match.start();end=text.find("\n(def",match.end())
  assert end>start
  original=text[start:end]
  args=match.group(1);names=re.findall(r"([\w-]+) :[\w-]+",args)
  inner="prof-original-"+name
  body=original.replace("("+name+" ","("+inner+" ").replace("(defn- "+name+" ","(defn- "+inner+" ",1)
  active='true' if not from_sir else '(>= (gn-g '+names[0]+' (+ gn-g-open 92)) '+str(from_sir)+')'
  wrapper='(defn- '+name+' ['+args+'] :'+match.group(2)+' (let [active '+active+' b (if active (io-err "B '+name+'\\n") 0) result ('+inner+' '+' '.join(names)+') e (if active (io-err "E '+name+'\\n") 0)] result))\n'
  text=text[:start]+body+"\n"+wrapper+text[end:]
 if not revision:
  marker='(let [module-info (if (= i 1) (io-err (string-concat "MODULE " (string-concat (mem-u2dec (vector-at M MM-SIR-N)) (string-concat " INDEX " (string-concat (mem-u2dec (glx-base M)) "\\n"))))) 0) M1 (gn-ins M i (gn-op M i))'
  text=text.replace('(let [M1 (gn-ins M i (gn-op M i))', marker, 1)
 unit=out/"probe.kotoba";unit.write_text(text)
 corepaths=[p for p in read("seed/MANIFEST").decode().splitlines() if p and not p.startswith("#")]
 core=out/"core.kotoba";core.write_bytes(b"".join(read(p)+b"\n" for p in corepaths))
 lock=out/"core.ksl";lock.write_text(f"KSL1\nentry {core}\nfile {pin(core)['sha256']} {core}\n")
 env=dict(PATH="/nonexistent",KEXE_STACK_BYTES="8388608",KEXE_CAP_RESOURCES_35=str(out))
 image=out/"probe.elf";build=[str(producer),"compile",str(unit),"--target",target,"--output",str(image),"--format","static"]
 r=subprocess.run(build,env=env,capture_output=True,timeout=900)
 (out/"build.stdout").write_bytes(r.stdout);(out/"build.stderr").write_bytes(r.stderr)
 assert r.returncode==0 and not r.stderr,(r.returncode,r.stderr[-1000:])
 image.chmod(0o755)
 report=dict(schema="amu.proof-scan-diagnostic.v1",nativeVerdictAuthority=False,qualificationReplacement=False,host=[platform.system(),platform.machine(),platform.release()],sourceBindings=bindings,source=pin(core),producer=pin(producer),instrumented=pin(unit),compiler=pin(image),status="RUNNING",events=0,totals={},stack=[])
 (out/"observations.json").write_text(json.dumps(report,indent=2)+"\n")
 argv=[str(image),"compile",str(core),"--target","aarch64-macos","--output",str(out/"core.kseed"),"--source-lock",str(lock),"--source-lock-sha256",pin(lock)["sha256"]]
 start=time.monotonic();process=subprocess.Popen(argv,env=env,stdout=(out/"compile.stdout").open("wb"),stderr=subprocess.PIPE)
 stop=threading.Timer(seconds,process.terminate);stop.start()
 stack=[];totals={};last=start
 with (out/"events.jsonl").open("w") as raw:
  for data in process.stderr:
   now=time.monotonic();line=data.decode().strip();raw.write(json.dumps([now-start,line])+"\n")
   if stack:
    totals.setdefault(stack[-1][0],dict(exclusiveSeconds=0,inclusiveSeconds=0,calls=0))["exclusiveSeconds"]+=now-last
   if line.startswith("B "):
    name=line[2:];stack.append((name,now));totals.setdefault(name,dict(exclusiveSeconds=0,inclusiveSeconds=0,calls=0))["calls"]+=1
   elif line.startswith("E "):
    name=line[2:];assert stack and stack[-1][0]==name,(line,stack[-5:]);_,began=stack.pop();totals[name]["inclusiveSeconds"]+=now-began
   last=now;report["events"]+=1
   if report["events"]%256==0:
    report.update(seconds=now-start,totals=totals,stack=[n for n,_ in stack]);(out/"observations.json").write_text(json.dumps(report,indent=2)+"\n")
 code=process.wait();stop.cancel();report.update(exit=code,seconds=time.monotonic()-start,totals=totals,stack=[n for n,_ in stack],status="COMPLETED_DIAGNOSTIC" if code==0 else "RIGHT_CENSORED_DIAGNOSTIC",artifact=pin(out/"core.kseed") if (out/"core.kseed").exists() else None)
 (out/"observations.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2),flush=True)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--seconds",type=int,default=240);p.add_argument("--baseline-revision");p.add_argument("--from-sir",type=int,default=0);p.add_argument("--ccf-only",action="store_true");a=p.parse_args();main(a.output.resolve(),a.seconds,a.baseline_revision,a.from_sir,a.ccf_only)
