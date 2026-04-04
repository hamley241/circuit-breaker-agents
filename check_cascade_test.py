import json
from collections import defaultdict

files = {
    ("no_cb", "p05"): "results/phaseB_dep_p05_no_cb_all.jsonl",
    ("ai_cb", "p05"): "results/phaseB_dep_p05_ai_cb_all.jsonl",
    ("adaptive_cb", "p05"): "results/phaseB_dep_p05_adaptive_cb_all.jsonl",
    ("no_cb", "p07"): "results/phaseB_dep_p07_no_cb_all.jsonl",
    ("ai_cb", "p07"): "results/phaseB_dep_p07_ai_cb_all.jsonl",
    ("adaptive_cb", "p07"): "results/phaseB_dep_p07_adaptive_cb_all.jsonl",
}

results = defaultdict(lambda: defaultdict(lambda: {"cascade":0, "prop":0, "abst":0}))

for (policy, p), fp in files.items():
    with open(fp) as f:
        for line in f:
            r = json.loads(line)
            if not r.get("cascade", False):
                continue

            results[policy][p]["cascade"] += 1

            final = r.get("final_answer")

            if final in [None, "reject"]:
                results[policy][p]["abst"] += 1
            else:
                results[policy][p]["prop"] += 1

for policy in ["no_cb", "ai_cb", "adaptive_cb"]:
    for p in ["p05", "p07"]:
        row = results[policy][p]
        print(policy, p, row)
