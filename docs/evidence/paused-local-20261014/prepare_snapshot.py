from pathlib import Path
import collections, gzip, hashlib, io, json, os, shutil, stat, subprocess, tarfile

GITHUB = Path('/Users/junkawasaki/github')
W = GITHUB / 'workspaces/codex'
REPO = GITHUB / 'wt/codex/amu-local-paused-save-20261014'
OUT = REPO / 'docs/evidence/paused-local-20261014'
BASE = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
SELECTED = W / 'seed-local-selected-private-twocharge-slre-neon-20261014-v3'
records = {}
pin_expectations = collections.defaultdict(set)
missing = set()
queue = []
historical = []

def add(path, scan_json=True):
    p = Path(path)
    if p.is_file() and not any(v in p.parts for v in ('.git', '__pycache__')):
        if str(p) not in records:
            b = p.read_bytes()
            records[str(p)] = {'originalPath': str(p), 'sha256': hashlib.sha256(b).hexdigest(),
                              'bytes': len(b), 'mode': stat.S_IMODE(p.stat().st_mode)}
            if p.suffix == '.json' and scan_json and p.name not in ('INDEX.json', 'continuation-checkpoint.json'):
                queue.append(p)

def tree(path):
    p = W / path
    if not p.is_dir():
        raise FileNotFoundError(p)
    for f in p.rglob('*'):
        add(f)

def walk(obj):
    if isinstance(obj, dict):
        p, digest = obj.get('path'), obj.get('sha256')
        if isinstance(p, str) and isinstance(digest, str) and len(digest) == 64 and p.startswith(str(GITHUB) + '/'):
            pin_expectations[p].add(digest)
            if Path(p).is_file():
                actual = hashlib.sha256(Path(p).read_bytes()).hexdigest()
                if actual == digest:
                    # One hop preserves direct evidence/dependencies. Do not
                    # follow mutable historical indices through every old run.
                    add(p, scan_json=False)
                else:
                    historical.append({'path': p, 'expected': digest, 'current': actual,
                                       'currentFileWasExplicitlySelected': p in records})
            else:
                missing.add(p)
        for v in obj.values():
            walk(v)
    elif isinstance(obj, list):
        for v in obj:
            walk(v)

for name in [
    'seed-local-selected-private-twocharge-slre-neon-20261014-v3',
    'seed-local-selected-slre-context-neon-20261014-v2',
    'seed-local-selected-neon-madd-20261014',
    'pico-gap-20261014/idct-private-writer-twocharge-slre-context-neon-source-v5',
    'pico-private-twocharge-current-slre-neon-fixed16-20261014-v1',
    'slre-reader-context-return-current-neon-fixed16-20261014-v1',
    'nsich-wiki-private-current-source-20261014-v1',
    'nsich-closed-context-slre-neon-source-20261014-v1',
    'nsich-closed-context-slre-neon-source-20261014-v2',
    'nsich-closed-context-slre-neon-source-20261014-v3',
    'wiki-insertion-copy-count-slre-context-source-20261014-v1',
    'wiki-insertion-copy-count-slre-context-source-20261014-v2',
    'wiki-copy-count-private-current-source-20261014-v1',
    'nsich-closed-context-current-private-combined-fixed16-20261014-v1',
    'pico-gap-20261014/nsich-wiki-private-combined-pico-controls-v1',
    'pico-gap-20261014/nsich-wiki-private-combined-pico-controls-v2',
    'pico-gap-20261014/wiki-insertion-complete-payload-afbc-v1',
    'pico-gap-20261014/wiki-insertion-complete-payload-afbc-v2',
    'pico-gap-20261014/review-selected-privatewriter-slre-neon-v3',
    'statemate-gap-20261013/review-combined-ctx-wiki-native-20261014-v1',
    'slre-gap-20261013/review-nsich-native-word-resource-v3-20261014',
    'slre-gap-20261013/review-nsich-wiki-private-combined-source-20261014-v1',
    'slre-gap-20261013/review-private-twocharge-first16-20261014',
    'seed-local-cycle-20261014',
    'embench-total-C-round114-copy-chain-forward-20261014-v1',
    'embench-pf-twoarg-20261013/priority-repair-v3/original483-g1-v1',
    'embench-pf-twoarg-20261013/compare-priority-v7/all39-stable-v1',
]:
    tree(name)

for name in ['seed-copy-chain48-review-20261014', 'embench-paused-handoff-publication-20261013']:
    p = W / name
    for f in p.iterdir():
        if f.is_file():
            add(f)
for p in [W / 'seed-local-current-20261014.json',
          W / 'slre-gap-20261013/PAUSED-HANDOFF-20261014-nsich-wiki.json',
          W / 'seed-copy-chain-forward-20261014/main-integration-receipt.json',
          W / 'embench-total-C-round52-20261011/continuation-checkpoint.json']:
    add(p)

while queue:
    p = queue.pop()
    try:
        walk(json.loads(p.read_text()))
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass

