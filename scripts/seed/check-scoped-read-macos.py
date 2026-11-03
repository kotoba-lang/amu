#!/usr/bin/env python3
"""Exercise KFR1 with a candidate native Darwin packager and FD3 scope."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--compiler', type=Path, required=True)
ap.add_argument('--packager', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
a = ap.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
spec = importlib.util.spec_from_file_location('scope', ROOT / 'scripts/seed/check-macos-arena-scope.py')
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)
gate = scope.module()
source = ROOT / 'seed/tests/scoped-read/probe.kotoba'
image = scope.build(gate, a.compiler.resolve(strict=True), a.packager.resolve(strict=True), out, 'probe', source)
(out / 'empty').write_bytes(b'')
(out / 'hello').write_text('hello\n')
(out / 'big').write_bytes(b'x' * (1048576 + 1))
(out / 'link').symlink_to('hello')
(out / 'folder').mkdir()
(out / 'folder' / 'hello').write_text('hello\n')
(out / 'parent-link').symlink_to('folder', target_is_directory=True)
outside = out.parent / (out.name + '-outside')
outside.write_text('protected-outside')
(out / 'outside-link').symlink_to(outside)
cases = []
for name, path, expected, output in [
    ('regular', 'hello', 0, b'1 7 hello\n\n'),
    ('empty', 'empty', 0, b'1 1 \n'),
    ('missing', 'missing', 2, b'0 1 \n'),
    ('directory', '.', 2, b'0 1 \n'),
    ('too-large', 'big', 2, b'0 1 \n'),
    ('symlink', 'link', 2, b'0 1 \n'),
    ('outside', '../outside', 2, b'0 1 \n'),
    ('nested', 'folder/hello', 0, b'1 7 hello\n\n'),
    ('virtual-root', '/folder/hello', 0, b'1 7 hello\n\n'),
    ('parent-symlink', 'parent-link/hello', 2, b'0 1 \n'),
    ('outside-file', '../' + outside.name, 2, b'0 1 \n'),
    ('outside-virtual-root', '/../' + outside.name, 2, b'0 1 \n'),
    ('outside-link', 'outside-link', 2, b'0 1 \n'),
    ('nested-escape', 'folder/../../' + outside.name, 2, b'0 1 \n'),
    ('double-root', '//etc/passwd', 2, b'0 1 \n'),
    ('empty-path', '', 2, b'0 1 \n')]:
    print('checking', name, flush=True)
    result = gate.native_run(image, out, path, expected=expected, timeout=30)
    if result.stdout != output or result.stderr:
        raise ValueError((name, result.returncode, result.stdout, result.stderr))
    cases.append(name)
if outside.read_text() != 'protected-outside':
    raise ValueError('outside sentinel changed')
ksl = source.read_text().replace('KFR1', 'KSL1')
if ksl == source.read_text():
    raise ValueError('source-lock control not constructed')
ksl_image = scope.build(gate, a.compiler.resolve(strict=True), a.packager.resolve(strict=True), out, 'ksl', ksl)
ksl_result = gate.native_run(ksl_image, out, 'hello', expected=0, timeout=30)
if ksl_result.stdout != b'1 7 hello\n\n' or ksl_result.stderr:
    raise ValueError(('source-lock regression', ksl_result.stdout, ksl_result.stderr))
cases.append('source-lock-existing-prefix')
fs2 = '''(ns fs2-control (:export [main]))
(defn main [] :i64
  (let [nul (string-from-utf8 (bytes-from-vector-i64 (vector-alloc 1)))
        reply (typed-cap-call 35 :string :string (str nul "FS2" nul "Ahello" nul))]
    (if (= reply (str nul "FS2" nul "hello\\n")) 0 1)))
'''
fs2_image = scope.build(gate, a.compiler.resolve(strict=True), a.packager.resolve(strict=True), out, 'fs2-control', fs2)
fs2_result = gate.native_run(fs2_image, out, expected=0, timeout=30)
if fs2_result.stdout or fs2_result.stderr:
    raise ValueError(('existing FS2 regression', fs2_result.stdout, fs2_result.stderr))
cases.append('existing-fs2-read')
(out / 'binary').write_bytes(bytes([0, 255, 128]))
binary = scope.build(gate, a.compiler.resolve(strict=True), a.packager.resolve(strict=True), out,
                     'binary-control', ROOT / 'seed/tests/scoped-read/binary.kotoba')
binary_result = gate.native_run(binary, out, 'binary', expected=0, timeout=30)
if binary_result.stdout or binary_result.stderr:
    raise ValueError(('exact binary regression', binary_result.stdout, binary_result.stderr))
cases.append('exact-binary')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(out / 'receipt.json').write_text(json.dumps(dict(status='PASS', cases=cases,
    compilerSha256=sha(a.compiler), packagerSha256=sha(a.packager), imageSha256=sha(image),
    sourceSha256=sha(source), scope='Mac arm64, synthetic FD3 scope; fleet integration unqualified'), indent=2) + '\n')
print('PASS_SCOPED_READ_MACOS_ARM64', flush=True)
