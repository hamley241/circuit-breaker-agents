#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt

MODES = ["linear_subtractive", "linear_multiplicative", "exp"]

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


def pretty_mode_name(mode: str) -> str:
    if mode == "linear_subtractive":
        return "Linear subtractive"
    if mode == "linear_multiplicative":
        return "Linear multiplicative"
    if mode == "exp":
        return "Exponential"
    return mode.replace("_", " ").title()


def main() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)

    for ax, deg_mode in zip(axes, MODES):
        path = f"results_mode_{deg_mode}.csv"
        if not Path(path).exists():
            raise FileNotFoundError(path)

        data = load_csv(path)
        pp_vals = sorted(set(data["ai_cb"].keys()) & set(data["adaptive_cb"].keys()))

        delta_success = [
            data["adaptive_cb"][p]["success_rate"] - data["ai_cb"][p]["success_rate"]
            for p in pp_vals
        ]
        delta_cfr = [
            data["adaptive_cb"][p]["catastrophic_fail_rate"] - data["ai_cb"][p]["catastrophic_fail_rate"]
            for p in pp_vals
        ]

        ax.axhline(0.0, linestyle="--", linewidth=1.0)
        ax.plot(pp_vals, delta_success, marker="o", linewidth=2.0, label=r"$\Delta$ success")
        ax.plot(pp_vals, delta_cfr, marker="x", linewidth=2.0, label=r"$\Delta$ CFR")

        ax.set_title(pretty_mode_name(deg_mode))
        ax.set_xlabel(r"Propagation probability ($p_p$)")
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel(r"$\Delta$ metric (adaptive $-$ AI)")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 1.04),
    )

    fig.suptitle("Robustness to fallback degradation models", y=1.10)
    fig.tight_layout()

    fig.savefig("appendix_degradation_modes.png", dpi=300, bbox_inches="tight")
    fig.savefig("appendix_degradation_modes.pdf", bbox_inches="tight")
    print("Wrote appendix_degradation_modes.png")
    print("Wrote appendix_degradation_modes.pdf")

    plt.show()


if __name__ == "__main__":
    main()
