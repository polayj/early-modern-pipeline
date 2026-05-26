"""Create significant word accuracy visualization"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Load data
results_dir = Path(__file__).parent.parent
summary_file = list(results_dir.glob('*_summary_*.csv'))[0]
detailed_file = list(results_dir.glob('*_detailed_*.csv'))[0]

summary_df = pd.read_csv(summary_file)
detailed_df = pd.read_csv(detailed_file)

output_dir = Path(__file__).parent

# --- Chart 1: Mean Significant Word Accuracy bar chart (horizontal) ---
print("Creating significant word accuracy bar chart...")

fig, ax = plt.subplots(figsize=(10, 8))

df_sorted = summary_df.sort_values('Mean Significant Word Accuracy', ascending=True)

# Top 3 systems to highlight
top3 = set(df_sorted.nlargest(3, 'Mean Significant Word Accuracy')['OCR System'])

# Color gradient: green for high accuracy, red for low
norm = plt.Normalize(df_sorted['Mean Significant Word Accuracy'].min(),
                     df_sorted['Mean Significant Word Accuracy'].max())
colors = plt.cm.RdYlGn(norm(df_sorted['Mean Significant Word Accuracy']))

bars = ax.barh(df_sorted['OCR System'], df_sorted['Mean Significant Word Accuracy'],
               color=colors, alpha=0.85, edgecolor='black', linewidth=1.5)

# Add value labels
for i, (idx, row) in enumerate(df_sorted.iterrows()):
    val = row['Mean Significant Word Accuracy']
    is_top3 = row['OCR System'] in top3
    ax.text(val + 0.01, i, f"{val:.3f}",
            va='center', fontsize=11, fontweight='bold')

# Bold the top 3 y-tick labels
ytick_labels = []
for label in df_sorted['OCR System']:
    if label in top3:
        ytick_labels.append(label)
    else:
        ytick_labels.append(label)
ax.set_yticks(range(len(df_sorted)))
ax.set_yticklabels(ytick_labels)
for tick_label in ax.get_yticklabels():
    if tick_label.get_text() in top3:
        tick_label.set_fontweight('bold')
        tick_label.set_fontsize(12)

# Add median line
median_val = summary_df['Mean Significant Word Accuracy'].median()
ax.axvline(median_val, color='gray', linestyle='--', alpha=0.6, linewidth=1.5,
           label=f'Median ({median_val:.3f})')

ax.set_xlabel('Mean Significant Word Accuracy', fontsize=12, fontweight='bold')
ax.set_title('Significant Word Accuracy by OCR System\n(Higher is Better)', fontsize=14, fontweight='bold', pad=15)
ax.set_xlim(0, 1.05)
ax.grid(axis='x', alpha=0.3)
ax.legend(fontsize=10)

plt.tight_layout()
output_file = output_dir / 'significant_word_accuracy.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"  [SAVED] {output_file}")
plt.close()

# --- Chart 2: Box plot of significant word accuracy distribution per system ---
print("Creating significant word accuracy distribution box plot...")

fig, ax = plt.subplots(figsize=(10, 8))

# Order systems by median significant word accuracy
system_order = (detailed_df.groupby('OCR System')['Significant Word Accuracy']
                .median().sort_values(ascending=False).index.tolist())

# Top 3 systems
top3_box = set(system_order[:3])

# Box plot
bp = ax.boxplot(
    [detailed_df[detailed_df['OCR System'] == sys]['Significant Word Accuracy'].dropna().values
     for sys in system_order],
    tick_labels=system_order, vert=True, patch_artist=True,
    medianprops=dict(color='black', linewidth=2),
    whiskerprops=dict(linewidth=1.5),
    capprops=dict(linewidth=1.5),
    flierprops=dict(marker='o', markerfacecolor='red', markersize=4, alpha=0.5)
)

# Color boxes
colors_box = plt.cm.RdYlGn(np.linspace(0.9, 0.2, len(system_order)))
for patch, color in zip(bp['boxes'], colors_box):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
    patch.set_edgecolor('black')
    patch.set_linewidth(1.5)

# Add mean markers
means = [detailed_df[detailed_df['OCR System'] == sys]['Significant Word Accuracy'].mean()
         for sys in system_order]
ax.scatter(range(1, len(system_order) + 1), means, marker='D', color='blue',
           s=50, zorder=5, label='Mean')

ax.set_ylabel('Significant Word Accuracy', fontsize=12, fontweight='bold')
ax.set_xlabel('OCR System', fontsize=12, fontweight='bold')
ax.set_title('Distribution of Significant Word Accuracy by OCR System\n(Sorted by Median, Descending)',
             fontsize=14, fontweight='bold', pad=15)
ax.set_xticklabels(system_order, rotation=45, ha='right')
# Bold top 3 x-tick labels
for tick_label in ax.get_xticklabels():
    if tick_label.get_text() in top3_box:
        tick_label.set_fontweight('bold')
        tick_label.set_fontsize(11)
ax.set_ylim(-0.6, 1.15)
ax.grid(axis='y', alpha=0.3)
ax.legend(fontsize=10)

plt.tight_layout()
output_file = output_dir / 'significant_word_accuracy_distribution.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"  [SAVED] {output_file}")
plt.close()

print("\nDone!")
