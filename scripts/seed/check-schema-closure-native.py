#!/usr/bin/env python3
"""Check native KIR record-schema closure; Python stages bytes and compares CIDs.

The frozen CIDs were measured from the pinned reference on 2026-11-02 and
independently reconstructed with the native 04 encoder. They are data, not a
runtime fallback or cache admission. Source schema closure remains separate.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('macos_native_image', ROOT / 'scripts/seed/macos_native_image.py')
mac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mac)
EXTRA = ['seed/04-definition-cid.kotoba', 'seed/05-definition-graph.kotoba',
         'seed/05-checked-definition.kotoba', 'seed/06-definition-groups.kotoba']
ENTRY = '''
(defn- seed-main [] :i64
 (if (not= (io-argc) 1) 2
  (let [K (io-fs2-text 65 (io-arg 0) "") status (dcs-run-resource K 1)]
   (if (= status 0) 0 (let [e (io-err (string-concat "SCHEMA:" (string-concat (mem-u2dec status) "\\n")))] 1)))))
'''
GOLDEN = {
    'simple': 'bafyreiagssxmxbxfy7i3zq4m6ayucfkyjylomcruexauvgvw6dtjqtfeeu',
    'wide': 'bafyreidaytqoaqbuviy36bdr4cqhxp44t7fyi4p7imewkf43pyz2patx34',
    'transitive': 'bafyreiadno3ibxqnk6ifmempx2gx2f6agdxrtw33aesdteniywuddrhpou',
    'transitive-edit': 'bafyreihfv6o5vy2qm5ovfbog7g5fo5o7k7urmvhuupo7jazxcsgiyz5gdy',
    'cycle': 'bafyreic4u2yz7lplpnqy6e6kcxjo2mgbkvp3zfla7552pgtcd45cxy7bii',
}
SCC = {
    'simple': ('bafyreihtokury6llizbq7wmkyqcfxbercbjmyphgbhzuqws354lgcnhenq',
               'bafyreie7ddqj6iifuc4cu4vhjasuba7cjxamxiboevo3urztubufhhwosy',
               'bafyreibtoqy7rc5f5axhbriw5tlmixzxeud6z76wmuh7libnydnbyxb6se'),
    'wide': ('bafyreibsizl5lawwbx6q4cke72mcgrumbdkua6sxt37k2d7k7hno5j2moi',
             'bafyreiepwb6pqth2fa2qksm3soohtlhdk62omqs3awruva5nmgya6wen3i',
             'bafyreiesxu6f72as4v3bgyywftdz3nrl3b6v7rny4kji4mzw5ozls32esi'),
}
SCHEMAS = {
    'simple': '{:s/r [:record :s/r [[:a :i64]]]}',
    'wide': '{:s/r [:record :s/r [[:a :i64] [:b :i64]]]}',
    'unrelated': '{:s/r [:record :s/r [[:a :i64]]] :s/u [:record :s/u [[:z :string]]]}',
    'transitive': '{:s/r [:record :s/r [[:n [:ref :s/n]]]] :s/n [:record :s/n [[:v :i64]]]}',
    'transitive-edit': '{:s/r [:record :s/r [[:n [:ref :s/n]]]] :s/n [:record :s/n [[:v :string]]]}',
    'reordered': '{:s/n [:record :s/n [[:v :i64]]] :s/r [:record :s/r [[:n [:ref :s/n]]]]}',
    'cycle': '{:s/r [:record :s/r [[:next [:ref :s/n]]]] :s/n [:record :s/n [[:prev [:ref :s/r]]]]}',
    'missing': '{}',
    'missing-transitive': '{:s/r [:record :s/r [[:n [:ref :s/n]]]]}',
    'duplicate': '{:s/r [:record :s/r [[:a :i64]]] :s/r [:record :s/r [[:a :string]]]}',
    'bad-name': '{:s/r [:record :s/wrong [[:a :i64]]]}',
    'bad-type': '{:s/r [:record :s/r [[:a :not-a-type]]]}',
    'bad-unused': '{:s/r [:record :s/r [[:a :i64]]] :s/bad [:record :s/bad [[:z :not-a-type]]]}',
    'duplicate-field': '{:s/r [:record :s/r [[:a :i64] [:a :string]]]}',
    'bad-legacy': '{:Foo [:record {:x :i64}]}',
}


def pin(path):
    b = path.read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def module(schema, functions):
    return ('{:format :kotoba.kir/v4 :entry nil :exports [] :effects #{} :schemas ' + schema +
            ' :functions [' + ' '.join(functions) + ']}\n')


def fn(name, body, param='[x]', types='[[:ref :s/r]]'):
    return ('{:name ' + name + ' :params ' + param + ' :param-types ' + types +
            ' :result :i64 :effects #{} :body ' + body + '}')


def main(compiler, out):
    darwin = mac.available()
    machine = platform.machine()
    assert darwin or (platform.system() == 'Linux' and machine in ('aarch64', 'x86_64'))
    target = 'aarch64-linux' if machine == 'aarch64' else 'x86_64-linux'
    product = json.loads((ROOT / 'native-product.json').read_text())
    if darwin:
        root, packager = mac.root_images()
        assert pin(compiler) == pin(root)
    else:
        assert pin(compiler) == product['rootImage' if machine == 'aarch64' else 'image']
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    paths = [p for p in (ROOT / 'seed/CORE-STATIC-MANIFEST').read_text().splitlines() if p and not p.startswith('#')]
    assert paths.pop() == 'seed/99-entry.kotoba'
    paths += EXTRA
    text = '\n'.join((ROOT / p).read_text() for p in paths) + ENTRY
    env = dict(PATH='/nonexistent', KEXE_STACK_BYTES='8388608', KEXE_FUEL='10000000000',
               KEXE_ALLOW='35,37,38,39', KEXE_CAP_RESOURCES_35=str(out))
    report = {'schema': 'amu.native-kir-schema-closure.v1', 'host': [platform.system(), machine],
              'compiler': pin(compiler), 'observer': pin(Path(__file__)),
              'modules': {p: pin(ROOT / p) for p in paths}, 'inputs': {},
              'calls': [], 'nativeVerdictAuthority': False, 'sourceClosureQualified': False,
              'persistentBuildQualified': False, 'resourceProofQualified': False}

    def save():
        (out / 'observations.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(name, image, args, code=0):
        if darwin:
            result = mac.run(image, out, args)
        else:
            result = subprocess.run([str(image), *map(str, args)], cwd=out, env=env,
                                    capture_output=True, timeout=300)
        for stream in ('stdout', 'stderr'):
            (out / (name + '.' + stream)).write_bytes(getattr(result, stream))
        report['calls'].append({'name': name, 'exit': result.returncode,
                                'stdout': pin(out / (name + '.stdout')),
                                'stderr': pin(out / (name + '.stderr'))})
        save()
        assert result.returncode == code, (name, result.returncode, result.stderr[-400:])
        return result

    def build(name, source):
        file = out / (name + '.kotoba')
        file.write_text(source)
        if darwin:
            image, _ = mac.build(compiler, packager, out, file.name, name)
            return image
        image = out / (name + '.elf')
        result = subprocess.run([str(compiler), 'compile', str(file), '--target', target,
                                 '--output', str(image), '--format', 'static'], cwd=out, env=env,
                                capture_output=True, timeout=300)
        assert result.returncode == 0, (name, result.stderr[-400:])
        image.chmod(0o700)
        return image

    producer = build('producer', text)
    old = '(dsq-walk M S A V schemas (vector-at V (+ 2 (* 2 i))) 0)'
    start = text.index('(defn- dsq-schemas ')
    before, after = text[:start], text[start:]
    assert after.count(old) == 1
    mutant_transitive = build('mutant-transitive', before + after.replace(old, '0', 1))
    old = '(dsq-walk M S A V schemas (dcp-field M S map ":param-types") 0)'
    assert text.count(old) == 1
    mutant_params = build('mutant-params', text.replace(old, '0', 1))
    old = '(dsq-catalog M S A doc)'
    assert text.count(old) == 1
    mutant_catalog = build('mutant-catalog', text.replace(old, 'A', 1))
    report['images'] = {name: pin(image) for name, image in (
        ('producer', producer), ('mutant-transitive', mutant_transitive),
        ('mutant-params', mutant_params), ('mutant-catalog', mutant_catalog))}
    save()

    def evaluate(name, source, image=producer, code=0):
        path = out / (name + '.kir')
        path.write_text(source)
        report['inputs'][name] = pin(path)
        p = run(name, image, [path.name if darwin else path], code)
        if code:
            assert not p.stdout and p.stderr.startswith(b'SCHEMA:')
            return {}
        assert not p.stderr
        lines = p.stdout.decode().splitlines()
        assert lines.pop(0) == 'DCP1 6 2'
        rows = {}
        for line in lines:
            row = line.split()
            assert len(row) == 4 and row[0] not in rows
            rows[row[0]] = row[1:]
        return rows

    for name in ('simple', 'wide', 'unrelated', 'transitive', 'transitive-edit', 'reordered', 'cycle'):
        expected = 'simple' if name == 'unrelated' else 'transitive' if name == 'reordered' else name
        assert evaluate(name, module(SCHEMAS[name], [fn('f', '42')]))['f'][0] == GOLDEN[expected]
    for name in ('missing', 'missing-transitive', 'duplicate', 'bad-name', 'bad-type', 'bad-unused', 'duplicate-field'):
        evaluate(name, module(SCHEMAS[name], [fn('f', '42')]), code=1)
    pure = evaluate('pure', module('{}', [fn('g', '42', '[]', '[]')]))['g'][0]
    evaluate('bad-legacy', module(SCHEMAS['bad-legacy'], [fn('g', '42', '[]', '[]')]), code=1)
    mixed = evaluate('mixed', module(SCHEMAS['simple'], [fn('f', '42'), fn('g', '42', '[]', '[]')]))
    assert mixed['f'][0] == GOLDEN['simple'] and mixed['g'][0] == pure
    for name in ('simple', 'wide', 'unrelated'):
        functions = [fn('f', '(if true 42 (g x))'), fn('g', '(if true 43 (f x))')]
        actual = evaluate('scc-' + name, module(SCHEMAS[name], functions))
        group, f, g = SCC['simple' if name == 'unrelated' else name]
        assert actual == {'f': [f, group, '0'], 'g': [g, group, '1']}
    assert evaluate('mutant-transitive', module(SCHEMAS['transitive'], [fn('f', '42')]), mutant_transitive)['f'][0] != GOLDEN['transitive']
    assert evaluate('mutant-transitive-control', module(SCHEMAS['simple'], [fn('f', '42')]), mutant_transitive)['f'][0] == GOLDEN['simple']
    assert evaluate('mutant-params', module(SCHEMAS['simple'], [fn('f', '42')]), mutant_params)['f'][0] != GOLDEN['simple']
    # Removing the catalog check must admit the otherwise unreferenced bad
    # schema; the normal producer refuses the same module atomically.
    assert evaluate('mutant-catalog', module(SCHEMAS['bad-legacy'], [fn('g', '42', '[]', '[]')]), mutant_catalog)['g'][0] == pure
    report['status'] = 'PASS_NATIVE_KIR_SCHEMA_CLOSURE'
    save()
    print(report['status'], len(report['calls']), 'calls', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.compiler.resolve(), args.output.resolve())
