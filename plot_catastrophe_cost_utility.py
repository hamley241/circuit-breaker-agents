#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

COSTS = [2, 5, 10]

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
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharex=True)

    color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    cost_to_color = {cost: color_cycle[i % len(color_cycle)] for i, cost in enumerate(COSTS)}

    # Left panel: absolute utility
    for cost in COSTS:
        path = f"results_cost_{cost}.csv"
        if not Path(path).exists():
            raise FileNotFoundError(path)

        data = load_csv(path)
        pp_vals = sorted(set(data["ai_cb"].keys()) & set(data["adaptive_cb"].keys()))
        color = cost_to_color[cost]

        ai_u = [data["ai_cb"][p]["utility"] for p in pp_vals]
        ad_u = [data["adaptive_cb"][p]["utility"] for p in pp_vals]

        axes[0].plot(
            pp_vals,
            ad_u,
            marker="o",
            linewidth=2.0,
            linestyle="-",
            color=color,
        )
        axes[0].plot(
            pp_vals,
            ai_u,
            marker="o",
            linewidth=2.0,
            linestyle="--",
            color=color,
        )

    axes[0].set_title("Absolute utility")
    axes[0].set_xlabel(r"Propagation probability ($p_p$)")
    axes[0].set_ylabel("Utility")
    axes[0].grid(True, alpha=0.3)

    # Right panel: delta utility
    for cost in COSTS:
        path = f"results_cost_{cost}.csv"
        data = load_csv(path)
        pp_vals = sorted(set(data["ai_cb"].keys()) & set(data["adaptive_cb"].keys()))
        color = cost_to_color[cost]

        delta_u = [
            data["adaptive_cb"][p]["utility"] - data["ai_cb"][p]["utility"]
            for p in pp_vals
        ]

        axes[1].plot(
            pp_vals,
            delta_u,
            marker="o",
            linewidth=2.0,
            linestyle="-",
            color=color,
        )

    axes[1].axhline(0.0, linestyle="--", linewidth=1.0)
    axes[1].set_title(r"$\Delta$ utility (adaptive $-$ AI)")
    axes[1].set_xlabel(r"Propagation probability ($p_p$)")
    axes[1].set_ylabel(r"$\Delta$ utility")
    axes[1].grid(True, alpha=0.3)

    # Legend: color = catastrophe cost, linestyle = policy
    cost_handles = [
        Line2D([0], [0], color=cost_to_color[cost], lw=2.0, marker="o", label=f"cost = {cost}")
        for cost in COSTS
    ]
    policy_handles = [
        Line2D([0], [0], color="black", lw=2.0, linestyle="-", label="solid: adaptive"),
        Line2D([0], [0], color="black", lw=2.0, linestyle="--", label="dashed: AI-guided"),
    ]

    fig.legend(
        handles=cost_handles + policy_handles,
        loc="upper center",
        ncol=5,
        frameon=False,
        bbox_to_anchor=(0.5, 1.05),
    )

    fig.suptitle("Utility advantage of adaptive breakers grows with catastrophe cost", y=1.11)
    fig.tight_layout()

    fig.savefig("figure3_catastrophe_cost_utility.png", dpi=300, bbox_inches="tight")
    fig.savefig("figure3_catastrophe_cost_utility.pdf", bbox_inches="tight")
    print("Wrote figure3_catastrophe_cost_utility.png")
    print("Wrote figure3_catastrophe_cost_utility.pdf")

    plt.show()


if __name__ == "__main__":
    main()
