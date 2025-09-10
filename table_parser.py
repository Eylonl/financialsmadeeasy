"""
Table Parsing Functions for Financial Data Extraction
"""

import re
import pandas as pd
from bs4 import BeautifulSoup

def find_best_table_by_indicators(tables, statement_type, st):
    """Find the best table based on statement type indicators"""
    best_table = None
    best_score = 0
    
    # Define indicators based on statement type
    if statement_type == 'income_statement':
        target_indicators = ['revenue', 'subscription', 'services', 'total revenue', 
                           'cost of revenue', 'gross profit', 'operating expenses',
                           'sales and marketing', 'research and development', 'net income']
        exclude_indicators = ['reconciliation', 'gaap to non-gaap', 'adjusted', 'non-gaap']
    elif statement_type == 'balance_sheet':
        target_indicators = ['assets', 'liabilities', 'stockholders equity', 'cash and equivalents',
                           'accounts receivable', 'property and equipment']
        exclude_indicators = ['reconciliation', 'gaap to non-gaap', 'adjusted', 'non-gaap']
    elif statement_type == 'cash_flow':
        target_indicators = ['cash flows', 'operating activities', 'investing activities', 
                           'financing activities', 'net cash']
        exclude_indicators = ['reconciliation', 'gaap to non-gaap', 'adjusted', 'non-gaap']
    elif statement_type == 'sbc_breakdown':
        target_indicators = ['stock-based compensation', 'share-based compensation', 'stock based compensation',
                           'expenses associated with stock-based compensation', 'share-based payment',
                           'compensation expense', 'equity compensation', 'stock-based compensation expense',
                           'includes stock-based compensation expense as follows', 'includes stock-based compensation',
                           'cost of revenue—subscription', 'cost of revenue—services', 'cost of revenue subscription',
                           'cost of revenue services', 'total stock-based compensation expense']
        exclude_indicators = ['reconciliation', 'gaap to non-gaap', 'adjusted', 'non-gaap', 
                            'gross profit on a gaap basis', 'gross margin', 'reconciliation of gaap',
                            'total revenue', 'cash flows from operating activities', 'net loss', 
                            'depreciation and amortization', 'cash flows', 'operating activities', 
                            'investing activities', 'financing activities']
    else:
        target_indicators = ['revenue', 'income', 'expense', 'total']
        exclude_indicators = []
    
    for table in tables:
        score = 0
        rows = table.get('rows', [])
        
        # Check all rows for target indicators and exclude unwanted tables
        exclude_score = 0
        for row in rows:
            for cell in row:
                if isinstance(cell, dict):
                    cell_text = cell.get('original_text', '').lower()
                else:
                    cell_text = str(cell).lower()
                
                # Count target indicators
                for indicator in target_indicators:
                    if indicator in cell_text:
                        score += 1
                
                # Count exclusion indicators (negative score)
                for exclude_indicator in exclude_indicators:
                    if exclude_indicator in cell_text:
                        exclude_score += 1
        
        # Calculate final score
        row_count = len(rows)
        if score > 0 and row_count > 5:  # Must have target indicators and reasonable size
            if (statement_type == 'income_statement' or statement_type == 'sbc_breakdown') and exclude_score > 0:
                total_score = 0  # Exclude reconciliation tables completely
                st.write(f"   Table excluded: {exclude_score} reconciliation indicators found")
            else:
                total_score = score * 10 + row_count  # Weight indicators heavily
                if total_score > best_score:
                    best_score = total_score
                    best_table = table
                    st.write(f"   Table candidate: {score} target indicators, {exclude_score} exclude indicators, {row_count} rows, score: {total_score}")
    
    # Fallback to largest table if no indicators found (but not for SBC breakdown)
    if not best_table:
        if statement_type == 'sbc_breakdown':
            st.write("   No SBC breakdown table found - SBC tables must contain specific stock compensation indicators")
            return None
        else:
            max_rows = 0
            for table in tables:
                row_count = len(table.get('rows', []))
                if row_count > max_rows:
                    max_rows = row_count
                    best_table = table
            st.write("   No indicators found, using largest table")
    
    return best_table

