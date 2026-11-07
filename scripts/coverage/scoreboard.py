#!/usr/bin/env python3
"""Report how much of the ADR 0410 denominator has native evidence (JUN-890).

This is a report, not a gate. Python reads receipts that native gates wrote and
adds up shares. It does not run the compiler, and it does not replace the native
controller's verdict. A digest here shows that a stored receipt is unchanged
since collection. It does not authenticate the receipt.

  collect  copy the receipts the table names from two successful CI runs
  report   compute the numbers for a snapshot on a given day
  verify   recompute a snapshot on its own day and compare with its report.json

A cell without evidence counts as 0. An ISA split nobody has measured gives the
OS credit in the lower bound only when every listed target passes.
"""
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COVERAGE = ROOT / 'docs/qualification/target-coverage'
REPO = 'kotoba-lang/amu'
WORKFLOWS = {'selfhost': 'selfhost-native', 'mac': 'mac-selfhost-aiueos'}
ARTIFACTS = {
    'x86_64-native-receipt': 'selfhost',
    'bootstrap-arm64': 'selfhost',
    'mac-aiueos-user-root': 'mac',
}
LEVELS = ('L1', 'L2', 'L3')


class Refused(Exception):
    pass


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value):
    return json.dumps(value, indent=2, sort_keys=True) + '\n'


def table_paths(table):
    return sorted({r['path'] for t in table['targets'].values() for c in t['cells'].values()
                   for r in c.get('receipts', ())})


def check_table(table):
    if table.get('schema') != 'amu.target-coverage-table.v1':
        raise Refused('unknown table schema')
    slices = table['denominator']['slices']
    if sum(s['shareBasisPoints'] for s in slices.values()) > 10000:
        raise Refused('denominator is over 100%')
    listed = [t for s in slices.values() for t in s['targets']]
    if len(listed) != len(set(listed)):
        raise Refused('a target is listed in two slices')
    for name in [*listed, *table['developmentHosts']]:
        if name not in table['targets']:
            raise Refused(f'target has no row: {name}')
    for name, target in table['targets'].items():
        if set(target['cells']) != set(LEVELS):
            raise Refused(f'{name} must have exactly {LEVELS}')
    for name, part in slices.items():
        split = part.get('isaSplitBasisPoints')
        if split is not None and (set(split) != set(part['targets']) or sum(split.values()) != 10000):
            raise Refused(f'{name}: a measured split must cover its targets and total 100%')


def receipt_problems(snapshot, provenance, spec, host):
    path = spec['path']
    file = snapshot / 'receipts' / path
    if path not in provenance['receipts']:
        return [f'{path}: not in provenance'], None
    if not file.is_file():
        return [f'{path}: missing'], None
    if digest(file) != provenance['receipts'][path]:
        return [f'{path}: digest differs from provenance'], None
    try:
        body = json.loads(file.read_text())
    except ValueError:
        return [f'{path}: not JSON'], None
    problems = []
    if 'status' in spec and body.get('status') != spec['status']:
        problems.append(f"{path}: status {body.get('status')!r}")
    for key, want in spec.get('fields', {}).items():
        if key not in body or body[key] != want:
            problems.append(f'{path}: {key} is {body.get(key)!r}, wants {want!r}')
    if body.get('emulation') is True:
        problems.append(f'{path}: ran under emulation')
    if spec.get('identicalGenerations'):
        hashes = {g.get('sha256') for g in body.get('generations', ())}
        if len(body.get('generations', ())) < 2 or len(hashes) != 1:
            problems.append(f'{path}: generations are not identical')
    seen = body.get('host')
    if seen is not None and list(seen[:len(host)]) != host:
        problems.append(f'{path}: ran on {seen}, wants {host}')
    return problems, body


