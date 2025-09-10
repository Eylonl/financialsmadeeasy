"""
Financial Statement Extraction Logic
"""

import re
import pandas as pd
from table_parser import find_best_table_by_indicators, parse_table_to_financial_data

def process_financial_extraction(filings, statement_types, ticker, exhibit_extractor, recon_threshold, st, status_text, progress_bar):
    """Main function to process financial statement extraction"""
    
    # Step 3: Extract financial statements using AI
    status_text.text("🤖 Extracting financial statements with AI...")
    progress_bar.progress(60)

    all_financial_data = {}

    # Create a mapping of filing dates to exhibit URLs early
    filing_date_to_url = {}
    for filing in filings:
        filing_date = filing.get('filing_date', '')
        exhibit_url = filing.get('exhibit_url', '')
        if filing_date and exhibit_url:
            filing_date_to_url[filing_date] = exhibit_url

    # Show AI extraction debug info
    with st.expander("🔍 Debug: AI Extraction Process", expanded=False):
        st.write(f"**Filing Date to URL Mapping:** {filing_date_to_url}")
        
        for i, filing in enumerate(filings):
            st.write(f"**Processing Filing {i+1}:**")
            if 'content' in filing and filing['content']:
                st.write(f"- Date: {filing['filing_date']}")
                st.write(f"- Content length: {len(filing['content']):,} characters")
                
                for statement_type in statement_types:
                    try:
                        with st.expander(f"Extract {statement_type.replace('_', ' ').title()}", expanded=False):
                            st.write(f"Extracting {statement_type} from {filing['filing_date']}...")
                            
                            # Get the specific financial table content
                            table_content = filing.get('financial_tables', {}).get(statement_type, '')
                            if not table_content:
                                st.warning(f"No {statement_type} table found - skipping extraction")
                                continue
                            
                            st.write(f"Content length: {len(table_content)} characters")
                            
                            # Debug: Show table content preview
                            st.write("**Table Content Preview:**")
                            preview = table_content[:1000] + "..." if len(table_content) > 1000 else table_content
                            st.text(preview)
                            
                            # Extract using the enhanced Exhibit 99.1 pipeline
                            full_content = filing.get('content', '')
                            if full_content:
                                exhibit_results = exhibit_extractor.extract_all_tables(full_content, f"{ticker}_{filing['filing_date']}")
                                
                                if exhibit_results.get('status') == 'success':
                                    if statement_type == 'gaap_reconciliation':
                                        extracted_data = process_reconciliation_extraction(
                                            exhibit_results, recon_threshold, st
                                        )
                                    else:
                                        extracted_data = process_standard_extraction(
                                            exhibit_results, statement_type, st
                                        )
                                else:
                                    extracted_data = {"periods": [], "data": {}}
                            else:
                                extracted_data = {"periods": [], "data": {}}
                            
                            # Store the extracted data
                            filing_data = store_extracted_data(
                                all_financial_data, ticker, filing, statement_type, extracted_data, st
                            )
                            
                    except Exception as e:
                        st.error(f"❌ Error extracting {statement_type}: {e}")
            else:
                st.warning("No content available for this filing")
    
    return all_financial_data

def process_reconciliation_extraction(exhibit_results, recon_threshold, st):
    """Process GAAP reconciliation extraction with candidate scoring"""
    if exhibit_results.get('status') == 'success' and exhibit_results.get('candidate_tables'):
        # Find ALL reconciliation candidates with good scores
        good_candidates = []
        
        for score in exhibit_results.get('scores', []):
            # Handle both ReconScore objects and dictionaries
            if hasattr(score, 'table_id'):
                # ReconScore object
                table_id = score.table_id
                recon_score = score.recon_score
                recon_candidate = score.recon_candidate
                recon_rationale = score.recon_rationale
            else:
                # Dictionary
                table_id = score.get('table_id')
                recon_score = score.get('recon_score')
                recon_candidate = score.get('recon_candidate')
                recon_rationale = score.get('recon_rationale', [])
            
            st.write(f"🔍 **Table {table_id}:** Score={recon_score:.1f}, Candidate={recon_candidate}")
            st.write(f"   Rationale: {recon_rationale[:3]}")  # First 3 reasons
            if recon_candidate and recon_score > recon_threshold:
                # Find corresponding table
                for table in exhibit_results['candidate_tables']:
                    if table.get('table_id') == table_id:
                        good_candidates.append((table, recon_score))
                        break
        
        # Sort by score, highest first
        good_candidates.sort(key=lambda x: x[1], reverse=True)
        
        if good_candidates:
            # Process all good reconciliation tables and combine data
            all_reconciliation_data = {"periods": [], "data": {}}
            
            for candidate, score in good_candidates:
                st.write(f"🔍 **Processing Table {candidate.get('table_id')}** (Score: {score:.1f})")
                st.write(f"   Candidate keys: {list(candidate.keys())}")
                
                # Parse table using the comprehensive debugging function
                table_data = parse_table_to_financial_data(candidate, st, 'gaap_reconciliation')
                
                if table_data and table_data.get('periods') and table_data.get('data'):
                    # Add to all_reconciliation_data
                    if not all_reconciliation_data["periods"]:
                        all_reconciliation_data["periods"] = table_data["periods"]
                    
                    for line_item, values in table_data["data"].items():
                        if line_item not in all_reconciliation_data["data"]:
                            all_reconciliation_data["data"][line_item] = values
                else:
                    st.warning(f"No data extracted from table {candidate.get('table_id')}")
            
            # Use combined data from all reconciliation tables
            extracted_data = all_reconciliation_data
            st.success(f"🎯 Combined {len(good_candidates)} reconciliation tables")
            st.write(f"📊 Extracted {len(extracted_data['data'])} line items across {len(extracted_data['periods'])} periods")
            
        else:
            extracted_data = {"periods": [], "data": {}}
            st.warning("No high-scoring reconciliation candidates found")
    else:
        extracted_data = {"periods": [], "data": {}}
        st.warning("No reconciliation candidates found")
    
    return extracted_data