def parse_table_to_financial_data(table, st, statement_type=''):
    """Parse a table into financial data format"""
    try:
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        # Build HTML table for pandas parsing
        html_parts = ['<table><tr>']
        for i, header in enumerate(headers):
            if isinstance(header, dict):
                header_text = header.get('original_text', '').strip()
                if not header_text:
                    header_text = f'Column_{i}'
            else:
                header_text = str(header).strip()
            html_parts.append(f'<th>{header_text}</th>')
        html_parts.append('</tr>')
        
        # Store the raw HTML for period detection
        raw_table_html = ''.join(html_parts)
        
        for row in rows:
            html_parts.append('<tr>')
            for cell in row:
                if isinstance(cell, dict):
                    cell_text = cell.get('original_text', '')
                else:
                    cell_text = str(cell)
                html_parts.append(f'<td>{cell_text}</td>')
            html_parts.append('</tr>')
        html_parts.append('</table>')
        
        table_html = ''.join(html_parts)
        dfs = pd.read_html(table_html, header=0)
        
        if dfs:
            df = dfs[0].dropna(axis=1, how='all').fillna('')
            st.write(f"🔍 **DataFrame shape:** {df.shape}")
            st.write(f"🔍 **DataFrame columns:** {list(df.columns)}")
            
            # Use advanced period detection for all statement types
            period_headers = _extract_reconciliation_periods(raw_table_html, headers, rows, df, st)
            
            # Smart column grouping - couple related columns into periods
            data_columns = df.columns[1:].tolist()
            st.write(f"   Data columns to group: {data_columns}")
            
            column_groups = _group_columns_by_periods(data_columns, period_headers, st)
            merged_columns = _merge_column_groups(df, column_groups, period_headers, st)
            
            # Create final data structure
            periods, data = _create_final_data_structure(df, merged_columns)
            
            return {"periods": periods, "data": data}
        else:
            return {"periods": [], "data": {}}
    except Exception as e:
        st.error(f"🚨 Exception during table parsing: {str(e)}")
        return {"periods": [], "data": {}}

def _extract_reconciliation_periods(table_html, headers, rows, df, st):
    """Extract period headers for reconciliation tables with complex logic"""
    period_headers = []
    
    try:
        # Prepare context for analysis
        raw_table_text = table_html[:2000]
        
        # Extract original header text from structured headers
        original_header_texts = []
        for h in headers:
            if isinstance(h, dict):
                original_text = h.get('original_header', h.get('original_text', ''))
                original_header_texts.append(original_text)
            else:
                original_header_texts.append(str(h))
        
        table_context = {
            'raw_html': raw_table_text,
            'headers': original_header_texts,
        }
        
        # Get actual column headers from DataFrame
        df_headers = list(df.columns)
        full_periods = []
        
        st.write(f"🔍 **Starting Advanced Period Detection**")
        st.write(f"🔍 **DataFrame headers:** {df_headers}")
        st.write(f"🔍 **Original headers:** {original_header_texts}")
        
        # Debug: Show first few rows of DataFrame to see if period info is in the data
        st.write(f"🔍 **First 3 rows of DataFrame:**")
        for i in range(min(3, len(df))):
            row_data = df.iloc[i].tolist()
            st.write(f"   Row {i}: {row_data}")
        
        # First try: extract full period descriptions from DataFrame headers
        for header in df_headers[1:]:
            header_str = str(header).strip()
            if header_str and header_str not in ['nan', '']:
                if re.search(r'(Three|Six|Nine|Twelve)\s+Months?\s+Ended|Year\s+Ended|Quarter\s+Ended', header_str, re.IGNORECASE):
                    full_periods.append(header_str)
                    st.write(f"🔍 **Found period in DataFrame header:** {header_str}")
                elif re.search(r'\b20\d{2}\b', header_str):
                    full_periods.append(header_str)
                    st.write(f"🔍 **Found year in DataFrame header:** {header_str}")
        
        # Second try: Look for period patterns in DataFrame data rows
        if not full_periods:
            st.write(f"🔍 **Searching DataFrame data for period patterns...**")
            for row_idx in range(min(5, len(df))):
                row_data = df.iloc[row_idx].tolist()
                for cell in row_data:
                    cell_str = str(cell).strip()
                    # Look for date patterns like "April 30, 2024" or "January 31, 2024"
                    date_matches = re.findall(r'([A-Za-z]+ \d{1,2},?\s*\d{4})', cell_str)
                    for date_match in date_matches:
                        # Try to construct period descriptions
                        if "April 30" in date_match:
                            period_desc = f"Three Months Ended {date_match}"
                            if period_desc not in full_periods:
                                full_periods.append(period_desc)
                                st.write(f"🔍 **Constructed period from data:** {period_desc}")
                        elif "January 31" in date_match:
                            period_desc = f"Three Months Ended {date_match}"
                            if period_desc not in full_periods:
                                full_periods.append(period_desc)
                                st.write(f"🔍 **Constructed period from data:** {period_desc}")
        
        # Third try: parse raw HTML for complete period descriptions
        if not full_periods:
            st.write(f"🔍 **Trying HTML parsing for periods...**")
            st.write(f"🔍 **Raw HTML sample:** {raw_table_text[:200]}...")
            full_periods = _parse_html_for_periods(raw_table_text, df, st)
        
        # Fourth try: check original headers for period patterns
        if not full_periods:
            st.write(f"🔍 **Trying original headers for periods...**")
            full_periods = _extract_periods_from_headers(table_context, df, st)
        
        # Use extracted periods or create fallback
        if full_periods:
            period_headers = full_periods
            st.write(f"🔍 **Final Period Descriptions Found:** {period_headers}")
        else:
            period_headers = [f"Period_{i+1}" for i in range(len(df.columns[1:]))]
            st.write(f"🔍 **Generic Period Fallback:** {period_headers}")
            
    except Exception as e:
        st.write(f"🔍 **Period Detection Error:** {str(e)}")
        period_headers = [f"Period_{i+1}" for i in range(len(df.columns[1:]))]
    
    return period_headers


