from pathlib import Path
import hashlib
def sx(x, n):
    return x - (1 << n) if x & 1 << n - 1 else x

def ref(w, p):
    if w & 2080374784 == 335544320:
        return ('BL' if w & 2147483648 else 'B', p + 4 * sx(w & 67108863, 26), 4227858432)
    if w & 4278190096 == 1409286144:
        return ('BC', p + 4 * sx(w >> 5 & 524287, 19), 4278190111)
    if w & 2113929216 == 872415232:
        return ('CB', p + 4 * sx(w >> 5 & 524287, 19), 4278190111)
    if w & 2113929216 == 905969664:
        return ('TB', p + 4 * sx(w >> 5 & 16383, 14), 4294443039)
    if w & 989855744 == 402653184:
        return ('LIT', p + 4 * sx(w >> 5 & 524287, 19), 4278190111)
    if w & 2667577344 == 268435456:
        return ('ADR', p + sx((w >> 5 & 524287) << 2 | w >> 29 & 3, 21), 2667577375)
    assert w & 2667577344 != 2415919104, ('UNKNOWN_ADRP', p)
    return None

def payload(a):
    b = Path(a['native']['path']).read_bytes()
    h, v = Path(a['container']['path']).read_bytes().split(b'\n\n', 1)
    ls = h.decode().splitlines()
    m, n, c = ls[0].split()
    assert m == 'KSEED1' and int(n) == len(b) and (int(c) == len(ls) - 1) and (v == b)
    ex = {}
    for row in ls[1:]:
        name, p, k = row.split()
        assert name not in ex
        ex[name] = [int(p), int(k)]
        assert int(p) % 4 == 0 and 0 <= int(p) < len(b)
    if 'exports' in a:
        assert ex == {k: list(v) for k, v in a['exports'].items()}
    for kind, data in [('native', b), ('container', Path(a['container']['path']).read_bytes())]:
        if 'sha256' in a[kind]:
            assert hashlib.sha256(data).hexdigest() == a[kind]['sha256']
    return (b, ex)

def source_pool(source):
    import importlib.util
    p = Path(__file__).with_name('source-pool.py')
    spec = importlib.util.spec_from_file_location('current_source_owned_pool', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.source_pool(source)
