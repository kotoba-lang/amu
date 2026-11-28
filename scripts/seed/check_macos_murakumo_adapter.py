#!/usr/bin/env python3
"""Stage the native adapter and observe an isolated IPv4 QA fixture on Darwin arm64."""
import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import platform
import secrets
import socket
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'seed/tests/llm-v1-darwin-murakumo.kotoba'
MODEL = 'inkling-2-mini-gyomu-qa'
SCHEMA = '768859620bef185169b794b3ca1dbabb0de8e96186c61e698e61418afd27a034'
LOOKUP = 'amu: synthetic QA credential lookup\n'
TEXT = '確認 🐙\n'
SYSTEM = 'system "quote" \\ and\n日本語'
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return {'bytes': path.stat().st_size, 'sha256': sha(path)}


def result():
    return {'model': MODEL, 'object': 'chat.completion', 'id': 'synthetic', 'created': 1,
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': TEXT},
                         'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 7, 'completion_tokens': 1, 'total_tokens': 8}}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        prompt = request.get('messages', [{}, {}])[1].get('content')
        authentic = self.headers.get_all('Authorization') == [f'Bearer {self.server.bearer}']
        expected = {'model': MODEL, 'stream': False, 'max_tokens': 42, 'temperature': 0.125,
                    'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt}]}
        valid = (self.path == '/v1/chat/completions' and self.request_version == 'HTTP/1.1' and
                 self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}' and
                 self.headers.get('Content-Type') == 'application/json' and
                 self.headers.get('Accept') == 'application/json' and
                 self.headers.get('Connection') == 'close' and request == expected and
                 request.get('stream') is False and isinstance(prompt, str))
        self.server.observations.append((authentic, valid))
        self.close_connection = True
        if prompt == 'backend-stopped' and authentic and valid:
            self.connection.shutdown(socket.SHUT_RDWR)
            return
        if prompt == 'longer-than-ordinary':
            time.sleep(6)
        elif prompt == 'premature-deadline':
            time.sleep(4)
        body = result()
        status = 200
        if not authentic:
            status, body = 401, {'error': 'unauthorized'}
        elif not valid:
            status, body = 400, {'error': 'unexpected_fixture_request'}
        elif prompt == 'provider-error':
            status, body = 502, {'error': 'qa_backend_unavailable'}
        elif prompt == 'redirect':
            status, body = 302, {'error': 'redirect_fixture'}
        elif prompt == 'missing-usage':
            del body['usage']
        elif prompt == 'bad-usage':
            body['usage']['completion_tokens'] = 43
        elif prompt == 'duplicate-usage':
            body['usage']['prompt_tokens'] = -1
        elif prompt == 'wrong-response-model':
            body['model'] = 'unregistered'
        elif prompt == 'tool-response':
            body['choices'][0]['message']['tool_calls'] = [{'id': 'unavailable'}]
        elif prompt == 'oversize-text':
            body['choices'][0]['message']['content'] = 'a' * 65537
        elif prompt == 'oversize-body':
            body['choices'][0]['message']['content'] = 'a' * 524288
        raw = json.dumps(body, ensure_ascii=True, separators=(',', ':')).encode()
        if prompt == 'duplicate-usage':
            raw = raw.replace(b'"prompt_tokens":-1', b'"prompt_tokens":7,"prompt_tokens":-1')
        elif prompt == 'malformed-json':
            raw = b'{"model":'
        elif prompt == 'invalid-utf8':
            raw = raw.replace(b'"synthetic"', b'"\xff"')
        chunked = prompt in ('fixture-prompt', 'truncated-chunks')
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'text/event-stream' if prompt == 'stream-response' else 'application/json')
            self.send_header('Connection', 'close')
            if prompt == 'redirect':
                self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/forbidden')
            if chunked:
                self.send_header('Transfer-Encoding', 'chunked')
            else:
                self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            if chunked:
                for piece in (raw[:23], raw[23:]):
                    self.wfile.write(f'{len(piece):x}\r\n'.encode() + piece + b'\r\n')
                if prompt != 'truncated-chunks':
                    self.wfile.write(b'0\r\n\r\n')
            else:
                self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            if prompt not in ('premature-deadline', 'oversize-body'):
                raise


