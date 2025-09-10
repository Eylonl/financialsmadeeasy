"""
Part 2: Main UI and Configuration
"""
import streamlit as st
import os
from sec_edgar import SECEdgar
from excel_exporter import ExcelExporter

# Page configuration - only set if not already configured
try:
    st.set_page_config(
        page_title="Financial Statements Extractor",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
except:
    pass  # Page config already set

def main():
    st.title("📊 Financial Statements Extractor")
    st.markdown("Extract Income Statement, Balance Sheet, and Cash Flow Statement from SEC 10-K/10-Q filings")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")
        st.info("Copy `.env.template` to `.env` and add your OpenAI API key.")
        return
    
    # Input section
    ticker_or_cik = st.text_input(
        "Enter Stock Ticker or CIK (e.g., MSFT or 0000789019)",
        "AAPL",
        help="Enter either a stock ticker (e.g., MSFT) or a 10-digit CIK code (e.g., 0000789019)"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        model = st.selectbox(
            "OpenAI Model",
            options=["gpt-4o-mini", "gpt-4", "gpt-4-turbo"],
            index=0,
            help="Select the OpenAI model for extraction. GPT-4o-mini is faster and cheaper."
        )
    
    st.info("🚀 Using Enhanced 8-K Exhibit 99.1 Extraction Pipeline - Complete table extraction with reconciliation scoring")

    # Time period selection
    st.subheader("Time Period")
    year_input = st.text_input("How many years back to search for filings? (Leave blank for most recent only)", "")
    quarter_input = st.text_input("OR enter specific quarter (e.g., 2Q25, Q4FY24)", "")
    
    remove_duplicates = st.toggle("Remove duplicate periods", value=True, help="Remove duplicate periods across different filings, keeping the most recent data")
    include_raw_data = st.checkbox("Include Raw Data tab (before AI cleaning)", value=False, 
                                  help="Adds a separate tab with the original extracted data before AI cleaning and merging")
    
    # Data extraction selection
    st.subheader("Select Data to Extract")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        extract_income = st.checkbox("Income Statement", value=True)
        extract_balance = st.checkbox("Balance Sheet", value=True)
    
    with col2:
        extract_cash_flow = st.checkbox("Cash Flow Statement", value=True)
        extract_sbc = st.checkbox("Stock-Based Compensation", value=True)
    
    with col3:
        extract_gaap = st.checkbox("GAAP to Non-GAAP Reconciliation", value=True)
        
    # Exhibit 99.1 extraction options
    st.info("📋 Enhanced extraction will analyze all tables from 8-K filings with reconciliation scoring")
    
    # Reconciliation threshold
    recon_threshold = st.number_input(
        "Reconciliation Score Threshold", 
        min_value=0.0, 
        max_value=1000.0, 
        value=100.0, 
        step=10.0,
        help="Minimum score required for a table to be considered a reconciliation candidate"
    )
    
    # Extract button
    if st.button("🚀 Extract Financial Statements", type="primary", use_container_width=True):
        if not ticker_or_cik:
            st.error("Please enter a stock ticker symbol or CIK.")
            return
        
        # Check if at least one data type is selected
        if not any([extract_income, extract_balance, extract_cash_flow, extract_sbc, extract_gaap]):
            st.error("Please select at least one type of data to extract.")
            return
        
        # Build statement_types list based on selections
        statement_types = []
        if extract_income:
            statement_types.append('income_statement')
        if extract_balance:
            statement_types.append('balance_sheet')
        if extract_cash_flow:
            statement_types.append('cash_flow')
        if extract_sbc:
            statement_types.append('sbc_breakdown')
        if extract_gaap:
            statement_types.append('gaap_reconciliation')
        
        # Parse input - determine if it's a ticker or CIK
        user_input = ticker_or_cik.upper().strip()
        
        def is_cik_format(s):
            return s.isdigit() and len(s) == 10
        
        if is_cik_format(user_input):
            cik = user_input
            ticker = user_input  # Use CIK as ticker for processing
            st.info(f"Using CIK {cik}")
        elif user_input.isalnum():
            ticker = user_input
            cik = None  # Will be looked up by edgar module
        else:
            st.error("Please enter a valid ticker (e.g., MSFT) or 10-digit CIK (e.g., 0000789019).")
            return
        
        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Initialize components
            edgar = SECEdgar()
            exporter = ExcelExporter()
            
            # Initialize token tracking
            total_tokens_used = 0
            total_cost = 0.0
            
            # Initialize Exhibit 99.1 extractor
            from exhibit_99_1_extractor import Exhibit99Extractor
            exhibit_extractor = Exhibit99Extractor("test_outputs")
            
            # Step 1: Get company CIK
            status_text.text("🔍 Looking up company information...")
            progress_bar.progress(10)
            
            cik = edgar.get_company_cik(ticker)
            if not cik:
                st.error(f"❌ Could not find company with ticker '{ticker}'. Please verify the ticker symbol.")
                return
            
            st.info(f"✅ Found CIK: {cik} for ticker: {ticker}")
            
            # Debug: Show the exact parameters being passed
            with st.expander("🔧 Debug Parameters", expanded=False):
                st.write(f"- Ticker: {ticker}")
                st.write(f"- CIK: {cik}")
                st.write(f"- Year Input: '{year_input}'")
                st.write(f"- Quarter Input: '{quarter_input}'")
                st.write(f"- Model: {model}")
            
            # Step 2: Fetch filings
            status_text.text("📋 Fetching SEC filings...")
            progress_bar.progress(30)
            
            filings = edgar.get_filings_by_timeframe(ticker, year_input, quarter_input)
            if not filings:
                st.warning(f"⚠️ No 8-K earnings releases found for {ticker} in the specified timeframe. Retrying same search...")
                
                # Retry the same exact search
                status_text.text(f"🔄 Retrying search for {ticker}...")
                filings = edgar.get_filings_by_timeframe(ticker, year_input, quarter_input)  # Same exact search
                
                if not filings:
                    st.error(f"❌ No 8-K earnings releases found for {ticker} in the specified timeframe.")
                    
                    # Show debug info when no filings found
                    with st.expander("🔍 Debug: Why no filings found?", expanded=True):
                        st.write("**Troubleshooting steps:**")
                        st.write("1. Check if the ticker is correct")
                        st.write("2. Verify the quarter format (e.g., 1Q24, Q1FY24)")
                        st.write("3. Check if the company had earnings in that quarter")
                        st.write("4. Look at the console output for detailed debug info")
                    return
                else:
                    st.success(f"✅ Found {len(filings)} 8-K earnings releases for {ticker} (retry successful)")
            
            st.success(f"✅ Found {len(filings)} 8-K earnings releases for {ticker}")
            
            # Show debug information about filings
            with st.expander("🔍 Debug: 8-K Earnings Release Details", expanded=False):
                for i, filing in enumerate(filings):
                    st.write(f"**Filing {i+1}: {filing['form']} Earnings Release ({filing['filing_date']})**")
                    st.write(f"- Accession: {filing['accession_number']}")
                    
                    # Show filing URL if content exists
                    if 'content' in filing and filing['content']:
                        # Show the exhibit 99.1 URL (earnings release)
                        exhibit_url = filing.get('exhibit_url', 'N/A')
                        st.write(f"- Earnings Release URL: [View Exhibit 99.1]({exhibit_url})")
                        st.write(f"- Content Length: {len(filing['content']):,} characters")
                        
                        # Show content preview
                        preview = filing['content'][:1000] + "..." if len(filing['content']) > 1000 else filing['content']
                        st.code(preview, language="html")
                        
                        # Show extracted financial tables info
                        if 'financial_tables' in filing:
                            tables = filing['financial_tables']
                            st.write(f"- Extracted Tables: {list(tables.keys())}")
                            for table_name, table_content in tables.items():
                                if table_content:
                                    st.write(f"  - {table_name}: {len(table_content):,} characters")
                                    with st.expander(f"Full {table_name} Content (Debug)", expanded=False):
                                        st.code(table_content, language="html")
                        else:
                            st.write("- ⚠️ No financial tables extracted")
                    else:
                        st.write("- ❌ No content retrieved")
            
            # Execute Part 3: Extraction Logic
            exec_globals = globals()
            exec_locals = locals()
            
            # Ensure all required variables are in the execution context
            exec_locals.update({
                'all_financial_data': {},
                'st': st,
                'status_text': status_text,
                'progress_bar': progress_bar,
                'remove_duplicates': remove_duplicates,
                'exporter': exporter,
                'ticker': ticker,
                'include_raw_data': include_raw_data,
                'total_tokens_used': total_tokens_used,
                'total_cost': total_cost,
                'model': model,
                'filings': filings,
                'statement_types': statement_types
            })
            
            exec(open('app_part3_extraction_logic.py', encoding='utf-8').read(), exec_globals, exec_locals)
            
            # Update globals with any new variables from part 3
            globals().update(exec_locals)
            
            # Execute Part 4: Data Processing with updated context
            exec(open('app_part4_data_processing.py', encoding='utf-8').read(), exec_globals, exec_locals)
            
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
        
        finally:
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
    
    # Execute Part 5: Sidebar
    exec(open('app_part5_sidebar_and_main.py', encoding='utf-8').read())

# Remove duplicate main() call - this is handled by run_app.py
