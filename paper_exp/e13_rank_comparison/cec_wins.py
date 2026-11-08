#!/usr/bin/env python3
import json, os, sys
E13 = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.dirname(os.path.dirname(E13))
FINAL = '/home/joey123230/ICCAD_A/final_release_100/final_release_100'
sys.path.insert(0, AGENT)
from cada.netlist import reader
from evaluator import checks
todo = json.load(open(f'{E13}/improve_scores.json'))['cec_todo']
res = {}
for t in todo:
    c = t['case']
    a = reader.parse_file(f'{FINAL}/{c}/{c}.v')
    b = reader.parse_file(t['src'])
    eq = checks.equiv(a, b, timeout=600)
    res[c] = (True if eq is True else False if eq is False else 'undecided')
    print(c, res[c], flush=True)
json.dump(res, open(f'{E13}/cec_wins.json','w'), indent=1)
bad = [c for c,v in res.items() if v is not True]
print('ALL-EQUIV' if not bad else f'PROBLEM: {bad}')
