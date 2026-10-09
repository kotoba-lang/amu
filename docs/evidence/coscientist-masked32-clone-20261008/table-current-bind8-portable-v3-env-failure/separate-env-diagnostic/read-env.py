from pathlib import Path
import os, json, hashlib
D = Path(__file__).resolve().parent
P = Path('/Users/junkawasaki/github/workspaces/codex/crc-table-decision-collapse-native-component-v3-portable-draft-20261008/preregistration.json')
expected = json.loads(P.read_bytes())['environment']
actual = dict(os.environ)
assert len(actual) <= 64
report = {
    'status': 'FIXED_INTERPRETER_ENVIRONMENT_DIAGNOSTIC_ONLY',
    'addedKeyNames': sorted(set(actual) - set(expected)),
    'missingKeyNames': sorted(set(expected) - set(actual)),
    'changedExpectedKeyNames': sorted(k for k in expected if actual.get(k) != expected[k]),
    'expectedKeys': len(expected), 'actualKeys': len(actual),
    'nativeCalls': 0, 'setters': 0, 'processAPIReads': 0,
    'preregistrationSHA256': hashlib.sha256(P.read_bytes()).hexdigest(),
}
assert not (D / 'result.json').exists()
(D / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
