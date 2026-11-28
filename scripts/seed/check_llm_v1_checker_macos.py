#!/usr/bin/env python3
"""Check llm-v1 admission and optional Darwin guest lowering.

Python stages source and observes native execution. Wire vectors use synthetic
values, and the ordinary packaged guest has no provider grant.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'seed/tests/llm-v1-checker.kotoba'
SOURCE_REF = ROOT / 'seed/tests/llm-v1-ref-checker.kotoba'
CODEC = ROOT / 'seed/runtime/llm-v1-wire.kotoba'
VECTORS = ROOT / 'seed/tests/llm-v1-wire-vectors.kotoba'
KIT = ROOT / 'resources/kotoba/lang/capability-kits/llm-v1.edn'
CATALOG = ROOT / 'resources/kotoba/lang/capability-catalog.edn'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native(image, directory, *args):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    saved_fd3 = None
    try:
        if fd != 3:
            try:
                saved_fd3 = os.dup(3)
            except OSError:
                pass
            os.dup2(fd, 3)
        passed = (3,) if saved_fd3 is None else (3, saved_fd3)
        return subprocess.run([str(image), *args], cwd=directory, pass_fds=passed,
                              capture_output=True, timeout=60, check=False)
    finally:
        if saved_fd3 is not None:
            os.dup2(saved_fd3, 3)
            os.close(saved_fd3)
        os.close(fd)


def run_native(image, output, *args):
    result = native(image, output, *args)
    if result.returncode or result.stderr:
        raise RuntimeError(args[0] + ': ' + result.stderr.decode(errors='replace')[:400])
    return result.stdout


def schema_digest():
    # The kit descriptors are closed EDN vectors of keywords. Their canonical
    # wire digest uses one space between forms and no edge whitespace.
    kit = KIT.read_text()
    wire = r':capability\s+\{:name\s+:llm/generate\s+:id\s+11\}'
    catalog = r':llm/generate\s+\{[^}]*:compiler-wire-id\s+11\b'
    if not re.search(wire, kit) or not re.search(catalog, CATALOG.read_text()):
        raise RuntimeError('the canonical LLM kit or registry no longer assigns wire 11')
    request, result = kit.split(':request\n', 1)[1].split(':result\n', 1)

    def canonical(text):
        text = ' '.join(text.split())
        return re.sub(r' +\]', ']', re.sub(r'\[ +', '[', text))

    encoded = f'[{canonical(request)} {canonical(result.split(";;", 1)[0])}]'
    return hashlib.sha256(encoded.encode('ascii')).hexdigest()


def check_embed():
    source = (ROOT / 'seed/90-drv.kotoba').read_text()
    embedded = source.split('(defn- drv-llm-wire-source [] :string\n  "', 1)[1]
    embedded = embedded.split('")\n;; END LLM V1 WIRE EMBED', 1)[0]
    fragment = CODEC.read_text().split(';; KLM1/KLR1', 1)[1]
    fragment = '\n\n;; KLM1/KLR1' + fragment.split('\n;; Host-side codec functions', 1)[0]
    if embedded != fragment.replace('\\', '\\\\').replace('"', '\\"'):
        raise RuntimeError('the embedded guest codec differs from its native source')


def package(image, packager, directory, name, source, container):
    raw = name + '.raw'
    extracted = run_native(image, directory, 'extract-native', container,
                           '--symbol', 'main', '--output', raw)
    offset = re.search(rb':offset (\d+), :length (\d+), :arity 0}', extracted)
    if not offset or int(offset[2]) != (directory / raw).stat().st_size:
        raise RuntimeError('wrong main extent in ' + container)
    macho = directory / (name + '.macho')
    run_native(packager, directory, macho.name, raw, 'amu-program', offset[1].decode(), source)
    macho.chmod(0o755)
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none',
                    '--identifier', 'org.kotoba.amu.wire11-test.v1', str(macho)],
                   check=True, capture_output=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(macho)],
                   check=True, capture_output=True)
    return directory / raw, macho


def execute(image, directory, timeout):
    return subprocess.run([str(image)], cwd=directory, env={'PATH': '/usr/bin:/bin', 'LANG': 'C'},
                          stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, check=False)


def wire_vectors(image, packager, output, note):
    check_embed()
    vector_source = output / 'vectors.kotoba'
    vector_source.write_text(CODEC.read_text().replace('(:export [])', '(:export [main])') +
                             '\n' + VECTORS.read_text())
    run_native(image, output, 'compile', vector_source.name, '--target', 'aarch64-macos',
               '--output', 'vectors.kseed')
    raw, macho = package(image, packager, output, 'vectors', vector_source.name, 'vectors.kseed')
    result = execute(macho, output, 60)
    if result.returncode or result.stdout != b'0\n' or result.stderr or raw.read_bytes().endswith(note):
        raise RuntimeError(f'native codec vectors failed: exit {result.returncode}, stdout {result.stdout!r}')
    return {'exit': result.returncode, 'result': 0, 'source_sha256': sha(vector_source),
            'container_sha256': sha(output / 'vectors.kseed'), 'raw_sha256': sha(raw),
            'macho_sha256': sha(macho)}


def ungranted(image, packager, output, note):
    source = output / 'ungranted.kotoba'
    fixture = SOURCE_REF.read_text().replace('(:export [generate])', '(:export [main])')
    source.write_text(fixture + '''
(defn main [] :i64
  (let [request (record-new [:ref :kotoba.llm/generate-request] :synthetic/model "system" "prompt" 42 125)
        result (generate request)]
    (match-variant result [:ref :kotoba.llm/result]
      (:ok completion (:output-tokens (:usage completion)))
      (:error failure (if (:retryable failure) 1 0)))))
''')
    run_native(image, output, 'compile', source.name, '--target', 'aarch64-macos',
               '--output', 'ungranted.kseed')
    raw, macho = package(image, packager, output, 'ungranted', source.name, 'ungranted.kseed')
    result = execute(macho, output, 5)
    if result.returncode != -signal.SIGTRAP or result.stdout or not raw.read_bytes().endswith(note):
        raise RuntimeError(f'ordinary wire-11 guest did not refuse: exit {result.returncode}')
    packaged = macho.read_bytes()
    if packaged[8192:8192 + raw.stat().st_size] != raw.read_bytes():
        raise RuntimeError('Darwin packaging lost the wire-11 requirement')
    return {'signal': 'SIGTRAP', 'source_sha256': sha(source),
            'container_sha256': sha(output / 'ungranted.kseed'), 'raw_sha256': sha(raw),
            'macho_sha256': sha(macho), 'provider_installed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--expected-image-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--wire11', action='store_true', help='expect compiled Darwin wire-11 guests')
    args = parser.parse_args()
    image = args.image.resolve(strict=True)
    if image.is_symlink() or sha(image) != args.expected_image_sha256:
        raise ValueError('signed compiler image pin mismatch')
    subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(image)],
                   check=True, capture_output=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    source = SOURCE.read_text()
    shutil.copyfile(SOURCE, output / 'positive.kotoba')
    shutil.copyfile(SOURCE_REF, output / 'positive-ref.kotoba')
    cases = [('positive', 0, b'ok'), ('positive-ref', 0, b'ok')]
    for name, old, new in (
        ('bad-request', '[:model :keyword]', '[:model :string]'),
        ('bad-usage', '[:output-tokens :i64]', '[:output-tokens :string]'),
        ('bad-result-name', ':kotoba.llm/result', ':kotoba.llm/other-result'),
    ):
        if old not in source:
            raise ValueError('fixture changed: ' + old)
        candidate = source.replace(old, new)
        (output / (name + '.kotoba')).write_text(candidate)
        cases.append((name, 1, b'E2115'))
    if args.wire11:
        (output / 'bad-raw.kotoba').write_text(
            '(ns llm.raw-probe (:export [main]))\n'
            '(defn main [] :i64 (typed-cap-call 11 :i64 :i64 123))\n')
        cases.append(('bad-raw', 1, b'E2115'))
    checks = []
    for name, expected_exit, expected_text in cases:
        result = native(image, output, 'check', name + '.kotoba')
        observed = result.stdout if expected_exit == 0 else result.stderr
        if result.returncode != expected_exit or expected_text not in observed:
            raise RuntimeError(name + ': wrong check result: ' +
                               result.stderr.decode(errors='replace')[:300])
        checks.append({'name': name, 'exit': result.returncode,
                       'source_sha256': sha(output / (name + '.kotoba'))})
    refusals, builds = [], []
    digest = schema_digest()
    note = (f'\0AMU-LLM-REQUIREMENT-V1\nwire 11 :llm/generate\nrequest :kotoba.llm/generate-request\n'
            f'result :kotoba.llm/result\nschema-sha256 {digest}\n').encode('ascii')
    for source_name in ('positive', 'positive-ref'):
        targets = ('aarch64-macos', 'x86_64-aiueos-user-v3')
        if args.wire11:
            targets += ('x86_64-linux', 'aarch64-linux', 'wasm32-browser')
        for target in targets:
            artifact = output / (source_name + '-' + target + '.bin')
            flags = ('--format', 'static') if target == 'aarch64-linux' else ()
            result = native(image, output, 'compile', source_name + '.kotoba',
                            '--target', target, '--output', artifact.name, *flags)
            if args.wire11 and target == 'aarch64-macos':
                if result.returncode or not artifact.is_file() or not artifact.read_bytes().endswith(note):
                    raise RuntimeError(source_name + ': Darwin wire-11 requirement missing: ' +
                                       result.stderr.decode(errors='replace')[:400])
                repeat = artifact.with_suffix('.repeat')
                run_native(image, output, 'compile', source_name + '.kotoba',
                           '--target', target, '--output', repeat.name)
                if repeat.read_bytes() != artifact.read_bytes():
                    raise RuntimeError(source_name + ': Darwin compile is not reproducible')
                builds.append({'source': source_name, 'target': target, 'repeat_equal': True,
                               'container_sha256': sha(artifact)})
                continue
            if result.returncode != 1 or b'E3004' not in result.stderr or artifact.exists():
                raise RuntimeError(source_name + ' ' + target +
                                   ': native transport was not refused: ' +
                                   result.stderr.decode(errors='replace')[:200])
            refusals.append({'source': source_name, 'target': target, 'exit': 1,
                             'diagnostic': 'E3004', 'artifact_exists': False})
    receipt = {'schema': 'amu.llm-v1-checker-macos.v1', 'ok': True,
               'image_sha256': sha(image), 'fixture_sha256': sha(SOURCE),
               'ref_fixture_sha256': sha(SOURCE_REF),
               'checks': checks, 'compile_refusals': refusals,
               'runtime_qualified': False}
    if args.wire11:
        descriptor = json.loads((ROOT / 'seed/bootstrap/aarch64-macos/root.json').read_text())
        packager = ROOT / descriptor['packager']['path']
        if packager.is_symlink() or sha(packager) != descriptor['packager']['sha256']:
            raise RuntimeError('pinned native packager identity mismatch')
        receipt.update(schema='amu.llm-v1-wire-macos.v1', schema_sha256=digest,
                       kit_sha256=sha(KIT), codec_sha256=sha(CODEC), packager_sha256=sha(packager),
                       darwin_compiles=builds, codec_vectors=wire_vectors(image, packager, output, note),
                       ungranted_guest=ungranted(image, packager, output, note))
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
