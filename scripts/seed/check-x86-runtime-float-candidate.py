#!/usr/bin/env python3
"""Observe an unadopted compiler's KX64 project and float results on native x86."""
import argparse
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def pin(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--compiler', type=Path, required=True)
    p.add_argument('--cross-receipt', type=Path, required=True)
    p.add_argument('--cross-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise SystemExit('native Linux x86_64 required')
    compiler = a.compiler.resolve(strict=True)
    cross_path = a.cross_receipt.resolve(strict=True)
    cross_pin = pin(cross_path)
    if cross_pin['sha256'] != a.cross_sha256:
        raise SystemExit('cross receipt pin mismatch')
    cross = json.loads(cross_path.read_text())
    if cross['status'] != 'MAC_NATIVE_CROSS_CANDIDATES_UNADOPTED' or pin(compiler) != cross['x86FullCompiler']:
        raise SystemExit('unadopted compiler mismatch')
    spec = importlib.util.spec_from_file_location('cross_gate', ROOT / 'scripts/seed/check-macos-cross-linux-native.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    gate.source_unity(ROOT / 'seed/FULL-MANIFEST', cross['fullSource'])
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = {'PATH': '/nonexistent', 'KEXE_STACK_BYTES': '8388608', 'KEXE_CAP_RESOURCES_35': str(out)}
    calls = []
    def run(name, argv, env_override=None):
        result = subprocess.run([str(x) for x in argv], cwd=out, env=env if env_override is None else env_override, capture_output=True, timeout=900)
        stdout = out / (name + '.stdout'); stderr = out / (name + '.stderr')
        stdout.write_bytes(result.stdout); stderr.write_bytes(result.stderr)
        calls.append({'name': name, 'exit': result.returncode, 'stdout': pin(stdout), 'stderr': pin(stderr)})
        print(name, result.returncode, result.stderr.decode(errors='replace')[-400:], flush=True)
        return result
    project = run('project-observer', ['python3', ROOT / 'scripts/seed/check-x86-project-native.py', '--compiler', compiler, '--output', out / 'project'], {'PATH': '/usr/bin:/bin'})
    if project.returncode:
        raise SystemExit('existing project fixture failed')
    runner_source = out / 'runner.kotoba'
    shutil.copyfile(ROOT / 'seed/x86_64-kx64-runner.kotoba', runner_source)
    runner = out / 'runner.elf'
    built = run('runner-compile', [compiler, 'compile', runner_source, '--target', 'x86_64-linux', '--output', runner, '--format', 'kx64-runner'])
    if built.returncode or not runner.is_file():
        raise SystemExit('runner compile failed')
    runner.chmod(0o700)
    examples = [('full-float', ROOT / 'test/fixtures/selfhost/x86-float/native/x86_float_test.kotoba', 511),
                ('float-original-stack', ROOT / 'test/fixtures/selfhost/x86-float/native/x86_float_stack_test.kotoba', 3),
                ('document-f64', ROOT / 'diagnostics/kotoba161-runtime-float/doc-f64.kotoba', 42),
                ('float-stack', ROOT / 'diagnostics/kotoba161-runtime-float/float-stack.kotoba', 42)]
    cases = []
    for name, input_source, expected in examples:
        source = out / (name + '.kotoba'); shutil.copyfile(input_source, source)
        image = out / (name + '.kx64')
        result = run(name + '-compile', [compiler, 'compile', source, '--target', 'x86_64-linux', '--output', image, '--format', 'kx64-v1'])
        if result.returncode or not image.is_file():
            raise SystemExit(name + ' compile failed')
        header, body = image.read_bytes().split(b'\n\n', 1)
        match = re.fullmatch(rb'KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0', header)
        if not match or len(body) != int(match[1]) or body[0] != 0xe9:
            raise SystemExit(name + ' invalid KX64')
        payload = out / (name + '.bin'); payload.write_bytes(body)
        result = run(name + '-run', [runner, payload, '0', '0', 'x86_64', '-'], dict(env, KEXE_STRUCTURED_REPORT='1', KEXE_ALLOW='-'))
        found = re.search(rb':result (-?[0-9]+)', result.stdout)
        if result.returncode or not found or int(found[1]) != expected:
            raise SystemExit(name + ' execution mismatch')
        cases.append({'name': name, 'source': pin(source), 'image': pin(image), 'payload': pin(payload), 'expected': expected})
    mx = run('mxcsr-observer', ['python3', ROOT / 'scripts/seed/observe-x86-mxcsr.py', '--runner', runner, '--payload', out / 'full-float.bin', '--output', out / 'mxcsr'], {'PATH': '/usr/bin:/bin'})
    if mx.returncode:
        raise SystemExit('caller MXCSR diagnostic failed')
    src = out / 'f32-range-trap.kotoba'
    shutil.copyfile(ROOT / 'diagnostics/kotoba161-runtime-float/f32-range-trap.kotoba', src)
    image = out / 'f32-range-trap.kx64'
    result = run('f32-range-trap-compile', [compiler, 'compile', src, '--target', 'x86_64-linux', '--output', image, '--format', 'kx64-v1'])
    if result.returncode or not image.is_file():
        raise SystemExit('f32 range trap compile failed')
    header, body = image.read_bytes().split(b'\n\n', 1)
    match = re.fullmatch(rb'KX64V1 x86_64-linux sysv-ctx-v11 ([0-9]+) 0', header)
    if not match or len(body) != int(match[1]) or body[0] != 0xe9:
        raise SystemExit('f32 range trap invalid KX64')
    payload = out / 'f32-range-trap.bin'; payload.write_bytes(body)
    result = run('f32-range-trap-run', [runner, payload, '0', '0', 'x86_64', '-'], dict(env, KEXE_STRUCTURED_REPORT='1', KEXE_ALLOW='-'))
    if result.returncode != 120 or b':status :trap' not in result.stdout or b'SIGILL' not in result.stderr:
        raise SystemExit('f32 range trap did not fail closed')
    cases.append({'name': 'f32-range-trap', 'source': pin(src), 'image': pin(image), 'payload': pin(payload), 'expectedTrap': True})
    for name, diagnostic in [('kernel-floating-operation', b'E7102'), ('kernel-floating-result', b'E2104')]:
        source = out / (name + '.kotoba')
        shutil.copyfile(ROOT / 'test/fixtures/selfhost/x86-float/refusals' / (name + '.kotoba'), source)
        image = out / (name + '.o')
        result = run(name + '-refusal', [compiler, 'compile', source, '--target', 'x86_64-aiueos-kernel-v1', '--output', image])
        if result.returncode == 0 or image.exists() or diagnostic not in result.stderr:
            raise SystemExit(name + ' expected refusal missing')
        cases.append({'name': name, 'source': pin(source), 'expectedDiagnostic': diagnostic.decode(), 'noArtifact': True})
    if pin(cross_path) != cross_pin or pin(compiler) != cross['x86FullCompiler']:
        raise SystemExit('candidate changed during run')
    report = {'status': 'PASS_X86_RUNTIME_FLOAT_DIAGNOSTIC', 'compiler': pin(compiler), 'crossReceipt': cross_pin,
              'sourceUnity': cross['fullSource']['unity'], 'projectReceipt': pin(out / 'project/x86-project.json'),
              'runner': pin(runner), 'cases': cases, 'calls': calls, 'publicProductAdopted': False,
              'fullNativeCorpusQualified': False}
    (out / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], flush=True)

if __name__ == '__main__':
    main()
