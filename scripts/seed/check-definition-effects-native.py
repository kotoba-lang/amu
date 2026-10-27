#!/usr/bin/env python3
"""Stage effect fixtures; catalog checks, inference, payloads and CIDs are native."""
import argparse
import hashlib
import json
import platform
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRA = ['seed/04-definition-cid.kotoba', 'seed/05-definition-graph.kotoba',
         'seed/05-checked-definition.kotoba', 'seed/06-definition-groups.kotoba',
         'seed/05-checked-source.kotoba', 'seed/05-source-loops.kotoba',
         'seed/tests/native-definition-effects.kotoba']
ENTRY = '''
(defn- seed-main [] :i64
 (cond (and (= (io-argc) 2) (= (io-arg 0) "catalog"))
         (if (dfx-catalog (io-fs2-text 65 (io-arg 1) "")) 0 1)
       (and (= (io-argc) 4) (= (io-arg 0) "oracle"))
         (let [text (io-arg 1) wire (mem-parse-dec text 0 (string-length text)) name (io-arg 2)
               payload (cond (= (io-arg 3) "leaf") (dfx-leaf wire name)
                         (= (io-arg 3) "caller") (dfx-caller wire name)
                         (= (io-arg 3) "self") (dfx-self-member wire name)
                         (= (io-arg 3) "group") (dfx-self-group wire name) :else "")
               cid (dc-definition-cid payload) out (io-out (string-concat cid "\\n"))]
           (if (= (string-length cid) 59) 0 1))
       (and (= (io-argc) 2) (= (io-arg 0) "source")) (dsb-source (io-fs2-text 65 (io-arg 1) "") false)
       (and (= (io-argc) 2) (= (io-arg 0) "kir"))
         (let [status (dcs-run (io-fs2-text 65 (io-arg 1) ""))]
           (if (= status 0) 0 (let [e (io-err (string-concat "DCP:E" (string-concat (mem-u2dec status) "\\n")))] 1)))
       :else 2))
'''
WIRES = [(3, 'hash/sha256'), (7, 'clock/now'), (11, 'llm/generate'), (20, 'process/spawn'),
         (23, 'entropy/draw'), (33, 'env/read'), (34, 'fs/browse'), (35, 'fs/app-data'),
         (37, 'io/write'), (38, 'cli/args'), (39, 'io/write-error'), (40, 'sys/cwd'), (41, 'io/read'),
         (42, 'gpu/compute'), (43, 'net/listen'), (44, 'net/accept'), (45, 'net/dial'), (46, 'net/read'), (47, 'net/write')]
def pin(p):
    b = p.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
def effects(*wires):
    return '#{' + ' '.join(f'[:cap/call {w}]' for w in wires) + '}'
def fn(name, body, row):
    return f'{{:name {name} :params [x] :param-types [:string] :result :string :effects {row} :body {body}}}'
def module(functions, row):
    return '{:format :kotoba.kir/v4 :entry nil :exports [] :effects ' + row + ' :functions [' + ' '.join(functions) + ']}\n'
