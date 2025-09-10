"""
Test script for the enhanced GAAP reconciliation extractor
"""
import os
from extractors.gaap_extractor import GaapExtractor

def test_gaap_extractor():
    """Test the enhanced GAAP extractor with sample reconciliation data"""
    
    # Sample HTML content with GAAP reconciliation table
    sample_html = """
    <html>
    <body>
    <h2>Reconciliation of GAAP to Non-GAAP Financial Measures</h2>
    <table>
        <tr>
            <th>Line Item</th>
            <th>Q3 2024</th>
            <th>Q2 2024</th>
            <th>Q1 2024</th>
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
            <td>Non-GAAP net income (loss)</td>
            <td>(20,000)</td>
            <td>(20,000)</td>
            <td>(21,000)</td>
        </tr>
        <tr>
            <td>GAAP loss per share, basic and diluted</td>
            <td>(0.45)</td>
            <td>(0.50)</td>
            <td>(0.55)</td>
        </tr>
        <tr>
            <td>Non-GAAP earnings per share, basic</td>
            <td>(0.20)</td>
            <td>(0.20)</td>
            <td>(0.21)</td>
        </tr>
    </table>
    </body>
    </html>
    """
    
    print("Testing Enhanced GAAP Reconciliation Extractor")
    print("=" * 60)
    
    try:
        # Initialize extractor
        extractor = GaapExtractor()
        print("[OK] GAAP extractor initialized successfully")
        
        # Test pattern initialization
        print(f"[INFO] Reconciliation header patterns: {len(extractor.reconciliation_headers)}")
        print(f"[INFO] GAAP line patterns: {len(extractor.gaap_line_patterns)}")
        print(f"[INFO] Adjustment patterns: {len(extractor.adjustment_patterns)}")
        print(f"[INFO] Non-GAAP patterns: {len(extractor.non_gaap_patterns)}")
        
        # Test reconciliation section detection
        sections = extractor._find_reconciliation_sections(sample_html)
        print(f"[SEARCH] Found {len(sections)} reconciliation sections")
        
        if sections:
            best_section = extractor._select_best_reconciliation_section(sections)
            print(f"[SELECT] Selected best section (length: {len(best_section)} chars)")
            
            # Test table-based extraction
            table_result = extractor._extract_from_reconciliation_tables(best_section, "Test Company")
            print(f"[TABLE] Table extraction result: {len(table_result.get('data', {}))} line items")
            
            if table_result.get('data'):
                print("[SUCCESS] Table-based extraction successful!")
                print(f"   Periods: {table_result.get('periods', [])}")
                print(f"   Line items: {list(table_result.get('data', {}).keys())}")
            else:
                print("[WARNING] Table-based extraction returned no data")
        
        # Test full extraction
        print("\n[TEST] Testing full GAAP reconciliation extraction...")
        result = extractor.extract_gaap_reconciliation(sample_html, "Test Company")
        
        print(f"[RESULTS] Extraction Results:")
        print(f"   Periods found: {len(result.get('periods', []))}")
        print(f"   Line items extracted: {len(result.get('data', {}))}")
        print(f"   Token usage: {extractor.last_token_usage}")
        
        if result.get('data'):
            print("\n[DATA] Extracted Line Items:")
            for item, values in result['data'].items():
                print(f"   • {item}: {values}")
        
        print("\n[SUCCESS] Enhanced GAAP extractor test completed successfully!")
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gaap_extractor()
