"""
Part 1: Imports and Utility Functions
"""
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import re
import openai
import json
from typing import Dict, List, Any, Optional
import traceback
from dotenv import load_dotenv
from sec_edgar import SECEdgar
from excel_exporter import ExcelExporter
from exhibit_99_1_extractor import Exhibit99Extractor
from period_utils import extract_period_end_date, is_cumulative_overlap, get_period_priority

# Load environment variables from .env file
load_dotenv()

def remove_duplicate_periods(all_financial_data):
    """Remove duplicate periods, keeping the most recent filing data for each period and avoiding cumulative period overlaps"""
    for ticker, filings_list in all_financial_data.items():
        # Combine all data across filings for each statement type
        combined_statements = {}
        
        # Sort filings by date (most recent first) 
        filings_list.sort(key=lambda x: x['filing_date'], reverse=True)
        
        # Collect all filing link debug info for single expander
        filing_link_debug_info = []
        
        for statement_type in ['income_statement', 'balance_sheet', 'cash_flow', 'gaap_reconciliation', 'sbc_breakdown']:
            seen_periods = set()
            seen_end_dates = set()  # Track end dates to avoid cumulative overlaps
            combined_periods = []
            combined_data = {}
            combined_filing_links = {}  # Track 8-K links for each period
            
            # Process each filing in order (most recent first)
            for filing in filings_list:
                if statement_type in filing:
                    data = filing[statement_type]
                    periods = data.get('periods', [])
                    
                    # Sort periods by priority (quarterly first, then cumulative)
                    period_data = [(period, i, get_period_priority(period)) for i, period in enumerate(periods)]
                    period_data.sort(key=lambda x: x[2])  # Sort by priority
                    
                    for period, original_index, priority in period_data:
                        # Extract end date from period (e.g., "Three Months Ended March 31, 2024")
                        period_end_date = extract_period_end_date(period)
                        
                        # Skip if we've already seen this exact period or this end date
                        if period not in seen_periods and period_end_date not in seen_end_dates:
                            # Check if this is a cumulative period that overlaps with existing data
                            if not is_cumulative_overlap(period, seen_end_dates):
                                seen_periods.add(period)
                                if period_end_date:
                                    seen_end_dates.add(period_end_date)
                                combined_periods.append(period)
                                
                                # Add 8-K filing link for this period if available
                                filing_links = data.get('filing_links', {})
                                if period in filing_links:
                                    combined_filing_links[period] = filing_links[period]
                                    filing_link_debug_info.append({
                                        'statement_type': statement_type,
                                        'period': period,
                                        'url': filing_links[period]
                                    })
                                
                                # Initialize data arrays for all line items from this filing
                                for line_item in data.get('data', {}).keys():
                                    if line_item not in combined_data:
                                        combined_data[line_item] = [None] * len(combined_periods)
                                
                                # Add data for this period - use the position in combined_periods, not original index
                                new_period_index = len(combined_periods) - 1
                                for line_item, values in data.get('data', {}).items():
                                    if line_item not in combined_data:
                                        combined_data[line_item] = [None] * len(combined_periods)
                                    
                                    # Ensure the array is long enough
                                    while len(combined_data[line_item]) <= new_period_index:
                                        combined_data[line_item].append(None)
                                    
                                    # Map the value from the original filing to the correct position in combined data
                                    if isinstance(values, list) and original_index < len(values):
                                        combined_data[line_item][new_period_index] = values[original_index]
                                    elif not isinstance(values, list):
                                        combined_data[line_item][new_period_index] = values
                                    else:
                                        combined_data[line_item][new_period_index] = None
            
            # Store combined statement if we have data
            if combined_periods:
                combined_statements[statement_type] = {
                    'periods': combined_periods,
                    'data': combined_data,
                    'filing_links': combined_filing_links
                }
        
        # Show consolidated filing link debug info
        if filing_link_debug_info:
            try:
                import streamlit as st
                with st.expander("🔗 Debug: Filing Links Preserved", expanded=False):
                    st.write(f"**Preserved {len(filing_link_debug_info)} filing links for {ticker}:**")
                    for info in filing_link_debug_info:
                        st.write(f"• {info['statement_type']}: {info['period']} → {info['url']}")
            except:
                pass
        
        # Replace the filings list with a single combined filing
        if combined_statements:
            combined_filing = {'filing_date': filings_list[0]['filing_date']}
            combined_filing.update(combined_statements)
            all_financial_data[ticker] = [combined_filing]
        else:
            all_financial_data[ticker] = []
    
    return all_financial_data

# Placeholder functions for period utilities
def get_period_priority(period):
    """Get priority for period sorting"""
    if 'three months' in period.lower():
        return 1
    elif 'six months' in period.lower():
        return 2
    elif 'nine months' in period.lower():
        return 3
    elif 'twelve months' in period.lower() or 'year' in period.lower():
        return 4
    else:
        return 5

def extract_period_end_date(period):
    """Extract end date from period string"""
    import re
    from datetime import datetime
    
    # Look for date patterns like "March 31, 2024"
    date_pattern = r'(\w+)\s+(\d{1,2}),\s+(\d{4})'
    match = re.search(date_pattern, period)
    if match:
        month_name, day, year = match.groups()
        try:
            date_obj = datetime.strptime(f"{month_name} {day}, {year}", "%B %d, %Y")
            return date_obj.strftime("%Y-%m-%d")
        except:
            pass
    return None

def is_cumulative_overlap(period, seen_end_dates):
    """Check if period overlaps with existing cumulative periods"""
    period_lower = period.lower()
    if 'six months' in period_lower or 'nine months' in period_lower or 'twelve months' in period_lower:
        # This is a cumulative period, check for overlaps
        period_end_date = extract_period_end_date(period)
        if period_end_date:
            # Simple overlap check - if we've seen this end date, it's an overlap
            return period_end_date in seen_end_dates
    return False
