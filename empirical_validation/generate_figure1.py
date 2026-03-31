import matplotlib.pyplot as plt
import numpy as np

plt.style.use("default")
plt.rcParams.update({
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "legend.fontsize": 10
})

# Real API validation results (inject_rate = 0.2)
methods = ["No CB", "AI CB", "Adaptive CB"]
cascade_rate = [0.62, 0.00, 0.00]
final_success = [0.38, 0.44, 0.40]

x = np.arange(len(methods))
width = 0.36

fig, ax = plt.subplots(figsize=(8, 5))
ax.set_ylim(0, 0.7)
ax.bar(x - width/2, cascade_rate, width, label="Cascade Rate")
ax.bar(x + width/2, final_success, width, label="Final Success Rate")

ax.set_ylabel("Rate")
ax.set_title("Real-World Validation: Cascade Containment and Task Success")
ax.set_xticks(x)
ax.set_xticklabels(methods)
ax.set_ylim(0, 0.8)
ax.legend()

for i, v in enumerate(cascade_rate):
    y = 0.02 if v == 0 else v + 0.02
    ax.text(i - width/2, y, f"{v:.2f}", ha="center", va="bottom", fontsize=9)

    if v == 0:
        ax.plot(i - width/2, 0, marker='o')

for i, v in enumerate(final_success):
    ax.text(i + width/2, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    if v == 0:
        ax.text(i - width/2, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=9)

plt.tight_layout()
plt.savefig("figure_real_api_results.png", dpi=300, bbox_inches="tight")
plt.show()