def rows(s):
    lines = s.decode().splitlines()
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
    paths = [p for p in (ROOT / 'seed/CORE-STATIC-MANIFEST').read_text().splitlines() if p and not p.startswith('#')][:-1] + EXTRA
    unity = '\n'.join((ROOT / p).read_text() for p in paths) + ENTRY
    env = dict(PATH='/nonexistent', KEXE_STACK_BYTES='8388608', KEXE_FUEL='10000000000',
               KEXE_ALLOW='35,37,38,39', KEXE_CAP_RESOURCES_35=str(out))
    report = dict(schema='amu.native-definition-effects.v1', status='RUNNING', host=[platform.system(), machine],
                  compiler=pin(compiler), observer=pin(Path(__file__)), modules={p:pin(ROOT / p) for p in paths},
                  calls=[], mutations=[], productionCompilerClosureChanged=False, nativeVerdictAuthority=False,
                  persistentBuildQualified=False, sourceResourceProofQualified=False)
    def save():
        (out / 'observations.json').write_text(json.dumps(report, indent=2) + '\n')
    def run(name, argv, code=0):
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=300)
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
    producer = build('effect-producer', unity)
    report['producer'] = pin(producer)
    catalog = out / 'capability-catalog.edn'
    shutil.copyfile(ROOT / 'seed/tests/checked-definition-authority/capability-catalog.edn', catalog)
    report['catalog'] = pin(catalog)
    run('catalog', [producer, 'catalog', catalog])
    forged = out / 'forged-catalog.edn'
    forged.write_bytes(catalog.read_bytes().replace(b':compiler-wire-id 37', b':compiler-wire-id 39'))
    run('refuse-catalog', [producer, 'catalog', forged], 1)
    sources, observed = {}, {}
    def produce(name, text, lane='kir', code=0, image=producer):
        src = out / (name + '.input'); src.write_text(text); sources[name] = (lane, src)
        p = run(name, [image, lane, src], code)
        if code == 0: observed[name] = rows(p.stdout)
        else: assert not p.stdout and p.stderr.startswith((b'DCP:', b'DSB:'))
        return p
    for wire, name in WIRES:
        if wire == 11: continue  # exact nominal request/result remain required
        row = effects(wire); body = f'(typed-cap-call {wire} :string :string x)'
        produce(f'kir-{wire}', module([fn('f', body, row)], row))
        produce(f'source-{wire}', f'(ns effect) (defn f [x :string] :string (typed-cap-call :{name} :string :string x))\n', 'source')
        oracle = run(f'oracle-{wire}', [producer, 'oracle', wire, name, 'leaf']).stdout.decode().strip()
        assert observed[f'kir-{wire}']['f'][0] == observed[f'source-{wire}']['f'][0] == oracle
    row = effects(37)
    leaf = fn('f', '(typed-cap-call 37 :string :string x)', row)
    produce('caller', module([leaf, fn('g', '(f x)', row)], row))
    assert observed['caller']['g'][0] == run('oracle-caller', [producer, 'oracle', 37, 'io/write', 'caller']).stdout.decode().strip()
    body = '(if (= (string-length x) 0) (typed-cap-call 37 :string :string x) (f ""))'
    produce('self', module([fn('f', body, row)], row))
    assert observed['self']['f'][0] == run('oracle-self', [producer, 'oracle', 37, 'io/write', 'self']).stdout.decode().strip()
    assert observed['self']['f'][1] == run('oracle-group', [producer, 'oracle', 37, 'io/write', 'group']).stdout.decode().strip()
    produce('sugar', '(ns effect) (defn f [x :string] :string (io/write x))\n', 'source')
    assert observed['sugar'] == observed['kir-37']
    produce('source-loop', '(ns effect) (defn f [x :string] :string (loop [s x] (if (= (string-length s) 0) (typed-cap-call :io/write :string :string s) (recur ""))))\n', 'source')
    assert observed['source-loop']['__kotoba_loop_1'][0:2] == observed['self']['f'][0:2]
    produce('source-caller', '(ns effect) (defn f [x :string] :string (io/write x)) (defn g [x :string] :string (f x))\n', 'source')
    assert observed['source-caller'] == observed['caller']
    alias = '{:name f :params [x] :param-types [:bytes] :result :bytes :effects ' + effects(35) + ' :body (typed-cap-call 35 :bytes :bytes x)}'
    produce('bytes-kir', module([alias], effects(35)))
    produce('bytes-source', '(ns effect) (defn f [x :bytes] :bytes (typed-cap-call :fs/app-data-bytes :bytes :bytes x))\n', 'source')
    assert observed['bytes-source'] == observed['bytes-kir'] != observed['kir-35']
    both = effects(37, 39)
    mixed = '(ns effect) (defn f [x :string] :string (let [a (io/write x)] (loop [s a] (if (= (string-length s) 0) (io/write-error s) (recur "")))))\n'
    produce('source-mixed-loop', mixed, 'source')
    helper = fn('__kotoba_loop_1', '(if (= (string-length x) 0) (typed-cap-call 39 :string :string x) (__kotoba_loop_1 ""))', effects(39))
    outer = fn('f', '(let [a (typed-cap-call 37 :string :string x)] (__kotoba_loop_1 a))', both)
    produce('kir-mixed-loop', module([outer, helper], both))
    assert observed['source-mixed-loop'] == observed['kir-mixed-loop']
    assert observed['source-mixed-loop']['__kotoba_loop_1'][0] == run('oracle-mixed-helper', [producer, 'oracle', 39, 'io/write-error', 'self']).stdout.decode().strip()
    negatives = {
        'missing-function-row': module([fn('f', '(typed-cap-call 37 :string :string x)', '#{}')], row),
        'missing-module-row': module([leaf], '#{}'),
        'missing-transitive-row': module([leaf, fn('g', '(f x)', '#{}')], row),
        'invented-row': module([fn('f', 'x', row)], row),
        'unknown-wire': module([fn('f', 'x', effects(999))], effects(999)),
        'unregistered-native-wire': module([fn('f', 'x', effects(36))], effects(36)),
        'named-wire-row': module([fn('f', 'x', '#{:io/write}')], '#{:io/write}'),
        'malformed-wire': module([fn('f', 'x', '#{[:cap/call 37 39]}')], row),
        'duplicate-wire': module([leaf], '#{[:cap/call 37] [:cap/call 37]}'),
        'nominal-llm-shape': module([fn('f', '(typed-cap-call 11 :string :string x)', effects(11))], effects(11)),
    }
    for name, data in negatives.items(): produce('refuse-' + name, data, code=1)
    mutations = [
        ('catalog-name', '37 "io/write"', '37 "io/write-error"', 'catalog', 'refusal'),
        ('effect-erasure', '(dc-entry "effect-row" (dcp-effect-row effects))', '(dc-entry "effect-row" (dcp-effect-row 0))', 'kir-37', 'mismatch'),
        ('inference-guard', '(dcp-effects M S components doc)', 'components', 'refuse-missing-function-row', 'admission'),
        ('group-row', '(dcp-group-effects A C)', '0', 'self', 'mismatch'),
        ('helper-effect-borrow', '(dsb-effect-mask M (nm-nth M node 2))', '(ck-f2 M (vector-at C 3) FN2-FX)', 'source-mixed-loop', 'refusal'),
    ]
    for name, old, new, probe, detection in mutations:
        assert old in unity
        mutant = build('mutant-' + name, unity.replace(old, new))
        if probe == 'catalog':
            run('detect-' + name, [mutant, 'catalog', catalog], 1)
        else:
            lane, src = sources[probe]
            p = run('detect-' + name, [mutant, lane, src], 1 if detection == 'refusal' else 0)
            if detection == 'refusal': assert not p.stdout and p.stderr.startswith(b'DSB:')
            elif detection == 'mismatch': assert rows(p.stdout) != observed[probe]
            else: assert p.stdout.startswith(b'DCP1')
        report['mutations'].append(dict(name=name, image=pin(mutant), built=True, executed=True, detected=True))
    report.update(status='PASS_NATIVE_DEFINITION_EFFECTS', catalogWires=19, leafPairs=18,
                  independentLeafOracles=18, transitiveCaller=True, independentRecursiveGroup=True,
                  sourceSugar=True, sourceLoop=True, sourceTransitive=True, bytePayloadPrimaryName=True,
                  loopHelperOwnEffectRow=True,
                  atomicRefusals=len(negatives))
    assert all(pin(ROOT / p) == v for p, v in report['modules'].items())
    save(); print(report['status'], flush=True)
if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--compiler', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); main(a.compiler.resolve(), a.output.resolve())
