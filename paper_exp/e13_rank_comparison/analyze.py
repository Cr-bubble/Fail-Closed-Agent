#!/usr/bin/env python3
"""E13 analysis: completion stats, OPT cost recompute vs official, gap ratios.

Usage (any python; imports the WORKTREE's cada+evaluator):
  analyze.py            -> calib_results.json + calibration_report.md + stdout summary
  analyze.py --cec      -> ABC cec spot-check on 10 random transform-bearing cases
"""
import json, os, re, sys, random, datetime

CALIB = '/home/joey123230/ICCAD_A/calib_cdcf9af'
E13   = '/home/joey123230/ICCAD_A/Agent/paper_exp/e13_rank_comparison'
RUNS  = f'{E13}/calib_runs'
FINAL = '/home/joey123230/ICCAD_A/final_release_100/final_release_100'

sys.path.insert(0, CALIB)
os.environ.setdefault('ABC_BIN', '/home/joey123230/ICCAD_A/abc/abc')
os.chdir(CALIB)

from cada.netlist import reader                      # noqa: E402
from cada.analysis import depth as depth_mod         # noqa: E402
from evaluator.requirements import derive            # noqa: E402

CASES = [f'test{i:03d}' for i in range(1, 101)]
sheets = json.load(open(f'{E13}/official_sheets.json'))
GPT, BEST = sheets['gpt'], sheets['best']

FRAME = re.compile(r'#RESPONSE\s+(\d+)\s*\n(.*?)\n?#END\s+\1', re.DOTALL)


def frames(path):
    if not os.path.exists(path):
        return {}
    txt = open(path).read()
    return {int(m.group(1)): m.group(2) for m in FRAME.finditer(txt)}


def cost_of(nl, opt):
    if opt.metric == 'gate_count':
        return len(nl.gates)
    if opt.metric == 'cone_depth' and opt.output:
        return depth_mod.depth_of_cone(nl, opt.output)
    return depth_mod.global_max_depth(nl)


def text_cost(resp):
    m = re.search(r'from\s+(\d+)\s+to\s+(\d+)', resp)
    if m:
        return int(m.group(2))
    nums = re.findall(r'\d+', resp)
    return int(nums[-1]) if nums else None


def run_meta():
    """dur + load at start per case, from driver.log."""
    meta = {}
    p = f'{RUNS}/driver.log'
    if not os.path.exists(p):
        return meta
    start_load = {}
    for ln in open(p):
        m = re.match(r'run\s+(test\d+) start .* load=([\d.]+)', ln)
        if m:
            start_load[m.group(1)] = float(m.group(2))
        m = re.match(r'run\s+(test\d+) end\s+rc=(\d+) dur=(\d+)s .* load=([\d.]+)', ln)
        if m:
            meta[m.group(1)] = {'rc': int(m.group(2)), 'dur_s': int(m.group(3)),
                                'load_start': start_load.get(m.group(1)),
                                'load_end': float(m.group(4))}
    return meta


