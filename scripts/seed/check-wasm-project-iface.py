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
MODULE_FIXTURE = ROOT / 'seed/tests/unit/81-wasm-project-module_t.kotoba'
LINKED_FIXTURE = ROOT / 'seed/tests/unit/81-wasm-project-linked_t.kotoba'
GRAPH_FIXTURE = ROOT / 'seed/tests/unit/81-wasm-project-graph_t.kotoba'
RUNTIME_FIXTURE = ROOT / 'seed/tests/unit/81-wasm-project-runtime_t.kotoba'


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
    pool_guard = b'(not (xw-project-pool-literals? M len 1))'
    assert stub_bytes.count(pool_guard) == 1
    pool_source = out/'pool-mutant.kotoba'; pool_source.write_bytes(stub_bytes.replace(pool_guard,b'false'))
    pool_image = out/'pool-mutant.elf'
    built = subprocess.run([str(compiler),'compile',str(pool_source),'--target',target,'--output',str(pool_image),'--format','static'],
                           cwd=out,env=env,capture_output=True,timeout=900)
    assert built.returncode == 0 and not built.stderr and pool_image.is_file(), (built.returncode,built.stderr[-1000:])
    pool_image.chmod(0o755)
    negative = subprocess.run([str(pool_image)],cwd=out,env=dict(PATH='/nonexistent',KEXE_ALLOW='-',KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608'),
                              capture_output=True,timeout=120)
    assert not negative.stderr and re.search(rb':status :ok :result 84(?:\s|})',negative.stdout), (negative.returncode,negative.stdout,negative.stderr)
    module_source = out/'project-module.kotoba'; module_source.write_bytes(prefix+MODULE_FIXTURE.read_bytes())
    module_image = out/'project-module.elf'
    built = subprocess.run([str(compiler),'compile',str(module_source),'--target',target,'--output',str(module_image),'--format','static'],
                           cwd=out,env=env,capture_output=True,timeout=900)
    assert built.returncode == 0 and not built.stderr and module_image.is_file(), (built.returncode,built.stderr[-1000:])
    module_image.chmod(0o755)
    result = subprocess.run([str(module_image)],cwd=out,env=dict(PATH='/nonexistent',KEXE_ALLOW='37',KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608'),
                            capture_output=True,timeout=120)
    assert result.returncode == 0 and not result.stderr and re.search(rb':status :ok :result 0(?:\s|})',result.stdout), (result.returncode,result.stdout,result.stderr)
    match = re.search(rb'WASM-BEGIN\n([0-9a-f\n]+)WASM-END\n',result.stdout)
    assert match, result.stdout
    wasm = bytes.fromhex(match.group(1).decode())
    assert wasm[:8] == b'\x00asm\x01\x00\x00\x00' and b'abc' in wasm
    wasm_path = out/'project-module.wasm'; wasm_path.write_bytes(wasm)
    print('WASM_PROJECT_MODULE_HEX', wasm.hex())
    module_guard = b'(>= start (+ XW-NIMPORT count))'
    module_bytes = module_source.read_bytes(); assert module_bytes.count(module_guard) == 1
    module_mutant_source = out/'project-module-mutant.kotoba'
    module_mutant_source.write_bytes(module_bytes.replace(module_guard,b'false'))
    module_mutant = out/'project-module-mutant.elf'
    built = subprocess.run([str(compiler),'compile',str(module_mutant_source),'--target',target,'--output',str(module_mutant),'--format','static'],
                           cwd=out,env=env,capture_output=True,timeout=900)
    assert built.returncode == 0 and not built.stderr and module_mutant.is_file(), (built.returncode,built.stderr[-1000:])
    module_mutant.chmod(0o755)
    negative = subprocess.run([str(module_mutant)],cwd=out,env=dict(PATH='/nonexistent',KEXE_ALLOW='37',KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608'),
                              capture_output=True,timeout=120)
    assert not negative.stderr and re.search(rb':status :ok :result 1(?:\s|})',negative.stdout), (negative.returncode,negative.stdout,negative.stderr)
    linked_source = out/'project-linked.kotoba'; linked_source.write_bytes(prefix+LINKED_FIXTURE.read_bytes())
    linked_image = out/'project-linked.elf'
    built = subprocess.run([str(compiler),'compile',str(linked_source),'--target',target,'--output',str(linked_image),'--format','static'],
                           cwd=out,env=env,capture_output=True,timeout=900)
    assert built.returncode == 0 and not built.stderr and linked_image.is_file(), (built.returncode,built.stderr[-1000:])
    linked_image.chmod(0o755)
    result = subprocess.run([str(linked_image)],cwd=out,env=dict(PATH='/nonexistent',KEXE_ALLOW='37',KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608'),
                            capture_output=True,timeout=120)
    assert result.returncode == 0 and not result.stderr and re.search(rb':status :ok :result 0(?:\s|})',result.stdout), (result.returncode,result.stdout,result.stderr)
    match = re.search(rb'LINKED-BEGIN\n([0-9a-f\n]+)LINKED-END\n',result.stdout)
    assert match, result.stdout
    linked_wasm = bytes.fromhex(match.group(1).decode())
    assert linked_wasm[:8] == b'\x00asm\x01\x00\x00\x00'
    linked_path = out/'project-linked.wasm'; linked_path.write_bytes(linked_wasm)
    print('WASM_PROJECT_LINKED_HEX', linked_wasm.hex())
    policy_guard = b'(pj-r5b-after lowered L P S module)'
    linked_bytes = linked_source.read_bytes(); assert linked_bytes.count(policy_guard) == 1
    policy_source = out/'project-policy-mutant.kotoba'; policy_source.write_bytes(linked_bytes.replace(policy_guard,b'lowered'))
    policy_image = out/'project-policy-mutant.elf'
    built = subprocess.run([str(compiler),'compile',str(policy_source),'--target',target,'--output',str(policy_image),'--format','static'],
                           cwd=out,env=env,capture_output=True,timeout=900)
    assert built.returncode == 0 and not built.stderr and policy_image.is_file(), (built.returncode,built.stderr[-1000:])
    policy_image.chmod(0o755)
    negative = subprocess.run([str(policy_image)],cwd=out,env=dict(PATH='/nonexistent',KEXE_ALLOW='37',KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608'),
                              capture_output=True,timeout=120)
    assert not negative.stderr and re.search(rb':status :ok :result 21(?:\s|})',negative.stdout), (negative.returncode,negative.stdout,negative.stderr)
    graph_source = out/'project-graph.kotoba'; graph_source.write_bytes(prefix+GRAPH_FIXTURE.read_bytes())
    graph_image = out/'project-graph.elf'
    built = subprocess.run([str(compiler),'compile',str(graph_source),'--target',target,'--output',str(graph_image),'--format','static'],
                           cwd=out,env=env,capture_output=True,timeout=900)
    assert built.returncode == 0 and not built.stderr and graph_image.is_file(), (built.returncode,built.stderr[-1000:])
    graph_image.chmod(0o755)
    graph_dir = out/'graph-input'; graph_dir.mkdir()
    entry = graph_dir/'app.kotoba'; dep = graph_dir/'dep.kotoba'; lock = graph_dir/'source.ksl'
    entry.write_text('(ns app (:require [dep :refer [dep]]) (:export [main]))\n(defn main [] :i64 (dep 41))\n')
    dep.write_text('(ns dep (:export [dep]))\n(defn dep [x :i64] :i64 (+ x 1))\n')
    def digest(data): return hashlib.sha256(data).hexdigest()
    lock_text = f'KSL1\nentry {entry}\nroot {graph_dir}\n' + ''.join(
        f'file {digest(p.read_bytes())} {p}\n' for p in sorted((entry,dep)))
    lock.write_text(lock_text); lock_hash = digest(lock_text.encode())
    graph_env = dict(PATH='/nonexistent',KEXE_ALLOW='35,37,38,39',KEXE_CAP_RESOURCES_35=str(graph_dir),
                     KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608')
    def run_graph(digest_value, mapped=False):
        roots = [] if mapped else ['--source-path',str(graph_dir)]
        return subprocess.run([str(graph_image),'compile',str(entry),*roots,
                               '--source-lock',str(lock),'--source-lock-sha256',digest_value],
                              cwd=out,env=graph_env,capture_output=True,timeout=120)
    result = run_graph(lock_hash)
    assert result.returncode == 0 and not result.stderr and re.search(rb':status :ok :result 0(?:\s|})',result.stdout), (result.returncode,result.stdout,result.stderr)
    match = re.search(rb'GRAPH-BEGIN\n([0-9a-f\n]+)GRAPH-END\n',result.stdout); assert match, result.stdout
    graph_wasm = bytes.fromhex(match.group(1).decode()); assert graph_wasm[:8] == b'\x00asm\x01\x00\x00\x00'
    graph_path = out/'project-graph.wasm'; graph_path.write_bytes(graph_wasm)
    print('WASM_PROJECT_GRAPH_HEX', graph_wasm.hex())
    order_guard = b'(not (xw-project-order-valid? L))'
    graph_bytes = graph_source.read_bytes(); assert graph_bytes.count(order_guard) == 1
    order_source = out/'graph-order-mutant.kotoba'; order_source.write_bytes(graph_bytes.replace(order_guard,b'false'))
    order_image = out/'graph-order-mutant.elf'
    built = subprocess.run([str(compiler),'compile',str(order_source),'--target',target,'--output',str(order_image),'--format','static'],
                           cwd=out,env=env,capture_output=True,timeout=900)
    assert built.returncode == 0 and not built.stderr and order_image.is_file(), (built.returncode,built.stderr[-1000:])
    order_image.chmod(0o755)
    bad = subprocess.run([str(order_image),'compile',str(entry),'--source-path',str(graph_dir),
                          '--source-lock',str(lock),'--source-lock-sha256',lock_hash],cwd=out,env=graph_env,capture_output=True,timeout=120)
    assert not bad.stderr and re.search(rb':status :ok :result 39(?:\s|})',bad.stdout) and b'GRAPH-BEGIN' not in bad.stdout, (bad.returncode,bad.stdout,bad.stderr)
    bad = run_graph('0'*64)
    assert not bad.stderr and re.search(rb':status :ok :result 31(?:\s|})',bad.stdout) and b'GRAPH-BEGIN' not in bad.stdout, (bad.returncode,bad.stdout,bad.stderr)
    mapped = f'KSL2\nentry {entry}\nmodule app {entry}\nmodule dep {dep}\n' + ''.join(
        f'file {digest(p.read_bytes())} {p}\n' for p in sorted((entry,dep)))
    lock.write_text(mapped)
    mapped_result = run_graph(digest(mapped.encode()), mapped=True)
    assert mapped_result.returncode == 0 and not mapped_result.stderr and re.search(rb':status :ok :result 0(?:\s|})',mapped_result.stdout), (mapped_result.returncode,mapped_result.stdout,mapped_result.stderr)
    match = re.search(rb'GRAPH-BEGIN\n([0-9a-f\n]+)GRAPH-END\n',mapped_result.stdout)
    assert match and bytes.fromhex(match.group(1).decode()) == graph_wasm
    lock.write_text(lock_text)
    dep.write_text(dep.read_text()+';; tampered\n')
    bad = run_graph(lock_hash)
    assert not bad.stderr and re.search(rb':status :ok :result 31(?:\s|})',bad.stdout) and b'GRAPH-BEGIN' not in bad.stdout, (bad.returncode,bad.stdout,bad.stderr)
    dep.write_text('(ns dep (:export [dep]))\n(defn dep [x :i64] :i64 (let [s (typed-cap-call :io/write :string :string "x")] x))\n')
    lock_text = f'KSL1\nentry {entry}\nroot {graph_dir}\n' + ''.join(
        f'file {digest(p.read_bytes())} {p}\n' for p in sorted((entry,dep)))
    lock.write_text(lock_text)
    bad = run_graph(digest(lock_text.encode()))
    assert not bad.stderr and re.search(rb':status :ok :result 33(?:\s|})',bad.stdout) and b'GRAPH-BEGIN' not in bad.stdout, (bad.returncode,bad.stdout,bad.stderr)
    dep.write_text('(ns dep (:export [dep]))\n(defn dep [x :i64] :i64 (let [s (keyword-name :cat)] x))\n')
    lock_text = f'KSL1\nentry {entry}\nroot {graph_dir}\n' + ''.join(
        f'file {digest(p.read_bytes())} {p}\n' for p in sorted((entry,dep)))
    lock.write_text(lock_text)
    bad = run_graph(digest(lock_text.encode()))
    assert not bad.stderr and re.search(rb':status :ok :result 33(?:\s|})',bad.stdout) and b'GRAPH-BEGIN' not in bad.stdout, (bad.returncode,bad.stdout,bad.stderr)
    runtime_source = out/'project-runtime.kotoba'; runtime_source.write_bytes(prefix+RUNTIME_FIXTURE.read_bytes())
    runtime_image = out/'project-runtime.elf'
    built = subprocess.run([str(compiler),'compile',str(runtime_source),'--target',target,'--output',str(runtime_image),'--format','static'],
                           cwd=out,env=env,capture_output=True,timeout=900)
    assert built.returncode == 0 and not built.stderr and runtime_image.is_file(), (built.returncode,built.stderr[-1000:])
    runtime_image.chmod(0o755)
    runtime_result = subprocess.run([str(runtime_image)],cwd=out,env=dict(PATH='/nonexistent',KEXE_ALLOW='-',KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608'),
                                    capture_output=True,timeout=300)
    assert runtime_result.returncode == 0 and not runtime_result.stderr and re.search(rb':status :ok :result 0(?:\s|})',runtime_result.stdout), (runtime_result.returncode,runtime_result.stdout,runtime_result.stderr)
    runtime_guard = b'(not (xw-project-runtime-map-valid? R M))'
    runtime_bytes = runtime_source.read_bytes(); assert runtime_bytes.count(runtime_guard) == 1
    runtime_mutant_source = out/'runtime-map-mutant.kotoba'; runtime_mutant_source.write_bytes(runtime_bytes.replace(runtime_guard,b'false'))
    runtime_mutant = out/'runtime-map-mutant.elf'
    built = subprocess.run([str(compiler),'compile',str(runtime_mutant_source),'--target',target,'--output',str(runtime_mutant),'--format','static'],
                           cwd=out,env=env,capture_output=True,timeout=900)
    assert built.returncode == 0 and not built.stderr and runtime_mutant.is_file(), (built.returncode,built.stderr[-1000:])
    runtime_mutant.chmod(0o755)
    negative = subprocess.run([str(runtime_mutant)],cwd=out,env=dict(PATH='/nonexistent',KEXE_ALLOW='-',KEXE_STRUCTURED_REPORT='1',KEXE_STACK_BYTES='8388608'),
                              capture_output=True,timeout=300)
    assert not negative.stderr and re.search(rb':status :ok :result 4(?:\s|})',negative.stdout), (negative.returncode,negative.stdout,negative.stderr)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {'status':'PASS_WASM_PROJECT_IFACE', 'target':target, 'compilerSha256':sha(compiler),
               'fixtureSha256':sha(FIXTURE),'sourceSha256':sha(source),'imageSha256':sha(image),
               'negativeControlSourceSha256':sha(mutant_source),'negativeControlImageSha256':sha(mutant),
               'stubFixtureSha256':sha(STUB_FIXTURE),'stubSourceSha256':sha(stub_source),'stubImageSha256':sha(stub_image),
               'stubNegativeSourceSha256':sha(stub_mutant_source),'stubNegativeImageSha256':sha(stub_mutant),
               'archiveNegativeSourceSha256':sha(archive_source),'archiveNegativeImageSha256':sha(archive_image),
               'payloadNegativeControls':payload_receipts,
               'poolNegativeSourceSha256':sha(pool_source),'poolNegativeImageSha256':sha(pool_image),
               'projectModuleSha256':sha(wasm_path), 'projectModuleNegativeSha256':sha(module_mutant),
               'projectLinkedSha256':sha(linked_path), 'policyNegativeSha256':sha(policy_image),
               'projectGraphSha256':sha(graph_path), 'graphOrderNegativeSha256':sha(order_image),
               'runtimeMapFixtureSha256':sha(RUNTIME_FIXTURE), 'runtimeMapImageSha256':sha(runtime_image), 'runtimeMapNegativeSha256':sha(runtime_mutant),
               'limitations':['archive module fixture only; no project driver or Wasm execution in this gate']}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'],target)

if __name__ == '__main__': main()
