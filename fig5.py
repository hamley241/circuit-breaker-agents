import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

fig = plt.figure(figsize=(12, 4))
gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35)

policies = ['no_cb', 'ai_cb', 'adapt_cb', 'comp_cb']
x = np.arange(len(policies))
w = 0.35

# Panel A — CFR
ax1 = fig.add_subplot(gs[0])
ax1.bar(x - w/2, [0.29, 0.52, 0.50, 0.43], w, color='#378ADD', label='p=0.5')
ax1.bar(x + w/2, [0.43, 0.69, 0.50, 0.32], w, color='#D85A30', label='p=0.7')
ax1.set_xticks(x); ax1.set_xticklabels(policies, fontsize=8, rotation=15)
ax1.set_ylim(0, 0.85); ax1.set_ylabel('CFR', fontsize=9)
ax1.legend(fontsize=8); ax1.set_title('(a) Cascade failure rate', fontsize=10)
ax1.grid(axis='y', alpha=0.2)

# Panel B — Trip rate
ax2 = fig.add_subplot(gs[1])
colors = ['#B4B2A9', '#378ADD', '#378ADD', '#D85A30']
ax2.bar(policies, [0, 24, 24, 2], color=colors)
ax2.set_ylim(0, 30); ax2.set_ylabel('Trip rate (%)', fontsize=9)
ax2.set_xticklabels(policies, fontsize=8, rotation=15)
ax2.set_title('(b) CB trip rate', fontsize=10)
ax2.grid(axis='y', alpha=0.2)

# Panel C — P(trip|cascade) table
ax3 = fig.add_subplot(gs[2])
ax3.axis('off')
table_data = [['ai_cb', '0', '0'], ['adaptive_cb', '0', '0'],
              ['comp_cb', '0.083†', '0']]
t = ax3.table(cellText=table_data,
              colLabels=['Policy', 'p=0.5', 'p=0.7'],
              cellLoc='center', loc='center')
t.auto_set_font_size(False); t.set_fontsize(9)
t.scale(1, 1.6)
ax3.set_title('(c) P(trip | cascade)', fontsize=10)
ax3.text(0.5, 0.02, '† Single degenerate trajectory', ha='center',
         transform=ax3.transAxes, fontsize=7, color='gray')

plt.suptitle('Figure 5. Circuit breakers do not engage with cascade failures',
             fontsize=11, y=1.02)
plt.savefig('figure5_cb_engagement.png', dpi=150, bbox_inches='tight')
