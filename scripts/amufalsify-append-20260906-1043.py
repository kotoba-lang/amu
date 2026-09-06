import datetime, re
p = "docs/codegen-coscientist.md"
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M JST")
line = f"- [{ts}] [amu-falsify] host busy: load1=68.87 (1m avg, sysctl vm.loadavg; gate < 7.5). No measurement this tick. NEXT H-C2 remains queued.\n"
with open(p) as f:
    txt = f.read()
txt = txt.rstrip("\n") + "\n" + line
with open(p, "w") as f:
    f.write(txt)
print("appended")
