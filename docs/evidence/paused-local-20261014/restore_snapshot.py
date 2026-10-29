#!/usr/bin/env python3
"""Verify the paused snapshot; optionally materialize it into a new directory.

This tool never compiles, benchmarks, merges, or starts the paused goal.
"""
from pathlib import Path, PurePosixPath
import argparse, collections, hashlib, json, os, re, subprocess, tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

def relative(value):
    p = PurePosixPath(value)
    if p.is_absolute() or not p.parts or any(x in ('..', '.', '.git') for x in p.parts):
        raise ValueError('Unsafe snapshot path: ' + value)
    return p

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--prefix', help='Materialize only this restorePath prefix (verification still checks everything).')
    args = parser.parse_args()
    if args.verify_only == bool(args.destination):
        parser.error('Choose exactly one of --verify-only or --destination.')
    if args.prefix and not args.destination:
        parser.error('--prefix requires --destination.')
    manifest = json.loads((HERE / 'snapshot-manifest.json').read_text())
    summary = json.loads((HERE / 'SAVE-SUMMARY.json').read_text())
    assert digest((HERE / 'snapshot-manifest.json').read_bytes()) == summary['manifestSha256']
    assert manifest['goalStatus'] == 'paused'
    destination = args.destination
    if destination:
        destination = destination.absolute()
        if destination.exists() or destination.is_symlink():
            parser.error('Destination must be a new directory; existing files are never overwritten.')
        destination.mkdir(parents=True)
        destination = destination.resolve()
    prefix = str(relative(args.prefix)).rstrip('/') if args.prefix else None
    by_digest = collections.defaultdict(list)
    path_map = {}
    for row in manifest['files']:
        assert re.fullmatch(r'[0-9a-f]{64}', row['sha256'])
        relative(row['restorePath'])
        assert row['mode'] & ~0o777 == 0
        by_digest[row['sha256']].append(row)
    checked, materialized = set(), 0

    def accept(data, key):
        nonlocal materialized
        assert digest(data) == key
        rows = by_digest[key]
        for row in rows:
            assert len(data) == row['bytes']
            if destination and (prefix is None or row['restorePath'] == prefix or row['restorePath'].startswith(prefix + '/')):
                target = destination / row['restorePath']
                assert target.resolve().is_relative_to(destination)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as f:
                    f.write(data)
                target.chmod(row['mode'])
                path_map[row['originalPath']] = str(target)
                materialized += 1
        checked.add(key)

    archive_expectations = collections.defaultdict(dict)
    for key, rows in by_digest.items():
        storage = rows[0]['storage']
        assert all(row['storage'] == storage for row in rows)
        if storage['kind'] == 'repository':
            accept((REPO / str(relative(storage['path']))).read_bytes(), key)
        elif storage['kind'] == 'git':
            assert re.fullmatch(r'[0-9a-f]{40}', storage['commit'])
            result = subprocess.run(['git', 'show', storage['commit'] + ':' + str(relative(storage['path']))],
                                    cwd=REPO, capture_output=True, check=True)
            accept(result.stdout, key)
        else:
            assert storage['kind'] == 'archive'
            name, member = str(relative(storage['archive'])), str(relative(storage['member']))
            assert member == 'objects/' + key
            archive_expectations[name][member] = key
    for part in manifest['archives']:
        name = str(relative(part['path']))
        path = HERE / name
        assert path.stat().st_size == part['bytes']
        assert digest(path.read_bytes()) == part['sha256']
        expected = archive_expectations.pop(name, {})
        with tarfile.open(path, 'r:gz') as archive:
            for member in archive:
                assert member.isfile() and member.name in expected
                key = expected.pop(member.name)
                accept(archive.extractfile(member).read(), key)
        assert not expected
    assert not archive_expectations and checked == set(by_digest)
    if destination:
        (destination / 'path-map.json').write_text(json.dumps(path_map, indent=2) + '\n')
        (destination / 'RESTORE-READBACK.json').write_text(json.dumps({
            'goalStatus': 'paused', 'filesMaterialized': materialized,
            'filesVerified': len(manifest['files']), 'prefix': prefix,
            'snapshotManifestSha256': summary['manifestSha256'],
            'compilerOrBenchmarkInvoked': False,
        }, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'goalStatus': 'paused', 'filesVerified': len(manifest['files']),
                      'uniqueObjectsVerified': len(checked), 'filesMaterialized': materialized,
                      'compilerOrBenchmarkInvoked': False}))

if __name__ == '__main__':
    main()
