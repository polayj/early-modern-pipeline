"""
Create visualizations from OCR evaluation results
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
import argparse

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def load_latest_results(results_dir: Path, folder_name: str = None):
    """Load evaluation results from specified folder or most recent if not specified"""
    if folder_name:
        # Use the specified folder
        target_dir = results_dir / folder_name
        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"Specified folder not found: {target_dir}")
        latest_dir = target_dir
        print(f"Loading results from specified folder: {latest_dir}")
    else:
        # Find the latest evaluation directory
        eval_dirs = sorted([d for d in results_dir.glob('evaluation_*') if d.is_dir()], reverse=True)

        if not eval_dirs:
            raise FileNotFoundError(f"No evaluation results found in {results_dir}")

        latest_dir = eval_dirs[0]
        print(f"Loading results from latest folder: {latest_dir}")

    # Find the CSV files in that directory
    summary_files = list(latest_dir.glob('*_summary_*.csv'))
    detailed_files = list(latest_dir.glob('*_detailed_*.csv'))
    age_grouped_files = list(latest_dir.glob('*_age_grouped_*.csv'))

    if not summary_files:
        raise FileNotFoundError(f"No summary CSV found in {latest_dir}")

    summary_df = pd.read_csv(summary_files[0])
    detailed_df = pd.read_csv(detailed_files[0]) if detailed_files else None
    age_grouped_df = pd.read_csv(age_grouped_files[0]) if age_grouped_files else None

    return summary_df, detailed_df, age_grouped_df, latest_dir


def create_cer_wer_comparison(summary_df, output_dir):
    """Create comparison chart of CER and WER"""
    print("Creating CER/WER comparison chart...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # Sort by CER
    df_sorted = summary_df.sort_values('Mean CER')

    # CER chart
    bars1 = ax1.barh(df_sorted['OCR System'], df_sorted['Mean CER'],
                     color=plt.cm.RdYlGn_r(df_sorted['Mean CER']),
                     alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        ax1.text(row['Mean CER'] + 0.01, i, f"{row['Mean CER']:.3f}",
                va='center', fontsize=10, fontweight='bold')

    ax1.set_xlabel('Character Error Rate (CER)', fontsize=12, fontweight='bold')
    ax1.set_title('Character Error Rate by OCR System\n(Lower is Better)', fontsize=14, fontweight='bold', pad=15)
    ax1.grid(axis='x', alpha=0.3)

    # WER chart
    df_sorted_wer = summary_df.sort_values('Mean WER')

    bars2 = ax2.barh(df_sorted_wer['OCR System'], df_sorted_wer['Mean WER'],
                     color=plt.cm.RdYlGn_r(df_sorted_wer['Mean WER']),
                     alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels
    for i, (idx, row) in enumerate(df_sorted_wer.iterrows()):
        ax2.text(row['Mean WER'] + 0.01, i, f"{row['Mean WER']:.3f}",
                va='center', fontsize=10, fontweight='bold')

    ax2.set_xlabel('Word Error Rate (WER)', fontsize=12, fontweight='bold')
    ax2.set_title('Word Error Rate by OCR System\n(Lower is Better)', fontsize=14, fontweight='bold', pad=15)
    ax2.grid(axis='x', alpha=0.3)

    plt.tight_layout()

    output_file = output_dir / 'cer_wer_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def create_bleu_hallucination_scatter(summary_df, output_dir):
    """Create scatter plot of BLEU score vs hallucination rate"""
    print("Creating BLEU vs Hallucination scatter plot...")

    fig, ax = plt.subplots(figsize=(12, 10))

    # Create scatter plot
    colors = plt.cm.viridis(np.linspace(0, 1, len(summary_df)))

    for idx, row in summary_df.iterrows():
        ax.scatter(row['Mean Hallucination Rate'], row['Mean BLEU Score'],
                  s=300, color=colors[idx], alpha=0.7,
                  edgecolors='black', linewidths=2,
                  label=row['OCR System'])

        # Add system name label
        ax.annotate(row['OCR System'],
                   (row['Mean Hallucination Rate'], row['Mean BLEU Score']),
                   xytext=(8, 8), textcoords='offset points',
                   fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='black'))

    ax.set_xlabel('Hallucination Rate (Lower is Better)', fontsize=12, fontweight='bold')
    ax.set_ylabel('BLEU Score (Higher is Better)', fontsize=12, fontweight='bold')
    ax.set_title('OCR Quality: BLEU Score vs Hallucination Rate', fontsize=16, fontweight='bold', pad=20)
    ax.grid(alpha=0.3)

    # Add quadrant lines
    median_bleu = summary_df['Mean BLEU Score'].median()
    median_hall = summary_df['Mean Hallucination Rate'].median()
    ax.axhline(median_bleu, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(median_hall, color='gray', linestyle='--', alpha=0.5, linewidth=1)

    plt.tight_layout()

    output_file = output_dir / 'bleu_hallucination_scatter.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def create_accuracy_comparison(summary_df, output_dir):
    """Create grouped bar chart comparing different accuracy metrics"""
    print("Creating accuracy comparison chart...")

    fig, ax = plt.subplots(figsize=(14, 8))

    # Sort by char accuracy
    df_sorted = summary_df.sort_values('Char Accuracy', ascending=False)

    # Set up positions
    x = np.arange(len(df_sorted))
    width = 0.25

    # Create bars
    bars1 = ax.bar(x - width, df_sorted['Char Accuracy'], width,
                   label='Character Accuracy', color='#2E7D32', alpha=0.8, edgecolor='black')
    bars2 = ax.bar(x, df_sorted['Word Accuracy'], width,
                   label='Word Accuracy', color='#1976D2', alpha=0.8, edgecolor='black')
    bars3 = ax.bar(x + width, df_sorted['Mean Significant Word Accuracy'], width,
                   label='Significant Word Accuracy', color='#F57C00', alpha=0.8, edgecolor='black')

    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height + 0.01,
                   f'{height:.2f}', ha='center', va='bottom', fontsize=7, fontweight='bold')

    ax.set_xlabel('OCR System', fontsize=12, fontweight='bold')
    ax.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
    ax.set_title('OCR Accuracy Metrics Comparison', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(df_sorted['OCR System'], rotation=45, ha='right')
    ax.legend(fontsize=11, loc='lower left')
    ax.set_ylim(0, 1.05)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    output_file = output_dir / 'accuracy_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def create_age_grouped_performance(age_grouped_df, output_dir):
    """Create line chart showing performance by document age"""
    if age_grouped_df is None:
        print("  [SKIP] Age-grouped data not available")
        return

    print("Creating age-grouped performance chart...")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Get unique OCR systems
    systems = age_grouped_df['OCR System'].unique()

    # Plot CER by age
    for system in systems:
        system_data = age_grouped_df[age_grouped_df['OCR System'] == system].sort_values('Age Group')
        ax1.plot(system_data['Age Group'], system_data['Mean CER'],
                marker='o', linewidth=2, label=system, markersize=6)

    ax1.set_xlabel('Document Age Group', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Mean CER', fontsize=11, fontweight='bold')
    ax1.set_title('Character Error Rate by Document Age', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=8, loc='best')
    ax1.grid(alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)

    # Plot WER by age
    for system in systems:
        system_data = age_grouped_df[age_grouped_df['OCR System'] == system].sort_values('Age Group')
        ax2.plot(system_data['Age Group'], system_data['Mean WER'],
                marker='o', linewidth=2, label=system, markersize=6)

    ax2.set_xlabel('Document Age Group', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Mean WER', fontsize=11, fontweight='bold')
    ax2.set_title('Word Error Rate by Document Age', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=8, loc='best')
    ax2.grid(alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)

    # Plot BLEU by age
    for system in systems:
        system_data = age_grouped_df[age_grouped_df['OCR System'] == system].sort_values('Age Group')
        ax3.plot(system_data['Age Group'], system_data['Mean BLEU Score'],
                marker='o', linewidth=2, label=system, markersize=6)

    ax3.set_xlabel('Document Age Group', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Mean BLEU Score', fontsize=11, fontweight='bold')
    ax3.set_title('BLEU Score by Document Age', fontsize=13, fontweight='bold')
    ax3.legend(fontsize=8, loc='best')
    ax3.grid(alpha=0.3)
    ax3.tick_params(axis='x', rotation=45)

    # Plot Hallucination by age
    for system in systems:
        system_data = age_grouped_df[age_grouped_df['OCR System'] == system].sort_values('Age Group')
        ax4.plot(system_data['Age Group'], system_data['Mean Hallucination Rate'],
                marker='o', linewidth=2, label=system, markersize=6)

    ax4.set_xlabel('Document Age Group', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Mean Hallucination Rate', fontsize=11, fontweight='bold')
    ax4.set_title('Hallucination Rate by Document Age', fontsize=13, fontweight='bold')
    ax4.legend(fontsize=8, loc='best')
    ax4.grid(alpha=0.3)
    ax4.tick_params(axis='x', rotation=45)

    plt.tight_layout()

    output_file = output_dir / 'age_grouped_performance.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def create_error_type_distribution(summary_df, output_dir):
    """Create stacked bar chart of error type distribution"""
    print("Creating error type distribution chart...")

    fig, ax = plt.subplots(figsize=(14, 8))

    # Sort by total errors
    summary_df['Total Char Errors'] = summary_df['Total Char Errors'].astype(float)
    df_sorted = summary_df.sort_values('Total Char Errors')

    # Create stacked bars
    insertions = ax.barh(df_sorted['OCR System'], df_sorted['Char Ins %'],
                        label='Insertions', color='#E53E3E', alpha=0.8, edgecolor='black')
    deletions = ax.barh(df_sorted['OCR System'], df_sorted['Char Del %'],
                       left=df_sorted['Char Ins %'],
                       label='Deletions', color='#F57C00', alpha=0.8, edgecolor='black')
    substitutions = ax.barh(df_sorted['OCR System'], df_sorted['Char Sub %'],
                           left=df_sorted['Char Ins %'] + df_sorted['Char Del %'],
                           label='Substitutions', color='#7B1FA2', alpha=0.8, edgecolor='black')

    ax.set_xlabel('Error Distribution (%)', fontsize=12, fontweight='bold')
    ax.set_title('Character Error Type Distribution by OCR System', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()

    output_file = output_dir / 'error_type_distribution.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def main():
    """Generate all visualizations"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Create visualizations from OCR evaluation results')
    parser.add_argument('--folder', '-f', type=str, default=None,
                        help='Specific evaluation folder to visualize (e.g., "evaluation_20250112_143025"). If not specified, uses the latest.')
    args = parser.parse_args()

    results_dir = Path(r'Z:\OCR Evaluation\results')

    print("="*80)
    print("CREATING OCR EVALUATION VISUALIZATIONS")
    print("="*80)
    print()

    # Load data
    summary_df, detailed_df, age_grouped_df, latest_dir = load_latest_results(results_dir, args.folder)

    # Create output directory
    output_dir = latest_dir / 'visualizations'
    output_dir.mkdir(exist_ok=True)

    print(f"\nSystems evaluated: {len(summary_df)}")
    print(f"Output directory: {output_dir}\n")

    # Generate visualizations
    create_cer_wer_comparison(summary_df, output_dir)
    create_accuracy_comparison(summary_df, output_dir)
    create_bleu_hallucination_scatter(summary_df, output_dir)
    create_error_type_distribution(summary_df, output_dir)
    create_age_grouped_performance(age_grouped_df, output_dir)

    print()
    print("="*80)
    print("[SUCCESS] ALL VISUALIZATIONS CREATED")
    print("="*80)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    print("  - cer_wer_comparison.png")
    print("  - accuracy_comparison.png")
    print("  - bleu_hallucination_scatter.png")
    print("  - error_type_distribution.png")
    print("  - age_grouped_performance.png")
    print()


if __name__ == "__main__":
    main()
