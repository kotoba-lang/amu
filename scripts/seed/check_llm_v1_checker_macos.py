#!/usr/bin/env python3
"""Check exact llm-v1 admission and native refusal with a signed Mac Amu image.

Python stages source and observes the native compiler; it is not a runtime
provider or a claim that the guest can call an LLM.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'seed/tests/llm-v1-checker.kotoba'
SOURCE_REF = ROOT / 'seed/tests/llm-v1-ref-checker.kotoba'


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--expected-image-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
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
    checks = []
    for name, expected_exit, expected_text in cases:
        result = native(image, output, 'check', name + '.kotoba')
        observed = result.stdout if expected_exit == 0 else result.stderr
        if result.returncode != expected_exit or expected_text not in observed:
            raise RuntimeError(name + ': wrong check result: ' +
                               result.stderr.decode(errors='replace')[:300])
        checks.append({'name': name, 'exit': result.returncode,
                       'source_sha256': sha(output / (name + '.kotoba'))})
    refusals = []
    for source_name in ('positive', 'positive-ref'):
        for target in ('aarch64-macos', 'x86_64-aiueos-user-v3'):
            artifact = output / (source_name + '-' + target + '.bin')
            result = native(image, output, 'compile', source_name + '.kotoba',
                            '--target', target, '--output', artifact.name)
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
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
