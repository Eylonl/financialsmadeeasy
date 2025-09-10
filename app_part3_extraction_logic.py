"""
Part 3: Financial Statement Extraction Logic
"""

from extraction_logic import process_financial_extraction

# Execute the extraction logic
all_financial_data = process_financial_extraction(
    filings, statement_types, ticker, exhibit_extractor, recon_threshold, st, status_text, progress_bar
)
