# compare.py <host.kexe> <guest.edn>: SAME when :code is equal and :exports has the same entries (order ignored: the
# host prints a map of more than eight entries in hash order), else CODE-DIFF / EXPORTS-DIFF.
import re, sys

def part(text, key, op, cl):
    i = text.find(key + ' ' + op)
    if i < 0:
        return None
    j = i + len(key) + 1
    depth = 0
    for n, c in enumerate(text[j:], j):
        if c == op:
            depth += 1
        elif c == cl:
            depth -= 1
            if depth == 0:
                return text[j:n + 1]

def entries(exports):
    return sorted(re.findall(r'([^\s{},]+) (\{[^}]*\})', exports or ''))

host, guest = open(sys.argv[1]).read(), open(sys.argv[2]).read()
if part(host, ':code', '[', ']') != part(guest, ':code', '[', ']'):
    print('CODE-DIFF')
elif entries(part(host, ':exports', '{', '}')) != entries(part(guest, ':exports', '{', '}')):
    print('EXPORTS-DIFF')
else:
    print('SAME')
