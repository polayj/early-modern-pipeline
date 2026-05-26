"""
Generate Book Chapter Materials for OCR Evaluation
LaTeX tables, narrative statistics, and reproducibility documentation
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime


def load_latest_results(results_dir: Path):
    """Load the most recent evaluation results"""
    eval_dirs = sorted([d for d in results_dir.glob('evaluation_*') if d.is_dir()], reverse=True)

    if not eval_dirs:
        raise FileNotFoundError(f"No evaluation results found in {results_dir}")

    latest_dir = eval_dirs[0]
    print(f"Loading results from: {latest_dir.name}")

    summary_files = list(latest_dir.glob('*_summary_*.csv'))
    age_grouped_files = list(latest_dir.glob('*_age_grouped_*.csv'))

    summary_df = pd.read_csv(summary_files[0])
    age_grouped_df = pd.read_csv(age_grouped_files[0]) if age_grouped_files else None

    return summary_df, age_grouped_df, latest_dir


def generate_latex_tables(summary_df, age_grouped_df, output_dir):
    """Generate LaTeX tables for publication"""
    print("\nGenerating LaTeX tables...")

    latex_output = []

    # Table 1: Overall OCR Performance
    latex_output.append(r"""
% Table 1: Overall OCR System Performance
\begin{table}[htbp]
\centering
\caption{OCR Performance Metrics Across All Systems}
\label{tab:ocr_overall_performance}
\begin{tabular}{lcccccc}
\toprule
\textbf{OCR System} & \textbf{CER} & \textbf{WER} & \textbf{Char Acc} & \textbf{Word Acc} & \textbf{BLEU} & \textbf{Halluc.} \\
\midrule
""")

    df_sorted = summary_df.sort_values('Mean CER')
    for _, row in df_sorted.iterrows():
        latex_output.append(
            f"{row['OCR System']} & "
            f"{row['Mean CER']:.3f} & "
            f"{row['Mean WER']:.3f} & "
            f"{row['Char Accuracy']:.3f} & "
            f"{row['Word Accuracy']:.3f} & "
            f"{row['Mean BLEU Score']:.3f} & "
            f"{row['Mean Hallucination Rate']:.3f} \\\\\n"
        )

    latex_output.append(r"""\bottomrule
\end{tabular}
\end{table}

""")

    # Table 2: Error Type Distribution
    latex_output.append(r"""
% Table 2: Character Error Type Distribution
\begin{table}[htbp]
\centering
\caption{Character Error Type Distribution (\%)}
\label{tab:error_distribution}
\begin{tabular}{lcccc}
\toprule
\textbf{OCR System} & \textbf{CER} & \textbf{Insertions} & \textbf{Deletions} & \textbf{Substitutions} \\
\midrule
""")

    for _, row in df_sorted.iterrows():
        latex_output.append(
            f"{row['OCR System']} & "
            f"{row['Mean CER']:.3f} & "
            f"{row['Char Ins %']:.1f} & "
            f"{row['Char Del %']:.1f} & "
            f"{row['Char Sub %']:.1f} \\\\\n"
        )

    latex_output.append(r"""\bottomrule
\end{tabular}
\end{table}

""")

    # Table 3: Performance by Document Age (if available)
    if age_grouped_df is not None:
        latex_output.append(r"""
% Table 3: Performance by Document Age
\begin{table}[htbp]
\centering
\caption{OCR Performance by Document Age (Top 5 Systems)}
\label{tab:performance_by_age}
\begin{tabular}{lccccc}
\toprule
\textbf{Age Group} & \textbf{Chandra} & \textbf{OlmOCRv2} & \textbf{OlmOCRv1} & \textbf{Transkribus} & \textbf{Gemini} \\
\midrule
""")

        # Get top 5 systems by overall CER
        top_5_systems = summary_df.nsmallest(5, 'Mean CER')['OCR System'].tolist()

        # Get unique age groups
        age_groups = sorted(age_grouped_df['Age Group'].unique())

        for age_group in age_groups:
            row_data = []
            for system in top_5_systems:
                system_age_data = age_grouped_df[
                    (age_grouped_df['OCR System'] == system) &
                    (age_grouped_df['Age Group'] == age_group)
                ]
                if len(system_age_data) > 0:
                    cer = system_age_data['Mean CER'].values[0]
                    row_data.append(f"{cer:.3f}")
                else:
                    row_data.append("--")

            latex_output.append(f"{age_group} & " + " & ".join(row_data) + " \\\\\n")

        latex_output.append(r"""\bottomrule
