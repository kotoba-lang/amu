#!/usr/bin/env python3
"""Stage resource-profile fixtures; all checking/identities/cache builds are native."""
import argparse
import hashlib
import json
import platform
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRA = ['seed/04-definition-cid.kotoba', 'seed/05-definition-graph.kotoba',
         'seed/05-checked-definition.kotoba', 'seed/06-definition-groups.kotoba',
         'seed/05-checked-source.kotoba', 'seed/05-source-loops.kotoba',
         'seed/07-definition-objects.kotoba', 'seed/08-definition-object-emitter.kotoba',
         'seed/09-definition-build.kotoba', 'seed/tests/native-definition-object-checks.kotoba',
         'seed/tests/native-definition-build.kotoba', 'seed/tests/native-identity-resource-profile.kotoba']
ENTRY = '''
(defn- seed-main [] :i64
 (if (= (io-argc) 7) (dcb-test-entry (dirp-resource (io-arg 6)) 7)
  (if (not= (io-argc) 3) 2
   (let [mode (io-arg 0) resource (dirp-resource (io-arg 1)) text (io-arg 2)
         number (mem-parse-dec text 0 (string-length text))]
    (cond (= mode "source") (dsb-source-resource (io-fs2-text 65 text "") false resource)
          (= mode "kir") (let [status (dcs-run-resource (io-fs2-text 65 text "") resource)]
             (if (= status 0) 0 (let [out (io-err (string-concat "DIRP:E" (string-concat (mem-u2dec status) "\\n")))] 1)))
          (= mode "context") (if (not (dip-valid? resource)) 1
             (let [out (io-out (string-concat (dip-context resource) "\\n"))] 0))
          (= mode "codec") (if (dirp-codec-bound number resource) 0 1)
          (= mode "nodes") (if (dirp-node-bound number resource) 0 1)
          (= mode "text") (if (dirp-large-text) 0 1)
          (= mode "bytes")
             (if (not (dip-valid? resource)) 1
               (let [hex (dc-ascii-range (vector-alloc number) 0 number)
                     decoded (dc-unhex hex) out (io-out (string-concat (mem-u2dec (vector-count decoded)) "\\n"))] 0))
          (= mode "oracle")
             (let [cid (dc-definition-cid-resource (dirp-nested-payload number resource) resource)]
              (if (= cid "") 1 (let [out (io-out (string-concat cid "\\n"))] 0)))
          :else 2)))))
'''
def pin(p):
    b = p.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
def expr(n):
    return '(+ ' * n + 'x' + ' 1)' * n
def fn(name, body, params='x'):
    return '{:name ' + name + ' :params [' + params + '] :param-types [' + (':i64' if params else '') + '] :result :i64 :effects #{} :body ' + body + '}'
def module(functions, entry=False):
    return '{:format :kotoba.kir/v4 :entry ' + ('main :exports [main]' if entry else 'nil :exports []') + ' :effects #{} :functions [' + ' '.join(functions) + ']}\n'
def rows(data):
    lines = data.decode().splitlines()
    assert lines[0] == 'DCP1 6 2'
    return {p[0]: p[1:] for p in [line.split() for line in lines[1:]]}