def run(launcher, *args, auth=None):
    """Remap an anonymous pipe only in the child. No bearer enters disk or argv."""
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        actions = [(os.POSIX_SPAWN_DUP2, stdout.fileno(), 1),
                   (os.POSIX_SPAWN_DUP2, stderr.fileno(), 2)]
        if auth is not None:
            read_fd, write_fd = os.pipe()
            try:
                os.write(write_fd, auth)
            finally:
                os.close(write_fd)
            actions += [(os.POSIX_SPAWN_DUP2, read_fd, 4)]
        try:
            pid = os.posix_spawn(str(launcher), [str(launcher), *map(str, args)], ENV, file_actions=actions)
        finally:
            if auth is not None:
                os.close(read_fd)
        end = time.monotonic() + 22
        while True:
            done, status = os.waitpid(pid, os.WNOHANG)
            if done:
                break
            if time.monotonic() >= end:
                os.kill(pid, 9)
                os.waitpid(pid, 0)
                raise AssertionError('native test process exceeded the fixture harness deadline')
            time.sleep(0.02)
        stdout.seek(0)
        stderr.seek(0)
        return os.waitstatus_to_exitcode(status), stdout.read().decode(), stderr.read().decode()


def grant(image, port, seconds=12, tokens=42):
    return (f'KLG1\nartifact={sha(image)}\nwire=11\nschema={SCHEMA}\nprofile=amu-program-llm-v1\n'
            f'provider=murakumo-qa-v1\nendpoint=http://127.0.0.1:{port}\nmodel=:{MODEL}\n'
            f'seconds={seconds}\ntokens={tokens}\n')


