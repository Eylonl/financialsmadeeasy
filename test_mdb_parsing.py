#!/usr/bin/env python3
"""
Test script for MDB-style table parsing with the enhanced extraction pipeline.
This simulates the structure of MongoDB's reconciliation tables.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from exhibit_99_1_extractor import Exhibit99Extractor

# Sample HTML content that mimics MDB's reconciliation table structure
sample_mdb_html = """
<html>
<body>
<div>
<p><strong>MONGODB, INC.</strong></p>
<p><strong>Reconciliation of GAAP to Non-GAAP Financial Measures</strong></p>
<p>(in thousands, except per share data)</p>

<table border="1" cellpadding="3" cellspacing="0">
<tr>
<td><strong>&nbsp;</strong></td>
<td align="center"><strong>Three Months Ended April 30,</strong></td>
<td align="center"><strong>Three Months Ended April 30,</strong></td>
</tr>
<tr>
<td><strong>&nbsp;</strong></td>
<td align="center"><strong>2024</strong></td>
<td align="center"><strong>2023</strong></td>
</tr>
<tr>
<td><strong>Reconciliation of GAAP gross profit to non-GAAP gross profit:</strong></td>
<td>&nbsp;</td>
<td>&nbsp;</td>
</tr>
<tr>
<td>Gross profit (GAAP basis)</td>
<td align="right">$&nbsp;&nbsp;&nbsp;277,861</td>
<td align="right">$&nbsp;&nbsp;&nbsp;270,431</td>
</tr>
<tr>
<td>Add back:</td>
<td>&nbsp;</td>
<td>&nbsp;</td>
</tr>
<tr>
<td>&nbsp;&nbsp;&nbsp;&nbsp;Expenses associated with stock-based compensation: Cost of Revenue—Subscription</td>
<td align="right">6,497</td>
<td align="right">5,638</td>
</tr>
<tr>
<td>&nbsp;&nbsp;&nbsp;&nbsp;Expenses associated with stock-based compensation: Cost of Revenue—Services</td>
<td align="right">2,413</td>
<td align="right">3,163</td>
</tr>
<tr>
<td><strong>Non-GAAP gross profit</strong></td>
<td align="right"><strong>$&nbsp;&nbsp;&nbsp;286,771</strong></td>
<td align="right"><strong>$&nbsp;&nbsp;&nbsp;279,232</strong></td>
</tr>
<tr>
<td><strong>Non-GAAP gross margin (Non-GAAP gross profit/Total revenue)</strong></td>
<td align="right"><strong>79.7%</strong></td>
<td align="right"><strong>79.7%</strong></td>
</tr>

<tr>
<td><strong>Reconciliation of GAAP operating expenses to non-GAAP operating expenses:</strong></td>
<td>&nbsp;</td>
<td>&nbsp;</td>
</tr>
<tr>
<td>Sales and marketing operating expense (a GAAP basis)</td>
<td align="right">$&nbsp;&nbsp;&nbsp;219,484</td>
<td align="right">$&nbsp;&nbsp;&nbsp;182,733</td>
</tr>
<tr>
<td>Less:</td>
<td>&nbsp;</td>
<td>&nbsp;</td>
</tr>
<tr>
<td>&nbsp;&nbsp;&nbsp;&nbsp;Expenses associated with stock-based compensation</td>
<td align="right">45,154</td>
<td align="right">40,331</td>
</tr>
<tr>
<td>&nbsp;&nbsp;&nbsp;&nbsp;Amortization of intangible assets</td>
<td align="right">760</td>
<td align="right">760</td>
</tr>
<tr>
<td><strong>Non-GAAP sales and marketing operating expense</strong></td>
<td align="right"><strong>$&nbsp;&nbsp;&nbsp;173,570</strong></td>
<td align="right"><strong>$&nbsp;&nbsp;&nbsp;141,642</strong></td>
</tr>

<tr>
<td>Research and development operating expense (a GAAP basis)</td>
<td align="right">$&nbsp;&nbsp;&nbsp;156,066</td>
<td align="right">$&nbsp;&nbsp;&nbsp;116,817</td>
</tr>
<tr>
<td>Less:</td>
<td>&nbsp;</td>
<td>&nbsp;</td>
</tr>
<tr>
<td>&nbsp;&nbsp;&nbsp;&nbsp;Expenses associated with stock-based compensation</td>
<td align="right">57,766</td>
<td align="right">45,754</td>
</tr>
<tr>
<td>&nbsp;&nbsp;&nbsp;&nbsp;Amortization of intangible assets</td>
<td align="right">1,534</td>
<td align="right">1,534</td>
</tr>
<tr>
<td><strong>Non-GAAP research and development operating expense</strong></td>
<td align="right"><strong>$&nbsp;&nbsp;&nbsp;96,766</strong></td>
<td align="right"><strong>$&nbsp;&nbsp;&nbsp;69,529</strong></td>
</tr>

