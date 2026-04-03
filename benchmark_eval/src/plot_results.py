from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd


RESULTS_DIR = Path("results")
OUT_DIR = RESULTS_DIR / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_single_row_csv(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    nonzero = df[df["runs"] > 0]
    if nonzero.empty:
        raise ValueError(f"No nonzero rows found in {path}")
    if len(nonzero) != 1:
        raise ValueError(f"Expected exactly one nonzero row in {path}, found {len(nonzero)}")
    return nonzero.iloc[0]


def pct(x: float) -> float:
    return 100.0 * float(x)


def save_bar(
    labels: List[str],
    values: List[float],
    ylabel: str,
    title: str,
    outfile: Path,
    ylim: tuple[float, float] | None = None,
    annotate_fmt: str = "{:.1f}",
) -> None:
    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(labels, values)
    plt.ylabel(ylabel)
    plt.title(title)
    if ylim is not None:
        plt.ylim(*ylim)

    for bar, v in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (0.5 if max(values) > 10 else 0.01),
            annotate_fmt.format(v),
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()
    plt.savefig(outfile, dpi=200, bbox_inches="tight")
    plt.close()


def save_grouped_bar(
    categories: List[str],
    series: Dict[str, List[float]],
    ylabel: str,
    title: str,
    outfile: Path,
    ylim: tuple[float, float] | None = None,
    annotate: bool = False,
) -> None:
    plt.figure(figsize=(8, 4.8))
    n_series = len(series)
    width = 0.8 / n_series
    x = list(range(len(categories)))

    for idx, (name, values) in enumerate(series.items()):
        offsets = [xi - 0.4 + width / 2 + idx * width for xi in x]
        bars = plt.bar(offsets, values, width=width, label=name)
        if annotate:
            for bar, v in zip(bars, values):
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (0.5 if max(values) > 10 else 0.01),
                    f"{v:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

    plt.xticks(x, categories)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    if ylim is not None:
        plt.ylim(*ylim)

    plt.tight_layout()
    plt.savefig(outfile, dpi=200, bbox_inches="tight")
    plt.close()


def plot_execution_mode_cascade() -> None:
    state_locked = load_single_row_csv(RESULTS_DIR / "no_cb_all.csv")
    free_recovery = load_single_row_csv(RESULTS_DIR / "free_no_cb_all.csv")

    # Prefer cascade rate = cascades / runs for Figure 1.
    values = [
        pct(float(state_locked["cascades"]) / float(state_locked["runs"])),
        pct(float(free_recovery["cascades"]) / float(free_recovery["runs"])),
    ]

    save_bar(
        labels=["State-locked", "Free-recovery"],
        values=values,
        ylabel="Cascade rate (%)",
        title="Failure propagation depends on execution mode",
        outfile=OUT_DIR / "figure1_execution_mode_cascade.png",
        ylim=(0, max(values) * 1.25 + 1),
    )


def plot_cb_tradeoff_state_locked() -> None:
    no_cb = load_single_row_csv(RESULTS_DIR / "no_cb_all.csv")
    ai_cb = load_single_row_csv(RESULTS_DIR / "ai_cb_all.csv")
    adaptive_cb = load_single_row_csv(RESULTS_DIR / "adaptive_cb_all.csv")

    categories = ["No CB", "AI-guided", "Adaptive"]
    cascade_rates = [
        pct(float(no_cb["cascades"]) / float(no_cb["runs"])),
        pct(float(ai_cb["cascades"]) / float(ai_cb["runs"])),
        pct(float(adaptive_cb["cascades"]) / float(adaptive_cb["runs"])),
    ]
    success_rates = [
        pct(no_cb["success_rate"]),
        pct(ai_cb["success_rate"]),
        pct(adaptive_cb["success_rate"]),
    ]

    save_grouped_bar(
        categories=categories,
        series={
            "Success rate (%)": success_rates,
            "Cascade rate (%)": cascade_rates,
        },
        ylabel="Rate (%)",
        title="Tradeoff between task success and cascade reduction",
        outfile=OUT_DIR / "figure2_cb_tradeoff.png",
        ylim=(0, 100),
        annotate=True,
    )


def plot_selectivity() -> None:
    ai_cb = load_single_row_csv(RESULTS_DIR / "ai_cb_all.csv")
    adaptive_cb = load_single_row_csv(RESULTS_DIR / "adaptive_cb_all.csv")

    categories = ["AI-guided", "Adaptive"]
    cfr_injected = [
        pct(ai_cb["cfr_injected"]),
        pct(adaptive_cb["cfr_injected"]),
    ]
    cfr_clean = [
        pct(ai_cb["cfr_clean"]),
        pct(adaptive_cb["cfr_clean"]),
    ]

    save_grouped_bar(
        categories=categories,
        series={
            "P(cascade | corrupted) (%)": cfr_injected,
            "P(cascade | clean) (%)": cfr_clean,
        },
        ylabel="Conditional cascade probability (%)",
        title="Conditional propagation by policy",
        outfile=OUT_DIR / "figure3_conditional_cascade.png",
        ylim=(0, max(cfr_injected + cfr_clean) * 1.3 + 1),
        annotate=True,
    )


def plot_trip_selectivity() -> None:
    # These are from your validated aggregate calculations.
    categories = ["AI-guided", "Adaptive"]
    trip_corrupted = [24.5901639344, 16.1764705882]
    trip_clean = [23.4375, 26.3157894737]

    save_grouped_bar(
        categories=categories,
        series={
            "P(trip | corrupted) (%)": trip_corrupted,
            "P(trip | clean) (%)": trip_clean,
        },
        ylabel="Trip probability (%)",
        title="Circuit breaker selectivity",
        outfile=OUT_DIR / "figure4_trip_selectivity.png",
        ylim=(0, max(trip_corrupted + trip_clean) * 1.3 + 1),
        annotate=True,
    )


def plot_trip_vs_cascade() -> None:
    # From your validated AI-guided aggregate calculations.
    values = [0.0, 27.2727272727]

    save_bar(
        labels=["Cascade", "No cascade"],
        values=values,
        ylabel="P(trip | outcome) (%)",
        title="AI-guided breakers never trip on cascading trajectories",
        outfile=OUT_DIR / "figure5_trip_vs_outcome.png",
        ylim=(0, max(values) * 1.3 + 1),
    )


def write_summary_table() -> None:
    no_cb = load_single_row_csv(RESULTS_DIR / "no_cb_all.csv")
    ai_cb = load_single_row_csv(RESULTS_DIR / "ai_cb_all.csv")
    adaptive_cb = load_single_row_csv(RESULTS_DIR / "adaptive_cb_all.csv")
    free_no_cb = load_single_row_csv(RESULTS_DIR / "free_no_cb_all.csv")
    free_ai_cb = load_single_row_csv(RESULTS_DIR / "free_ai_cb_all.csv")
    free_adaptive_cb = load_single_row_csv(RESULTS_DIR / "free_adaptive_cb_all.csv")

    rows = []
    for label, row, mode in [
        ("No CB", no_cb, "state_locked"),
        ("AI-guided", ai_cb, "state_locked"),
        ("Adaptive", adaptive_cb, "state_locked"),
        ("No CB", free_no_cb, "free_recovery"),
        ("AI-guided", free_ai_cb, "free_recovery"),
        ("Adaptive", free_adaptive_cb, "free_recovery"),
    ]:
        rows.append(
            {
                "mode": mode,
                "policy": label,
                "runs": int(row["runs"]),
                "success_rate_pct": round(pct(row["success_rate"]), 2),
                "cascade_rate_pct": round(pct(float(row["cascades"]) / float(row["runs"])), 2),
                "cfr": round(float(row["cfr"]), 4),
                "cfr_injected": round(float(row["cfr_injected"]), 4),
                "cfr_clean": round(float(row["cfr_clean"]), 4),
                "lift": round(float(row["lift"]), 4),
                "avg_trip_count": round(float(row["avg_trip_count"]), 4),
                "utility": round(float(row["utility"]), 4),
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "summary_table.csv", index=False)


def main() -> None:
    plot_execution_mode_cascade()
    plot_cb_tradeoff_state_locked()
    plot_selectivity()
    plot_trip_selectivity()
    plot_trip_vs_cascade()
    write_summary_table()
    print(f"Wrote figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
