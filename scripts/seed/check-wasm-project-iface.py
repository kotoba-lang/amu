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
    source.write_bytes(b''.join((ROOT/name).read_bytes()+b'\n' for name in names)+FIXTURE.read_bytes())
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
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {'status':'PASS_WASM_PROJECT_IFACE', 'target':target, 'compilerSha256':sha(compiler),
               'fixtureSha256':sha(FIXTURE),'sourceSha256':sha(source),'imageSha256':sha(image),
               'negativeControlSourceSha256':sha(mutant_source),'negativeControlImageSha256':sha(mutant),
               'limitations':['interface mapping component only; no project linker or Wasm execution']}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'],target)

if __name__ == '__main__': main()