def process_standard_extraction(exhibit_results, statement_type, st):
    """Process standard financial statement extraction"""
    st.write(f"🔍 **Processing {statement_type} - Non-reconciliation path**")
    st.write(f"🔍 **Exhibit results status:** {exhibit_results.get('status')}")
    st.write(f"🔍 **Available tables:** {len(exhibit_results.get('tables', []))}")
    
    if exhibit_results.get('tables'):
        # Find the best table based on statement type indicators
        best_table = find_best_table_by_indicators(
            exhibit_results['tables'], 
            statement_type,
            st
        )
        
        if best_table:
            # Parse table to financial data format with statement type for proper period detection
            extracted_data = parse_table_to_financial_data(best_table, st, statement_type)
        else:
            extracted_data = {"periods": [], "data": {}}
    else:
        extracted_data = {"periods": [], "data": {}}
        st.warning("Exhibit 99.1 extraction failed")
    
    return extracted_data

def store_extracted_data(all_financial_data, ticker, filing, statement_type, extracted_data, st):
    """Store extracted data in the main data structure"""
    if ticker not in all_financial_data:
        all_financial_data[ticker] = []
    
    # Find or create filing data for this date
    filing_data = None
    for existing_filing in all_financial_data[ticker]:
        if existing_filing.get('filing_date') == filing['filing_date']:
            filing_data = existing_filing
            break
    
    if filing_data is None:
        filing_data = {'filing_date': filing['filing_date']}
        all_financial_data[ticker].append(filing_data)
    
    # Process and store extracted data
    if (extracted_data and 
        isinstance(extracted_data, dict) and 
        'periods' in extracted_data and 
        'data' in extracted_data):
        
        # Add filing links
        exhibit_url = filing.get('exhibit_url', '')
        if exhibit_url:
            filing_links = {}
            for period in extracted_data['periods']:
                filing_links[period] = exhibit_url
            extracted_data['filing_links'] = filing_links
        
        # Clean data
        if extracted_data.get('data'):
            cleaned_data = {}
            for line_item, values in extracted_data['data'].items():
                cleaned_values = []
                for value in values:
                    value_str = str(value)
                    if value_str and value_str not in ['', 'nan']:
                        cleaned_value = re.sub(r'[^\w\s\.\-]', '', value_str).strip()
                        cleaned_values.append(cleaned_value if cleaned_value else value_str)
                    else:
                        cleaned_values.append(value)
                cleaned_data[line_item] = cleaned_values
            extracted_data['data'] = cleaned_data
        
        filing_data[statement_type] = extracted_data
        st.success(f"✅ Successfully extracted {statement_type}")
        
        # Show summary
        periods = extracted_data.get('periods', [])
        data_items = list(extracted_data.get('data', {}).keys())
        st.write(f"- Periods: {periods}")
        st.write(f"- Line items: {len(data_items)} items")
        if data_items:
            st.write(f"- Sample items: {data_items[:3]}")
        
        # Add preview table
        show_extraction_preview(extracted_data, periods, st)
        
    else:
        filing_data[statement_type] = extracted_data if extracted_data else {"periods": [], "data": {}}
        st.error(f"❌ Failed to extract {statement_type}")
    
    return filing_data

def show_extraction_preview(extracted_data, periods, st):
    """Show preview of extracted data"""
    with st.expander("📊 Preview Extracted Data", expanded=False):
        preview_data = []
        for item, values in extracted_data.get('data', {}).items():
            row = [item] + values[:len(periods)]
            preview_data.append(row)
        
        if preview_data:
            # Clean the actual data values (remove symbols from cells)
            cleaned_preview_data = []
            for row in preview_data:
                cleaned_row = []
                for i, cell in enumerate(row):
                    if i == 0:  # Keep line item as is
                        cleaned_row.append(cell)
                    else:
                        # Clean cell values - remove symbols but keep numbers
                        cell_str = str(cell)
                        if cell_str and cell_str not in ['', 'nan']:
                            # Only remove non-numeric symbols, keep decimal points and negative signs
                            cleaned_cell = re.sub(r'[^\w\s\.\-]', '', cell_str).strip()
                            cleaned_row.append(cleaned_cell if cleaned_cell else cell_str)
                        else:
                            cleaned_row.append(cell)
                cleaned_preview_data.append(cleaned_row)
            
            # Clean column headers for preview (remove symbols)
            clean_periods = []
            for period in periods:
                clean_period = re.sub(r'[^\w\s]', '', str(period))  # Remove symbols
                clean_period = re.sub(r'\s+', ' ', clean_period).strip()  # Normalize whitespace
                if not clean_period or clean_period.lower() in ['period', 'unnamed']:
                    clean_period = f"Period_{len(clean_periods)+1}"
                clean_periods.append(clean_period)
            
            preview_df = pd.DataFrame(cleaned_preview_data, columns=['Line Item'] + clean_periods)
            st.dataframe(preview_df, use_container_width=True)
