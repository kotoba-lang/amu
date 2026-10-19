import collections
def move(w, d):
    return w & ~(31 << 16 | 31) == 2852127712 and w & 31 == d
def expression(a, reg, pc, ri, lo):
    at = pc - 4
    for _ in range(64):
        assert at >= lo, ('INDEX_WITHOUT_BOUNDED_DEFINITION', reg, pc)
        w = a[at // 4]
        _, wr, ns, k = m.effects(w, at)
        assert k == 'normal' and ns == [at + 4], ('INDEX_DEFINITION_CROSSES_CONTROL', reg, pc, at, k)
        if reg in wr:
            if w & 4290772992 == 2432696320 and w >> 5 & 31 == ri and (w & 31 == reg):
                delta = w >> 10 & 4095
                assert 0 <= delta <= 4095
            elif move(w, reg) and w >> 16 & 31 == ri:
                delta = 0
            else:
                raise AssertionError(('UNKNOWN_INDEX_EXPRESSION', reg, pc, at, hex(w)))
            for p in range(at + 4, pc, 4):
                assert ri not in m.effects(a[p // 4], p)[1], ('SOURCE_INDEX_CHANGED_BEFORE_STORE', p)
            return (delta, at)
        at -= 4
    raise AssertionError('INDEX_DEFINITION_BUDGET')
def increments(a, pc, ri, lo):
    w = a[pc // 4]
    if w == 2432696320 | 1 << 10 | ri << 5 | ri:
        return 1
    if move(w, ri):
        delta, _ = expression(a, w >> 16 & 31, pc, ri, lo)
        assert delta == 1
        return delta
    return None
def condition(cc, v, k):
    return {0: v == k, 1: v != k, 2: v >= k, 3: v < k, 8: v > k, 9: v <= k, 10: v >= k, 11: v < k, 12: v > k, 13: v <= k}[cc]
def proof(a, region):
    anchor, end = (region['anchorPC'], region['endPC'])
    guards = []
    for pc in range(max(4, anchor - 400), anchor, 4):
        r = m.ref(a[pc // 4], pc)
        if r and r[0] == 'BC' and (r[1] == end):
            guards.append(pc)
    assert len(guards) == 6
    p = guards[0]
    w = a[p // 4 - 1]
    ri = w >> 5 & 31
    n = w >> 10 & 4095
    assert w & 4290773023 == 4043309087 and 19 <= ri <= 28 and (1 <= n <= 64) and (a[p // 4] & 15 == 2)
    for pc in range(p + 4, anchor + 4, 4):
        word=a[pc//4]; _, written, _, kind=m.effects(word, pc)
        assert ri not in written
        assert kind in ('normal','Bcond','CB','TB','direct-branch/call')
        assert word & 0xfc000000 != 0x94000000, ('CALL_IN_BOUNDED_HEADER',pc)
    graph = {r['pc']: m.effects(a[r['pc'] // 4], r['pc']) for r in region['rows']}
    values = {anchor + 4: set(range(n))}
    q = collections.deque([anchor + 4])
    steps = 0
    while q:
        pc = q.popleft()
        steps += 1
        assert steps < 100000
        vals = values[pc]
        w = a[pc // 4]
        _, wr, ns, k = graph[pc]
        new = None if vals is None else set(vals)
        if ri in wr:
            delta = increments(a, pc, ri, anchor + 4)
            new = None if delta is None or vals is None else {v + delta for v in vals}
            assert new is None or all((0 <= v <= 128 for v in new))
        split = {to: new for to in ns}
        if k == 'Bcond' and pc - 4 >= anchor + 4:
            c = a[pc // 4 - 1]
            if c & 4290773023 == 4043309087 and c >> 5 & 31 == ri and (vals is not None):
                cc = w & 15
                limit = c >> 10 & 4095
                assert cc in [0, 1, 2, 3, 8, 9, 10, 11, 12, 13]
                target = m.ref(w, pc)[1]
                split = {pc + 4: {v for v in vals if not condition(cc, v, limit)}, target: {v for v in vals if condition(cc, v, limit)}}
        for to, v in split.items():
            assert anchor + 4 <= to < end
            if v == set():
                continue
            if to not in values:
                values[to] = v
                q.append(to)
                continue
            old = values[to]
            joined = None if old is None or v is None else old | v
            if joined != old:
                values[to] = joined
                q.append(to)
    stores = []
    for row in region['rows']:
        pc = row['pc']
        w = a[pc // 4]
        if w & 4292934656 == 4162877440 and w >> 5 & 31 == 4:
            assert pc in values and values[pc] is not None
            vals = values[pc]
            assert vals and min(vals) >= 0 and (max(vals) < n)
            delta, defined = expression(a, w >> 16 & 31, pc, ri, anchor + 4)
            stores.append(dict(pc=pc, indexRegister=w >> 16 & 31, definitionPC=defined, sourceIndexRegister=ri, sourceMinimum=min(vals), sourceMaximum=max(vals), offset=delta, effectiveMinimum=min(vals) + delta, effectiveMaximum=max(vals) + delta))
    assert stores
    return dict(anchorPC=anchor, endPC=end, indexComparePC=p-4, indexGuardBranchPC=p, indexRegister=ri, bound=n, initialUnsignedIndexRange=[0, n - 1], allPayloadStoreIndicesNonnegativeAndBelowCheckedExtent=True, finiteCFGSteps=steps, stores=stores)
