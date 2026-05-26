#!/usr/bin/env python3
"""
Generate summary report and book materials for table evaluation
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def generate_latex_table(summary_df, output_dir):
    """Generate LaTeX table for publication"""
    print("Generating LaTeX table...")

    # Sort by CER
    df_sorted = summary_df.sort_values('Mean CER')

    latex = []
    latex.append("% Table: OCR System Performance on Historical Tables")
    latex.append("\\begin{table}[htbp]")
    latex.append("\\centering")
    latex.append("\\caption{OCR System Performance on Historical Table Documents (1682-1807)}")
    latex.append("\\label{tab:table-ocr-performance}")
    latex.append("\\begin{tabular}{lcccccc}")
    latex.append("\\toprule")
    latex.append("OCR System & CER & WER & BLEU & Char Acc. & Word Acc. & Hall. Rate \\\\")
    latex.append("\\midrule")

    for _, row in df_sorted.iterrows():
        latex.append(
            f"{row['OCR System']:15} & "
            f"{row['Mean CER']:.3f} & "
            f"{row['Mean WER']:.3f} & "
            f"{row['Mean BLEU Score']:.3f} & "
            f"{row['Char Accuracy']:.3f} & "
            f"{row['Word Accuracy']:.3f} & "
            f"{row['Mean Hallucination Rate']:.3f} \\\\"
        )

    latex.append("\\bottomrule")
    latex.append("\\end{tabular}")
    latex.append("\\end{table}")

    latex_str = "\n".join(latex)

    # Save to file
    output_file = output_dir / "table_performance_latex.tex"
    output_file.write_text(latex_str, encoding='utf-8')

    print(f"  [SAVED] {output_file}")
    return latex_str


def generate_narrative_statistics(summary_df, detailed_df, output_dir):
    """Generate narrative statistics for book chapter"""
    print("Generating narrative statistics...")

    # Best performing system
    best_cer = summary_df.nsmallest(1, 'Mean CER').iloc[0]
    best_wer = summary_df.nsmallest(1, 'Mean WER').iloc[0]
    best_bleu = summary_df.nlargest(1, 'Mean BLEU Score').iloc[0]

    # Worst performing system
    worst_cer = summary_df.nlargest(1, 'Mean CER').iloc[0]

    # Document-specific analysis
    doc_performance = {}
    for doc in detailed_df['document'].unique():
        doc_data = detailed_df[detailed_df['document'] == doc]
        best_system = doc_data.nsmallest(1, 'cer').iloc[0]
        worst_system = doc_data.nlargest(1, 'cer').iloc[0]

        # Shorten document name
        short_name = "Anonymous 1682" if "Anonymous" in doc else "Young 1807"

        doc_performance[short_name] = {
            'best_system': best_system['system'],
            'best_cer': best_system['cer'],
            'worst_system': worst_system['system'],
            'worst_cer': worst_system['cer'],
            'cer_range': worst_system['cer'] - best_system['cer']
        }

    # Calculate performance ranges
    cer_range = summary_df['Mean CER'].max() - summary_df['Mean CER'].min()
    wer_range = summary_df['Mean WER'].max() - summary_df['Mean WER'].min()

    # Create narrative text
    narrative = []
    narrative.append("# Table OCR Performance - Narrative Statistics")
    narrative.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    narrative.append("")
    narrative.append("## Overall Performance")
    narrative.append("")
    narrative.append(f"We evaluated 9 OCR systems on 2 historical table documents (dated 1682 and 1807).")
    narrative.append("")
    narrative.append(f"**Best Overall System (CER):** {best_cer['OCR System']} achieved the lowest character ")
    narrative.append(f"error rate of {best_cer['Mean CER']:.3f}, demonstrating superior accuracy in ")
    narrative.append(f"transcribing tabular data from historical documents.")
    narrative.append("")
    narrative.append(f"**Best Word Accuracy:** {best_wer['OCR System']} achieved the lowest word error ")
    narrative.append(f"rate of {best_wer['Mean WER']:.3f}, indicating strong performance at the word level.")
    narrative.append("")
    narrative.append(f"**Best Semantic Similarity:** {best_bleu['OCR System']} achieved the highest BLEU ")
    narrative.append(f"score of {best_bleu['Mean BLEU Score']:.3f}, showing the best semantic preservation ")
    narrative.append(f"of the original tabular content.")
    narrative.append("")
    narrative.append("## Performance Range")
    narrative.append("")
    narrative.append(f"Character error rates ranged from {summary_df['Mean CER'].min():.3f} ")
    narrative.append(f"({summary_df.nsmallest(1, 'Mean CER').iloc[0]['OCR System']}) to ")
    narrative.append(f"{summary_df['Mean CER'].max():.3f} ({worst_cer['OCR System']}), ")
    narrative.append(f"representing a span of {cer_range:.3f} or {cer_range*100:.1f}% across systems.")
    narrative.append("")
    narrative.append("## Document-Specific Analysis")
    narrative.append("")

    for doc_name, perf in doc_performance.items():
        narrative.append(f"### {doc_name}")
        narrative.append("")
        narrative.append(f"- **Best:** {perf['best_system']} (CER: {perf['best_cer']:.3f})")
        narrative.append(f"- **Worst:** {perf['worst_system']} (CER: {perf['worst_cer']:.3f})")
        narrative.append(f"- **Range:** {perf['cer_range']:.3f} ({perf['cer_range']*100:.1f}%)")
        narrative.append("")

    # Check for perfect scores
    perfect_scores = detailed_df[detailed_df['cer'] == 0.0]
    if len(perfect_scores) > 0:
        narrative.append("## Perfect Scores")
        narrative.append("")
        narrative.append("The following systems achieved perfect character-level accuracy on specific documents:")
        narrative.append("")
        for _, row in perfect_scores.iterrows():
            doc_name = "Anonymous 1682" if "Anonymous" in row['document'] else "Young 1807"
            narrative.append(f"- **{row['system']}** on {doc_name} (CER: 0.000, BLEU: {row['bleu']:.3f})")
        narrative.append("")

    # Top 3 systems
    narrative.append("## Top 3 Systems by CER")
    narrative.append("")
    top_3 = summary_df.nsmallest(3, 'Mean CER')
    for idx, (_, row) in enumerate(top_3.iterrows(), 1):
        narrative.append(f"{idx}. **{row['OCR System']}**: CER={row['Mean CER']:.3f}, "
                        f"WER={row['Mean WER']:.3f}, BLEU={row['Mean BLEU Score']:.3f}")
    narrative.append("")

    # Key insights
    narrative.append("## Key Insights")
    narrative.append("")

    # Check if one document type was harder
    anon_avg = detailed_df[detailed_df['document'].str.contains('Anonymous')]['cer'].mean()
    young_avg = detailed_df[detailed_df['document'].str.contains('Young')]['cer'].mean()

    if anon_avg > young_avg * 1.5:
        narrative.append(f"- The text-heavy table (Anonymous 1682) proved significantly more challenging ")
        narrative.append(f"  than the numerical table (Young 1807), with an average CER of {anon_avg:.3f} ")
        narrative.append(f"  compared to {young_avg:.3f}.")
    elif young_avg > anon_avg * 1.5:
        narrative.append(f"- The numerical table (Young 1807) proved significantly more challenging ")
        narrative.append(f"  than the text-heavy table (Anonymous 1682), with an average CER of {young_avg:.3f} ")
        narrative.append(f"  compared to {anon_avg:.3f}.")
    else:
        narrative.append(f"- Both documents presented similar difficulty levels, with average CERs of ")
        narrative.append(f"  {anon_avg:.3f} (Anonymous 1682) and {young_avg:.3f} (Young 1807).")
    narrative.append("")

    # Error type analysis
    top_system = summary_df.nsmallest(1, 'Mean CER').iloc[0]
    narrative.append(f"- The best-performing system ({top_system['OCR System']}) exhibited an error ")
    narrative.append(f"  distribution of {top_system['Char Ins %']:.1f}% insertions, ")
    narrative.append(f"  {top_system['Char Del %']:.1f}% deletions, and ")
    narrative.append(f"  {top_system['Char Sub %']:.1f}% substitutions.")
    narrative.append("")

    narrative_text = "\n".join(narrative)

    # Save narrative
    output_file = output_dir / "table_narrative_statistics.txt"
    output_file.write_text(narrative_text, encoding='utf-8')

    print(f"  [SAVED] {output_file}")

    return narrative_text


def main():
    """Generate all book materials"""
    results_dir = Path(r'Z:\Tables\results')

    print("=" * 80)
    print("GENERATING TABLE EVALUATION BOOK MATERIALS")
    print("=" * 80)
    print()

    # Load latest results
    summary_files = sorted(list(results_dir.glob('table_evaluation_summary_*.csv')), reverse=True)
    detailed_files = sorted(list(results_dir.glob('table_evaluation_detailed_*.csv')), reverse=True)

    if not summary_files:
        print("ERROR: No evaluation results found!")
        return

    summary_df = pd.read_csv(summary_files[0])
    detailed_df = pd.read_csv(detailed_files[0])

    print(f"Loaded results: {summary_files[0].name}")
    print()

    # Create output directory
    output_dir = results_dir / 'book_materials'
    output_dir.mkdir(exist_ok=True)

    # Generate materials
    generate_latex_table(summary_df, output_dir)
    generate_narrative_statistics(summary_df, detailed_df, output_dir)

    print()
    print("=" * 80)
    print("[SUCCESS] ALL BOOK MATERIALS GENERATED")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    print("  - table_performance_latex.tex")
    print("  - table_narrative_statistics.txt")
    print()


if __name__ == "__main__":
    main()
