"""
Test script for the 8-K Exhibit 99.1 extraction pipeline
"""
from exhibit_99_1_extractor import Exhibit99Extractor
import json

def test_extraction_pipeline():
    """Test the complete extraction pipeline with sample data"""
    
    # Sample 8-K Exhibit 99.1 HTML with multiple reconciliation tables
    sample_html = """
    <html>
    <body>
    <h2>Reconciliation of GAAP to Non-GAAP Financial Measures</h2>
    <p>(in thousands, except per share data)</p>
    
    <table>
        <caption>Reconciliation of GAAP Net Loss to Non-GAAP Net Income</caption>
        <tr>
            <th>Line Item</th>
            <th>Three Months Ended March 31, 2024</th>
            <th>Three Months Ended December 31, 2023</th>
            <th>Three Months Ended September 30, 2023</th>
        </tr>
        <tr>
            <td>GAAP net loss</td>
            <td>(45,000)</td>
            <td>(50,000)</td>
            <td>(55,000)</td>
        </tr>
        <tr>
            <td>Stock-based compensation</td>
            <td>15,000</td>
            <td>18,000</td>
            <td>20,000</td>
        </tr>
        <tr>
            <td>Amortization of intangible assets</td>
            <td>8,000</td>
            <td>9,000</td>
            <td>10,000</td>
        </tr>
        <tr>
            <td>Acquisition-related costs</td>
            <td>2,000</td>
            <td>3,000</td>
            <td>4,000</td>
        </tr>
        <tr>
            <td>Restructuring charges</td>
            <td>1,500</td>
            <td>2,500</td>
            <td>3,500</td>
        </tr>
        <tr>
            <td>Tax effects of adjustments</td>
            <td>(3,200)</td>
            <td>(4,100)</td>
            <td>(5,200)</td>
        </tr>
        <tr>
            <td>Non-GAAP net income (loss)</td>
            <td>(21,700)</td>
            <td>(21,600)</td>
            <td>(22,700)</td>
        </tr>
    </table>
    
    <h3>Operating Income Reconciliation</h3>
    <table>
        <tr>
            <th></th>
            <th>Q1 2024</th>
            <th>Q4 2023</th>
        </tr>
        <tr>
            <td>GAAP loss from operations</td>
            <td>(35,000)</td>
            <td>(40,000)</td>
        </tr>
        <tr>
            <td>Stock-based compensation</td>
            <td>12,000</td>
            <td>15,000</td>
        </tr>
        <tr>
            <td>Amortization of intangibles</td>
            <td>6,000</td>
            <td>7,000</td>
        </tr>
        <tr>
            <td>Non-GAAP income from operations</td>
            <td>(17,000)</td>
            <td>(18,000)</td>
        </tr>
    </table>
    
    <h3>Customer Metrics (Non-Financial)</h3>
    <table>
        <tr>
            <th>Metric</th>
            <th>Q1 2024</th>
            <th>Q4 2023</th>
        </tr>
        <tr>
            <td>Total Customers</td>
            <td>125,000</td>
            <td>120,000</td>
        </tr>
        <tr>
            <td>Active Users</td>
            <td>95,000</td>
            <td>90,000</td>
        </tr>
    </table>
    </body>
    </html>
    """
    
    print("Testing 8-K Exhibit 99.1 Extraction Pipeline")
    print("=" * 50)
    
    try:
        # Initialize extractor
        extractor = Exhibit99Extractor("test_outputs")
        
        # Run complete extraction
        results = extractor.extract_all_tables(sample_html, "TEST_FILING_001")
        
        # Print summary
        summary = extractor.get_extraction_summary(results)
        print(summary)
        
        # Show detailed results
        print("\nDetailed Results:")
        print(f"Status: {results['status']}")
        print(f"Total Tables: {results['total_tables']}")
        print(f"Reconciliation Candidates: {results['reconciliation_candidates']}")
        
        # Show top reconciliation candidates
        if results['scores']:
            print("\nTop Reconciliation Scores:")
            top_scores = sorted(results['scores'], key=lambda x: x.recon_score, reverse=True)[:3]
            for i, score in enumerate(top_scores, 1):
                print(f"{i}. {score.table_id}: {score.recon_score:.1f} points")
                print(f"   Rationale: {score.recon_rationale[:2]}")
        
        # Show generated files
        print(f"\nGenerated Files:")
        for file_type, file_path in results['files'].items():
            print(f"- {file_type}: {file_path}")
        
        print("\n[SUCCESS] Pipeline test completed successfully!")
        
        return results
        
    except Exception as e:
        print(f"[ERROR] Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_individual_components():
    """Test individual pipeline components"""
    
    print("\nTesting Individual Components")
    print("=" * 30)
    
    # Test HTML table extraction
    from extractors.html_tables import HTMLTableExtractor
    extractor = HTMLTableExtractor()
    
    simple_html = """
    <table>
        <tr><th>Item</th><th>Value</th></tr>
        <tr><td>Revenue</td><td>$1,000</td></tr>
        <tr><td>Expenses</td><td>($800)</td></tr>
    </table>
    """
    
    tables = extractor.extract_all_tables(simple_html)
    print(f"[OK] HTML Extraction: Found {len(tables)} tables")
    
    # Test number normalization
    from normalizers.numbers import NumberNormalizer
    normalizer = NumberNormalizer()
    
    test_values = ["$1,000", "(500)", "25.5%", "—", "N/A"]
    print("[OK] Number Normalization:")
    for value in test_values:
        result = normalizer.normalize_cell_value(value)
        print(f"   '{value}' -> {result.number_value} ({result.parsing_notes})")
    
    # Test period parsing
    from normalizers.periods import PeriodNormalizer
    period_normalizer = PeriodNormalizer()
    
    test_periods = ["Three months ended March 31, 2024", "Q1 2024", "FY 2023"]
    print("[OK] Period Parsing:")
    for period in test_periods:
        result = period_normalizer.normalize_period_header(period)
        print(f"   '{period}' -> {result.period_type} ending {result.period_end_date}")
    
    # Test vocabulary matching
    from normalizers.vocab import VocabularyNormalizer
    vocab_normalizer = VocabularyNormalizer()
    
    test_labels = ["Stock-based compensation", "GAAP net loss", "Adjusted operating income"]
    print("[OK] Vocabulary Matching:")
    for label in test_labels:
        result = vocab_normalizer.normalize_label(label)
        print(f"   '{label}' -> {result.label_group} (confidence: {result.confidence_score:.2f})")

if __name__ == "__main__":
    # Run tests
    test_individual_components()
    print("\n" + "="*60 + "\n")
    test_extraction_pipeline()
