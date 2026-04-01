#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import numpy as np

ALPHAS = [0.3, 0.5, 0.7]

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
})


def load_csv(path: str) -> Dict[str, Dict[float, Dict[str, float]]]:
    data: Dict[str, Dict[float, Dict[str, float]]] = {}
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mode = row["mode"]
            p_p = float(row["p_p"])
            data.setdefault(mode, {})[p_p] = {
                "success_rate": float(row["success_rate"]),
                "catastrophic_fail_rate": float(row["catastrophic_fail_rate"]),
                "utility": float(row["utility"]),
            }
    return data


def main() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)

    for ax, alpha in zip(axes, ALPHAS):
        path = f"results_linear_alpha_{alpha}.csv"
        if not Path(path).exists():
            raise FileNotFoundError(path)

        data = load_csv(path)
        pp_vals = sorted(set(data["ai_cb"].keys()) & set(data["adaptive_cb"].keys()))

        delta_success = np.array([
            data["adaptive_cb"][p]["success_rate"] - data["ai_cb"][p]["success_rate"]
            for p in pp_vals
        ])
        delta_cfr = np.array([
            data["adaptive_cb"][p]["catastrophic_fail_rate"] - data["ai_cb"][p]["catastrophic_fail_rate"]
            for p in pp_vals
        ])

        ax.axhline(0.0, linestyle="--", linewidth=1.0)
        ax.plot(pp_vals, delta_success, marker="o", linewidth=2.0, label=r"$\Delta$ success")
        ax.plot(pp_vals, delta_cfr, marker="x", linewidth=2.0, label=r"$\Delta$ CFR")

        # Tradeoff points are where adaptive has lower success AND lower CFR
        tradeoff_mask = (delta_success < 0.0) & (delta_cfr < 0.0) & (delta_success > -0.01) 
        tradeoff_x = np.array(pp_vals)[tradeoff_mask]

        if len(tradeoff_x) > 0:
            ax.scatter(
                tradeoff_x,
                np.zeros_like(tradeoff_x),
                s=90,
                facecolors="none",
                edgecolors="black",
                linewidths=1.5,
                zorder=5,
                label="tradeoff region" if alpha == ALPHAS[0] else None,
            )

        ax.set_title(rf"$\alpha = {alpha}$")
        ax.set_xlabel(r"Propagation probability ($p_p$)")
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel(r"$\Delta$ metric (adaptive $-$ AI)")

    handles, labels = axes[0].get_legend_handles_labels()
    seen = set()
    unique_handles = []
    unique_labels = []
    for h, l in zip(handles, labels):
        if l not in seen and l != "":
            seen.add(l)
            unique_handles.append(h)
            unique_labels.append(l)

    fig.legend(
        unique_handles,
        unique_labels,
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 1.04),
    )

    fig.suptitle("Safety–availability tradeoff induced by fallback degradation", y=1.10)
    fig.tight_layout()

    fig.savefig("figure2_linear_degradation_deltas.png", dpi=300, bbox_inches="tight")
    fig.savefig("figure2_linear_degradation_deltas.pdf", bbox_inches="tight")
    print("Wrote figure2_linear_degradation_deltas.png")
    print("Wrote figure2_linear_degradation_deltas.pdf")

    plt.show()


if __name__ == "__main__":
    main()
