# Test-only loopback peer and short-lived subprocesses; no production service.
import resource, socket, struct, subprocess, threading
worker = '''import socket,signal,sys
signal.signal(signal.SIGPIPE,signal.SIG_DFL)
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
if sys.argv[2]=="protected":s.setsockopt(socket.SOL_SOCKET,0x1022,1)
s.settimeout(2);s.connect(("127.0.0.1",int(sys.argv[1])))
try:s.recv(1)
except OSError:pass
try:s.sendall(b"x");print("unexpected-success",flush=True);sys.exit(3)
except OSError as e:print("errno",e.errno,flush=True);sys.exit(0 if e.errno==32 else 4)
'''
def limit():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
for mode in ('default', 'protected'):
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
        result = subprocess.run(['/usr/bin/python3', '-c', worker, str(port), mode],
                                capture_output=True, text=True, timeout=5, preexec_fn=limit)
        peer.join(4)
        assert not peer.is_alive()
        print(mode, i, result.returncode, result.stdout.strip(), flush=True)
        assert (result.returncode == -13 if mode == 'default'
                else result.returncode == 0 and result.stdout.strip() == 'errno 32')
