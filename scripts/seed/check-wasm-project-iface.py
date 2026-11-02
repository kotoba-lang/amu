#!/usr/bin/env python3
"""Compile and execute the Wasm project interface controls with native Amu."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'seed/tests/unit/81-wasm-project-iface_t.kotoba'
STUB_FIXTURE = ROOT / 'seed/tests/unit/81-wasm-project-stubs_t.kotoba'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert platform.system() == 'Linux'
    target = {'aarch64':'aarch64-linux', 'arm64':'aarch64-linux', 'x86_64':'x86_64-linux'}[platform.machine()]
    compiler = args.compiler.resolve(strict=True)
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    names = [line for line in (ROOT/'seed/FULL-MANIFEST').read_text().splitlines()
             if line and not line.startswith('#') and line != 'seed/78-full-entry.kotoba']
    source = out/'unit.kotoba'
    prefix = b''.join((ROOT/name).read_bytes()+b'\n' for name in names)
    source.write_bytes(prefix+FIXTURE.read_bytes())
    env = dict(PATH='/nonexistent', KEXE_ALLOW='35,37,38,39', KEXE_CAP_RESOURCES_35=str(out), KEXE_STACK_BYTES='8388608')
    image = out/'unit.elf'
    built = subprocess.run([str(compiler),'compile',str(source),'--target',target,'--output',str(image),'--format','static'],
                           cwd=out, env=env, capture_output=True, timeout=900)
    assert built.returncode == 0 and not built.stderr and image.is_file(), (built.returncode,built.stderr[-1000:])
    image.chmod(0o755)
    result = subprocess.run([str(image)],cwd=out,env=dict(PATH='/nonexistent', KEXE_ALLOW='-', KEXE_STRUCTURED_REPORT='1', KEXE_STACK_BYTES='8388608'),
                            capture_output=True,timeout=120)
    assert result.returncode == 0 and not result.stderr and re.search(rb':status :ok :result 0(?:\s|})',result.stdout), (result.returncode,result.stdout,result.stderr)
    # Removing the guard must make the same native test detect the defect.
    original = source.read_bytes()
    guard = b'(not (xw-iface-valid? M L first end base))'
    assert original.count(guard) == 1
    mutant_source = out/'mutant.kotoba'; mutant_source.write_bytes(original.replace(guard, b'false'))
    mutant = out/'mutant.elf'
    mutated_build = subprocess.run([str(compiler),'compile',str(mutant_source),'--target',target,'--output',str(mutant),'--format','static'],
                                   cwd=out,env=env,capture_output=True,timeout=900)
    assert mutated_build.returncode == 0 and not mutated_build.stderr and mutant.is_file(), (mutated_build.returncode,mutated_build.stderr[-1000:])
    mutant.chmod(0o755)
    negative = subprocess.run([str(mutant)],cwd=out,env=dict(PATH='/nonexistent', KEXE_ALLOW='-', KEXE_STRUCTURED_REPORT='1', KEXE_STACK_BYTES='8388608'),
                              capture_output=True,timeout=120)
    assert not negative.stderr and re.search(rb':status :ok :result 5(?:\s|})',negative.stdout), (negative.returncode,negative.stdout,negative.stderr)
    # Separate processes keep the compiler-sized test states independent.
    stub_source = out/'stubs.kotoba'; stub_source.write_bytes(prefix+STUB_FIXTURE.read_bytes())
    stub_image = out/'stubs.elf'
    stub_build = subprocess.run([str(compiler),'compile',str(stub_source),'--target',target,'--output',str(stub_image),'--format','static'],
                                cwd=out,env=env,capture_output=True,timeout=900)
    assert stub_build.returncode == 0 and not stub_build.stderr and stub_image.is_file(), (stub_build.returncode,stub_build.stderr[-1000:])
    stub_image.chmod(0o755)
    stub_result = subprocess.run([str(stub_image)],cwd=out,env=dict(PATH='/nonexistent', KEXE_ALLOW='-', KEXE_STRUCTURED_REPORT='1', KEXE_STACK_BYTES='8388608'),
                                 capture_output=True,timeout=120)
    assert stub_result.returncode == 0 and not stub_result.stderr and re.search(rb':status :ok :result 0(?:\s|})',stub_result.stdout), (stub_result.returncode,stub_result.stdout,stub_result.stderr)
    stub_guard = b'(not (xw-project-stubs-valid? M L first count start))'
    stub_bytes = stub_source.read_bytes(); assert stub_bytes.count(stub_guard) == 1
    stub_mutant_source = out/'stubs-mutant.kotoba'; stub_mutant_source.write_bytes(stub_bytes.replace(stub_guard, b'false'))
    stub_mutant = out/'stubs-mutant.elf'
    stub_mutant_build = subprocess.run([str(compiler),'compile',str(stub_mutant_source),'--target',target,'--output',str(stub_mutant),'--format','static'],
                                      cwd=out,env=env,capture_output=True,timeout=900)
    assert stub_mutant_build.returncode == 0 and not stub_mutant_build.stderr and stub_mutant.is_file(), (stub_mutant_build.returncode,stub_mutant_build.stderr[-1000:])
    stub_mutant.chmod(0o755)
    stub_negative = subprocess.run([str(stub_mutant)],cwd=out,env=dict(PATH='/nonexistent', KEXE_ALLOW='-', KEXE_STRUCTURED_REPORT='1', KEXE_STACK_BYTES='8388608'),
                                   capture_output=True,timeout=120)
    assert not stub_negative.stderr and re.search(rb':status :ok :result 39(?:\s|})',stub_negative.stdout), (stub_negative.returncode,stub_negative.stdout,stub_negative.stderr)
    archive_guard = b'(not (xw-project-archive-valid? M 1 n used start (+ XW-NIMPORT count)))'
    assert stub_bytes.count(archive_guard) == 1
    archive_source = out/'archive-mutant.kotoba'; archive_source.write_bytes(stub_bytes.replace(archive_guard,b'false'))
    archive_image = out/'archive-mutant.elf'
    archive_build = subprocess.run([str(compiler),'compile',str(archive_source),'--target',target,'--output',str(archive_image),'--format','static'],
                                   cwd=out,env=env,capture_output=True,timeout=900)
    assert archive_build.returncode == 0 and not archive_build.stderr and archive_image.is_file(), (archive_build.returncode,archive_build.stderr[-1000:])
    archive_image.chmod(0o755)
    archive_negative = subprocess.run([str(archive_image)],cwd=out,env=dict(PATH='/nonexistent',KEXE_ALLOW='-',KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608'),
                                      capture_output=True,timeout=120)
    assert not archive_negative.stderr and re.search(rb':status :ok :result 51(?:\s|})',archive_negative.stdout), (archive_negative.returncode,archive_negative.stdout,archive_negative.stderr)
    payload_guard = b'(not (xw-project-archive-readable? L start count))'
    assert stub_bytes.count(payload_guard) == 2
    payload_receipts = {}
    for name, replace_index, expected in (('types', 0, 74), ('bodies', 1, 72)):
        parts = stub_bytes.split(payload_guard)
        parts[replace_index] += b'false'
        mutant_bytes = payload_guard.join(parts[:replace_index+1]) + payload_guard.join(parts[replace_index+1:])
        payload_source = out/f'payload-{name}-mutant.kotoba'; payload_source.write_bytes(mutant_bytes)
        payload_image = out/f'payload-{name}-mutant.elf'
        built = subprocess.run([str(compiler),'compile',str(payload_source),'--target',target,'--output',str(payload_image),'--format','static'],
                               cwd=out,env=env,capture_output=True,timeout=900)
        assert built.returncode == 0 and not built.stderr and payload_image.is_file(), (built.returncode,built.stderr[-1000:])
        payload_image.chmod(0o755)
        negative = subprocess.run([str(payload_image)],cwd=out,env=dict(PATH='/nonexistent',KEXE_ALLOW='-',KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608'),
                                  capture_output=True,timeout=120)
        assert not negative.stderr and re.search(rb':status :ok :result '+str(expected).encode()+rb'(?:\s|})',negative.stdout), (negative.returncode,negative.stdout,negative.stderr)
        payload_receipts[name] = {'sourceSha256':hashlib.sha256(payload_source.read_bytes()).hexdigest(),
                                  'imageSha256':hashlib.sha256(payload_image.read_bytes()).hexdigest()}
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {'status':'PASS_WASM_PROJECT_IFACE', 'target':target, 'compilerSha256':sha(compiler),
               'fixtureSha256':sha(FIXTURE),'sourceSha256':sha(source),'imageSha256':sha(image),
               'negativeControlSourceSha256':sha(mutant_source),'negativeControlImageSha256':sha(mutant),
               'stubFixtureSha256':sha(STUB_FIXTURE),'stubSourceSha256':sha(stub_source),'stubImageSha256':sha(stub_image),
               'stubNegativeSourceSha256':sha(stub_mutant_source),'stubNegativeImageSha256':sha(stub_mutant),
               'archiveNegativeSourceSha256':sha(archive_source),'archiveNegativeImageSha256':sha(archive_image),
               'payloadNegativeControls':payload_receipts,
               'limitations':['interface mapping component only; no project linker or Wasm execution']}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'],target)

if __name__ == '__main__': main()
