"""
Test script for new extraction methods
"""
import os
from dotenv import load_dotenv
from extractors.hybrid_extractor import HybridExtractor
from extractors.smart_extractor import SmartExtractor

load_dotenv()

def test_extractors():
    """Test the new extraction methods with sample HTML content"""
    
    # Sample financial table HTML (simplified)
    sample_html = """
    <table>
        <tr>
            <th>Line Item</th>
            <th>Three Months Ended March 31, 2024</th>
            <th>Three Months Ended March 31, 2023</th>
        </tr>
        <tr>
            <td>Total Revenue</td>
            <td>$123,456</td>
            <td>$98,765</td>
        </tr>
        <tr>
            <td>Cost of Revenue</td>
            <td>$(45,678)</td>
            <td>$(38,901)</td>
        </tr>
        <tr>
            <td>Gross Profit</td>
            <td>$77,778</td>
            <td>$59,864</td>
        </tr>
        <tr>
            <td>Research & Development</td>
            <td>$(12,345)</td>
            <td>$(10,234)</td>
        </tr>
        <tr>
            <td>Sales and Marketing</td>
            <td>$(8,901)</td>
            <td>$(7,456)</td>
        </tr>
        <tr>
            <td>Net Income</td>
            <td>$25,432</td>
            <td>$18,765</td>
        </tr>
    </table>
    """
    
    print("Testing New Extraction Methods")
    print("=" * 50)
    
    # Test Hybrid Extractor
    print("\n1. Testing Hybrid Extractor:")
    try:
        hybrid = HybridExtractor()
        result = hybrid.extract_income_statement(sample_html, "Test Company")
        
        print(f"   Periods found: {len(result.get('periods', []))}")
        print(f"   Line items found: {len(result.get('data', {}))}")
        print(f"   Sample periods: {result.get('periods', [])[:2]}")
        print(f"   Sample line items: {list(result.get('data', {}).keys())[:3]}")
        
        if result.get('data'):
            print("   [SUCCESS] Hybrid extraction successful")
        else:
            print("   [FAILED] Hybrid extraction failed")
            
    except Exception as e:
        print(f"   [ERROR] Hybrid extractor error: {e}")
    
    # Test Smart Extractor
    print("\n2. Testing Smart Extractor:")
    try:
        smart = SmartExtractor()
        result = smart.extract_income_statement(sample_html, "Test Company")
        
        print(f"   Periods found: {len(result.get('periods', []))}")
        print(f"   Line items found: {len(result.get('data', {}))}")
        print(f"   Sample periods: {result.get('periods', [])[:2]}")
        print(f"   Sample line items: {list(result.get('data', {}).keys())[:3]}")
        
        if result.get('data'):
            print("   [SUCCESS] Smart extraction successful")
        else:
            print("   [FAILED] Smart extraction failed")
            
        # Show extraction stats
        stats = smart.get_extraction_stats()
        print(f"   Token usage: {stats.get('last_token_usage', 'N/A')}")
        print(f"   Method: {stats.get('extraction_method')}")
        
    except Exception as e:
        print(f"   [ERROR] Smart extractor error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("[ERROR] OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")
    else:
        test_extractors()