def _parse_html_for_periods(raw_html, df, st):
    """Parse HTML to find period descriptions"""
    full_periods = []
    
    try:
        # Find the position of the first data row in the HTML
        first_row_content = None
        if len(df) > 0:
            first_row = df.iloc[0]
            for cell in first_row:
                cell_str = str(cell).strip()
                if cell_str and cell_str != 'nan' and len(cell_str) > 2:
                    first_row_content = cell_str
                    break
        
        if first_row_content:
            row_position = raw_html.find(first_row_content)
            if row_position > 0:
                start_pos = max(0, row_position - 500)
                search_text = raw_html[start_pos:row_position + 100]
            else:
                search_text = raw_html[:500] if len(raw_html) > 500 else raw_html
        else:
            search_text = raw_html[:500] if len(raw_html) > 500 else raw_html
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(search_text, 'html.parser')
        all_text = soup.get_text()
        
        # Look for complete period descriptions with dates
        period_patterns = [
            r'Three Months Ended [A-Za-z]+ \d{1,2},?\s*\d{4}',
            r'Six Months Ended [A-Za-z]+ \d{1,2},?\s*\d{4}',
            r'Nine Months Ended [A-Za-z]+ \d{1,2},?\s*\d{4}',
            r'Twelve Months Ended [A-Za-z]+ \d{1,2},?\s*\d{4}',
            r'Year Ended [A-Za-z]+ \d{1,2},?\s*\d{4}',
            r'Quarter Ended [A-Za-z]+ \d{1,2},?\s*\d{4}'
        ]
        
        for pattern in period_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                if match not in full_periods:
                    full_periods.append(match)
                    st.write(f"🔍 **Found complete period: {match}")
        
    except Exception as e:
        st.write(f"🔍 **HTML Parsing Error:** {str(e)}")
    
    return full_periods

def _extract_periods_from_headers(table_context, df, st):
    """Extract periods from table headers"""
    full_periods = []
    period_headers_found = []
    year_headers = []
    
    if 'headers' in table_context:
        for header in table_context['headers']:
            header_str = str(header).strip()
            
            # Look for period descriptions
            if re.search(r'(Three|Six|Nine|Twelve|One|Two|Four|Five|Seven|Eight|Ten|Eleven)\s+Months?\s+Ended|Years?\s+Ended|Quarter\s+Ended', header_str, re.IGNORECASE):
                period_headers_found.append(header_str)
                st.write(f"🔍 **Found Period Header:** {header_str}")
            
            # Look for year headers
            elif re.match(r'^\s*20\d{2}\s*$', header_str):
                year_headers.append(header_str)
                st.write(f"🔍 **Found Year Header:** {header_str}")
        
        # Check DataFrame rows for years
        for row_idx in range(min(3, len(df))):
            row_data = df.iloc[row_idx].tolist()
            for cell in row_data[1:]:
                cell_str = str(cell).strip()
                if re.match(r'^\s*20\d{2}\s*$', cell_str):
                    year_headers.append(cell_str)
        
        # Combine period headers with years
        if period_headers_found and year_headers:
            years_per_period = len(year_headers) // len(period_headers_found)
            period_counter = 1
            
            for period_header in period_headers_found:
                start_idx = (period_headers_found.index(period_header)) * years_per_period
                end_idx = start_idx + years_per_period
                period_years = year_headers[start_idx:end_idx]
                
                for year in period_years:
                    combined_period = f"{period_header} {year}"
                    full_periods.append(combined_period)
                    st.write(f"🔍 **Combined Period {period_counter}:** {combined_period}")
                    period_counter += 1
        
        # If we found period headers but no years, try to extract years from DataFrame data
        elif period_headers_found and not year_headers:
            st.write(f"🔍 **Found period headers but no years, checking DataFrame data...**")
            # Look for years in the first few rows of data
            for row_idx in range(min(5, len(df))):
                row_data = df.iloc[row_idx].tolist()
                for cell in row_data[1:]:  # Skip first column (line items)
                    cell_str = str(cell).strip()
                    # Look for 4-digit years
                    year_matches = re.findall(r'\b(20\d{2})\b', cell_str)
                    for year in year_matches:
                        if year not in year_headers:
                            year_headers.append(year)
                            st.write(f"🔍 **Found Year in DataFrame data:** {year}")
            
            # Now try to combine again
            if year_headers:
                years_per_period = len(year_headers) // len(period_headers_found)
                period_counter = 1
                
                for period_header in period_headers_found:
                    start_idx = (period_headers_found.index(period_header)) * years_per_period
                    end_idx = start_idx + years_per_period
                    period_years = year_headers[start_idx:end_idx]
                    
                    for year in period_years:
                        combined_period = f"{period_header} {year}"
                        full_periods.append(combined_period)
                        st.write(f"🔍 **Combined Period {period_counter}:** {combined_period}")
                        period_counter += 1
    
    return full_periods