<tr>
<td>General and administrative operating expense (a GAAP basis)</td>
<td align="right">$&nbsp;&nbsp;&nbsp;60,546</td>
<td align="right">$&nbsp;&nbsp;&nbsp;50,828</td>
</tr>
<tr>
<td>Less:</td>
<td>&nbsp;</td>
<td>&nbsp;</td>
</tr>
<tr>
<td>&nbsp;&nbsp;&nbsp;&nbsp;Expenses associated with stock-based compensation</td>
<td align="right">16,845</td>
<td align="right">13,769</td>
</tr>
<tr>
<td>&nbsp;&nbsp;&nbsp;&nbsp;Amortization of intangible assets</td>
<td align="right">42,110</td>
<td align="right">25,048</td>
</tr>
<tr>
<td><strong>Non-GAAP general and administrative operating expense</strong></td>
<td align="right"><strong>$&nbsp;&nbsp;&nbsp;1,591</strong></td>
<td align="right"><strong>$&nbsp;&nbsp;&nbsp;12,011</strong></td>
</tr>

</table>
</div>
</body>
</html>
"""

def test_mdb_extraction():
    """Test the enhanced extraction pipeline with MDB-style content."""
    print("Testing Enhanced Extraction Pipeline with MDB-style Content")
    print("=" * 70)
    
    # Initialize the extractor
    extractor = Exhibit99Extractor("test_outputs")
    
    # Extract all tables
    print("Extracting tables...")
    results = extractor.extract_all_tables(sample_mdb_html, "MDB_TEST_2024-04-30")
    
    if results.get('status') == 'success':
        print(f"Extraction successful!")
        print(f"Total tables found: {results.get('total_tables', 0)}")
        print(f"Reconciliation candidates: {results.get('reconciliation_candidates', 0)}")
        
        # Show reconciliation candidates
        candidate_tables = results.get('candidate_tables', [])
        if candidate_tables:
            print("\nReconciliation Candidates:")
            for i, table in enumerate(candidate_tables):
                print(f"\n--- Table {i+1} ---")
                print(f"Table ID: {table.get('table_id')}")
                print(f"Headers: {table.get('headers', [])}")
                print(f"Row count: {len(table.get('rows', []))}")
                
                # Show first few rows
                rows = table.get('rows', [])
                print("First 5 rows:")
                for j, row in enumerate(rows[:5]):
                    print(f"  Row {j+1}: {row}")
        
        # Show scoring details
        scores = results.get('scores', [])
        if scores:
            print("\nScoring Details:")
            for score in scores:
                if score.recon_candidate:
                    print(f"Table {score.table_id}: Score {score.recon_score:.1f}")
                    if hasattr(score, 'rationale'):
                        print(f"  Rationale: {score.rationale}")
                    else:
                        print(f"  Recon candidate: {score.recon_candidate}")
        
        # Test the conversion logic (similar to what's in app.py)
        print("\nTesting Legacy Format Conversion:")
        if candidate_tables:
            best_candidate = candidate_tables[0]  # Take first candidate
            
            periods = []
            data = {}
            
            # Extract headers
            headers = best_candidate.get('headers', [])
            print(f"Raw headers: {headers}")
            
            if headers:
                for i, header in enumerate(headers):
                    if i == 0:  # Skip first column (labels)
                        continue
                        
                    if isinstance(header, dict):
                        period_text = header.get('original_header') or header.get('text') or header.get('original_text', '')
                    elif isinstance(header, str):
                        period_text = header
                    else:
                        period_text = str(header)
                    
                    if period_text and period_text.strip():
                        periods.append(period_text.strip())
            
            print(f"Extracted periods: {periods}")
            
            # Extract rows
            rows = best_candidate.get('rows', [])
            for row_idx, row in enumerate(rows):
                if not row or len(row) == 0:
                    continue
                    
                # Get label from first cell
                first_cell = row[0]
                if isinstance(first_cell, dict):
                    label = first_cell.get('original_text') or first_cell.get('text') or first_cell.get('normalized_text', '')
                elif isinstance(first_cell, str):
                    label = first_cell
                else:
                    label = str(first_cell)
                
                if not label or not label.strip():
                    continue
                
                label = label.strip()
                
                # Get values from remaining cells
                values = []
                for cell_idx in range(1, min(len(row), len(periods) + 1)):
                    if cell_idx < len(row):
                        cell = row[cell_idx]
                        if isinstance(cell, dict):
                            val = (cell.get('number_value') or 
                                  cell.get('normalized_value') or 
                                  cell.get('original_text') or 
                                  cell.get('text', ''))
                        elif cell is not None:
                            val = str(cell)
                        else:
                            val = ''
                    else:
                        val = ''
                    
                    values.append(val)
                
                # Pad values to match periods length
                while len(values) < len(periods):
                    values.append('')
                
                if label and any(v for v in values):
                    data[label] = values[:len(periods)]
            
            print(f"\nFinal extracted data:")
            print(f"Periods: {periods}")
            print(f"Data rows: {len(data)}")
            for label, values in list(data.items())[:5]:  # Show first 5 rows
                print(f"  {label}: {values}")
            
            if len(data) > 5:
                print(f"  ... and {len(data) - 5} more rows")
        
    else:
        print(f"Extraction failed: {results.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_mdb_extraction()
