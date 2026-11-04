#!/usr/bin/env python3
"""Observe ordinary native CLI commands and refusals, never compile in Python."""
import argparse
import importlib.util
import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check(cli, out):
    assert (platform.system(), platform.machine()) == ("Darwin", "arm64")
    spec = importlib.util.spec_from_file_location("mac_native", ROOT / "scripts/seed/check-aiueos-user-macos-native.py")
    mac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mac)
    mac.verify_macho(cli)
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    before_tmp = set(Path('/private/tmp').glob('amu-*'))
    calls = []

    def run(name, *args, expected=0, stdout=None, diagnostic=None, image=None):
        start = time.monotonic()
        r = subprocess.run([str(image or cli), *map(str, args)], cwd=out,
                           env={"PATH": "/nonexistent", "LANG": "C", "AMU_TARGET": "bad-target"},
                           capture_output=True, timeout=150)
        for stream in ('stdout', 'stderr'):
            (out / (name + '.' + stream)).write_bytes(getattr(r, stream))
        assert r.returncode == expected, (name, r.returncode, r.stdout, r.stderr)
        if stdout is not None:
            assert r.stdout == stdout, (name, r.stdout)
        if diagnostic is not None:
            assert diagnostic in r.stderr, (name, r.stderr)
        elif expected == 0:
            assert not r.stderr, (name, r.stderr)
        calls.append(dict(name=name, exit=r.returncode, seconds=round(time.monotonic()-start, 3),
                          stdout=mac.pin(out / (name + '.stdout')), stderr=mac.pin(out / (name + '.stderr'))))
        return r

    def source(name, body):
        p = out / (name + '.kotoba')
        p.write_text('(ns hello (:export [main]))\n' + body + '\n')
        return p

    hello = source('hello', '(defn main [] :i64 42)')
    run('check', 'check', hello.name, stdout=b'ok\n')
    # The public CLI must run the watcher frame classifier and reject a
    # deliberately fail-open implementation. This exercises source compiled
    # by the CLI; it does not execute the watcher or qualify a governor.
    watch_source = (ROOT / 'seed/darwin-watch-reply.kotoba').read_text()
    declaration = '(ns amu.darwin-watch-reply (:export [darwin-watch-ready? darwin-watch-reply-class]))'
    assert watch_source.count(declaration) == 1
    watch_source = watch_source.replace(declaration, '')
    watch_cases = (ROOT / 'seed/tests/awai152-darwin-watch/reply-cases.kotoba').read_text()
    watch_main = '\n(defn main [] :i64 (if (test-darwin-watch-reply) 42 7))\n'
    refusal = '"observer/bound-exit-observed" "observer/unknown"'
    assert watch_source.count(refusal) == 1
    watch_mutant = watch_source.replace(refusal, '"observer/bound-exit-observed" "observer/bound-exit-observed"')
    watch = source('watch-reply', watch_source + '\n' + watch_cases + watch_main)
    mutant = source('watch-reply-mutant', watch_mutant + '\n' + watch_cases + watch_main)
    run('watch-reply', 'run', watch.name, stdout=b'42\n')
    run('watch-reply-mutant', 'run', mutant.name, stdout=b'7\n')
    # Exercise the pure identity/event composition and a fail-open transition
    # mutant. Source namespaces are removed only in this test composition.
    watch_paths = ['seed/darwin-proc-identity.kotoba', 'seed/darwin-kqueue-event.kotoba',
                   'seed/darwin-proc-watch.kotoba', 'seed/tests/awai152-darwin-kqueue/event-cases.kotoba',
                   'seed/tests/awai152-darwin-watch/watch-cases.kotoba']
    watch_compose = '\n'.join('\n'.join(line for line in (ROOT / path).read_text().splitlines()
                                         if not line.startswith('(ns ')) for path in watch_paths)
    transition_guard = '(= (bit-and (vector-at event 15) 96) 0)'
    assert watch_compose.count(transition_guard) == 1
    transition_mutant = watch_compose.replace(transition_guard, 'true')
    watch_tail = '\n(defn main [] :i64 (if (and (test-darwin-proc-watch) (test-darwin-kqueue-event)) 42 7))\n'
    event_case = source('watch-events', watch_compose + watch_tail)
    event_mutant = source('watch-events-mutant', transition_mutant + watch_tail)
    run('watch-events', 'run', event_case.name, stdout=b'42\n')
    run('watch-events-mutant', 'run', event_mutant.name, stdout=b'7\n')
    # KOTOBA-161: negative float comparisons catch the previously observed
    # integer-condition lowering error; the reversed operands are the control.
    float_less = source('float-negative-less', '(defn main [] :i64 (if (f64-lt -2.0 -1.0) 42 7))')
    float_greater = source('float-negative-greater', '(defn main [] :i64 (if (f64-lt -1.0 -2.0) 42 7))')
    run('float-negative-less', 'run', float_less.name, stdout=b'42\n')
    run('float-negative-greater', 'run', float_greater.name, stdout=b'7\n')
    # JUN-846: f64-to-bits answers one canonical quiet NaN (0x7FF8000000000000) for every NaN, as the reference
    # does, so an x86 default NaN, a negative NaN and a payload NaN cannot make bits/serialisation host-dependent.
    # Infinity and -0.0 keep their exact bits. Each term is a distinct decimal digit; the pre-fix compiler answers 111001.
    nan_canonical = source('f64-nan-canonical', '''(defn main [] :i64
  (let [nan (f64-div (i64-to-f64-rounded 0) (i64-to-f64-rounded 0))
        neg-nan (f64-from-bits -2251799813685248)
        payload (f64-from-bits 9218868437227405313)
        neg-zero (f64-neg (i64-to-f64-rounded 0))
        inf (f64-div (i64-to-f64-rounded 1) (i64-to-f64-rounded 0))]
    (+ (if (= (f64-to-bits nan) 9221120237041090560) 1 0)
       (if (= (f64-to-bits neg-nan) 9221120237041090560) 10 0)
       (if (= (f64-to-bits payload) 9221120237041090560) 100 0)
       (if (= (f64-to-bits neg-zero) -9223372036854775808) 1000 0)
       (if (= (f64-to-bits 1.5) 4609434218613702656) 10000 0)
       (if (= (f64-to-bits inf) 9218868437227405312) 100000 0))))''')
    run('f64-nan-canonical', 'run', nan_canonical.name, stdout=b'111111\n')
    # JUN-846: :vector-f64 (library defn-s over :vector-i64; a type of its own). 7221907 = 7 + 100*19 + 10000*2 + 100000*2 +
    # 1000000*7 over new/conj/assoc/take/drop/get/at/count; the two mixes with :vector-i64 are E2104.
    vf64 = source('vector-f64', '''(defn sum [v :vector-f64] :f64
  (loop [i 0 acc 0.0]
    (if (>= i (vector-f64-count v)) acc (recur (+ i 1) (f64-add acc (vector-f64-at v i))))))
(defn main [] :i64
  (let [v (vector-f64-new 1.5 2.5 3.0)
        w (vector-f64-assoc (vector-f64-conj v 4.0) 0 10.0)
        t (vector-f64-take w 2)
        d (vector-f64-drop w 2)]
    (+ (f64-to-i64-truncating (sum v))
       (* 100 (f64-to-i64-truncating (sum w)))
       (* 10000 (vector-f64-count t))
       (* 100000 (vector-f64-count d))
       (* 1000000 (f64-to-i64-truncating (vector-f64-get v 9 7.0))))))''')
    run('vector-f64', 'run', vf64.name, stdout=b'7221907\n')
    vf64_as_i64 = source('vector-f64-as-i64', '(defn f [v :vector-i64] :i64 (vector-count v))\n(defn main [] :i64 (f (vector-f64-new 1.5)))')
    run('vector-f64-as-i64', 'check', vf64_as_i64.name, expected=1, diagnostic=b'E2104 type mismatch in')
    i64_as_vf64 = source('vector-i64-as-f64', '(defn f [v :vector-f64] :i64 (vector-f64-count v))\n(defn main [] :i64 (f (vector-alloc 3)))')
    run('vector-i64-as-f64', 'check', i64_as_vf64.name, expected=1, diagnostic=b'E2104 type mismatch in')
    vf64_field = source('vector-f64-field', '(defrecord R [v :vector-f64])\n(defn main [] :i64 1)')
    run('vector-f64-field', 'check', vf64_field.name, expected=1, diagnostic=b'E2128')
    # KOTOBA-13: the public host stages a locked KSL2 namespace map,
    # verifies every original source digest, then asks the pinned Kotoba
    # compiler to check the rewritten project lock in its private FS2 root.
    project = out / 'locked-project'
    project.mkdir()
    app = project / 'app.kotoba'
    util = project / 'util.kotoba'
    app.write_text('(ns app (:require [util :as u]) (:export [main]))\n(defn main [] :i64 (u/add 41))\n')
    util.write_text('(ns util (:export [add]))\n(defn add [x :i64] :i64 (+ x 1))\n')

    def project_lock(entry, modules, files):
        return ('KSL2\nentry ' + str(entry) + '\n'
                + ''.join('module ' + name + ' ' + str(path) + '\n' for name, path in modules)
                + ''.join('file ' + hashlib.sha256(path.read_bytes()).hexdigest() + ' ' + str(path) + '\n'
                          for path in sorted(files)))

    # The previous formatter exhausted the native string pool when formatting
    # subnormals repeatedly. Exercise the real formatter, parser and boundary
    # anchors; a deliberately wrong anchor must fail the same observation.
    f64_project = out / 'f64-resource-project'
    f64_project.mkdir()
    f64_source = (ROOT / 'test/fixtures/selfhost/f64-text/native/f64_text_test.kotoba').read_text()
    main_at = f64_source.index('(defn main [] :i64')
    f64_source = f64_source[:main_at] + '''(defn main [] :i64
  (if (and (anchors) (refusals)
           (loop [i 0] (if (= i 40) true (if (roundtrip 1) (recur (+ i 1)) false)))) 42 7))
'''
    f64_entry = f64_project / 'f64_text_test.kotoba'
    f64_text = f64_project / 'f64_text.kotoba'
    f64_decimal = f64_project / 'decimal_bits.kotoba'
    shutil.copyfile(ROOT / 'src/kotoba/compiler/f64_text.kotoba', f64_text)
    shutil.copyfile(ROOT / 'src/kotoba/compiler/decimal_bits.kotoba', f64_decimal)
    f64_modules = [('kotoba.compiler.decimal-bits', f64_decimal),
                   ('kotoba.compiler.f64-text', f64_text), ('native.f64-text-test', f64_entry)]
    f64_lock = f64_project / 'project.ksl'
    for suffix, body, expected_output in (('positive', f64_source, b'42\n'),
                                          ('negative', f64_source.replace('"5e-324"', '"5e-323"'), b'7\n')):
        assert body.count('"5e-324"') == (1 if suffix == 'positive' else 0)
        f64_entry.write_text(body)
        f64_lock.write_text(project_lock(f64_entry, f64_modules, [f64_entry, f64_text, f64_decimal]))
        f64_program = out / ('f64-resource-' + suffix)
        run('f64-resource-' + suffix + '-compile', 'compile', f64_entry, '--source-lock', f64_lock,
            '-o', f64_program.name, stdout=('compiled ' + str(f64_program) + '\n').encode())
        run('f64-resource-' + suffix + '-execute', image=f64_program, stdout=expected_output)

    lock = project / 'project.ksl'
    lock.write_text(project_lock(app, [('app', app), ('util', util)], [app, util]))
    run('locked-project-check', 'check', app, '--source-lock', lock, stdout=b'ok\n')
    # JUN-838: `check ENTRY --source-path DIR...` derives the KSL2 module map
    # from the declared roots; the pinned root still verifies it. A module on no
    # declared root keeps the root's E6002, two roots holding one module refuse.
    sp = out / 'source-path-project'
    for d in ('src/lib', 'other/lib', 'dup/lib'):
        (sp / d).mkdir(parents=True)
    sp_app = sp / 'src/app.kotoba'
    sp_app.write_text('(ns app (:require [lib.mid :as m]) (:export [main]))\n(defn main [] :i64 (m/two 40))\n')
    (sp / 'src/lib/mid.kotoba').write_text('(ns lib.mid (:require [lib.leaf :as l]) (:export [two]))\n'
                                           '(defn two [x :i64] :i64 (l/inc1 (l/inc1 x)))\n')
    (sp / 'other/lib/leaf.kotoba').write_text('(ns lib.leaf (:export [inc1]))\n(defn inc1 [x :i64] :i64 (+ x 1))\n')
    (sp / 'dup/lib/leaf.kotoba').write_bytes((sp / 'other/lib/leaf.kotoba').read_bytes())
    run('source-path-check', 'check', sp_app, '--source-path', sp / 'src', '--source-path', sp / 'other', stdout=b'ok\n')
    run('source-path-missing-module', 'check', sp_app, '--source-path', sp / 'src',
        expected=1, diagnostic=b'E6002 required module lib.leaf is missing from the explicit source paths')
    run('source-path-unlisted-root', 'check', sp_app, '--source-path', sp / 'other',
        expected=1, diagnostic=b'E6002 required module lib.mid is missing from the explicit source paths')
    run('source-path-ambiguous-module', 'check', sp_app, '--source-path', sp / 'src', '--source-path', sp / 'other',
        '--source-path', sp / 'dup', expected=1, diagnostic=b'EPATH module lib.leaf is found under more than one')
    run('source-path-with-lock', 'check', sp_app, '--source-path', sp / 'src', '--source-lock', sp / 'x.ksl',
        expected=2, diagnostic=b'usage')
    run('source-path-dangling-flag', 'check', sp_app, '--source-path', sp / 'src', '--source-path',
        expected=2, diagnostic=b'usage')
    # compile takes the same roots (parity with --source-lock compile). run stays
    # refused: mc-main-abi? cannot validate a multi-file project.
    sp_program = out / 'source-path-program'
    run('source-path-compile', 'compile', sp_app, '--source-path', sp / 'src', '--source-path', sp / 'other',
        '-o', sp_program.name, stdout=('compiled ' + str(sp_program) + '\n').encode())
    mac.verify_macho(sp_program)
    run('source-path-native-execute', expected=0, stdout=b'42\n', image=sp_program)
    run('source-path-run-artifact', 'run', sp_program, stdout=b'42\n')
    sp_profile = out / 'source-path-profile-program'
    run('source-path-compile-profile', 'compile', sp_app, '--source-path', sp / 'src', '--source-path', sp / 'other',
        '--runtime-profile', 'amu-program', '-o', sp_profile.name, stdout=('compiled ' + str(sp_profile) + '\n').encode())
    mac.verify_macho(sp_profile)
    sp_program_bytes = sp_program.read_bytes()
    run('source-path-compile-output-collision', 'compile', sp_app, '--source-path', sp / 'src',
        '--source-path', sp / 'other', '-o', sp_program.name, expected=1, diagnostic=b'EOUTPUT')
    assert sp_program.read_bytes() == sp_program_bytes
    run('source-path-compile-output-is-entry', 'compile', sp_app, '--source-path', sp / 'src',
        '--source-path', sp / 'other', '-o', sp_app, expected=1, diagnostic=b'EOUTPUT cannot replace the project entry')
    run('source-path-compile-missing-module', 'compile', sp_app, '--source-path', sp / 'src', '-o', 'sp-missing',
        expected=1, diagnostic=b'E6002 required module lib.leaf is missing from the explicit source paths')
    run('source-path-compile-ambiguous-module', 'compile', sp_app, '--source-path', sp / 'src', '--source-path', sp / 'other',
        '--source-path', sp / 'dup', '-o', 'sp-ambiguous', expected=1, diagnostic=b'EPATH module lib.leaf is found under more than one')
    run('source-path-compile-with-lock', 'compile', sp_app, '--source-path', sp / 'src', '--source-lock', sp / 'x.ksl',
        '-o', 'sp-mixed', expected=2, diagnostic=b'usage')
    run('source-path-run-refused', 'run', sp_app, '--source-path', sp / 'src', expected=2, diagnostic=b'usage')
    run('source-path-run-args-refused', 'run', sp_app, '--source-path', sp / 'src', '--', 'x', expected=2, diagnostic=b'usage')
    run('source-path-run-with-lock', 'run', sp_app, '--source-path', sp / 'src', '--source-lock', sp / 'x.ksl',
        expected=2, diagnostic=b'usage')
    run('source-path-compile-dangling-flag', 'compile', sp_app, '--source-path', sp / 'src', '-o',
        expected=2, diagnostic=b'usage')
    run('source-path-compile-no-root-value', 'compile', sp_app, '--source-path', expected=2, diagnostic=b'usage')
    run('source-path-run-no-separator', 'run', sp_app, '--source-path', sp / 'src', 'extra', expected=2, diagnostic=b'usage')
    run('source-path-run-receipt-refused', 'run', sp_app, '--source-path', sp / 'src', '--receipt', 'r.json',
        expected=2, diagnostic=b'usage')
    run('source-path-too-many-roots', 'check', sp_app, *(a for _ in range(17) for a in ('--source-path', sp / 'src')),
        expected=2, diagnostic=b'usage')
    project_program = out / 'locked-project-program'
    run('locked-project-compile', 'compile', app, '--source-lock', lock, '-o', project_program.name,
        stdout=('compiled ' + str(project_program) + '\n').encode())
    mac.verify_macho(project_program)
    run('locked-project-native-execute', expected=0, stdout=b'42\n', image=project_program)
    run('locked-project-run', 'run', app, '--source-lock', lock, stdout=b'42\n')
    run('locked-project-run-artifact', 'run', project_program, stdout=b'42\n')
    damaged_project_program = out / 'damaged-locked-project-program'
    damaged_bytes = bytearray(project_program.read_bytes())
    damaged_bytes[-1] ^= 1
    damaged_project_program.write_bytes(damaged_bytes)
    run('locked-project-run-damaged-artifact', 'run', damaged_project_program,
        expected=1, diagnostic=b'EARTIFACT supplied project differs')
    project_program_bytes = project_program.read_bytes()
    run('locked-project-output-collision', 'compile', app, '--source-lock', lock, '-o', project_program.name,
        expected=1, diagnostic=b'EOUTPUT')
    assert project_program.read_bytes() == project_program_bytes
    run('locked-project-wrong-entry', 'check', util, '--source-lock', lock,
        expected=1, diagnostic=b'ELOCK entry does not match')
    run('locked-project-compile-wrong-entry', 'compile', util, '--source-lock', lock, '-o', 'wrong-entry-program',
        expected=1, diagnostic=b'ELOCK entry does not match')
    bad_utf8_lock = project / 'invalid-utf8.ksl'
    bad_utf8_lock.write_bytes(b'KSL2\n\xff\n')
    run('locked-project-invalid-utf8-lock', 'check', app, '--source-lock', bad_utf8_lock,
        expected=1, diagnostic=b'ELOCK source lock must be valid UTF-8')
    legacy = project / 'legacy.cljk'
    legacy.write_text(app.read_text())
    legacy_lock = project / 'legacy.ksl'
    legacy_lock.write_text(project_lock(legacy, [('app', legacy), ('util', util)], [legacy, util]))
    run('locked-project-non-kotoba-path', 'check', legacy, '--source-lock', legacy_lock,
        expected=1, diagnostic=b'ELOCK project files must use canonical .kotoba paths')
    util.write_text(util.read_text() + '\n')
    run('locked-project-changed-source', 'check', app, '--source-lock', lock,
        expected=1, diagnostic=b'EINPUT a locked project source')
    run('locked-project-compile-changed-source', 'compile', app, '--source-lock', lock, '-o', 'changed-source-program',
        expected=1, diagnostic=b'EINPUT a locked project source')
    run('locked-project-run-changed-source', 'run', app, '--source-lock', lock,
        expected=1, diagnostic=b'EINPUT a locked project source')
    util.write_text('(ns util (:export [add]))\n(defn add [x :i64] :i64 (+ x 1))\n')

    missing = project / 'missing.kotoba'
    missing.write_text('(ns app (:require [absent :as a]) (:export [main]))\n(defn main [] :i64 (a/value))\n')
    missing_lock = project / 'missing.ksl'
    missing_lock.write_text(project_lock(missing, [('app', missing), ('util', util)], [missing, util]))
    run('locked-project-missing-import', 'check', missing, '--source-lock', missing_lock,
        expected=1, diagnostic=b'E')
    run('compile-default', 'compile', hello.name)
    mac.verify_macho(out / 'hello')
    run('execute-default', expected=0, stdout=b'42\n', image=out / 'hello')
    run('run-source', 'run', hello.name, stdout=b'42\n')
    run('run-artifact', 'run', './hello', stdout=b'42\n')
    # JUN-282: an opt-in run receipt binds source, host images, program and stdout
    run('run-receipt', 'run', hello.name, '--receipt', 'run-receipt.json', stdout=b'42\n')
    receipt = json.loads((out / 'run-receipt.json').read_text())
    assert receipt['schema'] == 'amu.run-receipt.v1' and receipt['exit'] == 0, receipt
    assert receipt['source'] == hashlib.sha256(hello.read_bytes()).hexdigest(), receipt
    assert receipt['stdout'] == hashlib.sha256(b'42\n').hexdigest(), receipt
    assert all(len(receipt[k]) == 64 for k in ('compiler', 'packager', 'program')), receipt
    kept = (out / 'run-receipt.json').read_bytes()
    run('run-receipt-exists', 'run', hello.name, '--receipt', 'run-receipt.json', expected=1, diagnostic=b'ERECEIPT')
    assert (out / 'run-receipt.json').read_bytes() == kept
    first = (out / 'hello').read_bytes()
    hello.write_text('(ns hello (:export [main]))\n(defn main [] :i64 43)\n')
    run('changed-source', 'run', hello.name, stdout=b'43\n')
    run('old-artifact-independent', 'run', './hello', stdout=b'42\n')
    run('compile-explicit', 'compile', hello.name, '-o', 'hello43')
    run('run-43-artifact', 'run', 'hello43', stdout=b'43\n')
    assert (out / 'hello43').read_bytes() != first
    run('preserve-output', 'compile', hello.name, '-o', 'hello', expected=1, diagnostic=b'EOUTPUT')
    assert (out / 'hello').read_bytes() == first
    nested = out / 'space 日本語'
    nested.mkdir()
    unicode_source = nested / '試験.kotoba'
    unicode_source.write_bytes(hello.read_bytes())
    run('unicode-check', 'check', unicode_source, stdout=b'ok\n')
    run('unicode-compile', 'compile', unicode_source, '--output', nested / 'native 実行')
    run('unicode-run', 'run', nested / 'native 実行', stdout=b'43\n')
    for i, value in enumerate((0, -1, 256, 9223372036854775807, -9223372036854775808)):
        p = source('integer' + str(i), f'(defn main [] :i64 {value})')
        run('integer' + str(i), 'run', p.name, stdout=f'{value}\n'.encode())
    scoped = source('scoped', '(defn main [] :i64 (arena-scope (+ (arena-scope 40) 2)))')
    run('scoped-result', 'run', scoped.name, stdout=b'42\n')
    for name, body in {
        'string': '(defn main [] :string "hello")',
        'bool': '(defn main [] :bool true)',
        'parameter': '(defn main [x :i64] :i64 x)',
        'no-main': '(defn other [] :i64 42)',
        'invalid': '(defn main [] :i64 "bad")',
        'trailing-reader-discard': '(defn main [] :string "bad")\n#_',
    }.items():
        p = source(name, body)
        run('reject-' + name, 'compile', p.name, '-o', name + '.out', expected=1, diagnostic=b'EABI')
        assert not (out / (name + '.out')).exists()
    bad = source('bad', '(defn main [] :i64 "bad")')
    run('check-type-error', 'check', bad.name, expected=1, diagnostic=b'E')
    for i, args in enumerate((('compile', hello.name, '--target', 'x86_64-linux'),
                              ('check', hello.name, '--source-path'),
                              ('check', hello.name, '--source-path', '.', '--source-lock', 'x.ksl'),
                              ('compile', hello.name, '-o'), ('garbage', hello.name),
                              ('run', hello.name, '--receipt'), ('run', hello.name, '--receipt', 'r.json', 'extra'))):
        run('usage' + str(i), *args, expected=2, diagnostic=b'usage:')
    run('project-run-missing-lock', 'run', hello.name, '--source-lock', 'missing',
        expected=1, diagnostic=b'EINPUT expected a bounded regular source lock')
    # removed with the C loader (docs/c-loader-removal.md): refused by name, not as unknown (JUN-282)
    for name in ('measure-runtime', 'package-ios', 'package-macos', 'test'):
        run('removed-' + name, name, hello.name, expected=2, diagnostic=b'EREMOVED ' + name.encode())
    for name, path in [('missing', out/'missing.kotoba'), ('directory', nested)]:
        run(name, 'run', path, expected=1, diagnostic=b'EINPUT')
    link = out / 'link.kotoba'
    link.symlink_to(hello)
    run('symlink', 'check', link.name, expected=1, diagnostic=b'EINPUT')
    fifo = out / 'fifo.kotoba'
    os.mkfifo(fifo)
    run('fifo', 'check', fifo.name, expected=1, diagnostic=b'EINPUT')
    big = out / 'big.kotoba'
    with big.open('wb') as f:
        f.truncate(1048577)
    run('oversize', 'check', big.name, expected=1, diagnostic=b'EINPUT')
    for i, at in enumerate((0, 1024, len(first)-1)):
        changed = bytearray(first)
        changed[at] ^= 1
        p = out / ('tampered' + str(i))
        p.write_bytes(changed)
        run('tampered' + str(i), 'run', p.name, expected=1, diagnostic=b'EARTIFACT')
    p = source('args', '(defn main [] :i64 (let [w (typed-cap-call :io/write :string :string (typed-cap-call :cli/args :string :string "0"))] 42))')
    run('guest-argv', 'run', p.name, '--', 'hello 日本語', stdout='hello 日本語42\n'.encode())
    for name, cap, kind, payload in [('fs', ':fs/app-data-bytes', ':bytes', '(bytes-from-vector-i64 [0 70 83 50 0 65 120 0])'),
                                     ('process', ':process/spawn', ':string', '"anything"')]:
        p = source('deny-' + name, f'(defn main [] :i64 (let [r (typed-cap-call {cap} {kind} {kind} {payload})] 42))')
        r = subprocess.run([str(cli), 'run', str(p)], cwd=out, capture_output=True, timeout=150)
        (out / ('denied-' + name + '.stdout')).write_bytes(r.stdout)
        (out / ('denied-' + name + '.stderr')).write_bytes(r.stderr)
        assert r.returncode != 0 and r.stdout != b'42\n', (name, r.returncode, r.stdout, r.stderr)
        calls.append(dict(name='guest-grant-denied-' + name, exit=r.returncode))
    loop = source('loop', '(defn main [] :i64 (loop [i 0] (recur (+ i 1))))')
    run('deadline', 'run', loop.name, expected=124, diagnostic=b'ETIME')
    # Caller-controlled program bytes are recompiled and compared, never exec'd.
    marker = out / 'must-not-execute'
    fake = out / 'untrusted'
    fake.write_bytes(b'#!/bin/sh\ntouch ' + str(marker).encode() + b'\n')
    fake.chmod(0o700)
    run('untrusted-executable', 'run', fake, expected=1, diagnostic=b'EINPUT')
    assert not marker.exists()
    isolated = out / 'provenance'
    isolated.mkdir()
    isolated_cli = isolated / 'amu-cli.macho'
    shutil.copy2(cli.resolve(), isolated_cli)
    run('missing-compiler', 'check', hello, expected=70, diagnostic=b'EPROVENANCE', image=isolated_cli)
    for name in ('amu-full-root.macho', 'kotoba-packager-root.macho'):
        shutil.copy2(cli.resolve().parent / name, isolated / name)
        with (isolated / name).open('r+b') as f:
            first_byte = f.read(1)
            f.seek(0)
            f.write(bytes([first_byte[0] ^ 1]))
        run('corrupted-' + name, 'check', hello, expected=70, diagnostic=b'EPROVENANCE', image=isolated_cli)
        shutil.copy2(cli.resolve().parent / name, isolated / name)
    assert set(Path('/private/tmp').glob('amu-*')) == before_tmp, 'private CLI directories leaked'
    result = dict(schema='amu.macos-cli-product-observation.v1', status='PASS_ORDINARY_MACOS_CLI',
                  cli=mac.pin(cli), calls=calls, manualFD3=False, hostedFallback=False,
                  nativeResults=[42,43], nativeBuildRequired=True, independentUserQualified=False)
    (out / 'cli-product.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], len(calls), 'native observations')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cli', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    check(args.cli.resolve(), args.output.resolve())