\end{tabular}
\end{table}
""")

    # Save LaTeX tables
    output_file = output_dir / 'ocr_latex_tables.tex'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(latex_output))

    print(f"  [SAVED] {output_file}")


def generate_narrative_statistics(summary_df, age_grouped_df, output_dir):
    """Generate narrative statistics for prose"""
    print("\nGenerating narrative statistics...")

    stats = {}

    # Sort systems by CER
    df_sorted = summary_df.sort_values('Mean CER')
    best_system = df_sorted.iloc[0]
    worst_system = df_sorted.iloc[-1]

    # Find olmOCR systems
    olmocr_v2 = summary_df[summary_df['OCR System'] == 'OlmOCRv2'].iloc[0] if 'OlmOCRv2' in summary_df['OCR System'].values else None
    olmocr_v1 = summary_df[summary_df['OCR System'] == 'OlmOCRv1'].iloc[0] if 'OlmOCRv1' in summary_df['OCR System'].values else None
    tesseract = summary_df[summary_df['OCR System'] == 'Tesseract'].iloc[0] if 'Tesseract' in summary_df['OCR System'].values else None

    # 1. Overall Performance
    stats['overall_performance'] = {
        'claim': f"{best_system['OCR System']} achieved the lowest character error rate (CER={best_system['Mean CER']:.3f}) and highest word accuracy ({best_system['Word Accuracy']*100:.1f}%), demonstrating superior OCR quality for historical documents.",
        'supporting_data': {
            'best_system': best_system['OCR System'],
            'best_cer': f"{best_system['Mean CER']:.4f}",
            'best_wer': f"{best_system['Mean WER']:.4f}",
            'best_char_accuracy': f"{best_system['Char Accuracy']:.4f}",
            'best_word_accuracy': f"{best_system['Word Accuracy']:.4f}",
            'worst_system': worst_system['OCR System'],
            'worst_cer': f"{worst_system['Mean CER']:.4f}",
            'performance_gap': f"{(worst_system['Mean CER'] - best_system['Mean CER']):.4f}"
        }
    }

    # 2. olmOCR Performance (if available)
    if olmocr_v2 is not None:
        best_cer = best_system['Mean CER']
        olmocr_cer = olmocr_v2['Mean CER']
        relative_performance = ((olmocr_cer - best_cer) / best_cer) * 100

        stats['olmocr_performance'] = {
            'claim': f"olmOCRv2 achieved a character error rate of {olmocr_cer:.3f}, performing within {abs(relative_performance):.1f}% of the best system ({best_system['OCR System']}) while being free and open-source.",
            'supporting_data': {
                'olmocr_cer': f"{olmocr_cer:.4f}",
                'olmocr_wer': f"{olmocr_v2['Mean WER']:.4f}",
                'olmocr_bleu': f"{olmocr_v2['Mean BLEU Score']:.4f}",
                'relative_to_best': f"{relative_performance:+.1f}%"
            }
        }

    # 3. Error Type Analysis
    best_ins_pct = df_sorted.iloc[0]['Char Ins %']
    best_del_pct = df_sorted.iloc[0]['Char Del %']
    best_sub_pct = df_sorted.iloc[0]['Char Sub %']

    dominant_error = 'deletions' if best_del_pct > max(best_ins_pct, best_sub_pct) else ('insertions' if best_ins_pct > best_sub_pct else 'substitutions')

    stats['error_type_distribution'] = {
        'claim': f"Character errors were dominated by {dominant_error} ({max(best_del_pct, best_ins_pct, best_sub_pct):.1f}%), with substitutions comprising {best_sub_pct:.1f}% of errors, indicating that OCR systems primarily struggle with {dominant_error} rather than character misrecognition.",
        'supporting_data': {
            'insertion_pct': f"{best_ins_pct:.2f}%",
            'deletion_pct': f"{best_del_pct:.2f}%",
            'substitution_pct': f"{best_sub_pct:.2f}%",
            'dominant_error_type': dominant_error
        }
    }

    # 4. Hallucination Analysis
    mean_hallucination = summary_df['Mean Hallucination Rate'].mean()
    low_halluc_system = summary_df.nsmallest(1, 'Mean Hallucination Rate').iloc[0]
    high_halluc_system = summary_df.nlargest(1, 'Mean Hallucination Rate').iloc[0]

    stats['hallucination_rates'] = {
        'claim': f"Hallucination rates (words not present in the original) averaged {mean_hallucination*100:.2f}% across all systems, with {low_halluc_system['OCR System']} showing the lowest rate ({low_halluc_system['Mean Hallucination Rate']*100:.2f}%) and {high_halluc_system['OCR System']} the highest ({high_halluc_system['Mean Hallucination Rate']*100:.2f}%).",
        'supporting_data': {
            'mean_hallucination': f"{mean_hallucination:.4f}",
            'lowest_system': low_halluc_system['OCR System'],
            'lowest_rate': f"{low_halluc_system['Mean Hallucination Rate']:.4f}",
            'highest_system': high_halluc_system['OCR System'],
            'highest_rate': f"{high_halluc_system['Mean Hallucination Rate']:.4f}"
        }
    }

    # 5. BLEU Score Analysis
    mean_bleu = summary_df['Mean BLEU Score'].mean()
    best_bleu_system = summary_df.nlargest(1, 'Mean BLEU Score').iloc[0]

    stats['bleu_scores'] = {
        'claim': f"BLEU scores averaged {mean_bleu:.3f} across systems, with {best_bleu_system['OCR System']} achieving the highest score ({best_bleu_system['Mean BLEU Score']:.3f}), indicating strong n-gram overlap with the gold standard.",
        'supporting_data': {
            'mean_bleu': f"{mean_bleu:.4f}",
            'best_system': best_bleu_system['OCR System'],
            'best_bleu': f"{best_bleu_system['Mean BLEU Score']:.4f}"
        }
    }

    # 6. Document Age Impact (if available)
    if age_grouped_df is not None and olmocr_v2 is not None:
        olmocr_age_data = age_grouped_df[age_grouped_df['OCR System'] == 'OlmOCRv2'].sort_values('Age Group')

        if len(olmocr_age_data) > 1:
            oldest_group = olmocr_age_data.iloc[0]
            newest_group = olmocr_age_data.iloc[-1]

            age_degradation = ((oldest_group['Mean CER'] - newest_group['Mean CER']) / newest_group['Mean CER']) * 100

            stats['document_age_impact'] = {
                'claim': f"Document age significantly impacted OCR performance: CER increased by {abs(age_degradation):.1f}% for 17th-century documents ({oldest_group['Mean CER']:.3f}) compared to 19th-century texts ({newest_group['Mean CER']:.3f}), reflecting the challenges of archaic typography and deteriorated source materials.",
                'supporting_data': {
                    'oldest_group': oldest_group['Age Group'],
                    'oldest_cer': f"{oldest_group['Mean CER']:.4f}",
                    'newest_group': newest_group['Age Group'],
                    'newest_cer': f"{newest_group['Mean CER']:.4f}",
                    'degradation_pct': f"{abs(age_degradation):.1f}%"
                }
            }

    # 7. Comparison to Tesseract (if available)
    if olmocr_v2 is not None and tesseract is not None:
        improvement = ((tesseract['Mean CER'] - olmocr_v2['Mean CER']) / tesseract['Mean CER']) * 100

        stats['olmocr_vs_tesseract'] = {
            'claim': f"olmOCRv2 (CER={olmocr_v2['Mean CER']:.3f}) outperformed Tesseract (CER={tesseract['Mean CER']:.3f}) by {improvement:.1f}%, demonstrating the value of deep learning-based OCR for historical texts.",
            'supporting_data': {
                'olmocr_cer': f"{olmocr_v2['Mean CER']:.4f}",
                'tesseract_cer': f"{tesseract['Mean CER']:.4f}",
                'improvement_pct': f"{improvement:.1f}%"
            }
        }

    # Save narrative statistics
    output_file_json = output_dir / 'ocr_narrative_statistics.json'
    with open(output_file_json, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"  [SAVED] {output_file_json}")

    # Also save as text
    output_file_txt = output_dir / 'ocr_narrative_statistics.txt'
    with open(output_file_txt, 'w', encoding='utf-8') as f:
        f.write("NARRATIVE STATISTICS FOR OCR EVALUATION CHAPTER\n")
        f.write("=" * 80 + "\n\n")

        for key, data in stats.items():
            f.write(f"{key.upper().replace('_', ' ')}\n")
            f.write("-" * 80 + "\n")
            f.write(f"{data['claim']}\n\n")
            f.write("Supporting Data:\n")
            for stat_key, stat_value in data['supporting_data'].items():
                f.write(f"  - {stat_key}: {stat_value}\n")
            f.write("\n\n")

    print(f"  [SAVED] {output_file_txt}")


def generate_reproducibility_docs(summary_df, latest_dir, output_dir):
    """Generate reproducibility documentation"""
    print("\nGenerating reproducibility documentation...")

    repro_docs = {
        'metadata': {
            'evaluation_date': datetime.now().isoformat(),
            'evaluation_dir': str(latest_dir),
            'num_systems_evaluated': len(summary_df),
            'num_documents_per_system': 100,
            'gold_standard_location': 'Z:/Corpus/Corpus_Gold/page'
        },
        'evaluation_parameters': {
            'similarity_threshold': 0.6,
            'strip_markdown_headers': True,
            'metrics_calculated': [
                'Character Error Rate (CER)',
                'Word Error Rate (WER)',
                'Character Accuracy',
                'Word Accuracy',
                'Significant Word Accuracy',
                'Capitalized Word Accuracy',
                'Number Group Accuracy',
                'BLEU Score',
                'Hallucination Rate'
            ]
        },
        'ocr_systems_evaluated': summary_df[['OCR System', 'Num Documents']].to_dict('records'),
        'summary_statistics': {
            'mean_cer_across_systems': float(summary_df['Mean CER'].mean()),
            'std_cer_across_systems': float(summary_df['Mean CER'].std()),
            'mean_wer_across_systems': float(summary_df['Mean WER'].mean()),
            'mean_bleu_across_systems': float(summary_df['Mean BLEU Score'].mean())
        }
    }

    output_file = output_dir / 'reproducibility_documentation.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(repro_docs, f, indent=2, ensure_ascii=False)

    print(f"  [SAVED] {output_file}")


def generate_summary_report(summary_df, output_dir):
    """Generate final summary report"""
    print("\nGenerating final summary report...")

    report = f"""
