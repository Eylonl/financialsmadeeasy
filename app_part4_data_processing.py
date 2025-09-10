"""
Part 4: Data Processing and Export Logic
"""

# Import required modules
import streamlit as st
from datetime import datetime
import copy

# This code assumes the following variables are available from previous parts:
# all_financial_data, st, status_text, progress_bar, remove_duplicates, 
# exporter, ticker, include_raw_data, total_tokens_used, total_cost, model

# Check if all_financial_data exists and has content
# Debug the data state
with st.expander("🔍 Debug: Data Processing State", expanded=False):
    st.write(f"all_financial_data exists: {'all_financial_data' in globals()}")
    if 'all_financial_data' in globals():
        st.write(f"Type: {type(all_financial_data)}")
        st.write(f"Content: {all_financial_data}")
        st.write(f"Boolean value: {bool(all_financial_data)}")
        if all_financial_data:
            for ticker, filings in all_financial_data.items():
                st.write(f"Ticker {ticker}: {len(filings)} filings")
                for i, filing in enumerate(filings):
                    st.write(f"  Filing {i}: {list(filing.keys())}")

# Check if we have any extracted data
has_data = False
if 'all_financial_data' in globals() and all_financial_data:
    for ticker, filings in all_financial_data.items():
        for filing in filings:
            for key in ['income_statement', 'balance_sheet', 'cash_flow', 'gaap_reconciliation', 'sbc_breakdown']:
                if key in filing and filing[key].get('data'):
                    has_data = True
                    break
            if has_data:
                break
        if has_data:
            break

if has_data:
    # Step 4: Keep raw data separate, only apply duplicate removal to reconciliation data
    status_text.text("📊 Preparing data for export...")
    progress_bar.progress(80)

    # Store raw data separately (no duplicate removal)
    raw_financial_data = copy.deepcopy(all_financial_data)

    # Create processed data for reconciliation (with duplicate removal if enabled)
    processed_financial_data = all_financial_data
    if remove_duplicates:
        # Only apply duplicate removal for processed data used in reconciliation
        processed_financial_data = remove_duplicate_periods(all_financial_data)

    # Step 4.5: Skip standardization - ChatGPT will handle merging in Excel export
    progress_bar.progress(85)

    # Skip standardization and filing links - proceed directly to Excel export

    # Step 6: Export to Excel
    status_text.text("📊 Creating Excel export...")
    progress_bar.progress(90)

    excel_data = exporter.export_to_excel(processed_financial_data, ticker, include_raw_data, raw_financial_data)

    # Collect token usage from Excel exporter
    if hasattr(exporter, 'last_token_usage') and exporter.last_token_usage:
        usage = exporter.last_token_usage
        total_tokens_used += usage.get('total_tokens', 0)
        
        # Calculate cost based on model (use model from previous parts or fallback)
        usage_model = usage.get('model', model if 'model' in globals() else 'gpt-4')
        if usage_model == 'gpt-4':
            input_cost = usage.get('prompt_tokens', 0) * 0.03 / 1000
            output_cost = usage.get('completion_tokens', 0) * 0.06 / 1000
        elif usage_model == 'gpt-4o-mini':
            input_cost = usage.get('prompt_tokens', 0) * 0.00015 / 1000
            output_cost = usage.get('completion_tokens', 0) * 0.0006 / 1000
        else:
            input_cost = usage.get('prompt_tokens', 0) * 0.01 / 1000
            output_cost = usage.get('completion_tokens', 0) * 0.03 / 1000
        
        total_cost += input_cost + output_cost

    # Step 7: Show results
    progress_bar.progress(100)
    status_text.text("✅ Extraction complete!")

    # Display summary with token usage
    st.success(f"🎉 Successfully extracted financial data for {ticker}!")

    total_filings = sum(len(filings) for filings in all_financial_data.values())

    # Create columns for summary and token usage
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"📈 **Summary:** Processed {total_filings} filing(s)")

    with col2:
        if total_tokens_used > 0:
            st.write(f"🔢 **OpenAI Usage:**")
            st.write(f"   • Tokens: {total_tokens_used:,}")
            st.write(f"   • Cost: ${total_cost:.4f}")
        else:
            st.write("🚀 **No OpenAI tokens used!**")

    # Download button
    st.download_button(
        label="📥 Download Excel File",
        data=excel_data,
        file_name=f"{ticker}_financial_statements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.error("❌ No financial statement data could be extracted from the filings.")
    
    # Show troubleshooting info
    with st.expander("🔍 Debug: Why no financial data extracted?", expanded=True):
        st.write("**Possible reasons:**")
        st.write("1. The 8-K earnings release doesn't contain full financial statements")
        st.write("2. The financial data is in a format the AI can't parse")
        st.write("3. The content is mostly text narrative rather than tabular data")
        st.write("4. The OpenAI API key may not be working")
        st.write("**Suggestion:** Try a different quarter or check the exhibit content manually")
