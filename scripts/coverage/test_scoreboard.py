#!/usr/bin/env python3
"""Negative controls for the coverage report (JUN-890, ADR 0410).

Each control damages a copy of the real snapshot and requires the number to
fall, or the report to refuse. Nothing here touches the committed files.
"""
import copy
import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('scoreboard', HERE / 'scoreboard.py')
scoreboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoreboard)

SNAPSHOT = scoreboard.COVERAGE / 'snapshots/20261106'
TABLE = json.loads((scoreboard.COVERAGE / 'table.json').read_text())
DAY = '2026-11-06'
ARM = 'bootstrap-arm64/selfhost-bootstrap.json'
X86 = 'x86_64-native-receipt/x86/x86_64-native.json'
X86_COMPLETE = 'x86_64-native-receipt/complete/complete-x86.json'
MAC = 'mac-aiueos-user-root/public-macos-product/public-macos-product.json'


def scored(damage=None, table=TABLE, as_of=DAY):
    with tempfile.TemporaryDirectory() as temp:
        snapshot = Path(temp, 'snapshot')
        shutil.copytree(SNAPSHOT, snapshot)
        if damage:
            damage(snapshot)
        return scoreboard.report(table, snapshot, as_of)


def bounds(result):
    return result['lowerBasisPoints'], result['upperBasisPoints']


def refused(damage=None, table=TABLE):
    try:
        scored(damage, table)
    except scoreboard.Refused:
        return True
    return False


def remove(path):
    return lambda snapshot: (snapshot / 'receipts' / path).unlink()


def rewrite(path, change, fix_digest=True):
    def damage(snapshot):
        file = snapshot / 'receipts' / path
        body = json.loads(file.read_text())
        change(body)
        file.write_text(json.dumps(body))
        if fix_digest:
            name = snapshot / 'provenance.json'
            provenance = json.loads(name.read_text())
            provenance['receipts'][path] = hashlib.sha256(file.read_bytes()).hexdigest()
            name.write_text(json.dumps(provenance))
    return damage


def change_runs(change):
    def damage(snapshot):
        name = snapshot / 'provenance.json'
        provenance = json.loads(name.read_text())
        change(provenance['runs'])
        name.write_text(json.dumps(provenance))
    return damage


def with_slice(name, **fields):
    table = copy.deepcopy(TABLE)
    table['denominator']['slices'][name].update(fields)
    return table


def main():
    baseline = scored()
    assert bounds(baseline) == (215, 809), bounds(baseline)
    assert baseline['gateVerdict'] is False
    assert baseline['meetsThreshold'] is False
    assert baseline['denominatorBasisPoints'] == 9918
    assert baseline['developmentHostsAtL3'] == {
        'x86_64-linux': True, 'aarch64-linux': False, 'aarch64-macos': True,
        'x86_64-macos': False, 'x86_64-windows': False, 'aarch64-windows': False}

    # Removing evidence lowers the number. Linux needs both ISAs in the lower bound.
    assert bounds(scored(remove(ARM))) == (0, 809)
    assert bounds(scored(remove(X86))) == (0, 809)
    assert bounds(scored(remove(MAC))) == (215, 215)
    both = lambda s: (remove(ARM)(s), remove(X86)(s))
    assert bounds(scored(both)) == (0, 594)

    # Removing evidence from one level leaves the others, and fails that level alone.
    no_complete = scored(remove(X86_COMPLETE))
    assert no_complete['targets']['x86_64-linux']['L3']['state'] == 'fail'
    assert no_complete['targets']['x86_64-linux']['L1']['state'] == 'pass'
    assert no_complete['developmentHostsAtL3']['x86_64-linux'] is False

    # A receipt must say the right thing, even when its digest was updated to match.
    for name, change in (
        ('status', lambda b: b.update(status='FAIL')),
        ('emulation', lambda b: b.update(emulation=True)),
        ('other host', lambda b: b.update(host=['Linux', 'x86_64'])),
        ('dropped required field', lambda b: b.pop('cCompilerOrLoader')),
    ):
        assert bounds(scored(rewrite(ARM, change))) == (0, 809), name

    # Emulation fails a cell even when the table does not name that field.
    assert bounds(scored(rewrite(MAC, lambda b: b.update(emulation=True)))) == (215, 215)

    # An unrecorded edit is caught, and so is a receipt with no host at all.
    assert bounds(scored(rewrite(ARM, lambda b: None, fix_digest=False))) == (0, 809)
    assert bounds(scored(rewrite(ARM, lambda b: b.pop('host')))) == (0, 809)
    mac_host = 'mac-aiueos-user-root/mac-smoke/execution/receipt.json'
    assert bounds(scored(rewrite(mac_host, lambda b: b.pop('host')))) == (215, 215)

    # A fixed point needs identical generations.
    def split(body):
        body['generations'][0]['sha256'] = '0' * 64
    assert scored(rewrite(X86_COMPLETE, split))['targets']['x86_64-linux']['L3']['state'] == 'fail'

    # Old evidence counts as nothing. The limit is 30 days.
    assert bounds(scored(as_of='2026-12-06')) == (215, 809)
    assert bounds(scored(as_of='2026-12-07')) == (0, 0)

    # Runs must agree and must have succeeded.
    assert refused(change_runs(lambda r: r['mac'].update(headSha='0' * 40)))
    assert refused(change_runs(lambda r: r['selfhost'].update(conclusion='failure')))
    assert refused(change_runs(lambda r: r.pop('mac')))

    # A measured split gives partial credit, and it must be a whole split.
    measured = with_slice('macos', isaSplitBasisPoints={'aarch64-macos': 9000, 'x86_64-macos': 1000})
    assert bounds(scored(table=measured)) == (215 + 534, 215 + 534)
    assert refused(table=with_slice('macos', isaSplitBasisPoints={'aarch64-macos': 9000, 'x86_64-macos': 999}))
    assert refused(table=with_slice('macos', isaSplitBasisPoints={'aarch64-macos': 10000}))

    # The table cannot overclaim.
    assert refused(table=with_slice('linux', shareBasisPoints=2000))
    assert refused(table=with_slice('linux', targets=['x86_64-linux', 'aarch64-macos']))
    assert refused(table=with_slice('linux', targets=['riscv64-linux']))

    # A cell the OS forbids is not a pass, and nothing evidences a missing target.
    assert baseline['targets']['aarch64-ios']['L3']['state'] == 'prohibited'
    assert baseline['slices']['ios']['upperBasisPoints'] == 0
    print('PASS coverage scoreboard negative controls')


if __name__ == '__main__':
    main()
