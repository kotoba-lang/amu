# compare_artifact.py <host.kexe> <guest.kexe>: the sealed artifacts compared semantically, never by text (the host
# prints a map of more than eight entries in hash order). The :sha256 seals first (they cover the canonical bytes);
# then the artifact maps key by key. Then the two .provenance.edn records the same way.
# Prints one line: "<seal> <keys> <prov> <prov-keys>": seal/prov is SAME or DIFF (prov MISSING when a side wrote
# none), keys a comma list of the differing top-level keys other than :sha256 ("-" when none).
# Values are compared with their EDN types: a list is not a vector, true is not 1, a set and a map are unordered.
import sys


def parse(text):
    i, n = 0, len(text)

    def ws():
        nonlocal i
        while i < n:
            c = text[i]
            if c in ' \t\r\n,':
                i += 1
            elif c == ';':
                while i < n and text[i] != '\n':
                    i += 1
            else:
                break

    def token():
        nonlocal i
        j = i
        while i < n and text[i] not in ' \t\r\n,()[]{}"':
            i += 1
        return text[j:i]

    def seq(close):
        nonlocal i
        out = []
        while True:
            ws()
            if text[i] == close:
                i += 1
                return out
            out.append(val())

    def mapping(items, ns=None):
        if len(items) % 2:
            raise ValueError('odd map')
        out = {}
        for k, v in zip(items[::2], items[1::2]):
            # #:ns{..}: a keyword key without a namespace takes ns; :_/k means no namespace
            if ns is not None and k[0] == 'k':
                if k[1].startswith(':_/'):
                    k = ('k', ':' + k[1][3:])
                elif '/' not in k[1]:
                    k = ('k', ':' + ns + '/' + k[1][1:])
            out[k] = v
        return ('m', frozenset(out.items()))

    def val():
        nonlocal i
        ws()
        c = text[i]
        if c == '{':
            i += 1
            return mapping(seq('}'))
        if c == '[':
            i += 1
            return ('v', tuple(seq(']')))
        if c == '(':
            i += 1
            return ('l', tuple(seq(')')))
        if c == '"':
            i += 1
            buf = []
            while text[i] != '"':
                if text[i] == '\\':
                    e = text[i + 1]
                    if e == 'u':
                        buf.append(chr(int(text[i + 2:i + 6], 16)))
                        i += 6
                        continue
                    buf.append({'n': '\n', 't': '\t', 'r': '\r', 'b': '\b', 'f': '\f'}.get(e, e))
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            i += 1
            return ('s', ''.join(buf))
        if c == '#':
            if text[i + 1] == '{':
                i += 2
                return ('set', frozenset(seq('}')))
            if text[i + 1] == ':':
                i += 2
                ns = token()
                ws()
                i += 1
                return mapping(seq('}'), ns)
            raise ValueError('tag at %d' % i)
        t = token()
        if t == 'nil':
            return ('nil',)
        if t in ('true', 'false'):
            return ('b', t == 'true')
        if t.startswith(':'):
            return ('k', t)
        try:
            return ('i', int(t))
        except ValueError:
            return ('y', t)

    return val()


def top(v):
    return dict(v[1]) if v[0] == 'm' else {}


def compare(hp, gp):
    h, g = top(parse(open(hp).read())), top(parse(open(gp).read()))
    sk = ('k', ':sha256')
    seal = 'SAME' if sk in h and h.get(sk) == g.get(sk) else 'DIFF'
    keys = sorted(k[1] for k in set(h) | set(g) if k != sk and h.get(k, 'absent') != g.get(k, 'absent'))
    return seal, keys


if __name__ == '__main__':
    hk, gk = sys.argv[1], sys.argv[2]
    seal, keys = compare(hk, gk)
    try:
        pseal, pkeys = compare(hk + '.provenance.edn', gk + '.provenance.edn')
    except FileNotFoundError:
        pseal, pkeys = 'MISSING', []
    print(seal, ','.join(keys) or '-', pseal, ','.join(pkeys) or '-')
