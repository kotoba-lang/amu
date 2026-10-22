#!/usr/bin/env python3
"""scripts/seed/kexe_code.py <in.kexe> <symbol> <out.bin> -- BOOTSTRAP-TOOL: the raw :code bytes of a stage-0
:kotoba.kexe/v1 and the offset of <symbol> (printed as {:ok true :offset N}), i.e. what `amu-native extract-native`
writes for the seed (measured byte-identical on build/seed/seed-0.kexe of R0: 146,455 bytes, main at 0). Needed because
the stable stage-0's extract-native refuses a kexe with more than 200,000 EDN nodes (bounded_edn max-nodes), which the
seed unity exceeds from about 5.5k lines on (its :code vector has one node per code byte)."""
import re
import sys

s = open(sys.argv[1], encoding='utf-8').read()
i = s.index(':code [') + len(':code [')
code = bytes(int(x) for x in s[i:s.index(']', i)].split())
m = re.search(r'\b' + re.escape(sys.argv[2]) + r' \{:offset (\d+), :length (\d+), :arity (\d+)\}', s)
if not m:
    print('{:ok false :message "symbol not exported"}')
    sys.exit(1)
open(sys.argv[3], 'wb').write(code)
print('{:ok true :symbol %s :offset %s :arity %s}' % (sys.argv[2], m.group(1), m.group(3)))
