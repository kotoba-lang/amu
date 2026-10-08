"""Independent saved-file reader only. Run after root explicitly confirms CLOSED.

No imports of the driver, subprocesses, native execution, timing or performance.
"""
from pathlib import Path
import json, hashlib, re, stat, sys

D = Path('/Users/junkawasaki/github/workspaces/codex/vector-fuel-scalar-dag-original19-selfbuild44-plan-v1-native-controls')
O = D / 'run-outputs'
Q = Path(__file__).resolve().parent
G = D.parent / 'vector-fuel-scalar-dag-original19-selfbuild44-go-v1-root/root-go.json'
EXPECTED = {
    'source-pins.json': '8c454e8b523f694f8d8e60be1cab8044a886b52c3ab39788562e82708792ce7a',
    'run.py': '3cf6ed1f27dc2397aec8cacc3d7b4ffdf8c1a62828b5638c3a2a89018c79ab8a',
    'preregistration.json': '27f4aae30266599e78acd6f8e465cde25a9e1a07c7aa37e810c26bef3ad4ac7f',
    'input-pins.json': '58827eb9d2862c54a461cd188ed73c6762cfae8a3ee2ac25020f6259065c125a',
}
GOHASH = '916d1258ca05d7896aff5ad0f683823e1015bdd0acb3a4c62d6502d3f231ca11'
FIELDS = 'pairs string-pool-bytes vectors vector-items heap-bytes conj conj-tail conj-region conj-copy copied-words reserved-words regions scope-releases string-regions string-region-appends string-copied-bytes string-reserved-bytes'.split()
PAT = re.compile(('KEXE_ARENA_USE {' + ' '.join(':' + k + ' ([0-9]+)' for k in FIELDS) + '}\n').encode())

def need(value, message):
    if not value:
        raise AssertionError(message)

def data(path, maximum=469762048):
    path = Path(path)
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and not path.is_symlink() and 0 <= before.st_size <= maximum, 'bounded regular file: ' + str(path))
    result = path.read_bytes()
    after = path.lstat()
    need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'stable read: ' + str(path))
    return result

def receipt(path):
    b = data(path)
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

def load(path):
    return json.loads(data(path))

def pin(path, expected):
    need(receipt(path) == {k: expected[k] for k in ('bytes', 'sha256')}, 'pin mismatch: ' + str(path))

def container(path):
    b = data(path, 4194560)
    header = re.match(rb'KSEED1 ([1-9][0-9]*) ([1-9][0-9]*)\n', b)
    need(header is not None, 'KSEED header')
    size, count = map(int, header.groups())
    need(0 < size <= 4194304 and 0 < count <= 128, 'KSEED bounds')
    end = b.find(b'\n\n', header.end())
    need(end >= header.end(), 'KSEED export separator')
    exports = []
    for line in b[header.end():end].splitlines():
        m = re.fullmatch(rb'([A-Za-z0-9_-]+) ([0-9]+) ([0-9]+)', line)
        need(m is not None, 'export schema')
        exports.append([m[1].decode(), int(m[2]), int(m[3])])
    payload = b[end + 2:]
    need(len(payload) == size and len(exports) == count and len({e[0] for e in exports}) == count, 'whole payload / export count')
    need(all(e[1] % 4 == 0 and e[1] + 4 <= size and e[2] <= 32 for e in exports), 'aligned bounded exports')
    return b, payload, exports

def first_difference(a, b):
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None if len(a) == len(b) else min(len(a), len(b)))