def _group_columns_by_periods(data_columns, period_headers, st):
    """Group data columns by periods"""
    num_periods = len(period_headers)
    
    if num_periods > 0 and len(data_columns) >= num_periods:
        cols_per_period = len(data_columns) // num_periods
        
        # If we have exactly 2x the periods in columns, assume pairs (amount + symbol)
        if len(data_columns) == num_periods * 2:
            cols_per_period = 2
        elif len(data_columns) == num_periods:
            cols_per_period = 1
        
        column_groups = []
        for i in range(num_periods):
            start_idx = i * cols_per_period
            end_idx = min(start_idx + cols_per_period, len(data_columns))
            
            period_cols = data_columns[start_idx:end_idx]
            column_groups.append(period_cols)
            st.write(f"   Period {i+1} ({period_headers[i] if i < len(period_headers) else f'Period_{i+1}'}): {period_cols}")
    else:
        # Fallback: create exactly 2 periods by splitting columns in half
        column_groups = []
        mid_point = len(data_columns) // 2
        
        column_groups.append(data_columns[:mid_point])
        column_groups.append(data_columns[mid_point:])
        
        st.write(f"   Fallback: Split {len(data_columns)} columns into 2 periods")
    
    return column_groups

def _merge_column_groups(df, column_groups, period_headers, st):
    """Merge columns within each group"""
    merged_columns = []
    
    for group_idx, group in enumerate(column_groups):
        if len(group) == 1:
            # Single column, use proper period header
            col_name = period_headers[group_idx] if group_idx < len(period_headers) else f"Period_{group_idx + 1}"
            values = df[group[0]].fillna('').astype(str).tolist()
            merged_columns.append((col_name, values))
        else:
            # Multiple columns, merge them by combining numeric values and symbols
            merged_values = []
            for row_idx in range(len(df)):
                # Separate numeric values from symbols across all columns in group
                numeric_values = []
                symbols = []
                
                for col in group:
                    val = str(df.iloc[row_idx][col]).strip()
                    if val and val not in ['', 'nan', 'NaN']:
                        # Check if it's a symbol (like $, %)
                        if val in ['$', '%', '(', ')']:
                            symbols.append(val)
                        # Check if it contains numbers
                        elif any(c.isdigit() for c in val):
                            clean_val = re.sub(r'[^\d\.\-\(\),]', '', val)
                            if clean_val:
                                numeric_values.append(clean_val)
                        else:
                            numeric_values.append(val)
                
                # Combine: symbols + numeric values
                if numeric_values:
                    final_value = numeric_values[0]
                    if '$' in symbols:
                        final_value = '$' + final_value if not final_value.startswith('$') else final_value
                    if '%' in symbols:
                        final_value = final_value + '%' if not final_value.endswith('%') else final_value
                    if '(' in symbols and ')' in symbols:
                        final_value = f"({final_value})" if not (final_value.startswith('(') and final_value.endswith(')')) else final_value
                else:
                    final_value = ''
                
                merged_values.append(final_value)
            
            # Use period names if available
            if group_idx < len(period_headers):
                col_name = period_headers[group_idx]
            else:
                col_name = f"Period_{group_idx + 1}"
            merged_columns.append((col_name, merged_values))
    
    return merged_columns

def _create_final_data_structure(df, merged_columns):
    """Create final data structure from merged columns"""
    # Create new dataframe with merged columns
    new_data = {df.columns[0]: df[df.columns[0]]}  # Keep line items column
    periods = []
    
    for col_name, values in merged_columns:
        new_data[col_name] = values
        periods.append(col_name)
    
    df = pd.DataFrame(new_data)
    
    data = {}
    for idx, row in df.iterrows():
        line_item = str(row[df.columns[0]]).strip()
        if line_item and line_item != 'nan':
            values = []
            for col in df.columns[1:]:
                val = str(row[col]).strip()
                if val == 'nan':
                    val = ''
                else:
                    val = re.sub(r'[^\w\s\.\-]', '', val).strip()
                values.append(val)
            
            if any(v for v in values if v):
                data[line_item] = values
    
    return periods, data