def main():
    meta = run_meta()
    results, opt_rows = {}, []
    n_complete = n_crash = 0
    for c in CASES:
        prompt = [ln.strip() for ln in open(f'{FINAL}/{c}/prompt.txt') if ln.strip()]
        exp = len(prompt)
        fr = frames(f'{RUNS}/{c}.stdout.log')
        rcp = f'{RUNS}/{c}.rc'
        rc = int(open(rcp).read().strip()) if os.path.exists(rcp) else None
        stderr_p = f'{RUNS}/{c}.stderr.log'
        stderr_tail = ''
        if os.path.exists(stderr_p) and os.path.getsize(stderr_p):
            stderr_tail = open(stderr_p).read()[-400:]
        complete = len(fr) == exp and all(fr.get(i, '').strip() for i in range(1, exp + 1))
        if complete:
            n_complete += 1
        crashed = (rc not in (0, None)) or ('Traceback' in stderr_tail)
        if crashed:
            n_crash += 1
        row = {'expected': exp, 'got': len(fr), 'complete': complete,
               'rc': rc, 'crashed': crashed}
        if stderr_tail:
            row['stderr_tail'] = stderr_tail
        if c in meta:
            row.update(meta[c])

        # OPT request for this case?
        opt_req = [r for r, info in GPT.get(c, {}).items() if info.get('score') == 'x']
        if opt_req:
            r = opt_req[0]
            i = int(r)
            line = prompt[i - 1]
            spec = derive(line)
            official = GPT[c][r].get('cost')
            b = BEST[c][r]
            resp = fr.get(i, '')
            t_cost = text_cost(resp) if resp else None
            outv = f'{RUNS}/{c}_out.v'
            r_cost = parse_err = None
            if os.path.exists(outv) and spec.optimize:
                try:
                    nl = reader.parse_file(outv)
                    r_cost = cost_of(nl, spec.optimize)
                except Exception as e:  # noqa: BLE001
                    parse_err = repr(e)[:200]
            achieved = r_cost if r_cost is not None else t_cost
            orow = {'case': c, 'req': i,
                    'metric': spec.optimize.metric if spec.optimize else '?',
                    'official': official, 'cost_min': b.get('cost_min'),
                    'text_cost': t_cost, 'recomputed': r_cost,
                    'achieved': achieved,
                    'match': achieved == official,
                    'gap_case': (b.get('cost') is not None and b.get('cost_min') is not None
                                 and b['cost'] > b['cost_min'])}
            if orow['gap_case'] and achieved is not None and b.get('cost_min'):
                orow['achieved_over_cost_min'] = round(achieved / b['cost_min'], 4)
            if parse_err:
                orow['parse_err'] = parse_err
            if t_cost is not None and r_cost is not None and t_cost != r_cost:
                orow['text_vs_recompute_disagree'] = True
            if c in meta:
                orow['dur_s'] = meta[c]['dur_s']
                orow['load_start'] = meta[c]['load_start']
            opt_rows.append(orow)
            row['opt'] = orow
        results[c] = row

    matches = [o for o in opt_rows if o['match']]
    mism    = [o for o in opt_rows if not o['match']]
    out = {'date': datetime.date.today().isoformat(),
           'commit': 'cdcf9af', 'n_cases': len(CASES),
           'complete_cases': n_complete, 'crashed_cases': n_crash,
           'opt_total': len(opt_rows), 'opt_match': len(matches),
           'mismatches': mism, 'opt_rows': opt_rows, 'cases': results}
    json.dump(out, open(f'{E13}/calib_results.json', 'w'), indent=1)

    # report
    L = []
    L.append(f"# E13 calibration report — cdcf9af on final_release_100 ({out['date']})\n")
    L.append(f"- complete cases: {n_complete}/100; crashed: {n_crash}")
    L.append(f"- OPT exact cost matches: {len(matches)}/{len(opt_rows)}\n")
    if mism:
        L.append('## MISMATCHES (flagged for idle re-run)\n')
        L.append('| case | metric | achieved | official | cost_min | text | dur_s | load@start |')
        L.append('|---|---|---|---|---|---|---|---|')
        for o in mism:
            L.append(f"| {o['case']} | {o['metric']} | {o['achieved']} | {o['official']} | "
                     f"{o['cost_min']} | {o['text_cost']} | {o.get('dur_s','?')} | {o.get('load_start','?')} |")
        L.append('')
    L.append('## All 46 OPT requests\n')
    L.append('| case | req | metric | achieved(recomputed) | text | official | cost_min | match | gap | ach/min |')
    L.append('|---|---|---|---|---|---|---|---|---|---|')
    for o in opt_rows:
        L.append(f"| {o['case']} | {o['req']} | {o['metric']} | {o['recomputed']} | {o['text_cost']} | "
                 f"{o['official']} | {o['cost_min']} | {'Y' if o['match'] else 'N'} | "
                 f"{'Y' if o['gap_case'] else ''} | {o.get('achieved_over_cost_min','')} |")
    incompl = [c for c, r in results.items() if not r['complete']]
    if incompl:
        L.append(f"\n## Incomplete/crashed cases: {incompl}")
    open(f'{E13}/calibration_report.md', 'w').write('\n'.join(L) + '\n')
    print(f"complete {n_complete}/100, crashes {n_crash}, "
          f"OPT match {len(matches)}/{len(opt_rows)}")
    for o in mism:
        print('MISMATCH', o['case'], o['metric'], 'achieved', o['achieved'],
              'official', o['official'], 'text', o['text_cost'], 'dur', o.get('dur_s'))


def cec():
    from evaluator import checks
    rng = random.Random(13)
    tb = []
    for c in CASES:
        prompt = [ln.strip() for ln in open(f'{FINAL}/{c}/prompt.txt') if ln.strip()]
        if any(derive(ln).is_transform for ln in prompt) and os.path.exists(f'{RUNS}/{c}_out.v'):
            tb.append(c)
    sample = rng.sample(tb, min(10, len(tb)))
    print(f'transform-bearing cases with outputs: {len(tb)}; sample: {sample}')
    res = {}
    for c in sample:
        a = reader.parse_file(f'{FINAL}/{c}/{c}.v')
        b = reader.parse_file(f'{RUNS}/{c}_out.v')
        eq = checks.equiv(a, b, timeout=300)
        res[c] = eq
        print(c, 'EQUIV' if eq is True else ('NOT-EQUIV' if eq is False else 'UNDECIDED'))
    json.dump({'sample': sample, 'result': {k: (v if v is not None else 'undecided')
               for k, v in res.items()}},
              open(f'{E13}/cec_spotcheck.json', 'w'), indent=1)


if __name__ == '__main__':
    cec() if '--cec' in sys.argv else main()