def evaluate_cell(snapshot, provenance, cell, host, caveat_fields, stale):
    if 'prohibited' in cell:
        return {'state': 'prohibited', 'reason': cell['prohibited']}
    if 'receipts' not in cell:
        return {'state': 'missing', 'reason': cell['missing']}
    problems, caveats, host_seen = [], [], False
    for spec in cell['receipts']:
        found, body = receipt_problems(snapshot, provenance, spec, host)
        problems += found
        if body is not None:
            host_seen = host_seen or 'host' in body
            caveats += [f"{spec['path']}: {k} is false" for k in caveat_fields if body.get(k) is False]
    if not problems and not host_seen:
        problems.append(f'no receipt records the host {host}')
    if stale:
        problems.append(stale)
    if problems:
        return {'state': 'fail', 'problems': problems}
    result = {'state': 'pass', 'receipts': [spec['path'] for spec in cell['receipts']]}
    if caveats:
        result['caveats'] = sorted(set(caveats))
    return result


def report(table, snapshot, as_of):
    check_table(table)
    provenance = json.loads((snapshot / 'provenance.json').read_text())
    heads = {run['headSha'] for run in provenance['runs'].values()}
    if len(heads) != 1:
        raise Refused(f'runs have different heads: {sorted(heads)}')
    if any(run['conclusion'] != 'success' for run in provenance['runs'].values()):
        raise Refused('a run did not succeed')
    if set(provenance['runs']) != set(WORKFLOWS):
        raise Refused('a snapshot needs the selfhost and the mac run')
    oldest = min(run['createdAt'][:10] for run in provenance['runs'].values())
    age = (datetime.date.fromisoformat(as_of) - datetime.date.fromisoformat(oldest)).days
    stale = f'evidence is {age} days old' if age > table['maxEvidenceAgeDays'] else None

    targets = {}
    for name, target in table['targets'].items():
        targets[name] = {level: evaluate_cell(snapshot, provenance, target['cells'][level], target['host'],
                                              table['caveatFields'], stale)
                         for level in LEVELS}

    level = table['coverageLevel']
    slices, lower, upper = {}, 0, 0
    for name, part in table['denominator']['slices'].items():
        share = part['shareBasisPoints']
        passing = [t for t in part['targets'] if targets[t][level]['state'] == 'pass']
        split = part.get('isaSplitBasisPoints')
        if split is None:
            low = share if len(passing) == len(part['targets']) else 0
            high = share if passing else 0
        else:
            low = high = share * sum(split[t] for t in passing) // 10000
        lower, upper = lower + low, upper + high
        slices[name] = {'shareBasisPoints': share, 'isaSplitMeasured': split is not None,
                        'passing': passing, 'lowerBasisPoints': low, 'upperBasisPoints': high}

    denominator = sum(s['shareBasisPoints'] for s in table['denominator']['slices'].values())
    return {
        'schema': 'amu.target-coverage-report.v1',
        'gateVerdict': False,
        'asOf': as_of,
        'head': heads.pop(),
        'denominator': {k: table['denominator'][k] for k in ('source', 'period', 'retrieved')},
        'denominatorBasisPoints': denominator,
        'thresholdBasisPoints': table['thresholdBasisPoints'],
        'coverageLevel': level,
        'lowerBasisPoints': lower,
        'upperBasisPoints': upper,
        'meetsThreshold': lower >= table['thresholdBasisPoints'],
        'slices': slices,
        'developmentHostsAtL3': {t: all(targets[t][l]['state'] == 'pass' for l in LEVELS)
                                 for t in table['developmentHosts']},
        'targets': targets,
    }


def gh_json(*args):
    return json.loads(subprocess.run(['gh', *args], check=True, capture_output=True, text=True).stdout)