def main(output):
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    output.mkdir(mode=0o700)
    receipt = []
    artifacts = []
    bearer = secrets.token_hex(32)
    listener = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    listener.bearer = bearer
    listener.observations = []
    port = listener.server_port
    loop = threading.Thread(target=listener.serve_forever, daemon=True)
    loop.start()
    source = FIXTURE.read_text()
    module_source = '(ns llm.qa-budget (:export [tokens]))\n(defn tokens [] :i64 42)\n'
    stage = output / 'stage'

    def guest(name, prompt='fixture-prompt', model=MODEL, budget=42, locked=True):
        work = output / name
        work.mkdir()
        entry, module, lock, image = (work / p for p in ('entry.kotoba', 'tokens.kotoba', 'source.ksl', 'guest.macho'))
        program = source.replace('"fixture-prompt"', json.dumps(prompt)).replace(':' + MODEL, ':' + model)
        cmd = ['compile', entry]
        if locked:
            entry.write_text(program)
            module.write_text(module_source.replace('42', str(budget)))
            lock.write_text(f'KSL2\nentry {entry}\nmodule llm.qa-budget {module}\nmodule llm.qa-fixture {entry}\n' +
                            ''.join(f'file {sha(p)} {p}\n' for p in (entry, module)))
            cmd += ['--source-lock', lock]
        else:
            entry.write_text(program.replace('  (:require [llm.qa-budget :as budget])\n', '').replace('(budget/tokens)', str(budget)))
        rc, _, err = run(cli, *cmd, '--runtime-profile', 'amu-program-llm-v1', '-o', image)
        assert rc == 0 and not err, f'{name}: native compile failed: {err}'
        subprocess.run(['/usr/bin/codesign', '--verify', '--strict', image], check=True)
        artifacts.append({'name': name, 'guest': pin(image), 'entry': pin(entry),
                          **({'module': pin(module)} if locked else {})})
        return image

    def case(name, image, *, token=None, patch=None, launcher=None, seconds=12, tokens=42,
             exit=0, stdout='', calls=0, lookups=0, requests=0, diagnostic='', authenticated=True):
        signed_grant = output / f'{name}.grant'
        text = grant(image, port, seconds, tokens)
        if patch:
            before, after = patch
            assert text.count(before) == 1
            text = text.replace(before, after)
        signed_grant.write_text(text)
        n = len(listener.observations)
        elapsed = time.monotonic()
        rc, out, err = run(launcher or cli, 'run-llm', image, '--grant', signed_grant, auth=token)
        elapsed = time.monotonic() - elapsed
        observations = listener.observations[n:]
        assert len(observations) == requests and all(a == authenticated and v for a, v in observations), f'{name}: HTTP count or request shape'
        if exit is None:
            # Darwin can report refusal immediately or wait until the timer
            # when a non-listening bound socket reserves the stopped port.
            assert (rc == 0 and out == '404\n') or (rc == 124 and not out and 'ETIME' in err), f'{name}: expected bounded refusal'
        else:
            assert rc == exit and out == stdout and diagnostic in err, f'{name}: exit {rc}, stdout {out!r}, stderr {err!r}'
        assert err.count(LOOKUP) == lookups and err.count(f'amu: wire11 provider-calls={calls}\n') == 1, f'{name}: wrong invocation counts'
        receipt.append({'case': name, 'exit': rc, 'stdout': out, 'providerCalls': calls,
                        'credentialLookups': lookups, 'httpRequests': requests,
                        'elapsedMilliseconds': round(elapsed * 1000)})
        print(f'PASS {name}', flush=True)
        return elapsed

    try:
        subprocess.run(['basilisp', 'run', '-p', 'scripts/seed',
                        'scripts/seed/stage-macos-murakumo-fixture.cljc', '--', stage, str(port)],
                       cwd=ROOT, check=True, timeout=120)
        cli = stage / 'amu-cli.macho'
        off = stage / 'unregistered.macho'
        token = bearer.encode()
        success = guest('completion')
        assert token not in success.read_bytes() and token not in cli.read_bytes()
        case('no-registration', success, launcher=off, token=token, exit=69, diagnostic='ELLMGRANT')
        case('completion-chunked', success, token=token, stdout='101\n', calls=1, lookups=1, requests=1)
        case('missing-authorization', success, exit=69, lookups=1, diagnostic='ELLMBROKER')
        case('malformed-authorization', success, token=b'G' * 64, exit=69, lookups=1, diagnostic='ELLMBROKER')
        other = (b'1' if token == b'0' * 64 else b'0') * 64
        case('listener-refuses-wrong-bearer', success, token=other, stdout='203\n', calls=1,
             lookups=1, requests=1, authenticated=False)
        case('budget-refused', success, token=token, tokens=41, exit=69, diagnostic='ELLMBROKER')
        for name, before, after in (
            ('alternate-port', f'127.0.0.1:{port}', '127.0.0.1:1'),
            ('alternate-address', '127.0.0.1:', 'localhost:'),
            ('override-path', f'127.0.0.1:{port}', f'127.0.0.1:{port}/alternate'),
            ('alternate-provider', 'murakumo-qa-v1', 'other-provider'),
            ('alternate-grant-model', MODEL, 'unregistered'),
            ('wrong-artifact', sha(success), '0' * 64),
            ('wrong-schema', SCHEMA, '0' * 64),
            ('excess-deadline', 'seconds=12', 'seconds=91'),
        ):
            case(name, success, token=token, patch=(before, after), exit=69, diagnostic='ELLMGRANT')
        case('wrong-request-model', guest('wrong-request-model', model='unknown-model'), token=token, exit=69, diagnostic='ELLMBROKER')
        case('invalid-request-tokens', guest('invalid-request-tokens', budget=0), token=token, exit=69, diagnostic='ELLMBROKER')
        case('ksl1-refused', guest('ksl1', locked=False), token=token, exit=69, diagnostic='requires a locked project')
        for name, printed in (
            ('provider-error', '202\n'), ('redirect', '203\n'), ('missing-usage', '303\n'),
            ('bad-usage', '303\n'), ('duplicate-usage', '303\n'), ('wrong-response-model', '303\n'),
            ('tool-response', '303\n'), ('oversize-text', '303\n'), ('oversize-body', '303\n'), ('malformed-json', '303\n'),
            ('invalid-utf8', '303\n'), ('truncated-chunks', '303\n'), ('stream-response', '303\n'),
        ):
            case(name, guest(name, prompt=name), token=token, stdout=printed, calls=1, lookups=1, requests=1)
        slow = case('longer-than-ordinary', guest('slow', prompt='longer-than-ordinary'), token=token,
                    seconds=90, stdout='101\n', calls=1, lookups=1, requests=1)
        assert slow > 5, 'scoped deadline did not exceed the ordinary five seconds'
        short = case('premature-deadline', guest('deadline', prompt='premature-deadline'), token=token,
                     seconds=1, exit=124, diagnostic='ETIME', calls=1, lookups=1, requests=1)
        assert short < 4, 'native deadline waited for the slow HTTP fixture'
        case('after-timeout', success, token=token, stdout='101\n', calls=1, lookups=1, requests=1)
        case('backend-stopped', guest('stopped', prompt='backend-stopped'), token=token,
             stdout='404\n', calls=1, lookups=1, requests=1)
    finally:
        listener.shutdown()
        listener.server_close()
        loop.join()
    # Reserve the same test port without listening. A bind race fails the
    # test before attempting a connection to an endpoint it does not own.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stopped:
        stopped.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        stopped.bind(('127.0.0.1', port))
        case('listener-stopped', success, token=token, seconds=1, exit=None, calls=1, lookups=1)
    report = {'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'fixtureSource': pin(FIXTURE), 'launcher': pin(off), 'fixtureLauncher': pin(cli),
              'packager': pin(stage / 'kotoba-packager-root.macho'), 'compiler': pin(stage / 'amu-full-root.macho'),
              'provider': 'murakumo-qa-v1', 'scope': 'synthetic-ipv4-loopback', 'checks': receipt,
              'artifacts': artifacts}
    (output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS_NATIVE_DARWIN_MURAKUMO_FIXTURE')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output.resolve())
