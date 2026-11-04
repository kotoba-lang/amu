#!/usr/bin/env python3
"""Build the diagnostic attribute emitter and preserve its exact output.

The emitted bytes are not a process boundary or a resource qualification.
Python stages and observes, while the pinned native compiler builds the source.
"""
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/seed' / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(compiler, packager, output, artifact_dir=None):
    gate = load('mac_attr_native', 'check-aiueos-user-macos-native.py')
    fixture = load('mac_attr_scope', 'check-macos-arena-scope.py')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    source_path = ROOT / 'seed/darwin-spawn-attribute.kotoba'
    fixture_path = ROOT / 'seed/tests/awai152-darwin-spawn/attribute-emitter.kotoba'
    source = source_path.read_text()
    declaration = '(ns amu.darwin-spawn-attribute (:export [darwin-spawn-attribute]))'
    if source.count(declaration) != 1:
        raise ValueError('unexpected attribute namespace')
    source = source.replace(declaration, '(ns darwin-attribute-emitter (:export [main]))')
    emitter = fixture.build(gate, compiler, packager, output, 'attribute-emitter',
                            source + '\n' + fixture_path.read_text())
    gate.native_run(emitter, output, timeout=120)
    result = output / 'attributes.bin'
    data = result.read_bytes()
    expected = bytearray(248)
    expected[0] = 128
    expected[56] = 1
    expected[64:66] = bytes((12, 128))
    expected[68:72] = b'\xff' * 4
    expected[72:76] = (64).to_bytes(4, 'little')
    expected[76:80] = (64).to_bytes(4, 'little')
    expected[112:128] = b'\xff' * 16
    if data != expected:
        raise ValueError('native attribute bytes differ from expected profile')
    paths = {'source': source_path, 'fixture': fixture_path, 'compiler': compiler,
             'packager': packager, 'emitter': emitter, 'attribute': result}
    pins = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    if artifact_dir is not None:
        artifact_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
        shutil.copyfile(result, artifact_dir / 'attributes.bin')
        (artifact_dir / 'evidence.json').write_text(json.dumps({
            'schema': 'amu.darwin-spawn-attribute-fixture.v1', 'sha256': pins,
            'scope': 'native 64 MiB attribute bytes only; no spawn or resource qualification'
        }, indent=2) + '\n')
    print('PASS_MAC_SPAWN_ATTRIBUTE_BYTES', json.dumps(pins, sort_keys=True), flush=True)
