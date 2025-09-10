"""
Part 5: Sidebar Information and Main Function Entry Point
"""

import streamlit as st

# Sidebar with information
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    This app extracts financial statement data from SEC 10-K and 10-Q filings using:
    
    - **SEC EDGAR API** for filing retrieval
    - **OpenAI GPT-4** for intelligent data extraction
    - **Professional Excel export** with formatting
    
    ### Supported Statements
    - Income Statement
    - Balance Sheet  
    - Cash Flow Statement
    
    ### Output Format
    Excel file with separate sheets for each statement plus a summary sheet.
    """)
    
    st.header("🔧 Setup")
    st.markdown("""
    1. Copy `.env.template` to `.env`
    2. Add your OpenAI API key
    3. Run: `streamlit run app.py`
    """)
    
    st.header("💡 Tips")
    st.markdown("""
    - Use major stock tickers (AAPL, MSFT, GOOGL)
    - "Last Year" typically includes 1 10-K + 3 10-Qs
    - Processing may take 1-2 minutes per company
    - Large companies have more detailed filings
    """)

# Remove duplicate main() call - this is handled by run_app.py