conflicts = []
for p, digests in pin_expectations.items():
    if p in records and records[p]['sha256'] not in digests:
        conflicts.append({'path': p, 'actual': records[p]['sha256'], 'expected': sorted(digests)})
inventory = {'files': len(records), 'bytes': sum(r['bytes'] for r in records.values()),
             'missingPins': sorted(missing), 'pinConflicts': conflicts,
             'historicalReferencesWithChangedPaths': historical,
             'baseMain': BASE, 'goalStatus': 'paused'}
(W / 'amu-local-paused-save-20261014/inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
print(json.dumps({k:v for k,v in inventory.items() if k not in ('pinConflicts','historicalReferencesWithChangedPaths')}), flush=True)
print('historical mutable path references:', len(historical), flush=True)
for p, expected in json.loads((SELECTED / 'SELECTION.json').read_text())['files'].items():
    assert records[expected['path']]['sha256'] == expected['sha256'], p
if os.environ.get('PACK_ARCHIVE') != '1':
    raise SystemExit(0)

OUT.mkdir(parents=True, exist_ok=False)
direct = {}
selected_out = OUT / 'selected'
selected_out.mkdir()
for p in SELECTED.iterdir():
    if p.is_file():
        dst = selected_out / p.name
        shutil.copy2(p, dst)
        direct[records[str(p)]['sha256']] = dst.relative_to(REPO).as_posix()

objects = {}
for p, r in sorted(records.items()):
    src = Path(p)
    r['restorePath'] = src.relative_to(GITHUB).as_posix()
    if r['sha256'] in direct:
        r['storage'] = {'kind': 'repository', 'path': direct[r['sha256']]}
        continue
    # Existing PR1313 evidence is already in the branch's main ancestry.
    marker = '/docs/evidence/copy-chain48-20261014/'
    if marker in p:
        rel = 'docs/evidence/copy-chain48-20261014/' + p.split(marker, 1)[1]
        z = subprocess.run(['git', 'show', BASE + ':' + rel], cwd=REPO, capture_output=True)
        if z.returncode == 0 and hashlib.sha256(z.stdout).hexdigest() == r['sha256']:
            r['storage'] = {'kind': 'git', 'commit': BASE, 'path': rel}
            continue
    r['storage'] = {'kind': 'archive', 'member': 'objects/' + r['sha256']}
    objects.setdefault(r['sha256'], src)

groups, group, group_size = [], [], 0
for digest, p in sorted(objects.items()):
    size = ((p.stat().st_size + 511) // 512 + 1) * 512
    if group and group_size + size > 32 * 1024 * 1024:
        groups.append(group)
        group, group_size = [], 0
    group.append((digest, p))
    group_size += size
if group:
    groups.append(group)
archives, object_archive = [], {}
for number, group in enumerate(groups, 1):
    archive = OUT / ('snapshot-%03d.tgz' % number)
    with archive.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w') as t:
            for digest, p in group:
                b = p.read_bytes()
                assert hashlib.sha256(b).hexdigest() == digest
                info = tarfile.TarInfo('objects/' + digest)
                info.size = len(b)
                info.mode = 0o644
                info.mtime = info.uid = info.gid = 0
                t.addfile(info, io.BytesIO(b))
                object_archive[digest] = archive.name
    assert archive.stat().st_size < 40 * 1024 * 1024
    archives.append({'path': archive.name, 'bytes': archive.stat().st_size,
                     'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
for r in records.values():
    if r['storage']['kind'] == 'archive':
        r['storage']['archive'] = object_archive[r['sha256']]

manifest = {'schema': 'amu-paused-snapshot-v1', 'goalStatus': 'paused',
            'baseMain': BASE, 'originalGithubRoot': str(GITHUB),
            'selectedSelectionSha256': records[str(SELECTED / 'SELECTION.json')]['sha256'],
            'selectedIsProductMain': False, 'unselectedCombinedPerformanceMeasured': False,
            'archives': archives,
            'missingPins': sorted(missing), 'pinConflicts': conflicts,
            'historicalReferencesWithChangedPaths': historical,
            'scope': 'Explicit paused source/evidence trees and one-hop pinned dependencies; historical manifests preserved, not exhaustive recursive history.',
            'files': [r for _, r in sorted(records.items())]}
(OUT / 'snapshot-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
for p in (W / 'seed-copy-chain48-review-20261014').iterdir():
    if p.is_file() and p.suffix in ('.md', '.json', '.txt', '.py'):
        shutil.copy2(p, OUT / p.name)
summary = {'files': len(records), 'uniqueArchiveObjects': len(objects),
           'uncompressedBytes': inventory['bytes'], 'archiveBytes': sum(a['bytes'] for a in archives),
           'archiveParts': len(archives),
           'manifestSha256': hashlib.sha256((OUT / 'snapshot-manifest.json').read_bytes()).hexdigest(),
           'baseMain': BASE, 'missingPins': sorted(missing), 'goalStatus': 'paused'}
(OUT / 'SAVE-SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary), flush=True)