def main(compiler, out):
    machine = platform.machine()
    assert platform.system() == 'Linux' and machine in ['aarch64', 'x86_64']
    target = 'aarch64-linux' if machine == 'aarch64' else 'x86_64-linux'
    product = json.loads((ROOT / 'native-product.json').read_text())
    assert pin(compiler) == product['rootImage' if machine == 'aarch64' else 'image']
    out.mkdir(parents=True, exist_ok=False)
    (out / 'observer.py').write_bytes(Path(__file__).read_bytes())
    paths = [p for p in (ROOT / 'seed/FULL-MANIFEST').read_text().splitlines() if p and not p.startswith('#')][:-1] + EXTRA
    parts = []
    for p in paths:
        text = (ROOT / p).read_text()
        if p == 'seed/tests/native-definition-build.kotoba':
            assert text.count('(defn- seed-main [] :i64') == 1
            text = text.replace('(defn- seed-main [] :i64', '(defn- dirp-default-main [] :i64')
        parts.append(text)
    unity = '\n'.join(parts) + ENTRY
    env = dict(PATH='/nonexistent', KEXE_STACK_BYTES='8388608', KEXE_FUEL='10000000000', KEXE_ALLOW='35,37,38,39', KEXE_CAP_RESOURCES_35=str(out))
    report = dict(schema='amu.native-identity-resource-profile.v1', status='RUNNING', host=[platform.system(), machine],
                  compiler=pin(compiler), observer=pin(Path(__file__)), modules={p:pin(ROOT / p) for p in paths}, calls=[], mutations=[],
                  productionCompilerClosureChanged=False, productionImageSealBound=False, wholeCompilerIdentityQualified=False,
                  wholeCompilerCacheQualified=False, sourceResourceProofQualified=False, ciPerformanceClaim=False, parity=[])
    def save():
        (out / 'observations.json').write_text(json.dumps(report, indent=2) + '\n')
    def run(name, argv, code=0, environment=env):
        p = subprocess.run(list(map(str, argv)), cwd=out, env=environment, capture_output=True, timeout=300)
        for stream in ['stdout', 'stderr']:
            (out / (name + '.' + stream)).write_bytes(getattr(p, stream))
        report['calls'].append(dict(name=name, exit=p.returncode, stdout=pin(out / (name + '.stdout')), stderr=pin(out / (name + '.stderr'))))
        save()
        if code is not None: assert p.returncode == code, (name, p.returncode, p.stdout[-200:], p.stderr[-400:])
        return p
    def build(name, source):
        src, image = out / (name + '.kotoba'), out / (name + '.elf')
        src.write_text(source)
        run('build-' + name, [compiler, 'compile', src, '--target', target, '--output', image, '--format', 'static'])
        image.chmod(0o755)
        assert struct.unpack_from('<H', image.read_bytes(), 18)[0] == (183 if machine == 'aarch64' else 62)
        return image
    producer = build('resource-producer', unity)
    report['producer'] = pin(producer)
    for profile, expression, codec in [('standard-v1', 64, 64), ('compiler-v1', 128, 288)]:
        raw = f'KIDP1\n{profile}\nexpr={expression}\ncodec={codec}\ntype=64\nnodes=8192\nbytes=65536\nscc=8\n'.encode()
        assert run('context-' + profile, [producer, 'context', profile, '0']).stdout.decode().strip() == hashlib.sha256(raw).hexdigest()
        run('codec-edge-' + profile, [producer, 'codec', profile, codec])
        run('codec-over-' + profile, [producer, 'codec', profile, codec + 1], 1)
        run('nodes-edge-' + profile, [producer, 'nodes', profile, '8190'])
        run('nodes-over-' + profile, [producer, 'nodes', profile, '8191'], 1)
        assert run('bytes-edge-' + profile, [producer, 'bytes', profile, '65536']).stdout == b'65536\n'
        assert run('bytes-over-' + profile, [producer, 'bytes', profile, '65537']).stdout == b'0\n'
    run('codec-unknown', [producer, 'codec', 'unknown', '0'], 1)
    run('large-ascii', [producer, 'text', 'standard-v1', '0'])
    identities = {}
    for n in [0, 4, 24, 48, 96, 128, 129]:
        src = out / f'nested-{n}.input'; src.write_text('(ns deep) (defn f [x :i64] :i64 ' + expr(n) + ')\n')
        kir = out / f'nested-{n}.kir'; kir.write_text(module([fn('f', expr(n))]))
        for profile in ['standard-v1', 'compiler-v1']:
            if profile == 'standard-v1' and n > 24 or n == 129:
                p = run(f'refuse-source-{profile}-{n}', [producer, 'source', profile, src], 1)
                assert not p.stdout and p.stderr
                p = run(f'refuse-kir-{profile}-{n}', [producer, 'kir', profile, kir], 1)
                assert not p.stdout and p.stderr
            else:
                a = rows(run(f'source-{profile}-{n}', [producer, 'source', profile, src]).stdout)
                b = rows(run(f'kir-{profile}-{n}', [producer, 'kir', profile, kir]).stdout)
                oracle = run(f'oracle-{profile}-{n}', [producer, 'oracle', profile, n]).stdout.decode().strip()
                assert a == b and a['f'][0] == oracle
                identities[profile, n] = oracle
    assert all(identities['standard-v1', n] == identities['compiler-v1', n] for n in [0, 4, 24])
    for count in [2, 8, 9]:
        cycle = module([fn('f' + str(i), '(if (= x 0) ' + str(count - i) + ' (f' + str((i + 1) % count) + ' (- x 1)))') for i in range(count)])
        path = out / f'scc-{count}.kir'; path.write_text(cycle)
        a = run(f'scc-standard-{count}', [producer, 'kir', 'standard-v1', path], 1 if count == 9 else 0)
        b = run(f'scc-compiler-{count}', [producer, 'kir', 'compiler-v1', path], 1 if count == 9 else 0)
        assert a.stdout == b.stdout
    src = out / 'nested-4.input'
    p = run('source-unknown', [producer, 'source', 'unknown', src], 1); assert not p.stdout
    shallow = out / 'shallow.kir'; shallow.write_text(module([fn('helper', '(+ x 2)'), fn('main', '(helper 40)', '')], True))
    deep = out / 'deep.kir'; deep.write_text(module([fn('helper', expr(96)), fn('main', '(helper 0)', '')], True))
    def directory(name):
        p = out / name; p.mkdir(mode=0o700); return p
    def invoke(name, src, cache, profile, *, mode='cached', hits=None, code=0, image=producer):
        output = out / (name + '.elf')
        p = run(name, [image, mode, src, cache, pin(image)['sha256'], output, '1000000', profile], code)
        if code == 0:
            assert output.exists() and struct.unpack_from('<H', output.read_bytes(), 18)[0] == 62
            if hits: assert f'DCB1 reused={hits[0]} rebuilt={hits[1]}\n'.encode() in p.stdout
        else: assert not output.exists() and not p.stdout
        return output
    cache = directory('cross-profile')
    standard = invoke('shallow-standard', shallow, cache, 'standard-v1', hits=(0, 2))
    candidate = invoke('shallow-compiler', shallow, cache, 'compiler-v1', hits=(0, 2))
    warm = invoke('shallow-warm', shallow, cache, 'compiler-v1', hits=(2, 0))
    reference = invoke('shallow-reference', shallow, cache, 'compiler-v1', mode='reference')
    assert standard.read_bytes() == candidate.read_bytes() == warm.read_bytes() == reference.read_bytes()
    deep_cache = directory('deep-cache')
    invoke('deep-standard-refused', deep, deep_cache, 'standard-v1', code=1)
    cold = invoke('deep-compiler', deep, deep_cache, 'compiler-v1', hits=(0, 2))
    warm = invoke('deep-warm', deep, deep_cache, 'compiler-v1', hits=(2, 0))
    reference = invoke('deep-reference', deep, deep_cache, 'compiler-v1', mode='reference')
    assert cold.read_bytes() == warm.read_bytes() == reference.read_bytes()
    for name, image, expected in [('shallow', candidate, 42), ('deep', cold, 96)]:
        if machine == 'x86_64':
            image.chmod(0o755)
            p = run('execute-' + name, [image], environment={})
            assert p.stdout == struct.pack('<q', expected) and not p.stderr
        report['parity'].append(dict(name=name, image=pin(image), expectedI64=expected, nativeExecution=machine == 'x86_64'))
    mutations = [
        ('profile-key-erasure', '(dip-context (dcp-resource A))', '(dip-context 0)', 'cache'),
        ('compiler-codec-erasure', '(case resource 0 64 1 288 -1)', '(case resource 0 64 1 64 -1)', 'oracle'),
        ('codec-overrun', '(case resource 0 64 1 288 -1)', '(case resource 0 64 1 289 -1)', 'overrun'),
        ('codec-unknown-fallback', '(case resource 0 64 1 288 -1)', '(case resource 0 64 1 288 64)', 'unknown'),
        ('quadratic-text',
         '(let [bytes (dc-ascii-range V 0 n)]\n        (if (and (> n 0) (= bytes "")) "" (string-concat (dc-head 96 n) bytes)))',
         '(loop [i 0 out (dc-head 96 n)] (cond (= i n) out (>= (vector-at V i) 128) "" :else (recur (inc i) (string-concat out (dc-byte-hex (vector-at V i))))))',
         'text'),
    ]
    for name, old, new, probe in mutations:
        assert old in unity
        image = build('mutant-' + name, unity.replace(old, new))
        if probe == 'cache':
            d = directory('mutant-profile-cache')
            invoke('mutant-cache-standard', shallow, d, 'standard-v1', hits=(0, 2), image=image)
            output = out / 'mutant-cache-compiler.elf'
            p = run('detect-' + name, [image, 'cached', shallow, d, pin(image)['sha256'], output, '1000000', 'compiler-v1'])
            assert b'DCB1 reused=2 rebuilt=0\n' in p.stdout
        elif probe == 'oracle':
            p = run('detect-' + name, [image, 'oracle', 'compiler-v1', '96'], 1); assert not p.stdout
        elif probe == 'overrun': run('detect-' + name, [image, 'codec', 'compiler-v1', '289'])
        elif probe == 'unknown': run('detect-' + name, [image, 'codec', 'unknown', '0'])
        else:
            p = run('detect-' + name, [image, 'text', 'standard-v1', '0'], None)
            assert p.returncode == 120 and b':budget/bytes' in p.stderr and b':string-pool' in p.stderr
        report['mutations'].append(dict(name=name, image=pin(image), built=True, executed=True, detected=True))
    report.update(status='PASS_NATIVE_IDENTITY_RESOURCE_PROFILE', defaultBoundsPreserved=True,
                  compilerExpressionBoundary=128, compilerCodecBoundary=288, smallCIDsUnchanged=True,
                  profileKeySeparation=True, deepPersistentReuse=True)
    assert all(pin(ROOT / p) == v for p,v in report['modules'].items())
    save(); print(report['status'], flush=True)
if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--compiler', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); main(a.compiler.resolve(), a.output.resolve())
