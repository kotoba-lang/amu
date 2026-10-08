"""Finite scheduler; operational adapter separately gated by immutable SOURCE.

Direct CLI refuses. Callback run(row, arm, calls, label) is a future adapter contract:
return (exact telemetry receipt, quietAdmissionBool, durableRawEvidenceId).
Timing SOURCE supplies a separately accepted nmax semantic map.
"""
import math
from statistics_core import ARMS, need, normalized, order

CAPS = {'runner': 5415, 'load': 10830, 'children': 16245,
        'runnerTimeoutSeconds': 30, 'loadTimeoutSeconds': 5,
        'workloadDeadlineSeconds': 9000, 'campaignDeadlineSeconds': 172800}

def next_calls(calls, elapsed):
    need(type(calls) is int and 1 <= calls <= 100000000 and
         type(elapsed) is int and elapsed >= 0, 'calibration integer bounds')
    if elapsed == 0:
        return min(100000000, calls * 10)
    # Exact rational round-to-nearest ties-to-even, avoiding platform float rounding.
    q, rem = divmod(calls * 300000000, elapsed)
    if 2 * rem > elapsed or (2 * rem == elapsed and q % 2): q += 1
    return max(1, min(100000000, q))

def quiet_admission(receipt, before_load, after_load, background_idle):
    need(all(type(x) in (float, int) and math.isfinite(x)
             for x in (before_load, after_load, background_idle)), 'finite quiet values')
    need(before_load >= 0 and after_load >= 0 and 0 <= background_idle <= 100, 'quiet ranges')
    return (receipt['elapsedNanoseconds'] >= 50000000 and before_load <= 4 and
            after_load <= 4 and background_idle >= 90)

def run_finite_engine(entries, run, semantic_guard, clock, persist):
    """Finite injectable scheduler. Operational caller must pass SOURCE authorization.
    Caller clocks are monotonic seconds. Every attempt, including rejection, consumes
    cap. Adapter must enforce global caps and timeout/closure before return; persist
    raw stdout/stderr and complete envelope before semantic/quiet validation.
    """
    need(len(entries) == 19 and len({e['workload'] for e in entries}) == 19, 'full19')
    start = clock(); calls_used = 0; complete = {}; states = []
    def invoke(e, arm, count, label, ws):
        nonlocal calls_used
        need(clock() - start <= 172800 and clock() - ws <= 9000, 'finite deadline')
        need(calls_used < CAPS['runner'], 'runner cap')
        calls_used += 1
        receipt, quiet, raw_id = run(e, arm, count, label)
        need(type(quiet) is bool and bool(raw_id), 'quiet admission and durable raw id')
        semantic_guard(e, arm, receipt)  # future exact accepted fresh285 semantic mapping
        need(receipt['calls'] == count and receipt['warmupCalls'] == 1, 'counts')
        need(type(receipt['elapsedNanoseconds']) is int and receipt['elapsedNanoseconds'] >= 0, 'timer')
        need(clock() - start <= 172800 and clock() - ws <= 9000, 'postprocess deadline')
        return receipt, quiet, raw_id
    for entry in entries:
        ws = clock(); workload = entry['workload']; counts = {}
        state = {'workload': workload, 'calibration': [], 'triples': [], 'accepted': []}
        states.append(state)
        for arm in ARMS:
            count = 3
            for attempt in range(5):
                receipt, quiet, raw_id = invoke(entry, arm, count, workload+'-cal-'+arm+'-'+str(attempt), ws)
                elapsed = receipt['elapsedNanoseconds']
                state['calibration'].append({'arm': arm, 'attempt': attempt, 'calls': count,
                                             'elapsedNs': elapsed, 'quiet': quiet, 'rawId': raw_id})
                persist(state)
                if quiet and 225000000 <= elapsed <= 450000000:
                    counts[arm] = count; break
                count = next_calls(count, elapsed)
            if arm not in counts:
                state['status'] = 'PARTIAL_CALIBRATION_CAP'; persist(state); break
        if len(counts) != 3: continue
        for attempt in range(90):
            triple = {}; events = {}; receipts = {}
            for arm in order(workload, attempt):
                receipt, quiet, raw_id = invoke(entry, arm, counts[arm], workload+'-measure-'+str(attempt)+'-'+arm, ws)
                triple[arm] = (receipt['elapsedNanoseconds'], counts[arm])
                events[arm] = {'quiet': quiet, 'rawId': raw_id}
                receipts[arm] = receipt
                # Guard checks each accepted arm against fresh285; pair guard before next child.
                if 'baseline' in receipts and 'candidate' in receipts:
                    semantic_guard(entry, 'native-pair', receipts)
            accepted = all(z['quiet'] for z in events.values()) and all(t[0] >= 50000000 for t in triple.values())
            state['triples'].append({'attempt': attempt, 'order': order(workload, attempt),
                                    'elapsedAndCalls': triple, 'events': events, 'accepted': accepted})
            if accepted: state['accepted'].append(normalized(triple, entry['bodyCountPerCall']))
            persist(state)
            if len(state['accepted']) == 30: break
        state['status'] = 'COMPLETE30' if len(state['accepted']) == 30 else 'PARTIAL_QUIET_TRIPLE_CAP'
        if len(state['accepted']) == 30: complete[workload] = state['accepted']
        persist(state)
    return {'states': states, 'complete': complete, 'runnerCallbacks': calls_used,
            'executionQualified': False, 'status': 'FINITE_SCHEDULE_COMPLETE_PENDING_ACTUAL_AUDIT'}

def main():
    raise SystemExit('HOLD_ENGINE_ONLY: use timing.py only after exact frozen SOURCE/two reviews/root GO')

if __name__ == '__main__': main()
