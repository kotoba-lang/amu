#!/usr/bin/python3
import os, subprocess, sys, datetime

REPO = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu"
OUT = "/private/tmp/amub_probe.txt"

lines = []
lines.append("== date ==")
lines.append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S JST"))
lines.append("== uptime ==")
lines.append(subprocess.run(["/usr/bin/uptime"], capture_output=True, text=True).stdout.strip())
lines.append("== sysctl ncpu ==")
lines.append(subprocess.run(["/usr/sbin/sysctl","-n","hw.ncpu"], capture_output=True, text=True).stdout.strip())
lines.append("== scripts dir ==")
try:
    lines.extend(sorted(os.listdir(os.path.join(REPO,"scripts"))))
except Exception as e:
    lines.append("ERR scripts: %r" % e)
lines.append("== docs amufalsify/amufalsify-like ==")
try:
    lines.extend(sorted(n for n in os.listdir(os.path.join(REPO,"docs")) if "amufalsify" in n or "append-" in n))
except Exception as e:
    lines.append("ERR docs: %r" % e)
lines.append("== grep idle>=9/10 in codegen log (tail mentions) ==")
logp = os.path.join(REPO,"docs","codegen-coscientist.md")
with open(logp) as f:
    t = f.read()
lines.append("log chars: %d" % len(t))
idx = t.rfind("jb_imod_control")
lines.append("last jb_imod_control idx: %d" % idx)
if idx >= 0:
    lines.append(t[max(0,idx-600):idx+600])
lines.append("== bench runtime-comparison dir ==")
bdir = os.path.join(REPO,"bench","runtime-comparison")
try:
    names = sorted(os.listdir(bdir))
    lines.append("%d entries" % len(names))
    lines.extend(n for n in names if "imod" in n or "jb" in n)
except Exception as e:
    lines.append("ERR bench: %r" % e)
lines.append("== perfgate ==")
for root, dirs, files in os.walk(REPO):
    dirs[:] = [d for d in dirs if d not in (".git","node_modules","target")]
    for fn in files:
        if "perfgate" in fn:
            lines.append(os.path.join(root, fn))
lines.append("== amu_cowork_state.sh ==")
for root, dirs, files in os.walk(REPO):
    dirs[:] = [d for d in dirs if d not in (".git","node_modules","target")]
    for fn in files:
        if "cowork" in fn or "state.sh" in fn:
            lines.append(os.path.join(root, fn))

with open(OUT,"w") as f:
    f.write("\n".join(lines)+"\n")
print("wrote", OUT)
