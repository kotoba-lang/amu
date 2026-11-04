# Test-only: stage a byte-length-preserving candidate source region into a
# disposable measured compiler copy. This is not a release or bootstrap step.
import hashlib, pathlib, sys
base, old, new, output = map(pathlib.Path, sys.argv[1:])
image = base.read_bytes()
assert hashlib.sha256(image).hexdigest() == '914b828a24ced086e09929894bb64806dea103bf79766ef144001a076717b1c4'
a, b = old.read_text(), new.read_text()
start, end = '(defn- kxrt-sp-kill ', '(defn- kxrt-spawn-refuse '
a, b = (s[s.index(start):s.index(end)] for s in (a,b))
b = ''.join(line for line in b.splitlines(keepends=True) if not line.lstrip().startswith(';;'))
assert len(b) <= len(a) and image.count(a.encode()) == 1
patched = image.replace(a.encode(), (b + ' ' * (len(a)-len(b))).encode(), 1)
assert hashlib.sha256(patched).hexdigest() == 'fc91250e9eb77e79878ea215ed9945be37b0329866f26c4c5cc75fdf8bfbecf0'
output.write_bytes(patched)
output.chmod(0o700)
