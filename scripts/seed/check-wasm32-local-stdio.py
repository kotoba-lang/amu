#!/usr/bin/env python3
"""Observe local Worker stdin/stdout with a selfhost-compiled Wasm probe."""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wasm', required=True, type=Path)
    parser.add_argument('--output-probe', required=True, type=Path)
    parser.add_argument('--read-probe', required=True, type=Path)
    parser.add_argument('--broker-probe', required=True, type=Path)
    parser.add_argument('--all-probe', required=True, type=Path)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    host = ROOT / 'runtime/wasm32-browser-static-host.js'
    page = ROOT / 'runtime/wasm32-browser-local-stdio-test.html'
    queue = ROOT / 'runtime/wasm32-browser-local-stdio.js'
    for source in (host, page, queue):
        shutil.copyfile(source, out / source.name)
    data = args.wasm.read_bytes()
    output_data = args.output_probe.read_bytes()
    read_data = args.read_probe.read_bytes()
    broker_data = args.broker_probe.read_bytes()
    all_data = args.all_probe.read_bytes()
    assert data[:8] == b'\0asm\x01\0\0\0'
    assert output_data[:8] == read_data[:8] == broker_data[:8] == all_data[:8] == b'\0asm\x01\0\0\0'
    (out / 'runs.js').write_text('window.KOTOBA_WASM=' + json.dumps(base64.b64encode(data).decode()) + ';\n' +
                                 'window.KOTOBA_OUTPUT_WASM=' + json.dumps(base64.b64encode(output_data).decode()) + ';\n' +
                                 'window.KOTOBA_READ_WASM=' + json.dumps(base64.b64encode(read_data).decode()) + ';\n' +
                                 'window.KOTOBA_BROKER_WASM=' + json.dumps(base64.b64encode(broker_data).decode()) + ';\n' +
                                 'window.KOTOBA_ALL_WASM=' + json.dumps(base64.b64encode(all_data).decode()) + ';\n')
    spec = importlib.util.spec_from_file_location('wasm_check', ROOT / 'scripts/seed/check-wasm32-browser.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    browser = module.find_browser(args.browser)
    assert browser
    profile = out / 'profile'
    profile.mkdir()
    pipe = module.Pipe(browser, profile)
    try:
        version = pipe.call('Browser.getVersion')
        target = pipe.call('Target.createTarget', {'url': (out / page.name).as_uri()})['targetId']
        session = pipe.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
        deadline = time.monotonic() + 150
        result = None
        while time.monotonic() < deadline:
            value = pipe.call('Runtime.evaluate', {'expression': "document.title === 'kotoba-done' ? document.getElementById('results').textContent : null", 'returnByValue': True}, session)
            if value.get('result', {}).get('value') is not None:
                result = json.loads(value['result']['value'])
                break
            time.sleep(0.2)
        assert result is not None and result.get('jspi') is True, result
    finally:
        pipe.close()
    (out / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    rows = {row['name']: row for row in result['results']}
    assert set(rows) == {'success', 'queued', 'queue-abort', 'queue-read-all', 'denied', 'not-local', 'no-jspi', 'conflict', 'oversized', 'lone-surrogate', 'read-refused', 'bounded-output', 'bounded-read-log', 'broker-isolation'}
    success = rows['success']
    assert success['exit'] == 0 and ':status :ok :result 42' in success['report'], success
    assert success['output'] == 'READY\nDONE\n', success
    assert [event['kind'] for event in success['events']] == ['output', 'read', 'read', 'read', 'output', 'output'], success
    assert success['events'][0]['text'] == 'READY\n' and success['events'][4]['text'] == 'DONE\n'
    assert success['events'][5]['text'].startswith('{:status :ok :result 42 ')
    assert [event['request'] for event in success['events'] if event['kind'] == 'read'] == ['1', '1', '1']
    queued = rows['queued']
    assert queued['exit'] == 0 and ':status :ok :result 42' in queued['report']
    assert queued['capacityRefused'] and queued['invalidUnicodeRefused']
    assert [event['kind'] for event in queued['events']] == ['output', 'read', 'read', 'read', 'output', 'output']
    assert ''.join(item['text'] for item in queued['queueOutput'] if item['fd'] == 1) == queued['stdout']
    assert rows['queue-abort']['exit'] == 120 and ':status :trap' in rows['queue-abort']['report']
    assert rows['queue-read-all']['exit'] == 0 and ':status :ok :result 42' in rows['queue-read-all']['report']
    assert [event['request'] for event in rows['queue-read-all']['events'] if event['kind'] == 'read'] == ['']
    assert not any(event['kind'] == 'broker' for name, row in rows.items() if name != 'broker-isolation' for event in row['events'])
    for name in ('denied', 'not-local', 'no-jspi', 'oversized', 'lone-surrogate', 'read-refused'):
        assert rows[name]['exit'] == 120 and ':status :trap' in (rows[name]['report'] or ''), rows[name]
    assert not any(event['kind'] == 'read' for name in ('denied', 'not-local', 'no-jspi') for event in rows[name]['events'])
    assert rows['conflict']['exit'] == 120 and 'both local stdin and broker-bound' in rows['conflict']['wasmTrap']
    assert all(sum(event['kind'] == 'read' for event in rows[name]['events']) == 1 for name in ('oversized', 'lone-surrogate', 'read-refused'))
    large = rows['bounded-output']
    assert large['exit'] == 0 and ':status :ok :result 42' in large['report'] and large['stdoutTruncated'] is True
    assert len(large['stdout'].encode('utf-8')) <= 65536 and sum(len(event['text']) for event in large['events'] if event['kind'] == 'output') > 70000
    many = rows['bounded-read-log']
    assert many['exit'] == 0 and ':status :ok :result 42' in many['report'] and many['localReadLogTruncated'] is True
    assert sum(event['kind'] == 'read' for event in many['events']) == 257 and len(many['capLog']) == 256
    broker = rows['broker-isolation']
    assert broker['exit'] == 0 and ':status :ok :result 6' in broker['report'] and broker['output'] == '200\nok\n'
    assert broker['events'] == [{'kind': 'broker', 'wire': 45}]
    receipt = {'status': 'PASS_LOCAL_STDIO_OFFLINE', 'browser': version.get('product'),
               'wasmSha256': hashlib.sha256(data).hexdigest(),
               'outputProbeSha256': hashlib.sha256(output_data).hexdigest(),
               'readProbeSha256': hashlib.sha256(read_data).hexdigest(),
               'brokerProbeSha256': hashlib.sha256(broker_data).hexdigest(),
               'allProbeSha256': hashlib.sha256(all_data).hexdigest(),
               'hostSha256': hashlib.sha256(host.read_bytes()).hexdigest(),
               'pageSha256': hashlib.sha256(page.read_bytes()).hexdigest(),
               'queueSha256': hashlib.sha256(queue.read_bytes()).hexdigest(),
               'network': 'CSP connect-src none', 'realUserQualified': False,
               'browserProjectQualified': False, 'brokerReviewQualified': False}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'], receipt['browser'])


if __name__ == '__main__':
    main()
