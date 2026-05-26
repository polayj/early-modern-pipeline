#!/usr/bin/env python3
"""
Create visualizations for table-specific OCR evaluation results
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def load_latest_results(results_dir: Path):
    """Load the most recent table evaluation results"""
    summary_files = sorted(list(results_dir.glob('table_evaluation_summary_*.csv')), reverse=True)
    detailed_files = sorted(list(results_dir.glob('table_evaluation_detailed_*.csv')), reverse=True)

    if not summary_files:
        raise FileNotFoundError(f"No summary results found in {results_dir}")

    summary_df = pd.read_csv(summary_files[0])
    detailed_df = pd.read_csv(detailed_files[0]) if detailed_files else None

    print(f"Loaded results: {summary_files[0].name}")
    return summary_df, detailed_df


def create_cer_wer_comparison(summary_df, output_dir):
    """Create comparison chart of CER and WER for tables"""
    print("Creating CER/WER comparison chart...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # Sort by CER
    df_sorted = summary_df.sort_values('Mean CER')

    # CER chart
    bars1 = ax1.barh(df_sorted['OCR System'], df_sorted['Mean CER'],
                     color=plt.cm.RdYlGn_r(df_sorted['Mean CER'] / df_sorted['Mean CER'].max()),
                     alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        ax1.text(row['Mean CER'] + 0.01, i, f"{row['Mean CER']:.3f}",
                va='center', fontsize=10, fontweight='bold')

    ax1.set_xlabel('Character Error Rate (CER)', fontsize=12, fontweight='bold')
    ax1.set_title('CER for Table Documents\n(Lower is Better)', fontsize=14, fontweight='bold', pad=15)
    ax1.grid(axis='x', alpha=0.3)

    # WER chart
    df_sorted_wer = summary_df.sort_values('Mean WER')

    bars2 = ax2.barh(df_sorted_wer['OCR System'], df_sorted_wer['Mean WER'],
                     color=plt.cm.RdYlGn_r(df_sorted_wer['Mean WER'] / df_sorted_wer['Mean WER'].max()),
                     alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels
    for i, (idx, row) in enumerate(df_sorted_wer.iterrows()):
        ax2.text(row['Mean WER'] + 0.01, i, f"{row['Mean WER']:.3f}",
                va='center', fontsize=10, fontweight='bold')

    ax2.set_xlabel('Word Error Rate (WER)', fontsize=12, fontweight='bold')
    ax2.set_title('WER for Table Documents\n(Lower is Better)', fontsize=14, fontweight='bold', pad=15)
    ax2.grid(axis='x', alpha=0.3)

    plt.tight_layout()

    output_file = output_dir / 'table_cer_wer_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def create_per_document_heatmap(detailed_df, output_dir):
    """Create heatmap showing performance per document"""
    print("Creating per-document performance heatmap...")

    # Pivot data for heatmap
    cer_pivot = detailed_df.pivot(index='system', columns='document', values='cer')

    # Shorten document names for display
    cer_pivot.columns = ['Anonymous 1682', 'Young 1807']

    # Sort by average CER
    cer_pivot['Average'] = cer_pivot.mean(axis=1)
    cer_pivot = cer_pivot.sort_values('Average')
    cer_pivot = cer_pivot.drop('Average', axis=1)

    fig, ax = plt.subplots(figsize=(10, 8))

    # Create heatmap
    sns.heatmap(cer_pivot, annot=True, fmt='.3f', cmap='RdYlGn_r',
                cbar_kws={'label': 'Character Error Rate'},
                linewidths=2, linecolor='black',
                vmin=0, vmax=cer_pivot.values.max(),
                ax=ax)

    ax.set_title('CER by OCR System and Document\n(Lower is Better)',
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Document', fontsize=12, fontweight='bold')
    ax.set_ylabel('OCR System', fontsize=12, fontweight='bold')

    plt.tight_layout()

    output_file = output_dir / 'table_per_document_heatmap.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def create_bleu_comparison(summary_df, output_dir):
    """Create bar chart of BLEU scores"""
    print("Creating BLEU score comparison...")

    fig, ax = plt.subplots(figsize=(12, 8))

    # Sort by BLEU score
    df_sorted = summary_df.sort_values('Mean BLEU Score', ascending=False)

    # Create bars
    bars = ax.barh(df_sorted['OCR System'], df_sorted['Mean BLEU Score'],
                   color=plt.cm.YlGn(df_sorted['Mean BLEU Score']),
                   alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        ax.text(row['Mean BLEU Score'] + 0.01, i, f"{row['Mean BLEU Score']:.3f}",
                va='center', fontsize=10, fontweight='bold')

    ax.set_xlabel('BLEU Score', fontsize=12, fontweight='bold')
    ax.set_title('BLEU Score for Table Documents\n(Higher is Better)',
                 fontsize=14, fontweight='bold', pad=15)
    ax.grid(axis='x', alpha=0.3)
    ax.set_xlim(0, 1.0)

    plt.tight_layout()

    output_file = output_dir / 'table_bleu_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def create_accuracy_comparison(summary_df, output_dir):
    """Create grouped bar chart of accuracy metrics"""
    print("Creating accuracy metrics comparison...")

    fig, ax = plt.subplots(figsize=(14, 8))

    # Sort by character accuracy
    df_sorted = summary_df.sort_values('Char Accuracy', ascending=False)

    # Set up positions
    x = np.arange(len(df_sorted))
    width = 0.35

    # Create bars
    bars1 = ax.bar(x - width/2, df_sorted['Char Accuracy'], width,
                   label='Character Accuracy', color='#2E7D32', alpha=0.8, edgecolor='black')
    bars2 = ax.bar(x + width/2, df_sorted['Word Accuracy'], width,
                   label='Word Accuracy', color='#1976D2', alpha=0.8, edgecolor='black')

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height + 0.01,
                   f'{height:.2f}', ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax.set_xlabel('OCR System', fontsize=12, fontweight='bold')
    ax.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
    ax.set_title('Table Accuracy Metrics Comparison', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(df_sorted['OCR System'], rotation=45, ha='right')
    ax.legend(fontsize=11, loc='lower left')
    ax.set_ylim(0, 1.05)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    output_file = output_dir / 'table_accuracy_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def create_error_type_distribution(summary_df, output_dir):
    """Create stacked bar chart of error type distribution"""
    print("Creating error type distribution chart...")

    fig, ax = plt.subplots(figsize=(14, 8))

    # Sort by total errors
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
    ax.set_title('Character Error Type Distribution for Tables', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()

    output_file = output_dir / 'table_error_type_distribution.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  [SAVED] {output_file}")
    plt.close()


def main():
    """Generate all table visualizations"""
    results_dir = Path(r'Z:\Tables\results')

    print("=" * 80)
    print("CREATING TABLE EVALUATION VISUALIZATIONS")
    print("=" * 80)
    print()

    # Load data
    summary_df, detailed_df = load_latest_results(results_dir)

    # Create output directory
    output_dir = results_dir / 'visualizations'
    output_dir.mkdir(exist_ok=True)

    print(f"\nSystems evaluated: {len(summary_df)}")
    print(f"Documents evaluated: {len(detailed_df['document'].unique()) if detailed_df is not None else 'N/A'}")
    print(f"Output directory: {output_dir}\n")

    # Generate visualizations
    create_cer_wer_comparison(summary_df, output_dir)
    create_bleu_comparison(summary_df, output_dir)
    create_accuracy_comparison(summary_df, output_dir)
    create_error_type_distribution(summary_df, output_dir)

    if detailed_df is not None:
        create_per_document_heatmap(detailed_df, output_dir)

    print()
    print("=" * 80)
    print("[SUCCESS] ALL VISUALIZATIONS CREATED")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    print("  - table_cer_wer_comparison.png")
    print("  - table_bleu_comparison.png")
    print("  - table_accuracy_comparison.png")
    print("  - table_error_type_distribution.png")
    print("  - table_per_document_heatmap.png")
    print()


if __name__ == "__main__":
    main()
