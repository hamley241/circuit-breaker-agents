import matplotlib.pyplot as plt
import csv
from collections import defaultdict

def load_results(csv_path):
    data = defaultdict(dict)

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mode = row["mode"]
            p_p = float(row["p_p"])

            data[mode][p_p] = {
                "success": float(row["success_rate"]),
                "cfr": float(row["catastrophic_fail_rate"]),
            }

    return data


def plot_tradeoff(data):
    modes = ["ai_cb", "adaptive_cb"]

    p_p_values = sorted(data["ai_cb"].keys())

    plt.figure(figsize=(8, 5))

    # --- Success ---
    for mode in modes:
        y = [data[mode][p]["success"] for p in p_p_values]
        plt.plot(p_p_values, y, marker="o", label=f"{mode} - success")

    # --- CFR ---
    for mode in modes:
        y = [data[mode][p]["cfr"] for p in p_p_values]
        plt.plot(p_p_values, y, linestyle="--", marker="x", label=f"{mode} - CFR")

    plt.xlabel("Propagation Probability (p_p)")
    plt.ylabel("Rate")
    plt.title("Circuit Breaker Tradeoff: Success vs Catastrophic Failure")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.savefig("tradeoff_plot.png", dpi=200)
    plt.show()


if __name__ == "__main__":
    data = load_results("results.csv")
    plot_tradeoff(data)
