"""Finite SOURCE inspection only: no imports of subprocess/network/native APIs.

This s-expression inventory counts syntax, not typed applicability or execution.
Run once against fixed local files; preserves all product and prior frozen sources.
"""
import collections
import hashlib
import json
import pathlib
import re

D = pathlib.Path(__file__).resolve().parent
R = pathlib.Path('/Users/junkawasaki/github/wt/amu-seed17')
W = pathlib.Path('/Users/junkawasaki/github/workspaces/codex')

def pin(p):
    b = p.read_bytes()
    assert len(b) <= 16 * 1024 * 1024
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def parse(s):
    # The fixed workload grammar has no reader dispatch or quoted strings.
    tokens = re.findall(r';[^\n]*|[()\[\]]|[^\s()\[\];]+', s)
    stack = [[]]
    delimiters = []
    for t in tokens:
        if t.startswith(';'):
            continue
        if t in ('(', '['):
            q = []
            stack[-1].append(q)
            stack.append(q)
            delimiters.append(t)
        elif t in (')', ']'):
            assert len(stack) > 1 and delimiters.pop() == ( '(' if t == ')' else '[' )
            stack.pop()
        else:
            assert '"' not in t
            stack[-1].append(t)
    assert len(stack) == 1 and not delimiters
    return stack[0]

def walk(x):
    if isinstance(x, list):
        yield x
        for y in x:
            yield from walk(y)

manifest = R / 'seed/MANIFEST'
mods = [R / l for l in manifest.read_text().splitlines() if l.strip() and not l.startswith('#')]
assert len(mods) == 16
unity = hashlib.sha256(b''.join(p.read_bytes() + b'\n' for p in mods)).hexdigest()
assert unity == '953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418'
assert pin(R / 'seed/41-a64gen.kotoba')['sha256'] == '4ed9b5600505c33013c966d266a977a3d4ccd56ad3cdc425b1805acf390b95f3'
stats = {}
for name in ('statemate', 'nsichneu'):
    p = R / f'bench/embench/batch-ports/{name}.kotoba'
    forms = parse(p.read_text())
    funcs = [f for f in forms if f and f[0] in ('defn', 'defn-')]
    names = {f[1] for f in funcs}
    nodes = list(walk(forms))
    heads = collections.Counter(x[0] for x in nodes if x and isinstance(x[0], str))
    reads = [x for x in nodes if x and x[0] == 'vector-at']
    writes = [x for x in nodes if x and x[0] == 'vector-assoc!']
    literal = lambda x: isinstance(x, str) and re.fullmatch(r'-?\d+', x) is not None
    def access_count(xs):
        return {'sites': len(xs), 'literalIndexSites': sum(literal(x[2]) for x in xs),
                'dynamicIndexSites': sum(not literal(x[2]) for x in xs)}
    stats[name] = {'source': pin(p), 'functions': len(funcs),
        'privateFunctions': sum(f[0] == 'defn-' for f in funcs),
        'vectorResultFunctions': sum(f[3] == ':vector-i64' for f in funcs),
        'maximumParameterCount': max(len(f[2]) // 2 for f in funcs),
        'localFunctionCallSyntaxSites': sum(heads[n] for n in names),
        'ifSyntaxSites': heads['if'], 'reads': access_count(reads),
        'inPlaceWrites': access_count(writes), 'persistentAssocSyntaxSites': heads['vector-assoc'],
        'literalAllocationLengths': [int(x[1]) for x in nodes if x and x[0] == 'vector-alloc'],
        'completeOrderedFunctionNames': [f[1] for f in funcs]}
    assert stats[name]['persistentAssocSyntaxSites'] == 0

extra = [R / 'AGENTS.md', R / 'seed/SIR', R / 'bench/embench/comparison-matrix.json',
 R / 'docs/coscientist-scalar-dag-inline-20261006.md',
 W / 'vector-masked32-source-bound-loader-build-plan-v2-native-controls/kexe_loader.c',
 W / 'crc-table-decision-collapse-native-component-v4-portable-env-20261008/run-outputs/current-baseline.bin',
 W / 'crc-table-decision-collapse-native-component-v4-portable-actual-review-independent-20261008/report.json']
for name in stats:
    extra.append(W / f'vector-param-embench-C-rebuild-plan-v1-native-controls/inputs/upstream/src/{name}/lib{name}.c')
out = {'schema': 'vector-state-source-frontier/v1', 'status': 'SOURCE_ONLY',
 'nativeCompilerLoaderNetworkSetterCalls': 0,
 'unity': {'moduleCount': 16, 'sha256': unity, 'construction': 'MANIFEST order, each raw module plus newline'},
 'pins': [pin(p) for p in [manifest] + mods + extra], 'syntaxInventory': stats,
 'caveat': 'Syntax counts are not current typed SIR, emitted operations, dynamic counts, or performance proof.'}
(D / 'source-inspection.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({n: {k:v for k,v in st.items() if k != 'completeOrderedFunctionNames'} for n,st in stats.items()}, indent=2))
