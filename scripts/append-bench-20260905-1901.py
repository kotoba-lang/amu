import io

path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
with io.open(path, encoding="utf-8") as f:
    text = f.read()

stamp = "2026-09-05 19:01 JST falsify tick: host busy (load1 31.87, load5 33.72, load15 44.99, up 11:43, 15 users), no measurement attempted; NEXT は H-C2 のまま"

idx = text.find("| H-C2 | the remaining ~4.4% vs Clang")
assert idx != -1
end = text.find("\n", idx)
line = text[idx:end]
print(repr(line[-120:]))
new_line = line + " ; " + stamp
text = text[:idx] + new_line + text[end:]
with io.open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("appended")
