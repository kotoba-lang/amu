# Test-only staging: inject the candidate FS2 source into an isolated copy of
# the measured Linux compiler. Never modify or replace a released compiler.
import hashlib
import os
import pathlib
import sys

EXPECTED_ROOT = '914b828a24ced086e09929894bb64806dea103bf79766ef144001a076717b1c4'
if len(sys.argv) != 5:
    raise SystemExit('usage: stage.py BASE_ELF ORIGINAL_SOURCE CANDIDATE_SOURCE NEW_ELF')
base, original, candidate, output = map(pathlib.Path, sys.argv[1:])
image = base.read_bytes()
if hashlib.sha256(image).hexdigest() != EXPECTED_ROOT:
    raise SystemExit('unexpected base compiler')

def runtime_text(path):
    source = path.read_text()
    start = source.index('\n"') + 2
    end = source.rindex('\n")')
    return source[start:end]

old = runtime_text(original).encode()
new = runtime_text(candidate)
# Free bytes without changing runtime forms; the embedded string length stays
# unchanged so all offsets and the compiler's stored source length are intact.
for comment in (
    ';; Every response, including an absent/empty one, carries FS2 acknowledgement.\n',
    ';; Only the bounded path/mode header is copied into private scratch.\n',
):
    if new.count(comment) != 1:
        raise SystemExit('candidate differs from the expected staging layout')
    new = new.replace(comment, '', 1)
new = new.encode()
if image.count(old) != 1 or len(new) > len(old):
    raise SystemExit('base source mismatch or candidate does not fit')
patched = image.replace(old, new + b' ' * (len(old) - len(new)), 1)
fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
with os.fdopen(fd, 'wb') as f:
    f.write(patched)
print('test compiler sha256:', hashlib.sha256(patched).hexdigest())
