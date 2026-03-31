import matplotlib.pyplot as plt

plt.style.use("default")
plt.rcParams.update({
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "legend.fontsize": 10
})

methods = ["AI CB", "Adaptive CB"]
trip_rate = [0.56, 0.60]
success_rate = [0.44, 0.40]

plt.figure(figsize=(6, 5))
plt.scatter(trip_rate, success_rate, s=120)

for i, label in enumerate(methods):
    plt.text(trip_rate[i] + 0.005, success_rate[i], label, fontsize=10, va="center")

plt.xlabel("Average Breaker Trip Count")
plt.ylabel("Final Success Rate")
plt.title("Containment–Intervention Tradeoff")
plt.xlim(0.53, 0.63)
plt.ylim(0.38, 0.46)
plt.tight_layout()
plt.savefig("figure_tradeoff.png", dpi=300, bbox_inches="tight")
plt.show()
