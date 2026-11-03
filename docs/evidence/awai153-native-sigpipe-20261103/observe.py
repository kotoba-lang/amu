# Test-only peer; strict.macho and unprotected.macho are task-owned images.
import pathlib, resource, signal, socket, struct, subprocess, threading
p = pathlib.Path('/private/tmp/awai153-sigpipe-native')
def limit():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
for mode in ('strict', 'unprotected'):
    for i in range(3):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(3)
        port = listener.getsockname()[1]
        def serve():
            with listener:
                conn, _ = listener.accept()
                with conn:
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
        peer = threading.Thread(target=serve)
        peer.start()
        result = subprocess.run([str(p / (mode + '.macho'))], input=port.to_bytes(2, 'big'),
                                capture_output=True, timeout=5, preexec_fn=limit)
        peer.join(4)
        assert not peer.is_alive()
        print(mode, i, 'exit', result.returncode, flush=True)
        assert result.returncode == (0 if mode == 'strict' else -13)