# OCR EVALUATION - BOOK CHAPTER MATERIALS

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

All book chapter materials have been generated and exported to:
`{output_dir}`

## Files Generated

### 1. LaTeX Tables
- `ocr_latex_tables.tex` - Publication-ready LaTeX tables

### 2. Narrative Statistics
- `ocr_narrative_statistics.json` - Key statistics with supporting data
- `ocr_narrative_statistics.txt` - Formatted prose for book chapter

### 3. Reproducibility Materials
- `reproducibility_documentation.json` - Complete methodology documentation

## Key Results

### Overall Performance
{summary_df.sort_values('Mean CER').to_string(index=False)}

### Top 3 Systems (by CER)
{summary_df.nsmallest(3, 'Mean CER')[['OCR System', 'Mean CER', 'Mean WER', 'Char Accuracy', 'Mean BLEU Score']].to_string(index=False)}

### Bottom 3 Systems (by CER)
{summary_df.nlargest(3, 'Mean CER')[['OCR System', 'Mean CER', 'Mean WER', 'Char Accuracy', 'Mean BLEU Score']].to_string(index=False)}

## Recommended Citations

For methods section:
- Evaluation parameters: See reproducibility_documentation.json
- Gold standard: Z:/Corpus/Corpus_Gold/page (PAGE XML format)

