#!/usr/bin/env python3
"""Exercise the browser keyword intern runtime on Wasm and JS (JUN-772).

Usage: python3 scripts/seed/check-browser-keyword-intern.py --compiler F
       --baseline OLD_F --output NEW_DIR --browser CHROME
The caller builds F from the candidate FULL-MANIFEST; OLD_F is an unmodified
root. Python stages inputs and observes compiler and browser reports.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for flag in ('compiler', 'baseline', 'output', 'browser'):
        ap.add_argument('--' + flag, type=Path, required=True)
    a = ap.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    mac = module('mac_native', ROOT / 'scripts/seed/check-aiueos-user-macos-native.py')
    check = module('browser_check', ROOT / 'scripts/seed/check-js-browser.py')
    source = (ROOT / 'seed/tests/browser-keyword-intern.kotoba').read_text(encoding='utf-8')
    old = '(string=? (keyword-name a) "名")'
    if source.count(old) != 1:
        raise ValueError('mutant anchor changed')
    for name, text in [('good', source), ('mutant', source.replace(old, old.replace('"名"', '"別"')))]:
        (out / (name + '.kotoba')).write_text(text, encoding='utf-8')
    compiler, baseline = a.compiler.resolve(strict=True), a.baseline.resolve(strict=True)
    rows = []
    for target, ext in [('wasm32-browser', '.wasm'), ('js-browser', '.mjs')]:
        refused = mac.native_run(baseline, out, 'compile', 'good.kotoba', '--target', target,
                                 '--output', 'baseline-' + target, expected=1)
        if b'E7101' not in refused.stderr:
            raise ValueError('baseline did not refuse missing runtime slot: ' + target)
        for name in ('good', 'mutant'):
            artifact = name + '-' + target + ext
            mac.native_run(compiler, out, 'compile', name + '.kotoba', '--target', target,
                           '--output', artifact)
            rows.append((name + '-' + target, out / artifact, {}))
    browser = check.WASM.find_browser(str(a.browser.resolve(strict=True)))
    version, lines = check.run_js(browser, out, rows)
    for name, expected in [('good-wasm32-browser', 0), ('mutant-wasm32-browser', 1),
                           ('good-js-browser', 0), ('mutant-js-browser', 1)]:
        line = lines[name]
        report = line.get('report') or ''
        if (line.get('exit') != 0 or line.get('wasmTrap') is not None
                or not re.search(rf'\{{:status :ok :result {expected}(?:\s|\}})', report)):
            raise ValueError(name + ': unexpected run ' + repr(line))
    for name in ('good', 'mutant'):
        if lines[name + '-wasm32-browser']['report'] != lines[name + '-js-browser']['report']:
            raise ValueError(name + ': Wasm and JS result/fuel mismatch')
    receipt = {'status': 'PASS_BROWSER_KEYWORD_INTERN', 'browser': version,
               'compiler': mac.pin(compiler), 'baseline': mac.pin(baseline),
               'source': mac.pin(ROOT / 'seed/tests/browser-keyword-intern.kotoba'),
               'runs': {name: {'report': line.get('report'), 'exit': line.get('exit'),
                               'wasmTrap': line.get('wasmTrap')} for name, line in lines.items()}}
    (out / 'browser-keyword-intern.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS_BROWSER_KEYWORD_INTERN: baseline refusals and 4 browser results')


if __name__ == '__main__':
    main()
