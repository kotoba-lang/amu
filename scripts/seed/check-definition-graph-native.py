#!/usr/bin/env python3
"""Observe the shared native dependency graph, never grant cache authority.

Graph building, validation, iterative traversal and the exhaustive small-graph
reachability oracle run in Amu images. Python stages bytes/processes and records
their outputs. The actual whole-compiler checked-KIR/identity bridge is separate.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KERNEL = "seed/05-definition-graph.kotoba"
TEST = "seed/tests/native-definition-graph.kotoba"
UNIT_ENTRY = "\n(defn- seed-main [] :i64 (dgt-run))\n"
SIR_TEST = "seed/tests/native-definition-graph-sir.kotoba"
WHOLE_ENTRY = "\n(defn- seed-main [] :i64 (if (= (io-argc) 1) (dgsr-run (drv-read (io-arg 0))) 2))\n"


def graph_observation(raw):
    lines = raw.decode().splitlines()
    assert lines and lines[0].startswith('DGG1 ')
    header = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', lines[0])}
    assert set(header) == {'functions', 'references', 'indirect', 'declarations', 'components', 'words', 'directOnly'}
    vertices, edges, indirect, constants, templates = {}, [], [], [], []
    for line in lines[1:]:
        row = line.split()
        if row[0] == 'V':
            assert len(row) == 3 and int(row[1]) not in vertices
            vertices[int(row[1])] = int(row[2])
        elif row[0] == 'E':
            assert len(row) == 3
            edges.append((int(row[1]), int(row[2])))
        elif row[0] == 'I':
            assert len(row) == 4
            indirect.append(dict(owner=int(row[1]), name=row[2], count=int(row[3])))
        else:
            assert row[0] in ('D', 'T') and len(row) == 3
            (constants if row[0] == 'D' else templates).append(dict(owner=int(row[1]), name=row[2]))
    n = header['functions']
    assert set(vertices) == set(range(1, n + 1)) and len(edges) == header['references']
    assert sum(r['count'] for r in indirect) == header['indirect']
    assert len(constants) + len(templates) == header['declarations']
    assert header['directOnly'] == (0 if indirect or constants or templates else 1)
    adj, reverse = [[] for _ in range(n + 1)], [[] for _ in range(n + 1)]
    for a, b in edges:
        assert a in vertices and b in vertices
        adj[a].append(b); reverse[b].append(a)
    seen, order = set(), []
    for start in range(1, n + 1):
        if start in seen:
            continue
        seen.add(start); stack = [(start, 0)]
        while stack:
            f, at = stack[-1]
            if at == len(adj[f]):
                stack.pop(); order.append(f)
            else:
                stack[-1] = (f, at + 1); nxt = adj[f][at]
                if nxt not in seen:
                    seen.add(nxt); stack.append((nxt, 0))
    seen, components = set(), []
    for start in reversed(order):
        if start in seen:
            continue
        seen.add(start); stack, group = [start], []
        while stack:
            f = stack.pop(); group.append(f)
            for nxt in reverse[f]:
                if nxt not in seen:
                    seen.add(nxt); stack.append(nxt)
        components.append(tuple(sorted(group)))
    native = {}
    for f, c in vertices.items():
        native.setdefault(c, []).append(f)
    assert sorted(components) == sorted(tuple(sorted(g)) for g in native.values())
    assert len(components) == header['components']
    return dict(**header, constantDeclarations=len(constants), statefulTemplates=len(templates),
                unresolvedIndirect=indirect, largeComponents=sorted([len(c) for c in components if len(c) > 8], reverse=True),
                nativeFunctionIntervalOracle=True, independentKosarajuMatches=True,
                completeSemanticDependencies=False)


def kernel_mutations(kernel):
    def change(old, new):
        assert kernel.count(old) == 1, old
        return kernel.replace(old, new)
    return [
        ('backedge-low', 'DGG:REACHABILITY', change(
            '(min (dgg-f advanced target 6) (dgg-f advanced f 7))', '(dgg-f advanced f 7)')),
        ('parent-low', 'DGG:REACHABILITY', change(
            '(dgg-put a parent 7 (min (dgg-f a f 7) (dgg-f a parent 7)))', 'a')),
        ('adjacency-chain', 'DGG:REACHABILITY', change(
            '(dgg-put a f 10 (dgg-edge a edge 1))', '(dgg-put a f 10 0)')),
        ('unused-vertex', 'DGG:REACHABILITY', change(
            '(> (dgg-f state start 6) 0)', '(or (> (dgg-f state start 6) 0) (= start 0))')),
        ('component-head', 'DGG:REACHABILITY', change(
            '(vector-assoc! current at (inc f))', '(vector-assoc! current at 0)')),
        ('sealed-write', 'DGG:REFUSAL', change('(not= (vector-at G 14) 0) ', '')),
        ('indirect-unknown', 'DGG:REFUSAL', change('(= (vector-at G 13) 0) (= (vector-at G 15) 0)',
                                                            '(= 0 0) (= (vector-at G 15) 0)')),
        ('declaration-unknown', 'DGG:REFUSAL', change('(= (vector-at G 15) 0)))', '(= 0 0)))')),
    ]


def pin(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main(args):
    assert platform.system() == "Linux" and platform.machine() in ("aarch64", "x86_64")
    compiler = args.compiler.resolve()
    data = compiler.read_bytes()
    machine = 183 if platform.machine() == "aarch64" else 62
    target = "aarch64-linux" if machine == 183 else "x86_64-linux"
    assert data[:7] == b"\x7fELF\x02\x01\x01" and struct.unpack_from('<H', data, 18)[0] == machine
    product = json.loads((ROOT / 'native-product.json').read_text())
    assert pin(compiler) == product['rootImage' if machine == 183 else 'image']
    out = args.output.resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    (out / 'observer.py').write_bytes(Path(__file__).read_bytes())
    paths = [p for p in (ROOT / "seed/CORE-STATIC-MANIFEST").read_text().splitlines() if p and not p.startswith('#')]
    assert paths[-1] == "seed/99-entry.kotoba"
    paths = paths[:-1] + [KERNEL, TEST]
    source = out / 'unit.kotoba'
    source.write_bytes(b'\n'.join((ROOT / p).read_bytes() for p in paths) + UNIT_ENTRY.encode())
    report = dict(schema='amu.native-definition-graph.v1', status='running',
                  compiler=pin(compiler), observer=pin(Path(__file__)), host=[platform.system(), platform.machine()],
                  modules={p: pin(ROOT / p) for p in paths}, calls=[], mutations=[],
                  emulation=False, canonicalIdentityBridgeQualified=False,
                  cacheAdmission=False, persistentBuildQualified=False,
                  productionCompilerClosureChanged=False)
    build_env = dict(PATH='/nonexistent', KEXE_ALLOW='35,37,38,39', KEXE_CAP_RESOURCES_35=str(out),
                     KEXE_STACK_BYTES='8388608', KEXE_FUEL='10000000000')

    def save():
        (out / 'observations.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(name, argv, env, expected=0):
        start = time.monotonic()
        p = subprocess.run(list(map(str, argv)), cwd=out, env=env, capture_output=True, timeout=900)
        (out / (name + '.stdout')).write_bytes(p.stdout)
        (out / (name + '.stderr')).write_bytes(p.stderr)
        report['calls'].append(dict(name=name, exit=p.returncode, seconds=time.monotonic()-start,
            stdout=pin(out / (name + '.stdout')), stderr=pin(out / (name + '.stderr'))))
        save()
        print(name, p.returncode, p.stdout[:160].decode(errors='replace'), p.stderr[:160].decode(errors='replace'), flush=True)
        assert p.returncode == expected, name
        return p

    image = out / 'unit.elf'
    run('unit-build', [compiler, 'compile', source, '--target', target, '--output', image, '--format', 'static'], build_env)
    image.chmod(0o700)
    p = run('unit-execute', [image], {**build_env, 'KEXE_ALLOW': '37,39'})
    assert p.stdout == b'PASS_NATIVE_SPARSE_GRAPH 66067 8191\n' and not p.stderr
    report.update(status='PASS_NATIVE_GRAPH_UNIT_DIAGNOSTIC', exhaustiveGraphs=66067, largestVertices=8191,
                  unit=pin(image), wholeCompilerGraphQualified=False)
    save()
    if args.unit_only:
        return
    prefix = b'\n'.join((ROOT / p).read_bytes() for p in paths[:-2]) + b'\n'
    kernel = (ROOT / KERNEL).read_text()
    suffix = b'\n' + (ROOT / TEST).read_bytes() + UNIT_ENTRY.encode()
    for name, message, changed in kernel_mutations(kernel):
        src, mutant = out / (name + '.kotoba'), out / (name + '.elf')
        src.write_bytes(prefix + changed.encode() + suffix)
        run('build-' + name, [compiler, 'compile', src, '--target', target, '--output', mutant, '--format', 'static'], build_env)
        mutant.chmod(0o700)
        p = run('detect-' + name, [mutant], {**build_env, 'KEXE_ALLOW': '37,39'}, 1)
        assert not p.stdout and p.stderr == (message + '\n').encode(), name
        report['mutations'].append(dict(name=name, built=True, executed=True, verdict=message, image=pin(mutant)))
        save()
    full_paths = [p for p in (ROOT / 'seed/FULL-MANIFEST').read_text().splitlines() if p and not p.startswith('#')]
    # Follow the complete pinned producer closure as native targets grow.
    # A fixed47 check would reject an adopted added backend or tempt dropping
    # its source from this observer; the product and unity must match instead.
    assert len(full_paths) == product['sourceModuleCount']
    assert len(set(full_paths)) == len(full_paths)
    assert all(p.startswith('seed/') and '..' not in Path(p).parts for p in full_paths)
    original = b''.join((ROOT / p).read_bytes() + b'\n' for p in full_paths)
    input_path = out / 'whole-compiler.kotoba'
    input_path.write_bytes(original)
    assert pin(input_path) == product['sourceUnity']
    parts = []
    for path in full_paths:
        # JUN-584: the kernel is in FULL-MANIFEST now; it is appended below (possibly mutated), never twice.
        if path == KERNEL:
            continue
        data = (ROOT / path).read_bytes()
        if path == 'seed/78-full-entry.kotoba':
            assert data.count(b'(defn- seed-main [] :i64') == 1
            data = data.replace(b'(defn- seed-main [] :i64', b'(defn- dgg-original-main [] :i64')
        parts.append(data)
    whole_source, whole_image = out / 'whole-producer.kotoba', out / 'whole-producer.elf'
    full_prefix = b'\n'.join(parts) + b'\n'
    whole_suffix = b'\n' + (ROOT / SIR_TEST).read_bytes() + WHOLE_ENTRY.encode()
    whole_source.write_bytes(full_prefix + kernel.encode() + whole_suffix)
    report['wholeModules'] = {p: pin(ROOT / p) for p in [*full_paths, SIR_TEST]}
    report['wholeInput'] = pin(input_path)
    save()
    run('whole-build', [compiler, 'compile', whole_source, '--target', target, '--output', whole_image, '--format', 'static'], build_env)
    whole_image.chmod(0o700)
    p = run('whole-execute', [whole_image, input_path], build_env)
    assert not p.stderr
    report['wholeCompilerKnownCalls'] = graph_observation(p.stdout)
    for name, text in [('ill-typed', '(ns bad (:export [main]))\n(defn main [] :i64 (missing 1))\n'),
                       ('claimed-checked', '{:checked true :source-digest "ignored"}\n')]:
        src = out / (name + '.kotoba'); src.write_text(text)
        p = run('refuse-' + name, [whole_image, src], build_env, 1)
        assert not p.stdout and p.stderr == b'DGG:FRONTEND\n'
    # The native interval oracle must detect real importer drift on the actual
    # unmodified whole compiler input, not a mocked SIR or a host verdict.
    old = '(or (= op OP-CALL) (= op OP-FADDR))\n                            (recur'
    assert kernel.count(old) == 1
    changed = kernel.replace(old, '(= op OP-CALL)\n                            (recur')
    src, mutant = out / 'missing-faddr.kotoba', out / 'missing-faddr.elf'
    src.write_bytes(full_prefix + changed.encode() + whole_suffix)
    run('build-missing-faddr', [compiler, 'compile', src, '--target', target, '--output', mutant, '--format', 'static'], build_env)
    mutant.chmod(0o700)
    p = run('detect-missing-faddr', [mutant, input_path], build_env, 1)
    assert not p.stdout and p.stderr == b'DGG:SIR-IMPORT\n'
    report['mutations'].append(dict(name='missing-faddr', built=True, executed=True,
        verdict='DGG:SIR-IMPORT', image=pin(mutant), input=pin(input_path)))
    assert all(pin(ROOT / p) == value for p, value in {**report['modules'], **report['wholeModules']}.items())
    report.update(status='PASS_NATIVE_SHARED_DEFINITION_GRAPH', knownWholeCompilerCallsObserved=True,
                  wholeProducer=pin(whole_image), wholeInputUnchanged=True)
    save()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiler', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--unit-only', action='store_true', help='Diagnostic subset, never the complete gate')
    main(p.parse_args())
