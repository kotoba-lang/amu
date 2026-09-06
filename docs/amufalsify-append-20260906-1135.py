import datetime, os, re
path = "docs/codegen-cosientist.md"
txt = open(path).read()
# find a hypothesis line to append evidence to; use H-C2 line (NEXT target)
m = re.search(r'^\| H-C2 \|.*$', txt, re.M)
line = m.group(0) if m else None
stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
note = f" falsify 2026-09-06 11:35 JST: measurement refused - host busy (load1 14.13 > 7.5 quiet gate)."
if line:
    txt = txt.replace(line, line.rstrip() + note, 1)
    open(path, "w").write(txt)
    print("APPENDED to H-C2")
else:
    print("H-C2 line not found; no edit")