def collect(table, runs, out):
    if out.exists():
        raise Refused(f'{out} already exists')
    provenance = {'schema': 'amu.target-coverage-provenance.v1', 'repository': REPO,
                  'runs': {}, 'artifacts': {}, 'receipts': {}}
    for role, run in runs.items():
        view = gh_json('run', 'view', str(run), '--repo', REPO, '--json',
                       'headSha,conclusion,workflowName,event,createdAt')
        if view['workflowName'] != WORKFLOWS[role] or view['conclusion'] != 'success':
            raise Refused(f"run {run} is {view['workflowName']}: {view['conclusion']}")
        provenance['runs'][role] = {'id': run, **view}
    if len({r['headSha'] for r in provenance['runs'].values()}) != 1:
        raise Refused('runs have different heads')
    paths = table_paths(table)
    with tempfile.TemporaryDirectory() as temp:
        for artifact, role in ARTIFACTS.items():
            run = runs[role]
            listed = gh_json('api', f'repos/{REPO}/actions/runs/{run}/artifacts', '--paginate')['artifacts']
            match = [a for a in listed if a['name'] == artifact and not a['expired']]
            if len(match) != 1:
                raise Refused(f'{artifact}: {len(match)} live artifacts in run {run}')
            provenance['artifacts'][artifact] = {'run': run, 'id': match[0]['id'], 'digest': match[0]['digest']}
            subprocess.run(['gh', 'run', 'download', str(run), '--repo', REPO, '-n', artifact,
                            '-D', str(Path(temp, artifact))], check=True)
        for path in paths:
            target = out / 'receipts' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(temp, path), target)
            provenance['receipts'][path] = digest(target)
    (out / 'provenance.json').write_text(dump(provenance))
    return provenance


def percent(basis_points):
    return f'{basis_points // 100}.{basis_points % 100:02d}%'


def show(result):
    print(f"{result['coverageLevel']} coverage on {result['asOf']}, head {result['head'][:9]}: "
          f"{percent(result['lowerBasisPoints'])} lower, {percent(result['upperBasisPoints'])} upper, "
          f"of {percent(result['denominatorBasisPoints'])} listed; threshold {percent(result['thresholdBasisPoints'])}")
    for name, part in result['slices'].items():
        print(f"  {name:8} {percent(part['shareBasisPoints']):>7}  lower {percent(part['lowerBasisPoints']):>6}  "
              f"upper {percent(part['upperBasisPoints']):>6}  passing {part['passing'] or '-'}")
    for name, cells in result['targets'].items():
        print(f"  {name:16} " + ' '.join(f'{level}={cells[level]["state"]}' for level in LEVELS))
    print('  development hosts at L3:', ', '.join(t for t, ok in result['developmentHostsAtL3'].items() if ok) or '-')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest='command', required=True)
    c = commands.add_parser('collect')
    c.add_argument('--selfhost-run', type=int, required=True)
    c.add_argument('--mac-run', type=int, required=True)
    c.add_argument('--date', required=True, help='YYYYMMDD')
    r = commands.add_parser('report')
    r.add_argument('--snapshot', type=Path, required=True)
    r.add_argument('--as-of', default=datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    r.add_argument('--output', type=Path)
    commands.add_parser('verify')
    args = parser.parse_args()

    table = json.loads((COVERAGE / 'table.json').read_text())
    try:
        if args.command == 'collect':
            check_table(table)
            out = COVERAGE / 'snapshots' / args.date
            collect(table, {'selfhost': args.selfhost_run, 'mac': args.mac_run}, out)
            day = f'{args.date[:4]}-{args.date[4:6]}-{args.date[6:]}'
            result = report(table, out, day)
            (out / 'report.json').write_text(dump(result))
            show(result)
        elif args.command == 'report':
            result = report(table, args.snapshot, args.as_of)
            if args.output:
                args.output.write_text(dump(result))
            show(result)
        else:
            snapshots = sorted((COVERAGE / 'snapshots').iterdir())
            if not snapshots:
                raise Refused('no snapshot')
            for snapshot in snapshots:
                stored = json.loads((snapshot / 'report.json').read_text())
                if report(table, snapshot, stored['asOf']) != stored:
                    raise Refused(f'{snapshot.name}: report.json differs from a recomputation')
                print(f"{snapshot.name}: report.json matches, lower {percent(stored['lowerBasisPoints'])}")
    except Refused as refusal:
        print(f'refused: {refusal}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
