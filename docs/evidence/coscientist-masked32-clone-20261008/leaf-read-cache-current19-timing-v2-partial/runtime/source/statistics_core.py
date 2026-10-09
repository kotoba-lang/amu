"""Pure LC-current19 formula draft v1. No file, process, CPU or network access."""
import hashlib
import itertools
import math

ARMS = ('baseline', 'candidate', 'C')
REPLICATES = 20000
FORMULA_VERSION = 'LC-current19-statistics/xorshift32-rejection-nearest-rank/v1'

def need(ok, message):
    if not ok:
        raise ValueError(message)

def order(workload, attempt):
    need(type(attempt) is int and 0 <= attempt < 90, 'attempt cap')
    block, slot = divmod(attempt, 6)
    salt = 'LC-current19-balanced-order/v1|' + workload + '|' + str(block) + '|'
    return sorted(itertools.permutations(ARMS), key=lambda p:
                  hashlib.sha256((salt + ','.join(p)).encode('ascii')).digest())[slot]

def normalized(triple, n):
    need(type(n) is int and n > 0 and set(triple) == set(ARMS), 'fixed body count/arms')
    out = {}
    for arm in ARMS:
        elapsed, calls = triple[arm]
        need(type(elapsed) is int and elapsed >= 50000000, 'minimum interval')
        need(type(calls) is int and 1 <= calls <= 100000000, 'calls cap')
        out[arm] = elapsed / (calls * n)
    return out

def mean(xs):
    return math.fsum(xs) / len(xs)

def validate(xs):
    need(type(xs) is list and len(xs) == 30, 'exact paired30 required')
    need(all(type(x) is dict and set(x) == set(ARMS) and
             all(type(v) in (int, float) and math.isfinite(v) and v > 0
                 for v in x.values()) for x in xs), 'finite positive paired arms')

class PRNG:
    """SHA256 first four bytes big endian; zero replaced by 0x6d2b79f5.
    xorshift32 (13,17,5), uint32 after each shift; unbiased rejection modulo.
    """
    def __init__(self, domain):
        self.state = int.from_bytes(hashlib.sha256(domain.encode('ascii')).digest()[:4], 'big') or 0x6d2b79f5
    def next(self):
        x = self.state
        x ^= (x << 13) & 0xffffffff
        x ^= x >> 17
        x ^= (x << 5) & 0xffffffff
        self.state = x & 0xffffffff
        return self.state
    def index(self):
        # xorshift32 emits 1..2^32-1; map to 0..2^32-2 before rejection.
        limit = 0xffffffff - 0xffffffff % 30
        while True:
            value = self.next() - 1
            if value < limit:
                return value % 30

def domain(cohort, workload, ratio, global_scope=False):
    prefix = 'LC-current19-fixed19-gm-ci/v1' if global_scope else 'LC-current19-paired-ci/v1'
    return '|'.join((prefix, cohort, workload, ratio))

def interval(draws, point):
    draws.sort()
    return {'geometricMeanPairedRatio': point, 'lower95': draws[499],
            'upper95': draws[19499], 'replicates': REPLICATES,
            'percentileRule': 'nearest rank ceil(p*20000)-1, p=.025/.975'}

def paired_ci(xs, numerator, cohort, workload):
    validate(xs)
    need(numerator in ('baseline', 'C'), 'ratio numerator')
    logs = [math.log(x[numerator] / x['candidate']) for x in xs]
    rng = PRNG(domain(cohort, workload, numerator + '/candidate'))
    draws = [math.exp(mean([logs[rng.index()] for _ in range(30)]))
             for _ in range(REPLICATES)]
    return interval(draws, math.exp(mean(logs)))

def summarize(xs, cohort, workload, changed=True):
    validate(xs)
    arms = {}
    for arm in ARMS:
        values = [x[arm] for x in xs]
        avg = mean(values)
        sd = math.sqrt(math.fsum((v - avg) ** 2 for v in values) / 29)
        arms[arm] = {'meanNsPerBody': avg, 'sampleSDNsPerBody': sd, 'relativeSD': sd / avg}
    stable = all(v['relativeSD'] <= .1 for v in arms.values())
    ci = {num + '/candidate': paired_ci(xs, num, cohort, workload) for num in ('baseline', 'C')}
    baseline, candidate, c = (arms[x] for x in ARMS)
    adoption = (stable and baseline['meanNsPerBody'] / candidate['meanNsPerBody'] >= 1.05
                and baseline['meanNsPerBody'] - candidate['meanNsPerBody'] >
                baseline['sampleSDNsPerBody'] + candidate['sampleSDNsPerBody']
                and ci['baseline/candidate']['lower95'] >= 1.05)
    return {'arms': arms, 'stable': stable, 'pairedCI95': ci,
            'baselineAdoptionBenefit': bool(changed and adoption),
            'codeChanged': changed, 'neutralAttribution': not changed,
            'COrBetter': stable and c['meanNsPerBody'] >= candidate['meanNsPerBody']
                         and ci['C/candidate']['lower95'] >= 1,
            'individualConfidenceScope': 'marginal95 per workload; no joint95 claim'}

def fixed19_ci(rows, names, numerator, cohort):
    need(len(names) == 19 and len(set(names)) == 19 and set(rows) == set(names), 'exact fixed19')
    for xs in rows.values(): validate(xs)
    vectors = [[math.log(x[numerator] / x['candidate']) for x in rows[n]] for n in names]
    rng = PRNG(domain(cohort, 'FULL19', numerator + '/candidate', True))
    draws = [math.exp(mean([mean([v[rng.index()] for _ in range(30)]) for v in vectors]))
             for _ in range(REPLICATES)]
    result = interval(draws, math.exp(mean([mean(v) for v in vectors])))
    result['scope'] = 'fixed19; independent within-workload paired triple resampling; no workload resampling'
    return result

def full_summary(rows, names, cohort, changed):
    need(len(names) == 19 and len(set(names)) == 19, 'fixed19 preregistration')
    need(set(rows) <= set(names), 'unknown workload')
    complete = [n for n in names if n in rows and len(rows[n]) == 30]
    if len(complete) != 19:
        return {'status': 'PARTIAL', 'completedWorkloads': len(complete), 'fixed19PairedGM': None,
                'full19AggregateCOrBetter': False, 'all19IndividualCOrBetter': False,
                'officialScore': False, 'CIDEffectQualified': False, 'productAdopted': False}
    per = {n: summarize(rows[n], cohort, n, n in changed) for n in names}
    gm = {num + '/candidate': fixed19_ci(rows, names, num, cohort) for num in ('baseline', 'C')}
    # Distinguish fixed19 GM of arithmetic means from paired-log point estimate.
    arithmetic_gm = {num + '/candidate': math.exp(mean([
        math.log(per[n]['arms'][num]['meanNsPerBody'] / per[n]['arms']['candidate']['meanNsPerBody'])
        for n in names])) for num in ('baseline', 'C')}
    stable = all(v['stable'] for v in per.values())
    return {'status': 'COMPLETE_SYNTHETIC_OR_INPUT_DATA_ONLY', 'workloads': per,
            'fixed19ArithmeticMeanRatioGM': arithmetic_gm, 'fixed19PairedGM': gm,
            'full19AggregateCOrBetter': stable and arithmetic_gm['C/candidate'] >= 1
                                            and gm['C/candidate']['lower95'] >= 1,
            'all19IndividualCOrBetter': all(v['COrBetter'] for v in per.values()),
            'officialScore': False, 'CIDEffectQualified': False, 'productAdopted': False,
            'formulaVersion': FORMULA_VERSION}
