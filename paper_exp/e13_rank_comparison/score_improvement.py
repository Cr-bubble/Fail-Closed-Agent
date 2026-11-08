#!/usr/bin/env python3
"""Score the improvement portfolio: per OPT case, best of {official, calibration,
improve variants, pilot candidates}; capped official ratio; cec TODO list."""
import json, os, re, sys, glob
E13 = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.dirname(os.path.dirname(E13))
FINAL = '/home/joey123230/ICCAD_A/final_release_100/final_release_100'
sys.path.insert(0, AGENT)
from cada.netlist import reader
from cada.analysis import depth as depth_mod
from evaluator.requirements import derive

best_sheet = json.load(open(f'{E13}/official_sheets.json'))['best']
rows = json.load(open(f'{E13}/calib_results.json'))['opt_rows']

def opt_req(case, rid):
    lines = [l.strip() for l in open(f'{FINAL}/{case}/prompt.txt') if l.strip()]
    return derive(lines[rid-1]).optimize

def cost_of(nl, opt):
    if opt.metric == 'gate_count':
        return len(nl.gates)
    if opt.metric == 'cone_depth' and opt.output:
        return depth_mod.depth_of_cone(nl, opt.output)
    return depth_mod.global_max_depth(nl)

out, cec_todo = [], []
for r in rows:
    case, rid = r['case'], r['req']
    e = best_sheet[case][str(rid)]
    opt = opt_req(case, rid)
    cands = {'official': e['cost']}
    if r.get('achieved') is not None:
        cands['calib'] = r['achieved']
    for path in glob.glob(f'{E13}/improve_runs/{case}_out.*.v') + \
                glob.glob(f'{E13}/candidates/{case}_out.*.v'):
        tag = os.path.basename(path).split('_out.')[1][:-2]
        try:
            cands[tag] = cost_of(reader.parse_file(path), opt)
        except Exception as ex:
            cands[tag] = f'parse-error {ex}'
    numeric = {k: v for k, v in cands.items() if isinstance(v, int)}
    bk = min(numeric, key=numeric.get)
    best = numeric[bk]
    ratio_old = min(1.0, e['cost_min']/e['cost'])
    ratio_new = min(1.0, e['cost_min']/best)
    rec = dict(case=case, req=rid, metric=r['metric'], cost_min=e['cost_min'],
               official=e['cost'], candidates=cands, best=best, best_src=bk,
               ratio_official=round(ratio_old, 4), ratio_improved=round(ratio_new, 4),
               gain_pts=round(ratio_new-ratio_old, 4))
    out.append(rec)
    if bk != 'official':
        src = (f'{E13}/improve_runs/{case}_out.{bk}.v' if os.path.exists(f'{E13}/improve_runs/{case}_out.{bk}.v')
               else f'{E13}/calib_runs/{case}_out.v' if bk == 'calib'
               else f'{E13}/candidates/{case}_out.{bk}.v')
        cec_todo.append({'case': case, 'src': src})

opt_official = sum(r['ratio_official'] for r in out)
opt_improved = sum(r['ratio_improved'] for r in out)
summary = dict(opt_requests=len(out), opt_official=round(opt_official,3),
               opt_improved=round(opt_improved,3),
               total_official=round(628+opt_official,3),
               total_improved=round(628+opt_improved,3),
               gain=round(opt_improved-opt_official,3),
               wins=len([r for r in out if r['gain_pts']>0]),
               cec_pending=len(cec_todo))
json.dump(dict(summary=summary, rows=out, cec_todo=cec_todo),
          open(f'{E13}/improve_scores.json','w'), indent=1)
print(json.dumps(summary, indent=1))
for r in sorted(out, key=lambda x:-x['gain_pts'])[:20]:
    if r['gain_pts'] != 0 or r['best_src'] != 'official':
        print(f"{r['case']} {r['metric']:<10} min={r['cost_min']:<6} official={r['official']:<6} "
              f"best={r['best']:<6} src={r['best_src']:<10} +{r['gain_pts']}")
