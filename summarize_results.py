#!/usr/bin/env python3
import csv
import glob
import sys

files = sys.argv[1:] if len(sys.argv) > 1 else sorted(glob.glob("results_*.csv"))

for path in files:
    print(f"\n=== {path} ===")
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["mode"] in ("ai_cb", "adaptive_cb"):
                rows.append(row)

    pp_vals = sorted(set(float(r["p_p"]) for r in rows))
    for p_p in pp_vals:
        ai = next(r for r in rows if r["mode"] == "ai_cb" and float(r["p_p"]) == p_p)
        ad = next(r for r in rows if r["mode"] == "adaptive_cb" and float(r["p_p"]) == p_p)

        ds = float(ad["success_rate"]) - float(ai["success_rate"])
        dc = float(ad["catastrophic_fail_rate"]) - float(ai["catastrophic_fail_rate"])
        du = float(ad["utility"]) - float(ai["utility"])

        print(
            f"p_p={p_p:.2f} "
            f"Δsuccess={ds:+.4f} "
            f"ΔCFR={dc:+.4f} "
            f"Δutility={du:+.4f}"
        )
