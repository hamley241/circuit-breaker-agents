import matplotlib.pyplot as plt

chain_lengths = [2, 3, 4, 5, 6]

plt.style.use("default")
plt.rcParams.update({
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "legend.fontsize": 10
})
no_cb = [0.269, 0.380, 0.472, 0.551, 0.617]
simple_cb = [0.269, 0.359, 0.433, 0.492, 0.540]
ai_cb = [0.185, 0.211, 0.236, 0.244, 0.255]
adaptive_cb = [0.133, 0.113, 0.094, 0.081, 0.069]

plt.figure(figsize=(8, 5))
plt.plot(chain_lengths, no_cb, marker="o", label="No CB")
plt.plot(chain_lengths, simple_cb, marker="o", label="Simple CB")
plt.plot(chain_lengths, ai_cb, marker="o", label="AI CB")
plt.plot(chain_lengths, adaptive_cb, marker="o", label="Adaptive CB")

plt.xlabel("Chain Length")
plt.ylabel("Cascade Failure Rate (CFR)")
plt.title("Simulation Results: CFR by Chain Length")
plt.xticks(chain_lengths)
plt.ylim(0, 0.7)
plt.legend()
plt.tight_layout()
plt.savefig("figure_simulation_cfr.png", dpi=300, bbox_inches="tight")
plt.show()