def audit():
    for name, sha in EXPECTED.items():
        need(receipt(D / name)['sha256'] == sha, 'frozen SOURCE registry')
    need(receipt(G)['sha256'] == GOHASH, 'exact root GO')
    pr, go = load(D / 'preregistration.json'), load(G)
    for name, value in load(D / 'source-pins.json').items():
        pin(D / name, value)
    ip = load(D / 'input-pins.json')
    need(len(ip) == 2161 and sum(v['bytes'] for v in ip.values()) == 406252033, 'whole input closure counts')
    for name, value in ip.items():
        pin(name, value)
    pin(go['guest10RootAcceptance']['path'], go['guest10RootAcceptance'])
    need(load(go['guest10RootAcceptance']['path']) == pr['guestRootAcceptanceSchema'], 'exact Guest10 root acceptance')
    pin(pr['guestReceipt']['path'], pr['guestReceipt'])
    need(go['status'] == pr['rootGOStatus'] and go['maximumLoaderCalls'] == 44 and go['noRetry'] is True and go['timingAuthorized'] is False and go['workloadGuestAuthorized'] is False, 'root scope')
    terminal, report = load(O / 'terminal.json'), load(O / 'report.json')
    need(terminal == dict(loaderCalls=44, allChildrenClosed=True, failure=False), 'CLOSED successful exact44 terminal')
    need(report['status'] == 'COMPLETE_FUEL_DAG_ORIGINAL19_COMPILATION_G1_G2_G3_FIXEDPOINT_ONLY' and report['closedLoaderCalls'] == 44 and report['original19JoinedCompileExtractCalls'] == 38 and report['retainedOrdinaryCalls'] == 0 and report['selfbuildCalls'] == 6, 'report scope/counts')
    need(report['sourcePinsSHA256'] == EXPECTED['source-pins.json'] and report['rootGOSHA256'] == GOHASH, 'actual report lineage')
    need(not (O / 'failure.json').exists(), 'no saved first failure')
    for field in ('runtimeWorkloadExecution', 'runtimeABITrapFuelQualified', 'performanceQualified', 'officialScore', 'fullSelfhostGoalAchieved'):
        need(report[field] is False, 'no overclaim: ' + field)
    env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME='/Users/junkawasaki', TMPDIR=str(O), LANG='C', LC_ALL='C', TZ='UTC', KEXE_COMMAND='1', KEXE_CAP_RESOURCES_35=str(O), KEXE_STRING_POOL='268435456', KEXE_VECTORS='4194304', KEXE_PAIRS='16777216', KEXE_VECTOR_ITEMS='134217728', KEXE_CPU_SECONDS='1800', KEXE_WALL_SECONDS='1800', KEXE_FUEL='off', KEXE_ARENA_USE='1')
    need(load(O / 'effective-environment.json') == env, 'exact clean compiler environment')
    rows = load(O / 'attempts.json')
    images, generations = load(O / 'images.json'), load(O / 'generations.json')
    need(len(rows) == 44 and len(images) == 19 and len(generations) == 3, 'exact saved census')
    need(report['images'] == images and report['generations'] == generations, 'whole report/census correspondence')
    need(load(O / 'original19-boundary.json') == dict(newClosedCalls=38, retainedClosedCalls=0, joinedClosedCompileExtractCalls=38, workloads=19, generatedWorkloadExecution=False), 'original19 boundary')
    generated = load(O / 'generated-pins.json')
    for path, value in generated.items():
        need(Path(path).parent == O, 'generated artifact ownership')
        pin(path, value)
    expected_calls, artifact_checks = [], []
    mat = load(pr['canonicalMatrix'])
    need(len(pr['entries']) == len(mat['entries']) == 19, 'canonical original19')
    for entry, matrix, image in zip(pr['entries'], mat['entries'], images):
        n = entry['workload']
        need(n == matrix['workload'] and entry['symbol'] == matrix['symbol'] and entry['iterations'] == matrix['iterations'] and entry['source']['sha256'] == matrix['expectedSourceSha256'], 'canonical body/symbol/profile')
        copied = O / (n + '.kotoba')
        pin(copied, entry['source'])
        need(data(copied) == data(entry['source']['path']), 'whole original body copy')
        need(image['label'] == image['workload'] == n and image['retained'] is False and image['source'] == entry['source'] and image['iterations'] == entry['iterations'], 'original image metadata')
        artifact_checks.append((image, entry['symbol'], 1))
        for action in ('compile', 'extract'):
            expected_calls.append((n, action, copied, entry['symbol'], pr['producer']))
    unity = O / 'unity-df-on.kotoba'
    pin(unity, ip[pr['parentSource']])
    need(data(unity) == data(pr['parentSource']), 'whole unity source')
    producer = pr['producer']
    for i, image in enumerate(generations, 1):
        label = 'G' + str(i)
        need(image['generation'] == i and image['label'] == label, 'exact generation order')
        need(image['producer'] == dict(path=producer, **receipt(producer)) and image['source'] == dict(path=str(unity), **receipt(unity)), 'actual producer/source sequence')
        artifact_checks.append((image, 'main', 0))
        for action in ('compile', 'extract'):
            expected_calls.append((label, action, unity, 'main', producer))
        producer = image['native']['path']
    raw_counter_values = []
    for index, (row, expected) in enumerate(zip(rows, expected_calls), 1):
        label, action, source, symbol, producer = expected
        full_label = label + '-' + action
        k, b = O / (label + '.kseed'), O / (label + '.bin')
        args = ['compile', str(source), '--target', 'aarch64-macos', '--output', str(k)] if action == 'compile' else ['extract-native', str(k), '--symbol', symbol, '--output', str(b)]
        argv = [pr['loader'], producer, '0', '0', 'aarch64', '35,37,38,39', '--', *args]
        need(row['index'] == index and row['label'] == full_label and row['argv'] == argv and row['effectiveEnvironment'] == env and row['timeoutSeconds'] == 1810, 'exact call argv/env/order')
        need(row['state'] == 'terminal' and row['spawned'] is True and row['reaped'] is True and row['returncode'] == 0 and row['error'] is None and row['terminationReason'] is None and row['cleanupExceptions'] == [], 'closed successful child')
        out, err = O / (full_label + '.stdout'), O / (full_label + '.stderr')
        pin(out, row['stdout']); pin(err, row['stderr'])
        raw, stderr = data(out, 16777216), data(err, 1048576)
        need(b':ok true' in raw and b':ok false' not in raw, 'raw compile/extract success')
        m = PAT.fullmatch(stderr)
        need(m is not None and all(len(x) <= 20 for x in m.groups()), 'whole exact17 counter stderr')
        values = dict(zip(FIELDS, map(int, m.groups())))
        need(all(0 <= v < 2**64 for v in values.values()), 'u64 counter range')
        need(values['heap-bytes'] == 16 * values['pairs'] + values['string-pool-bytes'] + 16 * values['vectors'] + 8 * values['vector-items'], 'counter heap equation')
        need(values['pairs'] <= 16777216 and values['string-pool-bytes'] <= 268435456 and values['vectors'] <= 4194304 and values['vector-items'] <= 134217728, 'compiler resource bounds')
        need(row['counterObservation'] == dict(status='valid', values=values, entireStderrIsCounterLine=True), 'raw counter observation correspondence')
        raw_counter_values.append(dict(index=index, label=full_label, values=values))
        if action == 'extract':
            image = artifact_checks[(index - 1) // 2][0]
            offsets = re.findall(rb':offset ([0-9]+)\b', raw)
            need(len(offsets) == 1 and int(offsets[0]) == image['offset'], 'raw extract offset')
    for image, symbol, arity in artifact_checks:
        label = image['label']
        for kind, suffix in [('container', '.kseed'), ('native', '.bin')]:
            expected_path = str(O / (label + suffix))
            need(image[kind]['path'] == expected_path, 'exact artifact path')
            pin(expected_path, image[kind])
            need(generated[expected_path] == {k: image[kind][k] for k in ('bytes', 'sha256')}, 'artifact generated pin')
        whole, payload, exports = container(image['container']['path'])
        need(exports == image['exports'] and data(image['native']['path'], 4194304) == payload, 'whole parsed container/native payload identity')
        selected = [e for e in exports if e[0] == symbol]
        need(len(selected) == 1 and selected[0][2] == arity and selected[0][1] == image['offset'], 'selected export ABI/offset')
        if arity == 0:
            need(exports == [['main', 0, 0]], 'sole main0 generation export')
    for kind in ('container', 'native'):
        need(data(generations[0][kind]['path']) == data(generations[1][kind]['path']) == data(generations[2][kind]['path']), 'G1 G2 G3 whole fixed point: ' + kind)
    g1 = generations[0]
    g0container = next(z for z in load(pr['actualProducerProof'])['images'] if z['arm'] == 'ON')['container']
    need(g1['G0Native'] == dict(path=pr['producer'], **ip[pr['producer']]) and g1['G0Container'] == g0container and g1['G0ToG1EqualityRequired'] is False, 'G0 recorded pinned lineage')
    for kind in ('Native', 'Container'):
        old = data(g1['G0' + kind]['path'])
        new = data(g1[kind.lower()]['path'])
        difference_key = 'G0ToG1FirstDifferentByte' if kind == 'Native' else 'G0ToG1ContainerFirstDifferentByte'
        need(g1['G0ToG1' + kind + 'Equality'] == (old == new) and g1[difference_key] == first_difference(old, new), 'allowed G0 difference exact recording')
    return dict(status='PASS_INDEPENDENT_SAVED_RAW_FUEL_DAG_ORIGINAL19_SELFBUILD44_FIXEDPOINT_ONLY', independent=True, priorAuthorship=False, authorshipDisclosure='No prior authorship of frozen SOURCE/driver/producer/loader/parent ledger; previously reviewed SOURCE and authored only this saved-file reader.', rootGOPath=str(G), rootGOSHA256=GOHASH, sourcePinsSHA256=EXPECTED['source-pins.json'], driverSHA256=EXPECTED['run.py'], preregistrationSHA256=EXPECTED['preregistration.json'], inputPinsSHA256=EXPECTED['input-pins.json'], exactInputFiles=2161, exactInputLogicalBytes=406252033, loaderCalls=44, allChildrenClosed=True, failure=False, original19CompileExtractCalls=38, selfbuildCalls=6, retainedOrdinaryCalls=0, exact44ArgvEnvironmentRaw17Counters=True, wholeOriginal19BodiesSymbolsProfilesExportsPayloads=True, wholeUnitySourceAndProducerSequence=True, G1G2G3WholeContainerNativeSoleMain0=True, G0G1DifferenceAllowedAndRecorded=True, counterValues=raw_counter_values, findings=[], nativeCompilerSSHDriverRerunCalls=0, workloadGuestCalls=0, runtimeABITrapFuelQualified=False, performanceQualified=False, officialScore=False, fullSelfhostGoalAchieved=False)

if __name__ == '__main__':
    need(sys.argv[1:] == ['--root-explicitly-confirmed-closed'], 'root CLOSED confirmation required before reader execution')
    need(not (Q / 'report.json').exists(), 'fresh review report')
    try:
        result = audit()
    except Exception as error:
        result = dict(status='HOLD_INDEPENDENT_SAVED_RAW_FUEL_DAG_ORIGINAL19_SELFBUILD44', failure=str(error), nativeCompilerSSHDriverRerunCalls=0, performanceQualified=False)
    (Q / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], report=str(Q / 'report.json'), **receipt(Q / 'report.json'))))
