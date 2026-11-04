"""Source-level control-flow diagnostic; does not generate or execute Mach-O.

Models only the explicitly listed source builder operations and stubbed Darwin
syscalls. It does not validate instruction encodings, ABI, kernel behavior,
branch fixups or the actual Amu-generated artifact.
"""
import re
import struct
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / 'seed/macos-flint-parent-fd-packager.kotoba'


def load_program():
    source = SOURCE.read_text()
    source = source[source.index('(defn- observer-words '):source.index('(defn- body-at ')]
    source = re.sub(r';;[^\n]*', '', source)
    program = []
    for name, args in re.findall(r'\(ds-([a-z-]+)(?:\s+([^()]*?))?\)', source):
        if name == 'new':
            continue
        program.append((name, tuple(int(x, 0) for x in args.split()) if args else ()))
    if not program or program[0][0] != 'cmpi':
        raise AssertionError('unexpected source')
    return program


def simulate(program, scenario):
    labels = {a[0]: i for i, (op, a) in enumerate(program) if op == 'label'}
    regs = [0] * 32
    regs[0], regs[31] = scenario.get('argc', 1), 0x10000
    memory = bytearray(0x12000)
    zero = carry = False
    output = b''
    pc = steps = 0

    def put(address, value, size):
        memory[address:address + size] = int(value).to_bytes(size, 'little')

    def stat_at(address, dev, ino, mode):
        put(address, dev, 4)
        put(address + 4, mode, 2)
        put(address + 8, ino, 8)

    while pc < len(program):
        steps += 1
        if steps > 10000:
            raise AssertionError('nonterminating source')
        op, a = program[pc]
        pc += 1
        if op == 'label':
            continue
        if op == 'imm':
            regs[a[0]] = a[1] & 0xffffffff
        elif op in ('add', 'sub'):
            regs[a[0]] = regs[a[1]] + (a[2] if op == 'add' else -a[2])
        elif op in ('lw', 'ldr', 'lh', 'lb'):
            n = {'lw': 4, 'ldr': 8, 'lh': 2, 'lb': 1}[op]
            regs[a[0]] = int.from_bytes(memory[regs[a[1]] + a[2]:regs[a[1]] + a[2] + n], 'little')
        elif op in ('sw', 'str', 'sb'):
            n = {'sw': 4, 'str': 8, 'sb': 1}[op]
            put(regs[a[1]] + a[2], regs[a[0]] & ((1 << (8 * n)) - 1), n)
        elif op in ('cmp', 'cmpi'):
            rhs = regs[a[1]] if op == 'cmp' else a[1]
            zero, carry = regs[a[0]] == rhs, regs[a[0]] >= rhs
        elif op == 'b':
            branch = {0x14000000: True, 0x54000000: zero,
                      0x54000001: not zero, 0x54000002: carry}[a[0]]
            if branch:
                pc = labels[a[1]]
        elif op == 'hex-digit':
            regs[11] = ord('0123456789abcdef'[regs[11]])
        elif op == 'i':
            word = a[0]
            if word == 0x12140d09:
                regs[9] = regs[8] & 0xf000
            elif word == 0xaa1403f8:
                regs[24] = regs[20]
            elif word == 0xd344fd4b:
                regs[11] = regs[10] >> 4
            elif word == 0x8a0c014b:
                regs[11] = regs[10] & regs[12]
            elif word == 0xaa1803e1:
                regs[1] = regs[24]
            elif word == 0xaa1903e2:
                regs[2] = regs[25]
            else:
                raise AssertionError(f'unmodelled raw instruction {word:#x}')
        elif op == 'sys':
            number = a[0]
            if number == 339:
                fd = regs[0]
                if fd not in (3, 4) or scenario.get('fail_fstat') == fd:
                    carry, regs[0] = True, 5
                else:
                    dev, ino, mode = scenario['parent' if fd == 3 else 'child']
                    stat_at(regs[1], dev, ino, mode)
                    carry, regs[0] = False, 0
            elif number == 470:
                name = bytes(memory[regs[1]:regs[1] + 9])
                if regs[0] != 3 or name != b'.kapitsa\0' or regs[3] != 0x2820:
                    raise AssertionError('unexpected fstatat arguments')
                if scenario.get('fail_fstatat'):
                    carry, regs[0] = True, 5
                else:
                    stat_at(regs[2], *scenario['entry'])
                    carry, regs[0] = False, 0
            elif number == 4:
                if regs[0] != 1:
                    raise AssertionError('unexpected output FD')
                count = regs[2] - (1 if scenario.get('short_write') else 0)
                output += bytes(memory[regs[1]:regs[1] + count])
                carry, regs[0] = False, count
            elif number == 1:
                return regs[0], output
            else:
                raise AssertionError(f'unmodelled syscall {number}')
        else:
            raise AssertionError(f'unmodelled builder operation {op}')
    raise AssertionError('no exit')


def main():
    program = load_program()
    good = {'parent': (127, 123, 0x4000), 'child': (127, 124, 0x4000),
            'entry': (127, 124, 0x4000)}
    code, out = simulate(program, good)
    expected = struct.pack('<4sIQQQQ', b'ADP1', 0, 127, 123, 127, 124).hex().encode() + b'\n'
    assert (code, out) == (0, expected)
    cases = [
        {'argc': 2}, {'fail_fstat': 3}, {'fail_fstat': 4}, {'fail_fstatat': True},
        {'parent': (127, 123, 0x8000)}, {'child': (127, 124, 0x8000)},
        {'parent': (127, 0, 0x4000)}, {'child': (127, 0, 0x4000)},
        {'child': (126, 124, 0x4000)}, {'child': (127, 123, 0x4000)},
        {'entry': (127, 124, 0xa000)}, {'entry': (127, 125, 0x4000)},
        {'entry': (126, 124, 0x4000)}, {'short_write': True},
    ]
    for override in cases:
        code, out = simulate(program, {**good, **override})
        assert code != 0 and out != expected, override
    # Negative control: remove the entry-inode mismatch branch. The replaced
    # entry must then get through this model, proving the case exercises it.
    at = program.index(('cmp', (8, 27)))
    assert program[at + 1] == ('b', (0x54000001, 9))
    mutant = program[:at + 1] + program[at + 2:]
    code, out = simulate(mutant, {**good, 'entry': (127, 125, 0x4000)})
    assert (code, out) == (0, expected)
    print('source-level model: one success and', len(cases), 'refusal cases passed')
    print('negative control: inode-check bypass was detected')
    print('not an instruction encoding, native artifact, kernel or race test')


if __name__ == '__main__':
    main()