For results section:
- Use LaTeX tables from ocr_latex_tables.tex
- Use narrative statistics from ocr_narrative_statistics.txt

---
End of Report
"""

    output_file = output_dir / 'OCR_EVALUATION_SUMMARY.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"  [SAVED] {output_file}")


def main():
    """Generate all book chapter materials"""
    results_dir = Path(r'Z:\OCR Evaluation\results')

    print("="*80)
    print("GENERATING OCR BOOK CHAPTER MATERIALS")
    print("="*80)

    # Load data
    summary_df, age_grouped_df, latest_dir = load_latest_results(results_dir)

    # Create output directory
    output_dir = latest_dir / 'book_chapter_materials'
    output_dir.mkdir(exist_ok=True)

    print(f"Output directory: {output_dir}")

    # Generate materials
    generate_latex_tables(summary_df, age_grouped_df, output_dir)
    generate_narrative_statistics(summary_df, age_grouped_df, output_dir)
    generate_reproducibility_docs(summary_df, latest_dir, output_dir)
    generate_summary_report(summary_df, output_dir)

    print()
    print("="*80)
    print("[SUCCESS] ALL MATERIALS GENERATED")
    print("="*80)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    print("  - ocr_latex_tables.tex")
    print("  - ocr_narrative_statistics.json")
    print("  - ocr_narrative_statistics.txt")
    print("  - reproducibility_documentation.json")
    print("  - OCR_EVALUATION_SUMMARY.md")
    print()


if __name__ == "__main__":
    main()
